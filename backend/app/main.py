"""API mínima del Sistema de Historial Vehicular (esqueleto inicial)."""
from fastapi import FastAPI

app = FastAPI(
    title="Historial Vehicular API",
    description="Backend del sistema de historial vehicular verificable basado en blockchain.",
    version="0.1.0",
)


@app.get("/")
def read_root() -> dict[str, str]:
    """Endpoint raíz de verificación del servicio."""
    return {"mensaje": "API de Historial Vehicular operativa"}


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check para el pipeline de CI y el monitoreo."""
    return {"status": "ok"}
