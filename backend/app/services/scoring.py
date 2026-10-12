"""Scoring de confiabilidad del historial de un vehículo.

Heurística determinística de pesos fijos (no es un modelo entrenado): para la
misma entrada devuelve siempre el mismo puntaje, y cada punto es trazable a una
regla explícita. Combina los cinco insumos definidos en el diseño:

    Insumo                                   Peso
    Ausencia de anomalías de kilometraje      30
    Regularidad del mantenimiento             25
    Cobertura de evidencia documental         20
    Antigüedad del primer registro on-chain   15
    Diversidad de concesionarias              10
                                             ----
                                              100

Sobre la suma se aplican dos topes: con anomalías el historial no puede
calificar como confiable, y sin ningún evento confirmado en el contrato el
puntaje no puede apoyarse en la verificabilidad que el sistema promete.
"""
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from itertools import pairwise

PESO_ANOMALIAS = 30
PESO_REGULARIDAD = 25
PESO_EVIDENCIA = 20
PESO_ANTIGUEDAD = 15
PESO_DIVERSIDAD = 10

# Plan de mantenimiento oficial típico: un service cada 10.000 km o cada 12
# meses, lo que ocurra primero. Se tolera un 20% / 3 meses de demora.
KM_ENTRE_SERVICES = 10_000
KM_TOLERADOS = 12_000
DIAS_TOLERADOS = 456  # 15 meses

PUNTOS_POR_ANOMALIA = 20
MESES_ANTIGUEDAD_PLENA = 24

TOPE_CON_ANOMALIAS = 59
TOPE_SIN_VERIFICACION = 39

UMBRAL_ALTO = 80
UMBRAL_MEDIO = 60


@dataclass(frozen=True)
class EventoScore:
    """Lo mínimo que el scoring necesita saber de cada evento del historial."""

    kilometraje: int
    fecha: datetime | None
    concesionaria: str | None
    con_evidencia: bool
    verificado: bool
    anomalia: bool
    es_alta: bool = False


def _razon(texto: str, tipo: str) -> dict:
    return {"texto": texto, "tipo": tipo}


