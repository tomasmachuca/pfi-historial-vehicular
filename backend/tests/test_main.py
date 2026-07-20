"""Pruebas de la API de Historial Vehicular."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_read_root() -> None:
    """La raíz responde 200 identificando al servicio y su versión."""
    response = client.get("/")
    assert response.status_code == 200
    cuerpo = response.json()
    assert cuerpo["ok"] is True
    assert cuerpo["service"] == "historial-0km"
    assert cuerpo["version"] == app.version


def test_health_check() -> None:
    """El health check responde 200 con estado ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
