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


class ConcesionariaCreate(BaseModel):
    nombre: str
    cuit: str | None = None
    email: EmailStr
    password: str


class ConcesionariaPublic(BaseModel):
    id: str
    nombre: str
    email: EmailStr
    wallet_address: str
    activa: bool

    class Config:
        from_attributes = True
