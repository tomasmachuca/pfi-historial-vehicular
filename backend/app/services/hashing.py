import hashlib

# Se sella en cadena cuando el evento no tiene comprobante adjunto: deja
# explícito, para cualquier lector del contrato, que no hay documento que verificar.
ZERO_HASH_HEX = "0" * 64


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_to_bytes32(hex_hash: str) -> bytes:
    h = hex_hash.removeprefix("0x")
    if len(h) != 64:
        raise ValueError("Hash SHA-256 invalido")
    return bytes.fromhex(h)
