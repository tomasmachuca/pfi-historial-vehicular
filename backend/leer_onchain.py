"""
Lee el kilometraje y el historial de un vehiculo DIRECTO de la blockchain (Polygon Amoy),
sin pasar por el backend ni el frontend. Solo consulta el RPC y el contrato.

Uso:
    ./.venv/Scripts/python.exe leer_onchain.py <VIN>
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# --- Config de la red (los mismos valores del .env, hardcodeables si querés) ---
RPC_URL = "https://polygon-amoy-bor-rpc.publicnode.com"
CONTRACT = "0xB6B07B384265D5087497863fd12977ecf1f98Bbb"
ABI_PATH = Path(__file__).resolve().parent / "app" / "abi" / "HistorialCeroKM.json"

TIPOS = {0: "Alta / 0km", 1: "Service", 2: "Reparacion", 3: "Inspeccion"}


def main(vin: str) -> None:
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    abi = json.loads(ABI_PATH.read_text(encoding="utf-8"))["abi"]
    c = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT), abi=abi)

    print(f"Red: Amoy chainId={w3.eth.chain_id}  bloque={w3.eth.block_number}")
    print(f"Contrato: {CONTRACT}")
    print(f"VIN consultado: {vin}\n")

    existe, km_inicial, alta, fecha_alta = c.functions.vehiculos(vin).call()
    if not existe:
        print("El VIN no existe on-chain.")
        return

    fa = datetime.fromtimestamp(fecha_alta, tz=timezone.utc)
    print(f"km inicial (alta 0km): {km_inicial:,} km")
    print(f"concesionaria de alta: {alta}")
    print(f"fecha de alta:         {fa:%Y-%m-%d %H:%M UTC}\n")

    eventos = c.functions.obtenerHistorial(vin).call()
    print(f"Historial on-chain ({len(eventos)} eventos):")
    for i, e in enumerate(eventos):
        km, tipo, hash_ev, conces, ts = e
        f = datetime.fromtimestamp(ts, tz=timezone.utc)
        print(
            f"  #{i}  {km:>10,} km  {TIPOS.get(tipo, tipo):<12}  "
            f"{f:%Y-%m-%d %H:%M}  by {conces[:10]}...  "
            f"hash=0x{hash_ev.hex()[:12]}..."
        )


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "VW12345678")
