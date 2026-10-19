from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Concesionaria, Servicio, TipoServicio, Vehiculo
from app.services.blockchain import get_blockchain
from app.services.hashing import ZERO_HASH_HEX
from app.services.scoring import EventoScore, calcular_score

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
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehículo no encontrado")

    bc = get_blockchain()
    on_chain = bc.obtener_historial(v.vin)
    anomalias_chain = bc.obtener_anomalias(v.vin)
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
    conces_by_wallet = {(c.wallet_address or "").lower(): c for c in conces}

    # Asientos realmente sellados en el contrato ACTUAL, como multiconjuntos de
    # (kilometraje, tipo, hash). Cada service de la base se marca como verificado
    # solo si coincide con un asiento en cadena en esos tres campos: si la base se
    # alterara, o el vehículo se registró contra un contrato anterior, no coincide.
    validos_chain = _multiconjunto(
        (ev["kilometraje"], ev["tipoServicio"], _norm(ev["hashEvidencia"])) for ev in on_chain
    )
    anomalias_pendientes = list(anomalias_chain)

    # Armamos el timeline desde la DB (descripción, comprobante, tx). La cadena confirma.
    eventos = []
    insumos_score = []
    for s in servicios_db:
        c = conces_by_id.get(s.concesionaria_id)
        # Hay comprobante si se selló su hash; la URL puede faltar si el almacén no está configurado.
        con_evidencia = bool(s.hash_evidencia) and s.hash_evidencia != ZERO_HASH_HEX
        clave = (s.kilometraje, s.tipo_servicio, _norm(s.hash_evidencia))
        verificado = False
        if s.km_regresivo:
            # Anomalía: verificada si está sellada en la lista de anomalías del contrato.
            match = next(
                (a for a in anomalias_pendientes
                 if (a["kilometrajeDeclarado"], a["tipoServicio"], _norm(a["hashEvidencia"])) == clave),
                None,
            )
            if match is not None:
                anomalias_pendientes.remove(match)
                verificado = True
        elif s.tx_hash and validos_chain.get(clave, 0) > 0:
            validos_chain[clave] -= 1
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
            "con_evidencia": con_evidencia,
            "tx_hash": s.tx_hash,
            "block_number": s.block_number,
            "km_regresivo": s.km_regresivo,
            "km_anterior": s.km_anterior,
            "verificado": verificado,
            "_orden": s.creado_en,
        })
        insumos_score.append(EventoScore(
            kilometraje=s.kilometraje,
            fecha=s.chain_timestamp or s.creado_en,
            concesionaria=str(s.concesionaria_id) if s.concesionaria_id else None,
            con_evidencia=con_evidencia,
            verificado=verificado,
            anomalia=bool(s.km_regresivo),
            es_alta=s.tipo_servicio == 0,
        ))
    # Anomalías selladas en cadena que la base no tiene (por ejemplo, si se borraron
    # de la base): se muestran igual, a partir de lo que el contrato conserva.
    for a in anomalias_pendientes:
        c = conces_by_wallet.get(str(a["concesionaria"]).lower())
        fecha = datetime.fromtimestamp(a["timestamp"], tz=UTC)
        eventos.append({
            "kilometraje": a["kilometrajeDeclarado"],
            "tipo_servicio": a["tipoServicio"],
            "tipo_nombre": tipos.get(a["tipoServicio"], f"Tipo {a['tipoServicio']}"),
            "hash_evidencia": _norm(a["hashEvidencia"]),
            "concesionaria_address": a["concesionaria"],
            "concesionaria_nombre": c.nombre if c else "Concesionaria",
            "chain_timestamp": fecha.isoformat(),
            "descripcion": None,
            "archivo_url": None,
            "con_evidencia": _norm(a["hashEvidencia"]) != ZERO_HASH_HEX,
            "tx_hash": None,
            "block_number": None,
            "km_regresivo": True,
            "km_anterior": a["kilometrajeVigente"],
            "verificado": True,
            "_orden": fecha,
        })
        insumos_score.append(EventoScore(
            kilometraje=a["kilometrajeDeclarado"], fecha=fecha,
            concesionaria=str(c.id) if c else str(a["concesionaria"]),
            con_evidencia=False, verificado=True, anomalia=True, es_alta=False,
        ))

    anomalias_total = sum(1 for e in eventos if e["km_regresivo"])
    anomalias_selladas = sum(1 for e in eventos if e["km_regresivo"] and e["verificado"])

    # Orden cronológico por fecha de carga; las anomalías se intercalan donde ocurrieron.
    _min_dt = datetime.min.replace(tzinfo=UTC)

    def _orden(e):
        f = e["_orden"] or _min_dt
        return f if f.tzinfo else f.replace(tzinfo=UTC)

    eventos.sort(key=_orden)
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
            "anomalias_count": max(v.anomalias_count or 0, anomalias_total),
            "creado_en": v.creado_en.isoformat() if v.creado_en else None,
        },
        "eventos": eventos,
        "score": calcular_score(insumos_score, datetime.now(UTC)),
        "cadena": {
            "verificado": bool(info_chain),
            "tx_hash_alta": v.tx_hash_alta,
            "contrato": bc.address,
            "chain_id": bc.w3.eth.chain_id,
            "cantidad_eventos_on_chain": len(on_chain),
            "anomalias_on_chain": len(anomalias_chain),
            # Anomalías anteriores al sellado en cadena (solo registradas en la base).
            "anomalias_off_chain": anomalias_total - anomalias_selladas,
        },
    }


def _norm(hash_hex: str | None) -> str:
    """Hash en hexadecimal, sin prefijo y en minúsculas, para comparar base y cadena."""
    return (hash_hex or "").lower().removeprefix("0x")


def _multiconjunto(claves) -> dict:
    conteo: dict = {}
    for k in claves:
        conteo[k] = conteo.get(k, 0) + 1
    return conteo


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
