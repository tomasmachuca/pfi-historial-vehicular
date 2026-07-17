from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_concesionaria
from app.models import Concesionaria
from app.schemas.auth import LoginRequest, TokenResponse, ConcesionariaPublic
from app.services.security import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    c = db.query(Concesionaria).filter(Concesionaria.email == req.email).first()
    if not c or not verify_password(req.password, c.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales invalidas")
    if not c.activa:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Concesionaria desactivada")

    token = create_access_token(str(c.id), {"nombre": c.nombre})
    return TokenResponse(
        access_token=token,
        concesionaria_id=str(c.id),
        nombre=c.nombre,
        wallet_address=c.wallet_address,
    )


@router.get("/me", response_model=ConcesionariaPublic)
def me(current: Concesionaria = Depends(get_current_concesionaria)):
    return ConcesionariaPublic(
        id=str(current.id),
        nombre=current.nombre,
        email=current.email,
        wallet_address=current.wallet_address,
        activa=current.activa,
    )
