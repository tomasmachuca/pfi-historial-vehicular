"""Pruebas del esqueleto de la API de Historial Vehicular."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_read_root() -> None:
    """La raíz responde 200 con el mensaje de servicio operativo."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"mensaje": "API de Historial Vehicular operativa"}


def test_health_check() -> None:
    """El health check responde 200 con estado ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
