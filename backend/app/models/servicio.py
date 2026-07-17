import uuid
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, ForeignKey, SmallInteger, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TipoServicio(Base):
    __tablename__ = "tipos_servicio"

    codigo = Column(SmallInteger, primary_key=True)
    nombre = Column(String, nullable=False)
    descripcion = Column(Text)


class Servicio(Base):
    __tablename__ = "servicios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehiculo_id = Column(UUID(as_uuid=True), ForeignKey("vehiculos.id"), nullable=False)
    concesionaria_id = Column(UUID(as_uuid=True), ForeignKey("concesionarias.id"), nullable=False)
    tipo_servicio = Column(SmallInteger, ForeignKey("tipos_servicio.codigo"), nullable=False)
    kilometraje = Column(Integer, nullable=False)
    descripcion = Column(Text)
    archivo_url = Column(String)
    archivo_nombre = Column(String)
    hash_evidencia = Column(String, nullable=False)
    tx_hash = Column(String)
    block_number = Column(BigInteger)
    chain_timestamp = Column(DateTime(timezone=True))
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    vehiculo = relationship("Vehiculo", back_populates="servicios")
    concesionaria = relationship("Concesionaria")
    tipo = relationship("TipoServicio")
