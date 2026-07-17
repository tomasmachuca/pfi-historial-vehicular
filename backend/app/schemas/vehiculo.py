from datetime import datetime
from pydantic import BaseModel, Field


class VehiculoCreate(BaseModel):
    vin: str = Field(min_length=5, max_length=32)
    patente: str = Field(min_length=1, max_length=16)
    marca: str
    modelo: str
    anio: int = Field(ge=1980, le=2100)
    color: str | None = None
    km_inicial: int = Field(default=0, ge=0)


class VehiculoPublic(BaseModel):
    id: str
    vin: str
    patente: str | None = None
    marca: str
    modelo: str
    anio: int
    color: str | None
    km_inicial: int
    tx_hash_alta: str | None
    creado_en: datetime

    class Config:
        from_attributes = True
