"""Baja de la cuenta de una concesionaria (derecho de supresión, Ley 25.326).

La baja no puede borrar lo que ya está en la cadena, y tampoco debe borrar los
services que la concesionaria registró: son parte del historial de vehículos que
hoy pertenecen a otras personas. Lo que sí hace es:

1. Revocar la autorización en el contrato, para que la billetera no pueda volver
   a escribir.
2. Suprimir las credenciales y los datos de contacto: correo, contraseña, CUIT y
   la clave privada custodiada (sin ella, nadie puede volver a firmar en su nombre).

Se conservan la razón social y la dirección de la billetera, que ya constan en la
cadena y permiten atribuir los asientos históricos.
"""
import secrets
from typing import Any

from app.models import Concesionaria
from app.services.security import hash_password


def revocar_en_contrato(c: Concesionaria, bc) -> dict[str, Any] | None:
    """Revoca la billetera en el contrato si todavía está autorizada."""
    if not bc.es_concesionaria_autorizada(c.wallet_address):
        return None
    return bc.revocar_concesionaria(c.wallet_address)


def suprimir_datos(c: Concesionaria) -> None:
    c.activa = False
    c.email = f"baja-{c.id}@baja.invalid"
    c.cuit = None
    # Un hash de una contraseña aleatoria que nadie conoce: la cuenta no admite login.
    c.password_hash = hash_password(secrets.token_urlsafe(32))
    c.wallet_pk_enc = ""


def dar_de_baja(c: Concesionaria, bc) -> dict[str, Any]:
    """Revoca primero en cadena: si falla, la cuenta queda intacta y se puede reintentar."""
    revocacion = revocar_en_contrato(c, bc)
    suprimir_datos(c)
    return {
        "ok": True,
        "revocada_on_chain": revocacion is not None,
        "tx_hash": revocacion["tx_hash"] if revocacion else None,
    }
