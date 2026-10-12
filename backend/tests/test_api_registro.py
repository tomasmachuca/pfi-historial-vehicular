"""Pruebas de alta de vehículos, registro de services y consulta pública."""
import hashlib

from app.services.hashing import ZERO_HASH_HEX

VIN = "8AP1234567ABC8901"


# --- Alta de vehículo ---------------------------------------------------------

def test_alta_sin_comprobante_sella_hash_nulo(client, bc, crear_concesionaria, alta_vehiculo):
    c = crear_concesionaria()
    r = alta_vehiculo(c["headers"], vin=VIN.lower(), patente=" ab123cd ")
    assert r.status_code == 201, r.text
    assert r.json()["vin"] == VIN and r.json()["patente"] == "AB123CD"
    assert bc.historial[VIN][0]["hashEvidencia"] == "0x" + ZERO_HASH_HEX


def test_alta_con_comprobante_sella_su_hash(client, bc, storage, crear_concesionaria, alta_vehiculo):
    c = crear_concesionaria()
    contenido = b"%PDF-1.4 orden de entrega"
    r = alta_vehiculo(c["headers"], archivo=("entrega.pdf", contenido, "application/pdf"))
    assert r.status_code == 201
    assert bc.historial[VIN][0]["hashEvidencia"] == "0x" + hashlib.sha256(contenido).hexdigest()
    assert len(storage.subidos) == 1


def test_alta_rechaza_duplicados_y_patente_vacia(client, crear_concesionaria, alta_vehiculo):
    c = crear_concesionaria()
    assert alta_vehiculo(c["headers"]).status_code == 201
    assert alta_vehiculo(c["headers"], patente="ZZ999ZZ").status_code == 400  # VIN repetido
    assert alta_vehiculo(c["headers"], vin="9BWZZZ377VT004251").status_code == 400  # patente repetida
    assert alta_vehiculo(c["headers"], vin="9BWZZZ377VT004252", patente="   ").status_code == 400


def test_alta_rechaza_wallet_no_autorizada(client, bc, crear_concesionaria, alta_vehiculo):
    c = crear_concesionaria()
    bc.autorizadas.clear()
    assert alta_vehiculo(c["headers"]).status_code == 403


def test_alta_informa_error_de_la_cadena(client, bc, crear_concesionaria, alta_vehiculo):
    c = crear_concesionaria()
    bc.fallar["registrar_vehiculo"] = RuntimeError("VIN invalido")
    r = alta_vehiculo(c["headers"])
    assert r.status_code == 400 and "VIN invalido" in r.json()["detail"]


def test_mis_vehiculos(client, crear_concesionaria, alta_vehiculo):
    c1 = crear_concesionaria(email="uno@example.com")
    c2 = crear_concesionaria(nombre="Concesionaria Sur", email="dos@example.com")
    alta_vehiculo(c1["headers"])
    alta_vehiculo(c2["headers"], vin="9BWZZZ377VT004251", patente="AC456EF")
    r = client.get("/vehiculos/mios", headers=c1["headers"])
    assert [v["vin"] for v in r.json()] == [VIN]


# --- Registro de services -----------------------------------------------------

def _service(client, headers, km, tipo=1, archivo=None, vin=VIN):
    files = {"archivo": archivo} if archivo else None
    return client.post("/servicios", headers=headers, files=files,
                       data={"vin": vin, "tipo_servicio": str(tipo), "kilometraje": str(km), "descripcion": "Service"})


def test_service_sin_comprobante(client, crear_concesionaria, alta_vehiculo):
    c = crear_concesionaria()
    alta_vehiculo(c["headers"])
    r = _service(client, c["headers"], 10000)
    assert r.status_code == 201
    assert r.json()["hash_evidencia"] == ZERO_HASH_HEX
    assert r.json()["con_evidencia"] is False


