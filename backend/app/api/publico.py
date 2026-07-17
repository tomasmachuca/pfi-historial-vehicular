from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Concesionaria, Servicio, TipoServicio, Vehiculo
from app.services.blockchain import get_blockchain

router = APIRouter(prefix="/publico", tags=["publico"])


@router.get("/red")
def estado_red():
    return get_blockchain().info_red()


@router.get("/vehiculo/{identificador}")
def consulta_publica(identificador: str, db: Session = Depends(get_db)):
    v = (
        db.query(Vehiculo)
        .filter((Vehiculo.vin == identificador) | (Vehiculo.patente == identificador))
        .first()
    )
    if not v:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehiculo no encontrado")

    bc = get_blockchain()
    on_chain = bc.obtener_historial(v.vin)
    info_chain = bc.info_vehiculo(v.vin) or {}

    servicios_db = (
        db.query(Servicio)
        .filter(Servicio.vehiculo_id == v.id)
        .order_by(Servicio.kilometraje.asc(), Servicio.creado_en.asc())
        .all()
    )

    tipos = {t.codigo: t.nombre for t in db.query(TipoServicio).all()}
    nombres_conces = {
        c.wallet_address.lower(): c.nombre for c in db.query(Concesionaria).all()
    }

    eventos = []
    for i, ev in enumerate(on_chain):
        s_db = servicios_db[i] if i < len(servicios_db) else None
        chain_dt = datetime.fromtimestamp(ev["timestamp"], tz=timezone.utc).isoformat()
        eventos.append({
            "kilometraje": ev["kilometraje"],
            "tipo_servicio": ev["tipoServicio"],
            "tipo_nombre": tipos.get(ev["tipoServicio"], f"Tipo {ev['tipoServicio']}"),
            "hash_evidencia": ev["hashEvidencia"],
            "concesionaria_address": ev["concesionaria"],
            "concesionaria_nombre": nombres_conces.get(
                ev["concesionaria"].lower(), "Concesionaria oficial"
            ),
            "chain_timestamp": chain_dt,
            "descripcion": s_db.descripcion if s_db else None,
            "archivo_url": s_db.archivo_url if s_db else None,
            "tx_hash": s_db.tx_hash if s_db else None,
            "block_number": s_db.block_number if s_db else None,
        })

    return {
        "vehiculo": {
            "vin": v.vin,
            "patente": v.patente,
            "marca": v.marca,
            "modelo": v.modelo,
            "anio": v.anio,
            "color": v.color,
            "km_inicial": v.km_inicial,
            "creado_en": v.creado_en.isoformat() if v.creado_en else None,
        },
        "eventos": eventos,
        "cadena": {
            "verificado": bool(info_chain),
            "tx_hash_alta": v.tx_hash_alta,
            "contrato": bc.address,
            "chain_id": bc.w3.eth.chain_id,
            "cantidad_eventos_on_chain": len(on_chain),
        },
    }


@router.get("/stats")
def stats_globales(db: Session = Depends(get_db)):
    total_vehiculos = db.query(Vehiculo).count()
    total_servicios = db.query(Servicio).count()
    total_conces = db.query(Concesionaria).filter(Concesionaria.activa.is_(True)).count()
    return {
        "vehiculos_registrados": total_vehiculos,
        "servicios_registrados": total_servicios,
        "concesionarias_activas": total_conces,
    }
