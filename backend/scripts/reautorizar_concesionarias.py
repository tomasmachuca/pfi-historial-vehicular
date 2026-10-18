"""Autoriza en el contrato configurado (CONTRACT_ADDRESS) a las concesionarias activas.

Después de desplegar un contrato nuevo, las billeteras de las concesionarias no
están autorizadas en él. Este script recorre las concesionarias activas de la base
y autoriza en el contrato a las que todavía no lo están, con la clave del
administrador. Informa además el saldo de cada billetera para el gas.

Uso, desde backend/ y con el .env apuntando al contrato nuevo:

    python scripts/reautorizar_concesionarias.py            (solo informa)
    python scripts/reautorizar_concesionarias.py --aplicar  (autoriza)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models import Concesionaria
from app.services.blockchain import get_blockchain


def main() -> int:
    aplicar = "--aplicar" in sys.argv
    bc = get_blockchain()
    print(f"Contrato: {bc.address}")
    with SessionLocal() as db:
        activas = db.query(Concesionaria).filter(Concesionaria.activa.is_(True)).all()
        print(f"Concesionarias activas: {len(activas)}")
        for c in activas:
            autorizada = bc.es_concesionaria_autorizada(c.wallet_address)
            saldo = bc.balance_matic(c.wallet_address)
            estado = "ya autorizada" if autorizada else "sin autorizar"
            if not autorizada and aplicar:
                res = bc.autorizar_concesionaria(c.wallet_address, c.nombre)
                estado = f"autorizada (tx {res['tx_hash']})"
            print(f"- {c.nombre} | {c.wallet_address} | saldo {saldo:.4f} POL | {estado}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
