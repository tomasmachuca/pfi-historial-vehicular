import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Vehiculo(Base):
    __tablename__ = "vehiculos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vin = Column(String, unique=True, nullable=False, index=True)
    patente = Column(String, index=True)
    marca = Column(String, nullable=False)
    modelo = Column(String, nullable=False)
    anio = Column(Integer, nullable=False)
    color = Column(String)
    concesionaria_alta_id = Column(UUID(as_uuid=True), ForeignKey("concesionarias.id"), nullable=False)
    km_inicial = Column(Integer, nullable=False, default=0)
    tx_hash_alta = Column(String)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    concesionaria_alta = relationship("Concesionaria")
    servicios = relationship("Servicio", back_populates="vehiculo", cascade="all, delete-orphan")
