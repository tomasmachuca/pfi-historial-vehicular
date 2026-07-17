import base64
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, extra: dict | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        raise ValueError(str(e))


def _fernet() -> Fernet:
    raw = settings.JWT_SECRET.encode("utf-8")
    raw = (raw * ((32 // len(raw)) + 1))[:32]
    key = base64.urlsafe_b64encode(raw)
    return Fernet(key)


def encrypt_pk(plain_pk: str) -> str:
    return _fernet().encrypt(plain_pk.encode("utf-8")).decode("utf-8")


def decrypt_pk(token: str) -> str:
    return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
