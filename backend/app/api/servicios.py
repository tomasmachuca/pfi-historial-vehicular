from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_concesionaria
from app.models import Concesionaria, Vehiculo, Servicio
from app.services.blockchain import get_blockchain
from app.services.hashing import sha256_bytes
from app.services.security import decrypt_pk
from app.services.storage import upload_evidencia

router = APIRouter(prefix="/servicios", tags=["servicios"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def registrar_service(
    vin: str = Form(...),
    tipo_servicio: int = Form(...),
    kilometraje: int = Form(...),
    descripcion: str | None = Form(None),
    archivo: UploadFile = File(...),
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
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehiculo no registrado (VIN o patente no encontrados)")

    contenido = await archivo.read()
    hash_hex = sha256_bytes(contenido)
    key = f"vehiculos/{v.vin}/service-{int(datetime.now(timezone.utc).timestamp())}-{archivo.filename}"
    url = upload_evidencia(contenido, key, archivo.content_type or "application/octet-stream")

    # Km máximo ya sellado on-chain (alta + services legítimos). Las anomalías previas
    # no cuentan como línea de base: se comparan siempre contra el historial honesto.
    km_max_onchain = (
        db.query(func.max(Servicio.kilometraje))
        .filter(Servicio.vehiculo_id == v.id, Servicio.km_regresivo.is_(False))
        .scalar()
    ) or 0

    # --- Caso anómalo: km regresivo -------------------------------------------
    # El contrato rechaza en cadena un km menor al último (revierte). En vez de
    # descartarlo, lo guardamos off-chain como "mancha" y marcamos vehículo y
    # concesionaria, para que alimente el scoring del historial.
    if kilometraje < km_max_onchain:
        s = Servicio(
            vehiculo_id=v.id,
            concesionaria_id=current.id,
            tipo_servicio=tipo_servicio,
            kilometraje=kilometraje,
            descripcion=descripcion,
            archivo_url=url,
            archivo_nombre=archivo.filename,
            hash_evidencia=hash_hex,
            tx_hash=None,
            block_number=None,
            chain_timestamp=None,
            km_regresivo=True,
            km_anterior=km_max_onchain,
        )
        db.add(s)
        v.anomalias_count = (v.anomalias_count or 0) + 1
        current.anomalias_count = (current.anomalias_count or 0) + 1
        db.commit()
        db.refresh(s)

        diferencia = km_max_onchain - kilometraje
        # Miles con punto (formato AR): formateamos cada número por separado para
        # no tocar las comas de la oración.
        f = lambda n: f"{n:,}".replace(",", ".")
        return {
            "id": str(s.id),
            "km_regresivo": True,
            "km_anterior": km_max_onchain,
            "km_cargado": kilometraje,
            "diferencia": diferencia,
            "hash_evidencia": s.hash_evidencia,
            "archivo_url": s.archivo_url,
            "tx_hash": None,
            "block_number": None,
            "advertencia": (
                f"Kilometraje regresivo: se cargó {f(kilometraje)} km, "
                f"{f(diferencia)} km por debajo del último kilometraje registrado ({f(km_max_onchain)} km). "
                "El service NO se selló en blockchain y quedó marcado como anomalía. "
                "El vehículo y la concesionaria fueron señalados en su historial."
            ),
        }

    # --- Caso normal: se sella en cadena --------------------------------------
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

    s = Servicio(
        vehiculo_id=v.id,
        concesionaria_id=current.id,
        tipo_servicio=tipo_servicio,
        kilometraje=kilometraje,
        descripcion=descripcion,
        archivo_url=url,
        archivo_nombre=archivo.filename,
        hash_evidencia=hash_hex,
        tx_hash=res["tx_hash"],
        block_number=res["block_number"],
        chain_timestamp=res["timestamp"],
        km_regresivo=False,
    )
    db.add(s)
    db.commit()
    db.refresh(s)

    return {
        "id": str(s.id),
        "km_regresivo": False,
        "tx_hash": s.tx_hash,
        "block_number": s.block_number,
        "hash_evidencia": s.hash_evidencia,
        "archivo_url": s.archivo_url,
    }
