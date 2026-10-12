"""Pruebas de administración de concesionarias, autenticación y baja de cuenta."""
from app.models import Concesionaria

# --- Administración -----------------------------------------------------------

def test_admin_rechaza_token_invalido(client):
    r = client.get("/admin/concesionarias", headers={"X-Admin-Token": "incorrecto"})
    assert r.status_code == 403


def test_crear_concesionaria_la_autoriza_en_el_contrato(client, bc, crear_concesionaria):
    c = crear_concesionaria()
    assert c["activa"] is True
    assert bc.es_concesionaria_autorizada(c["wallet_address"])


def test_crear_concesionaria_rechaza_email_duplicado(client, admin_headers, crear_concesionaria):
    crear_concesionaria(email="repetido@example.com")
    r = client.post("/admin/concesionarias", headers=admin_headers,
                    json={"nombre": "Otra", "email": "repetido@example.com", "password": "x"})
    assert r.status_code == 400


def test_crear_concesionaria_falla_si_el_contrato_rechaza(client, bc, admin_headers):
    bc.fallar["autorizar"] = RuntimeError("Solo el administrador")
    r = client.post("/admin/concesionarias", headers=admin_headers,
                    json={"nombre": "X", "email": "x@example.com", "password": "x"})
    assert r.status_code == 502
    assert "Solo el administrador" in r.json()["detail"]


def test_crear_concesionaria_falla_si_la_autorizacion_no_persiste(client, bc, admin_headers):
    bc.autorizar_persiste = False
    r = client.post("/admin/concesionarias", headers=admin_headers,
                    json={"nombre": "X", "email": "x@example.com", "password": "x"})
    assert r.status_code == 502


def test_crear_concesionaria_tolera_falla_al_fondear(client, bc, crear_concesionaria):
    bc.fallar["fondear"] = RuntimeError("sin saldo")
    assert crear_concesionaria()["activa"] is True


def test_listar_concesionarias(client, admin_headers, crear_concesionaria):
    crear_concesionaria(email="a@example.com")
    crear_concesionaria(email="b@example.com")
    r = client.get("/admin/concesionarias", headers=admin_headers)
    assert r.status_code == 200
    assert {c["email"] for c in r.json()} == {"a@example.com", "b@example.com"}


def test_fondear_y_estado(client, admin_headers, crear_concesionaria):
    c = crear_concesionaria()
    r = client.post(f"/admin/concesionarias/{c['id']}/fondear", headers=admin_headers)
    assert r.status_code == 200 and r.json()["balance"] == 0.5
    r = client.get(f"/admin/concesionarias/{c['id']}/estado", headers=admin_headers)
    assert r.status_code == 200 and r.json()["autorizada_on_chain"] is True


def test_operaciones_admin_sobre_concesionaria_inexistente(client, admin_headers):
    inexistente = "00000000-0000-0000-0000-000000000000"
    for metodo, ruta in (("post", "fondear"), ("post", "autorizar"), ("get", "estado"), ("post", "revocar")):
        r = getattr(client, metodo)(f"/admin/concesionarias/{inexistente}/{ruta}", headers=admin_headers)
        assert r.status_code == 404, ruta


def test_reautorizar(client, bc, admin_headers, crear_concesionaria):
    c = crear_concesionaria()
    r = client.post(f"/admin/concesionarias/{c['id']}/autorizar", headers=admin_headers)
    assert r.json()["ya_autorizada"] is True

    bc.autorizadas.clear()
    r = client.post(f"/admin/concesionarias/{c['id']}/autorizar", headers=admin_headers)
    assert r.status_code == 200 and r.json()["ya_autorizada"] is False


def test_reautorizar_con_fallas(client, bc, admin_headers, crear_concesionaria):
    c = crear_concesionaria()
    bc.autorizadas.clear()
    bc.fallar["autorizar"] = RuntimeError("rpc caído")
    assert client.post(f"/admin/concesionarias/{c['id']}/autorizar", headers=admin_headers).status_code == 502
    del bc.fallar["autorizar"]
    bc.autorizar_persiste = False
    assert client.post(f"/admin/concesionarias/{c['id']}/autorizar", headers=admin_headers).status_code == 502