def _miles(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _componente(clave: str, nombre: str, puntos: float, maximo: int, razon: dict) -> dict:
    return {
        "clave": clave,
        "nombre": nombre,
        "puntos": round(puntos, 1),
        "maximo": maximo,
        "razon": razon,
    }


def _anomalias(eventos: list[EventoScore]) -> dict:
    n = sum(1 for e in eventos if e.anomalia)
    puntos = max(0, PESO_ANOMALIAS - PUNTOS_POR_ANOMALIA * n)
    if n == 0:
        razon = _razon("El kilometraje nunca retrocedió entre registros.", "positivo")
    elif n == 1:
        razon = _razon(
            "Hubo 1 intento de cargar un kilometraje menor al ya registrado.", "negativo"
        )
    else:
        razon = _razon(
            f"Hubo {n} intentos de cargar un kilometraje menor al ya registrado.", "negativo"
        )
    return _componente("anomalias", "Ausencia de anomalías de kilometraje", puntos, PESO_ANOMALIAS, razon)


def _regularidad(legitimos: list[EventoScore], ahora: datetime) -> dict:
    """Proporción de intervalos entre registros que respetan el plan de mantenimiento."""
    con_fecha = [e for e in legitimos if e.fecha is not None]
    intervalos = 0
    regulares = 0
    for previo, actual in pairwise(con_fecha):
        intervalos += 1
        km = actual.kilometraje - previo.kilometraje
        dias = (actual.fecha - previo.fecha).days
        if km <= KM_TOLERADOS and dias <= DIAS_TOLERADOS:
            regulares += 1

    # El tramo abierto (último registro -> hoy) solo cuenta si ya está vencido:
    # no se conoce el km actual, pero sí el tiempo transcurrido.
    vencido = False
    if con_fecha:
        dias_desde_ultimo = (ahora - con_fecha[-1].fecha).days
        if dias_desde_ultimo > DIAS_TOLERADOS:
            intervalos += 1
            vencido = True

    if intervalos == 0:
        puntos = PESO_REGULARIDAD
        razon = _razon("Todavía no corresponde ningún service según el plan oficial.", "neutro")
    else:
        puntos = PESO_REGULARIDAD * regulares / intervalos
        if regulares == intervalos:
            razon = _razon(
                f"Los services se hicieron a tiempo (cada {_miles(KM_ENTRE_SERVICES)} km o 12 meses).",
                "positivo",
            )
        elif vencido and regulares == intervalos - 1:
            razon = _razon("Pasaron más de 15 meses desde el último registro.", "negativo")
        elif intervalos == 1:
            razon = _razon(
                f"El intervalo entre services superó los {_miles(KM_TOLERADOS)} km o los 15 meses.",
                "negativo",
            )
        else:
            razon = _razon(
                f"{intervalos - regulares} de {intervalos} intervalos entre services superaron "
                f"los {_miles(KM_TOLERADOS)} km o los 15 meses.",
                "negativo",
            )
    return _componente("regularidad", "Regularidad del mantenimiento", puntos, PESO_REGULARIDAD, razon)


def _evidencia(legitimos: list[EventoScore]) -> dict:
    total = len(legitimos)
    con = sum(1 for e in legitimos if e.con_evidencia)
    if total == 0:
        return _componente(
            "evidencia", "Cobertura de evidencia documental", 0, PESO_EVIDENCIA,
            _razon("No hay registros para evaluar.", "negativo"),
        )
    puntos = PESO_EVIDENCIA * con / total
    if con == total:
        razon = _razon("Todos los registros tienen su comprobante adjunto.", "positivo")
    elif con == 0:
        razon = _razon("Ningún registro tiene comprobante adjunto.", "negativo")
    else:
        verbo = "tiene" if con == 1 else "tienen"
        razon = _razon(f"{con} de {total} registros {verbo} comprobante adjunto.", "neutro")
    return _componente("evidencia", "Cobertura de evidencia documental", puntos, PESO_EVIDENCIA, razon)


def _antiguedad(legitimos: list[EventoScore], ahora: datetime) -> dict:
    fechas = [e.fecha for e in legitimos if e.fecha is not None and e.verificado]
    if not fechas:
        return _componente(
            "antiguedad", "Antigüedad del registro on-chain", 0, PESO_ANTIGUEDAD,
            _razon("No hay registros confirmados en la blockchain.", "negativo"),
        )
    meses = max(0, (ahora - min(fechas)).days) / 30.44
    puntos = PESO_ANTIGUEDAD * min(1, meses / MESES_ANTIGUEDAD_PLENA)
    meses_txt = int(meses)
    if meses >= MESES_ANTIGUEDAD_PLENA:
        razon = _razon(f"El historial se registra en blockchain hace {meses_txt} meses.", "positivo")
    else:
        unidad = "mes" if meses_txt == 1 else "meses"
        razon = _razon(
            f"El historial lleva {meses_txt} {unidad} en blockchain: la confianza crece con el tiempo.",
            "neutro",
        )
    return _componente("antiguedad", "Antigüedad del registro on-chain", puntos, PESO_ANTIGUEDAD, razon)


def _diversidad(legitimos: list[EventoScore]) -> dict:
    conces = {e.concesionaria for e in legitimos if e.concesionaria}
    n = len(conces)
    if n >= 2:
        puntos = PESO_DIVERSIDAD
        razon = _razon(f"{n} concesionarias oficiales distintas registraron eventos.", "positivo")
    elif n == 1:
        puntos = PESO_DIVERSIDAD / 2
        razon = _razon(
            "Todos los registros provienen de una misma concesionaria oficial.", "neutro"
        )
    else:
        puntos = 0
        razon = _razon("No hay concesionarias identificadas en el historial.", "negativo")
    return _componente("diversidad", "Diversidad de concesionarias", puntos, PESO_DIVERSIDAD, razon)


def nivel(puntaje: int) -> str:
    if puntaje >= UMBRAL_ALTO:
        return "alto"
    if puntaje >= UMBRAL_MEDIO:
        return "medio"
    return "bajo"


def _utc(fecha: datetime | None) -> datetime | None:
    # La base devuelve fechas con zona; los datos de prueba pueden no tenerla.
    if fecha is not None and fecha.tzinfo is None:
        return fecha.replace(tzinfo=timezone.utc)
    return fecha


def calcular_score(eventos: list[EventoScore], ahora: datetime) -> dict:
    """Devuelve el puntaje 0-100, su nivel, el desglose y las razones en lenguaje llano."""
    ahora = _utc(ahora)
    eventos = [replace(e, fecha=_utc(e.fecha)) for e in eventos]
    legitimos = sorted(
        (e for e in eventos if not e.anomalia),
        key=lambda e: (e.kilometraje, e.fecha or ahora),
    )
    componentes = [
        _anomalias(eventos),
        _regularidad(legitimos, ahora),
        _evidencia(legitimos),
        _antiguedad(legitimos, ahora),
        _diversidad(legitimos),
    ]
    puntaje = round(sum(c["puntos"] for c in componentes))
    topes = []

    if any(e.anomalia for e in eventos) and puntaje > TOPE_CON_ANOMALIAS:
        puntaje = TOPE_CON_ANOMALIAS
        topes.append(_razon(
            f"Por tener anomalías de kilometraje, el puntaje se limita a {TOPE_CON_ANOMALIAS}.",
            "negativo",
        ))
    if not any(e.verificado for e in legitimos) and puntaje > TOPE_SIN_VERIFICACION:
        puntaje = TOPE_SIN_VERIFICACION
        topes.append(_razon(
            "Ningún evento está confirmado en el contrato actual: "
            f"el puntaje se limita a {TOPE_SIN_VERIFICACION}.",
            "negativo",
        ))

    # Primero lo que resta confianza: es lo que el comprador necesita ver antes.
    orden = {"negativo": 0, "neutro": 1, "positivo": 2}
    razones = topes + sorted((c["razon"] for c in componentes), key=lambda r: orden[r["tipo"]])

    return {
        "puntaje": puntaje,
        "nivel": nivel(puntaje),
        "componentes": componentes,
        "razones": razones,
        "version": "1.0",
    }
