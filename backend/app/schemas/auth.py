from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    concesionaria_id: str
    nombre: str
    wallet_address: str


class BajaCuentaRequest(BaseModel):
    password: str


class ConcesionariaCreate(BaseModel):
    nombre: str
    cuit: str | None = None
    email: EmailStr
    password: str


class ConcesionariaPublic(BaseModel):
    id: str
    nombre: str
    # str y no EmailStr: una cuenta dada de baja conserva un correo de reemplazo no entregable.
    email: str
    wallet_address: str
    activa: bool
    anomalias_count: int = 0

    class Config:
        from_attributes = True
