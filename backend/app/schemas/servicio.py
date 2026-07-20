from datetime import datetime
from pydantic import BaseModel, Field


class ServicioCreate(BaseModel):
    vin: str
    tipo_servicio: int = Field(ge=1, le=255)
    kilometraje: int = Field(ge=0)
    descripcion: str | None = None


class ServicioPublic(BaseModel):
    id: str
    tipo_servicio: int
    tipo_nombre: str | None = None
    kilometraje: int
    descripcion: str | None
    archivo_url: str | None
    hash_evidencia: str
    tx_hash: str | None
    block_number: int | None
    chain_timestamp: datetime | None
    creado_en: datetime
    concesionaria_nombre: str | None = None

    class Config:
        from_attributes = True


class HistorialPublico(BaseModel):
    vehiculo: dict
    eventos: list[ServicioPublic]
    cadena: dict