def test_revocar_desactiva_y_revoca_en_cadena(client, bc, admin_headers, crear_concesionaria):
    c = crear_concesionaria()
    r = client.post(f"/admin/concesionarias/{c['id']}/revocar", headers=admin_headers)
    assert r.status_code == 200 and r.json()["revocada_on_chain"] is True
    assert not bc.es_concesionaria_autorizada(c["wallet_address"])
    # Revocada, la concesionaria ya no puede operar.
    assert client.get("/auth/me", headers=c["headers"]).status_code == 401


def test_revocar_falla_en_cadena(client, bc, admin_headers, crear_concesionaria):
    c = crear_concesionaria()
    bc.fallar["revocar"] = RuntimeError("rpc caído")
    r = client.post(f"/admin/concesionarias/{c['id']}/revocar", headers=admin_headers)
    assert r.status_code == 502


# --- Autenticación ------------------------------------------------------------

def test_login_y_me(client, crear_concesionaria):
    c = crear_concesionaria()
    r = client.get("/auth/me", headers=c["headers"])
    assert r.status_code == 200
    assert r.json()["email"] == "norte@example.com"


def test_login_rechaza_credenciales_invalidas(client, crear_concesionaria):
    crear_concesionaria()
    r = client.post("/auth/login", json={"email": "norte@example.com", "password": "otra"})
    assert r.status_code == 401
    r = client.post("/auth/login", json={"email": "nadie@example.com", "password": "otra"})
    assert r.status_code == 401


def test_login_rechaza_concesionaria_desactivada(client, sesiones, crear_concesionaria):
    c = crear_concesionaria()
    with sesiones() as db:
        db.query(Concesionaria).filter(Concesionaria.email == "norte@example.com").update({"activa": False})
        db.commit()
    r = client.post("/auth/login", json={"email": "norte@example.com", "password": c["password"]})
    assert r.status_code == 403


def test_token_invalido_o_sin_subject(client):
    from app.services.security import create_access_token

    assert client.get("/auth/me", headers={"Authorization": "Bearer no-es-un-jwt"}).status_code == 401
    sin_sub = create_access_token("")
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {sin_sub}"}).status_code == 401
    sub_malformado = create_access_token("no-es-un-uuid")
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {sub_malformado}"}).status_code == 401


def test_admin_rechaza_id_malformado(client, admin_headers):
    assert client.get("/admin/concesionarias/no-es-un-uuid/estado", headers=admin_headers).status_code == 422


# --- Baja de cuenta (derecho de supresión) ------------------------------------

def test_baja_de_cuenta_revoca_y_suprime_datos(client, bc, sesiones, crear_concesionaria):
    c = crear_concesionaria()
    r = client.request("DELETE", "/auth/cuenta", headers=c["headers"], json={"password": c["password"]})
    assert r.status_code == 200
    assert r.json()["revocada_on_chain"] is True
    assert not bc.es_concesionaria_autorizada(c["wallet_address"])

    with sesiones() as db:
        guardada = db.query(Concesionaria).filter(Concesionaria.wallet_address == c["wallet_address"]).one()
        assert guardada.activa is False
        assert guardada.email.endswith("@baja.invalid")
        assert guardada.cuit is None
        assert guardada.wallet_pk_enc == ""
        # La razón social se conserva: ya consta en la cadena y atribuye los asientos históricos.
        assert guardada.nombre == "Concesionaria Norte"

    assert client.post("/auth/login", json={"email": "norte@example.com", "password": c["password"]}).status_code == 401


def test_baja_de_cuenta_exige_la_contrasena(client, crear_concesionaria):
    c = crear_concesionaria()
    r = client.request("DELETE", "/auth/cuenta", headers=c["headers"], json={"password": "incorrecta"})
    assert r.status_code == 401
    assert client.get("/auth/me", headers=c["headers"]).status_code == 200


def test_baja_de_cuenta_no_borra_nada_si_falla_la_revocacion(client, bc, crear_concesionaria):
    c = crear_concesionaria()
    bc.fallar["revocar"] = RuntimeError("rpc caído")
    r = client.request("DELETE", "/auth/cuenta", headers=c["headers"], json={"password": c["password"]})
    assert r.status_code == 502
    assert client.get("/auth/me", headers=c["headers"]).status_code == 200


def test_baja_de_cuenta_ya_revocada_en_cadena(client, bc, crear_concesionaria):
    c = crear_concesionaria()
    bc.autorizadas.clear()
    r = client.request("DELETE", "/auth/cuenta", headers=c["headers"], json={"password": c["password"]})
    assert r.status_code == 200
    assert r.json()["revocada_on_chain"] is False
    assert r.json()["tx_hash"] is None
