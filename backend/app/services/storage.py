import boto3
from botocore.client import Config

from app.config import settings


def _r2_client():
    if not settings.R2_ACCOUNT_ID:
        return None
    endpoint = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def upload_evidencia(file_bytes: bytes, key: str, content_type: str) -> str:
    client = _r2_client()
    if client is None:
        return ""
    client.put_object(
        Bucket=settings.R2_BUCKET,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )
    if settings.R2_PUBLIC_URL:
        return f"{settings.R2_PUBLIC_URL.rstrip('/')}/{key}"
    return f"r2://{settings.R2_BUCKET}/{key}"


def generate_presigned_url(key: str, expires_seconds: int = 3600) -> str | None:
    client = _r2_client()
    if client is None:
        return None
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.R2_BUCKET, "Key": key},
        ExpiresIn=expires_seconds,
    )
