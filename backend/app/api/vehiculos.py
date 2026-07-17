from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.dependencies import get_current_concesionaria
from app.models import Concesionaria, Vehiculo, Servicio
from app.schemas.vehiculo import VehiculoPublic
from app.services.blockchain import get_blockchain
from app.services.hashing import sha256_bytes
from app.services.security import decrypt_pk
from app.services.storage import upload_evidencia

router = APIRouter(prefix="/vehiculos", tags=["vehiculos"])


ZERO_HASH_HEX = "0" * 64


@router.post("", response_model=VehiculoPublic, status_code=status.HTTP_201_CREATED)
async def alta_vehiculo(
    vin: str = Form(...),
    patente: str = Form(..., min_length=1),
    marca: str = Form(...),
    modelo: str = Form(...),
    anio: int = Form(...),
    color: str | None = Form(None),
    km_inicial: int = Form(0),
    archivo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current: Concesionaria = Depends(get_current_concesionaria),
):
    patente = patente.strip()
    if not patente:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La patente es obligatoria")

    if db.query(Vehiculo).filter(Vehiculo.vin == vin).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "VIN ya registrado")
    if db.query(Vehiculo).filter(Vehiculo.patente == patente).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Patente ya registrada")

    bc = get_blockchain()

    # Falla rápida si la wallet no está autorizada en el contrato.
    if not bc.es_concesionaria_autorizada(current.wallet_address):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "La wallet de la concesionaria no está autorizada en el contrato. "
            "Pedile al administrador que ejecute /admin/concesionarias/{id}/autorizar.",
        )

    hash_hex = ZERO_HASH_HEX
    archivo_url: str | None = None
    archivo_nombre: str | None = None
    if archivo is not None and archivo.filename:
        contenido = await archivo.read()
        if contenido:
            hash_hex = sha256_bytes(contenido)
            key = f"vehiculos/{vin}/alta-{int(datetime.now(timezone.utc).timestamp())}-{archivo.filename}"
            archivo_url = upload_evidencia(
                contenido, key, archivo.content_type or "application/octet-stream"
            )
            archivo_nombre = archivo.filename

    pk = decrypt_pk(current.wallet_pk_enc)
    try:
        res = bc.registrar_vehiculo(pk, vin, km_inicial, hash_hex)
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Error en blockchain: {e}")

    v = Vehiculo(
        vin=vin,
        patente=patente,
        marca=marca,
        modelo=modelo,
        anio=anio,
        color=color,
        concesionaria_alta_id=current.id,
        km_inicial=km_inicial,
        tx_hash_alta=res["tx_hash"],
    )
    db.add(v)
    db.flush()

    s = Servicio(
        vehiculo_id=v.id,
        concesionaria_id=current.id,
        tipo_servicio=0,
        kilometraje=km_inicial,
        descripcion="Alta 0km",
        archivo_url=archivo_url,
        archivo_nombre=archivo_nombre,
        hash_evidencia=hash_hex,
        tx_hash=res["tx_hash"],
        block_number=res["block_number"],
        chain_timestamp=res["timestamp"],
    )
    db.add(s)
    db.commit()
    db.refresh(v)

    return VehiculoPublic(
        id=str(v.id),
        vin=v.vin,
        patente=v.patente,
        marca=v.marca,
        modelo=v.modelo,
        anio=v.anio,
        color=v.color,
        km_inicial=v.km_inicial,
        tx_hash_alta=v.tx_hash_alta,
        creado_en=v.creado_en,
    )


@router.get("/mios", response_model=list[VehiculoPublic])
def listar_mios(
    db: Session = Depends(get_db),
    current: Concesionaria = Depends(get_current_concesionaria),
):
    items = (
        db.query(Vehiculo)
        .filter(Vehiculo.concesionaria_alta_id == current.id)
        .order_by(Vehiculo.creado_en.desc())
        .all()
    )
    return [
        VehiculoPublic(
            id=str(v.id),
            vin=v.vin,
            patente=v.patente,
            marca=v.marca,
            modelo=v.modelo,
            anio=v.anio,
            color=v.color,
            km_inicial=v.km_inicial,
            tx_hash_alta=v.tx_hash_alta,
            creado_en=v.creado_en,
        )
        for v in items
    ]
