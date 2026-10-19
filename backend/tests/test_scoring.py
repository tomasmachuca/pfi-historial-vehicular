"""Pruebas del módulo de scoring de confiabilidad."""
from datetime import UTC, datetime, timedelta

from app.services.hashing import ZERO_HASH_HEX, sha256_to_bytes32
from app.services.scoring import (
    PESO_ANOMALIAS,
    PESO_ANTIGUEDAD,
    PESO_DIVERSIDAD,
    PESO_EVIDENCIA,
    PESO_REGULARIDAD,
    TOPE_CON_ANOMALIAS,
    TOPE_SIN_VERIFICACION,
    EventoScore,
    calcular_score,
    nivel,
)

AHORA = datetime(2026, 10, 1, tzinfo=UTC)


def evento(meses_atras: float, km: int, *, conces="A", evidencia=True, verificado=True,
           anomalia=False, alta=False) -> EventoScore:
    return EventoScore(
        kilometraje=km,
        fecha=AHORA - timedelta(days=round(meses_atras * 30.44)),
        concesionaria=conces,
        con_evidencia=evidencia,
        verificado=verificado,
        anomalia=anomalia,
        es_alta=alta,
    )


def puntos(resultado: dict, clave: str) -> float:
    return next(c["puntos"] for c in resultado["componentes"] if c["clave"] == clave)


def historial_ejemplar() -> list[EventoScore]:
    """Alta hace 30 meses y un service por año, en dos concesionarias, todo con comprobante."""
    return [
        evento(30, 0, alta=True),
        evento(19, 9_800),
        evento(7, 19_500, conces="B"),
    ]


def test_los_pesos_suman_cien():
    assert PESO_ANOMALIAS + PESO_REGULARIDAD + PESO_EVIDENCIA + PESO_ANTIGUEDAD + PESO_DIVERSIDAD == 100


def test_historial_ejemplar_obtiene_puntaje_maximo():
    r = calcular_score(historial_ejemplar(), AHORA)
    assert r["puntaje"] == 100
    assert r["nivel"] == "alto"
    assert all(razon["tipo"] == "positivo" for razon in r["razones"])


def test_es_deterministico():
    assert calcular_score(historial_ejemplar(), AHORA) == calcular_score(historial_ejemplar(), AHORA)


def test_una_anomalia_resta_puntos_y_limita_el_puntaje():
    eventos = historial_ejemplar() + [evento(3, 12_000, anomalia=True, verificado=False)]
    r = calcular_score(eventos, AHORA)
    assert puntos(r, "anomalias") == PESO_ANOMALIAS - 20
    assert r["puntaje"] == TOPE_CON_ANOMALIAS
    assert r["nivel"] == "bajo"
    assert r["razones"][0]["tipo"] == "negativo"


def test_dos_anomalias_anulan_el_componente():
    eventos = historial_ejemplar() + [
        evento(3, 12_000, anomalia=True, verificado=False),
        evento(2, 11_000, anomalia=True, verificado=False),
    ]
    assert puntos(calcular_score(eventos, AHORA), "anomalias") == 0


def test_las_anomalias_no_cuentan_para_la_regularidad():
    eventos = historial_ejemplar() + [evento(3, 5_000, anomalia=True, verificado=False)]
    assert puntos(calcular_score(eventos, AHORA), "regularidad") == PESO_REGULARIDAD


def test_service_con_exceso_de_km_baja_la_regularidad():
    eventos = [evento(30, 0, alta=True), evento(19, 9_800), evento(7, 30_000)]
    r = calcular_score(eventos, AHORA)
    assert puntos(r, "regularidad") == PESO_REGULARIDAD / 2


def test_mucho_tiempo_sin_service_baja_la_regularidad():
    eventos = [evento(40, 0, alta=True), evento(29, 9_000)]
    r = calcular_score(eventos, AHORA)
    # Alta -> service a tiempo; service -> hoy vencido (29 meses).
    assert puntos(r, "regularidad") == PESO_REGULARIDAD / 2
    assert any("15 meses" in razon["texto"] for razon in r["razones"])


def test_vehiculo_nuevo_sin_services_no_es_penalizado_por_regularidad():
    r = calcular_score([evento(2, 5, alta=True)], AHORA)
    assert puntos(r, "regularidad") == PESO_REGULARIDAD


def test_services_sin_comprobante_bajan_la_cobertura_de_evidencia():
    eventos = [
        evento(30, 0, alta=True),
        evento(19, 9_800, evidencia=False),
        evento(7, 19_500, evidencia=False, conces="B"),
        evento(1, 25_000),
    ]
    r = calcular_score(eventos, AHORA)
    assert puntos(r, "evidencia") == PESO_EVIDENCIA / 2
    assert any("2 de 4" in razon["texto"] for razon in r["razones"])


def test_la_antiguedad_crece_hasta_los_24_meses():
    nuevo = calcular_score([evento(6, 0, alta=True)], AHORA)
    viejo = calcular_score([evento(36, 0, alta=True), evento(25, 9_000), evento(13, 18_000),
                            evento(1, 27_000)], AHORA)
    assert 0 < puntos(nuevo, "antiguedad") < PESO_ANTIGUEDAD
    assert puntos(viejo, "antiguedad") == PESO_ANTIGUEDAD


def test_una_sola_concesionaria_da_la_mitad_de_la_diversidad():
    eventos = [evento(30, 0, alta=True), evento(19, 9_800), evento(7, 19_500)]
    assert puntos(calcular_score(eventos, AHORA), "diversidad") == PESO_DIVERSIDAD / 2


def test_sin_eventos_verificados_el_puntaje_queda_limitado():
    eventos = [evento(30, 0, alta=True, verificado=False), evento(19, 9_800, verificado=False),
               evento(7, 19_500, conces="B", verificado=False)]
    r = calcular_score(eventos, AHORA)
    assert r["puntaje"] == TOPE_SIN_VERIFICACION
    assert puntos(r, "antiguedad") == 0
    # El tope ya explica la falta de verificación: la razón de antigüedad no se repite.
    textos = [x["texto"] for x in r["razones"]]
    assert any("se limita a 39" in t for t in textos)
    assert not any("No hay registros confirmados" in t for t in textos)


def test_fechas_sin_zona_horaria_se_interpretan_como_utc():
    ahora_naive = AHORA.replace(tzinfo=None)
    eventos = [EventoScore(0, ahora_naive - timedelta(days=60), "A", True, True, False, True)]
    assert calcular_score(eventos, ahora_naive)["puntaje"] > 0


def test_historial_vacio_no_falla():
    r = calcular_score([], AHORA)
    assert 0 <= r["puntaje"] <= TOPE_SIN_VERIFICACION
    assert r["nivel"] == "bajo"


def test_umbrales_de_nivel():
    assert nivel(80) == "alto"
    assert nivel(79) == "medio"
    assert nivel(60) == "medio"
    assert nivel(59) == "bajo"


def test_el_hash_cero_es_un_bytes32_valido():
    assert sha256_to_bytes32(ZERO_HASH_HEX) == bytes(32)
