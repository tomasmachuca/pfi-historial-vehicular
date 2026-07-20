import uuid
from sqlalchemy import Column, String, Boolean, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class Concesionaria(Base):
    __tablename__ = "concesionarias"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String, nullable=False)
    cuit = Column(String, unique=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    wallet_address = Column(String, unique=True, nullable=False)
    wallet_pk_enc = Column(String, nullable=False)
    activa = Column(Boolean, nullable=False, default=True)
    # Cantidad de services anómalos (km regresivo) cargados por esta concesionaria.
    anomalias_count = Column(Integer, nullable=False, default=0)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
