import hashlib


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_to_bytes32(hex_hash: str) -> bytes:
    h = hex_hash[2:] if hex_hash.startswith("0x") else hex_hash
    if len(h) != 64:
        raise ValueError("Hash SHA-256 invalido")
    return bytes.fromhex(h)