def test_service_con_comprobante_y_busqueda_por_patente(client, crear_concesionaria, alta_vehiculo):
    c = crear_concesionaria()
    alta_vehiculo(c["headers"])
    contenido = b"orden de trabajo 1234"
    r = _service(client, c["headers"], 10000, archivo=("orden.pdf", contenido, "application/pdf"), vin="ab123cd")
    assert r.status_code == 201
    assert r.json()["hash_evidencia"] == hashlib.sha256(contenido).hexdigest()
    assert r.json()["con_evidencia"] is True


def test_service_rechaza_tipo_cero_y_vehiculo_inexistente(client, crear_concesionaria, alta_vehiculo):
    c = crear_concesionaria()
    alta_vehiculo(c["headers"])
    assert _service(client, c["headers"], 10000, tipo=0).status_code == 400
    assert _service(client, c["headers"], 10000, vin="NOEXISTE").status_code == 404


def test_kilometraje_regresivo_queda_como_anomalia_sin_sellar(client, bc, crear_concesionaria, alta_vehiculo):
    c = crear_concesionaria()
    alta_vehiculo(c["headers"])
    _service(client, c["headers"], 30560)
    r = _service(client, c["headers"], 18400)
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["km_regresivo"] is True and cuerpo["tx_hash"] is None
    assert cuerpo["diferencia"] == 30560 - 18400
    assert "12.160" in cuerpo["advertencia"]
    # El intento no llegó al contrato: el historial en cadena sigue teniendo alta y un service.
    assert len(bc.historial[VIN]) == 2


def test_service_informa_wallet_no_autorizada_con_ayuda(client, bc, crear_concesionaria, alta_vehiculo):
    c = crear_concesionaria()
    alta_vehiculo(c["headers"])
    bc.autorizadas.clear()
    r = _service(client, c["headers"], 10000)
    assert r.status_code == 400
    assert "On-chain autorizada=False" in r.json()["detail"]


def test_service_informa_otros_errores_de_la_cadena(client, bc, crear_concesionaria, alta_vehiculo):
    c = crear_concesionaria()
    alta_vehiculo(c["headers"])
    bc.fallar["registrar_servicio"] = RuntimeError("nonce too low")
    r = _service(client, c["headers"], 10000)
    assert r.status_code == 400 and "nonce too low" in r.json()["detail"]


# --- Consulta pública ---------------------------------------------------------

def test_consulta_publica_con_historial_y_puntaje(client, crear_concesionaria, alta_vehiculo):
    c1 = crear_concesionaria(email="uno@example.com")
    c2 = crear_concesionaria(nombre="Concesionaria Sur", email="dos@example.com")
    alta_vehiculo(c1["headers"])
    _service(client, c1["headers"], 10000, archivo=("orden.pdf", b"orden", "application/pdf"))
    _service(client, c2["headers"], 19500)
    _service(client, c2["headers"], 15000)  # anomalía

    r = client.get("/publico/vehiculo/ab123cd")
    assert r.status_code == 200
    cuerpo = r.json()
    assert len(cuerpo["eventos"]) == 4
    anomalia = next(e for e in cuerpo["eventos"] if e["km_regresivo"])
    assert anomalia["verificado"] is False
    assert sum(e["verificado"] for e in cuerpo["eventos"]) == 3
    assert [e["con_evidencia"] for e in cuerpo["eventos"] if e["kilometraje"] == 10000] == [True]
    assert cuerpo["cadena"]["cantidad_eventos_on_chain"] == 3
    assert cuerpo["cadena"]["anomalias_off_chain"] == 1
    assert cuerpo["score"]["puntaje"] <= 59  # tope por anomalía
    assert cuerpo["vehiculo"]["anomalias_count"] == 1


def test_consulta_publica_inexistente(client):
    assert client.get("/publico/vehiculo/NOEXISTE").status_code == 404


def test_estado_de_red_y_estadisticas(client, crear_concesionaria, alta_vehiculo):
    c = crear_concesionaria()
    alta_vehiculo(c["headers"])
    assert client.get("/publico/red").json()["chain_id"] == 80002
    stats = client.get("/publico/stats").json()
    assert stats == {"vehiculos_registrados": 1, "servicios_registrados": 1, "concesionarias_activas": 1}
