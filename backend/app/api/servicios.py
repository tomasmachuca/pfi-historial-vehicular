from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_concesionaria
from app.models import Concesionaria, Servicio, Vehiculo
from app.services.blockchain import get_blockchain
from app.services.hashing import ZERO_HASH_HEX, sha256_bytes
from app.services.security import decrypt_pk
from app.services.storage import upload_evidencia

router = APIRouter(prefix="/servicios", tags=["servicios"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def registrar_service(
    vin: str = Form(...),
    tipo_servicio: int = Form(...),
    kilometraje: int = Form(...),
    descripcion: str | None = Form(None),
    archivo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current: Concesionaria = Depends(get_current_concesionaria),
):
    if tipo_servicio == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tipo 0 reservado para alta")

    ident = vin.strip().upper()
    v = (
        db.query(Vehiculo)
        .filter((func.upper(Vehiculo.vin) == ident) | (func.upper(Vehiculo.patente) == ident))
        .first()
    )
    if not v:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehículo no registrado (VIN o patente no encontrados)")

    # El comprobante es opcional: sin él se sella igual el evento (km, tipo,
    # concesionaria y fecha) con hash cero, y el scoring lo pondera como un
    # registro sin evidencia documental.
    hash_hex = ZERO_HASH_HEX
    url: str | None = None
    archivo_nombre: str | None = None
    if archivo is not None and archivo.filename:
        contenido = await archivo.read()
        if contenido:
            hash_hex = sha256_bytes(contenido)
            key = f"vehiculos/{v.vin}/service-{int(datetime.now(UTC).timestamp())}-{archivo.filename}"
            url = upload_evidencia(contenido, key, archivo.content_type or "application/octet-stream")
            archivo_nombre = archivo.filename

    # Todo service va al contrato, que es quien decide: si el km es menor al último
    # sellado, no lo agrega al historial válido sino que lo sella como anomalía. Así
    # el intento de retroceso queda en cadena y no depende de esta base de datos.
    bc = get_blockchain()
    pk = decrypt_pk(current.wallet_pk_enc)
    try:
        res = bc.registrar_servicio(pk, v.vin, kilometraje, tipo_servicio, hash_hex)
    except Exception as e:
        msg = str(e)
        if "No autorizado. Solo red oficial" in msg:
            ok = bc.es_concesionaria_autorizada(current.wallet_address)
            hint = (
                "La wallet de esta concesionaria no está autorizada en el contrato actual "
                f"({settings.CONTRACT_ADDRESS}, chain {settings.CHAIN_ID}). "
                "Si cambiaste CONTRACT_ADDRESS o redeployaste, usá POST "
                f"/admin/concesionarias/{current.id}/autorizar con X-Admin-Token."
            )
            msg = f"{msg}. On-chain autorizada={ok}. {hint}"
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Error en blockchain: {msg}")

    anomalia = bool(res.get("anomalia"))
    s = Servicio(
        vehiculo_id=v.id,
        concesionaria_id=current.id,
        tipo_servicio=tipo_servicio,
        kilometraje=kilometraje,
        descripcion=descripcion,
        archivo_url=url,
        archivo_nombre=archivo_nombre,
        hash_evidencia=hash_hex,
        tx_hash=res["tx_hash"],
        block_number=res["block_number"],
        chain_timestamp=res["timestamp"],
        km_regresivo=anomalia,
        km_anterior=res.get("km_vigente") if anomalia else None,
    )
    db.add(s)
    if anomalia:
        v.anomalias_count = (v.anomalias_count or 0) + 1
        current.anomalias_count = (current.anomalias_count or 0) + 1
    db.commit()
    db.refresh(s)

    respuesta = {
        "id": str(s.id),
        "km_regresivo": anomalia,
        "tx_hash": s.tx_hash,
        "block_number": s.block_number,
        "hash_evidencia": s.hash_evidencia,
        "archivo_url": s.archivo_url,
        "con_evidencia": url is not None,
    }
    if not anomalia:
        return respuesta

    km_vigente = res["km_vigente"]
    diferencia = km_vigente - kilometraje

    # Miles con punto (formato AR): formateamos cada número por separado para
    # no tocar las comas de la oración.
    def f(n):
        return f"{n:,}".replace(",", ".")

    respuesta.update({
        "km_anterior": km_vigente,
        "km_cargado": kilometraje,
        "diferencia": diferencia,
        "advertencia": (
            f"Kilometraje regresivo: se cargó {f(kilometraje)} km, "
            f"{f(diferencia)} km por debajo del último kilometraje registrado ({f(km_vigente)} km). "
            "El contrato no lo agregó al historial válido: lo selló en blockchain como anomalía, "
            "que queda visible en forma permanente en el historial público del vehículo."
        ),
    })
    return respuesta
