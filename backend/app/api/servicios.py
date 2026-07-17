from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
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

    v = (
        db.query(Vehiculo)
        .filter((Vehiculo.vin == vin) | (Vehiculo.patente == vin))
        .first()
    )
    if not v:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehiculo no registrado (VIN o patente no encontrados)")

    contenido = await archivo.read()
    hash_hex = sha256_bytes(contenido)
    key = f"vehiculos/{v.vin}/service-{int(datetime.now(timezone.utc).timestamp())}-{archivo.filename}"
    url = upload_evidencia(contenido, key, archivo.content_type or "application/octet-stream")

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
    )
    db.add(s)
    db.commit()
    db.refresh(s)

    return {
        "id": str(s.id),
        "tx_hash": s.tx_hash,
        "block_number": s.block_number,
        "hash_evidencia": s.hash_evidencia,
        "archivo_url": s.archivo_url,
    }
