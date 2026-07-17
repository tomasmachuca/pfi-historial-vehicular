from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Concesionaria
from app.schemas.auth import ConcesionariaCreate, ConcesionariaPublic
from app.services.blockchain import get_blockchain
from app.services.security import hash_password, encrypt_pk

router = APIRouter(prefix="/admin", tags=["admin"])


def _expected_admin_token() -> str:
    t = (settings.ADMIN_API_TOKEN or "").strip()
    return t if t else settings.JWT_SECRET[:32]


def _check_admin(x_admin_token: str = Header(...)):
    if x_admin_token != _expected_admin_token():
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token de admin invalido")


@router.post("/concesionarias", response_model=ConcesionariaPublic, dependencies=[Depends(_check_admin)])
def crear_concesionaria(payload: ConcesionariaCreate, db: Session = Depends(get_db)):
    if db.query(Concesionaria).filter(Concesionaria.email == payload.email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email ya registrado")

    bc = get_blockchain()
    address, pk = bc.crear_wallet()

    try:
        bc.autorizar_concesionaria(address, payload.nombre)
    except Exception as e:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"No se pudo autorizar la wallet en el contrato: {e}. "
            f"Verificá que ADMIN_PRIVATE_KEY corresponda al admin del contrato "
            f"({bc.admin_address()}).",
        )

    if not bc.es_concesionaria_autorizada(address):
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "La autorización on-chain no quedó registrada. Revisá la red y reintentá.",
        )

    try:
        bc.fondear_wallet(address, "0.5")
    except Exception:
        pass

    c = Concesionaria(
        nombre=payload.nombre,
        cuit=payload.cuit,
        email=payload.email,
        password_hash=hash_password(payload.password),
        wallet_address=address,
        wallet_pk_enc=encrypt_pk(pk),
        activa=True,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return ConcesionariaPublic(
        id=str(c.id),
        nombre=c.nombre,
        email=c.email,
        wallet_address=c.wallet_address,
        activa=c.activa,
    )


@router.get("/concesionarias", response_model=list[ConcesionariaPublic], dependencies=[Depends(_check_admin)])
def listar(db: Session = Depends(get_db)):
    items = db.query(Concesionaria).order_by(Concesionaria.creado_en.desc()).all()
    return [
        ConcesionariaPublic(
            id=str(c.id),
            nombre=c.nombre,
            email=c.email,
            wallet_address=c.wallet_address,
            activa=c.activa,
        )
        for c in items
    ]


@router.post("/concesionarias/{concesionaria_id}/fondear", dependencies=[Depends(_check_admin)])
def fondear(concesionaria_id: str, monto_matic: str = "0.5", db: Session = Depends(get_db)):
    c = db.query(Concesionaria).filter(Concesionaria.id == concesionaria_id).first()
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontrada")
    bc = get_blockchain()
    res = bc.fondear_wallet(c.wallet_address, monto_matic)
    return {"ok": True, **res, "balance": bc.balance_matic(c.wallet_address)}


@router.post("/concesionarias/{concesionaria_id}/autorizar", dependencies=[Depends(_check_admin)])
def reautorizar(concesionaria_id: str, db: Session = Depends(get_db)):
    """
    Re-autoriza la wallet de una concesionaria existente en el contrato.
    Útil cuando la autorización inicial falló silenciosamente y los registros
    revierten con 'No autorizado. Solo red oficial.'.
    """
    c = db.query(Concesionaria).filter(Concesionaria.id == concesionaria_id).first()
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontrada")

    bc = get_blockchain()
    if bc.es_concesionaria_autorizada(c.wallet_address):
        return {"ok": True, "ya_autorizada": True, "wallet": c.wallet_address}

    try:
        res = bc.autorizar_concesionaria(c.wallet_address, c.nombre)
    except Exception as e:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"No se pudo autorizar: {e}. Admin del contrato: {bc.admin_address()}.",
        )

    if not bc.es_concesionaria_autorizada(c.wallet_address):
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "La autorización on-chain no quedó registrada tras la transacción.",
        )

    return {"ok": True, "ya_autorizada": False, "wallet": c.wallet_address, **res}


@router.get("/concesionarias/{concesionaria_id}/estado", dependencies=[Depends(_check_admin)])
def estado_concesionaria(concesionaria_id: str, db: Session = Depends(get_db)):
    c = db.query(Concesionaria).filter(Concesionaria.id == concesionaria_id).first()
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontrada")
    bc = get_blockchain()
    return {
        "id": str(c.id),
        "nombre": c.nombre,
        "wallet_address": c.wallet_address,
        "autorizada_on_chain": bc.es_concesionaria_autorizada(c.wallet_address),
        "balance_matic": bc.balance_matic(c.wallet_address),
        "admin_contrato": bc.admin_address(),
    }
