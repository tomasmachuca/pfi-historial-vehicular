from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
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
    ident = identificador.strip().upper()
    v = (
        db.query(Vehiculo)
        .filter(
            (func.upper(Vehiculo.vin) == ident) | (func.upper(Vehiculo.patente) == ident)
        )
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
    conces = db.query(Concesionaria).all()
    conces_by_id = {c.id: c for c in conces}

    # Km de los eventos realmente sellados en el contrato ACTUAL (multiconjunto).
    # Se usa para marcar cada service de la DB como verificado o no: si el vehículo
    # se registró contra un contrato anterior, sus tx viejas no cuentan.
    on_chain_kms = {}
    for ev in on_chain:
        on_chain_kms[ev["kilometraje"]] = on_chain_kms.get(ev["kilometraje"], 0) + 1

    # Armamos el timeline desde la DB (registro completo). La cadena solo confirma.
    eventos = []
    for s in servicios_db:
        c = conces_by_id.get(s.concesionaria_id)
        # Verificado = no es anomalía, tiene tx y hay un evento on-chain con ese km.
        verificado = False
        if not s.km_regresivo and s.tx_hash and on_chain_kms.get(s.kilometraje, 0) > 0:
            on_chain_kms[s.kilometraje] -= 1
            verificado = True
        eventos.append({
            "kilometraje": s.kilometraje,
            "tipo_servicio": s.tipo_servicio,
            "tipo_nombre": tipos.get(s.tipo_servicio, f"Tipo {s.tipo_servicio}"),
            "hash_evidencia": s.hash_evidencia,
            "concesionaria_address": c.wallet_address if c else None,
            "concesionaria_nombre": c.nombre if c else "Concesionaria",
            "chain_timestamp": s.chain_timestamp.isoformat() if s.chain_timestamp else None,
            "descripcion": s.descripcion,
            "archivo_url": s.archivo_url,
            "tx_hash": s.tx_hash,
            "block_number": s.block_number,
            "km_regresivo": s.km_regresivo,
            "km_anterior": s.km_anterior,
            "verificado": verificado,
            "_orden": s.creado_en,
        })
    anomalias = [s for s in servicios_db if s.km_regresivo]

    # Orden cronológico por fecha de carga; las anomalías se intercalan donde ocurrieron.
    _min_dt = datetime.min.replace(tzinfo=timezone.utc)
    eventos.sort(key=lambda e: e["_orden"] or _min_dt)
    for e in eventos:
        e.pop("_orden", None)

    return {
        "vehiculo": {
            "vin": v.vin,
            "patente": v.patente,
            "marca": v.marca,
            "modelo": v.modelo,
            "anio": v.anio,
            "color": v.color,
            "km_inicial": v.km_inicial,
            "anomalias_count": v.anomalias_count or 0,
            "creado_en": v.creado_en.isoformat() if v.creado_en else None,
        },
        "eventos": eventos,
        "cadena": {
            "verificado": bool(info_chain),
            "tx_hash_alta": v.tx_hash_alta,
            "contrato": bc.address,
            "chain_id": bc.w3.eth.chain_id,
            "cantidad_eventos_on_chain": len(on_chain),
            "anomalias_off_chain": len(anomalias),
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
