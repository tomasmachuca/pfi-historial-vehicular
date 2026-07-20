from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Concesionaria
from app.services.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_concesionaria(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Concesionaria:
    try:
        payload = decode_access_token(token)
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido")

    cid = payload.get("sub")
    if not cid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token sin subject")

    c = db.query(Concesionaria).filter(Concesionaria.id == cid).first()
    if not c or not c.activa:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Concesionaria inactiva o inexistente")
    return c
