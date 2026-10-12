"""Configuracion de entorno para la suite de tests.

La app lee su configuracion con pydantic-settings al importarse (app.config),
por lo que sin estas variables no se puede ni importar app.main fuera de un
entorno con .env. Se definen aqui, antes de cualquier import de la app, con
valores ficticios: ninguna prueba abre conexiones reales contra la base ni
contra la red Polygon.
"""
import os

_ENTORNO_DE_PRUEBA = {
    # SQLite en memoria: create_engine no conecta al importar, solo valida la URL.
    "DATABASE_URL": "sqlite:///:memory:",
    "JWT_SECRET": "clave-solo-para-tests-no-usar-en-produccion",
    "RPC_URL": "http://localhost:8545",
    "CHAIN_ID": "31337",
    "CONTRACT_ADDRESS": "0x0000000000000000000000000000000000000000",
    "ADMIN_PRIVATE_KEY": "0x" + "11" * 32,
    "FRONTEND_ORIGIN": "http://localhost:5173",
}

for _clave, _valor in _ENTORNO_DE_PRUEBA.items():
    os.environ.setdefault(_clave, _valor)


# --- Fixtures de la API -------------------------------------------------------
# Se importan después de definir el entorno, porque la app lee la configuración
# al importarse.
import pytest

from tests.fakes import FakeBlockchain, FakeStorage

_MODULOS_CON_BLOCKCHAIN = ("app.api.admin", "app.api.auth", "app.api.vehiculos", "app.api.servicios", "app.api.publico")


@pytest.fixture()
def bc(monkeypatch):
    """Blockchain simulada, compartida por todos los routers durante la prueba."""
    fake = FakeBlockchain()
    for modulo in _MODULOS_CON_BLOCKCHAIN:
        monkeypatch.setattr(f"{modulo}.get_blockchain", lambda: fake)
    return fake


@pytest.fixture()
def storage(monkeypatch):
    fake = FakeStorage()
    for modulo in ("app.api.vehiculos", "app.api.servicios"):
        monkeypatch.setattr(f"{modulo}.upload_evidencia", fake.upload)
    return fake


@pytest.fixture()
def sesiones():
    """Base SQLite en memoria con el esquema de los modelos y los tipos de servicio."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.database import Base
    from app.models import TipoServicio

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    fabrica = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with fabrica() as db:
        db.add_all([
            TipoServicio(codigo=1, nombre="Service oficial"),
            TipoServicio(codigo=2, nombre="Reparación"),
            TipoServicio(codigo=3, nombre="Inspección"),
        ])
        db.commit()
    yield fabrica
    engine.dispose()


@pytest.fixture()
def client(sesiones, bc, storage):
    from fastapi.testclient import TestClient

    from app.database import get_db
    from app.main import app

    def _get_db():
        db = sesiones()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_headers():
    from app.api.admin import _expected_admin_token

    return {"X-Admin-Token": _expected_admin_token()}


@pytest.fixture()
def crear_concesionaria(client, admin_headers):
    """Da de alta una concesionaria por la API de administración y devuelve sus datos y su token."""

    creadas = []

    def _crear(nombre="Concesionaria Norte", email="norte@example.com", password="clave-segura-1"):
        creadas.append(email)
        cuit = f"30-{len(creadas):08d}-9"  # el CUIT es único por concesionaria
        r = client.post("/admin/concesionarias", headers=admin_headers,
                        json={"nombre": nombre, "cuit": cuit, "email": email, "password": password})
        assert r.status_code == 200, r.text
        datos = r.json()
        login = client.post("/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200, login.text
        datos["token"] = login.json()["access_token"]
        datos["headers"] = {"Authorization": f"Bearer {datos['token']}"}
        datos["password"] = password
        return datos

    return _crear


@pytest.fixture()
def alta_vehiculo(client):
    def _alta(headers, vin="8AP1234567ABC8901", patente="AB123CD", km=0, archivo=None):
        files = {"archivo": archivo} if archivo else None
        data = {"vin": vin, "patente": patente, "marca": "Toyota", "modelo": "Corolla", "anio": "2026",
                "color": "Gris", "km_inicial": str(km)}
        return client.post("/vehiculos", headers=headers, data=data, files=files)

    return _alta
