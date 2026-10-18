import base64
from datetime import UTC, datetime, timedelta

from cryptography.fernet import Fernet, MultiFernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, extra: dict | None = None) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        raise ValueError(str(e))


def _fernet_legacy() -> Fernet:
    """Llave derivada de JWT_SECRET, usada por las versiones anteriores. Se conserva
    solo para poder descifrar las claves privadas cifradas antes de la rotación."""
    raw = settings.JWT_SECRET.encode("utf-8")
    raw = (raw * ((32 // len(raw)) + 1))[:32]
    key = base64.urlsafe_b64encode(raw)
    return Fernet(key)


def _fernet() -> MultiFernet:
    """Cifra con WALLET_ENCRYPTION_KEY, una llave propia e independiente del secreto
    de las sesiones; descifra con ella o con la llave anterior."""
    llaves = [Fernet(settings.WALLET_ENCRYPTION_KEY)] if settings.WALLET_ENCRYPTION_KEY else []
    return MultiFernet([*llaves, _fernet_legacy()])


def recifrar_pk(token: str) -> str:
    """Vuelve a cifrar una clave con la llave vigente (rotación)."""
    return _fernet().rotate(token.encode("utf-8")).decode("utf-8")


def encrypt_pk(plain_pk: str) -> str:
    return _fernet().encrypt(plain_pk.encode("utf-8")).decode("utf-8")


def decrypt_pk(token: str) -> str:
    return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
