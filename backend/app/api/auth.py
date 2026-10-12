from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_concesionaria
from app.models import Concesionaria
from app.schemas.auth import (
    BajaCuentaRequest,
    ConcesionariaPublic,
    LoginRequest,
    TokenResponse,
)
from app.services.blockchain import get_blockchain
from app.services.cuentas import dar_de_baja
from app.services.security import create_access_token, verify_password

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
        anomalias_count=current.anomalias_count or 0,
    )


@router.delete("/cuenta")
def baja_cuenta(
    req: BajaCuentaRequest,
    current: Concesionaria = Depends(get_current_concesionaria),
    db: Session = Depends(get_db),
):
    """Baja de la cuenta a pedido de la concesionaria (derecho de supresión, Ley 25.326)."""
    if not verify_password(req.password, current.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Contraseña incorrecta")
    try:
        resultado = dar_de_baja(current, get_blockchain())
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"No se pudo revocar la autorización en el contrato: {e}. La cuenta sigue activa.",
        )
    db.commit()
    return resultado
