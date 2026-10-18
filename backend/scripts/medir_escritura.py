"""Mide de punta a punta la escritura y la lectura del sistema desplegado.

Da de alta un vehículo de prueba, registra services con kilometraje creciente y un
intento de kilometraje regresivo, y mide para cada operación el tiempo total que
percibe el usuario (desde que se envía el formulario hasta que la API confirma el
sellado). Luego lee de la red el gas efectivamente consumido por cada transacción
y mide la latencia de la consulta pública. Imprime los resultados como tablas en
Markdown, listas para el informe, y los guarda en un CSV.

Uso (las credenciales van por variables de entorno, no por argumentos):

    set TRAZARG_API=https://<backend>          (sin barra final)
    set TRAZARG_EMAIL=<correo de la concesionaria de prueba>
    set TRAZARG_PASSWORD=<contraseña>
    set RPC_URL=https://polygon-amoy-bor-rpc.publicnode.com
    set POL_USD=0.096                          (opcional, para convertir a dólares)
    python scripts/medir_escritura.py
"""
import csv
import os
import statistics
import sys
import time
from datetime import UTC, datetime

import requests
from web3 import Web3

API = os.environ.get("TRAZARG_API", "").rstrip("/")
EMAIL = os.environ.get("TRAZARG_EMAIL", "")
PASSWORD = os.environ.get("TRAZARG_PASSWORD", "")
RPC_URL = os.environ.get("RPC_URL", "https://polygon-amoy-bor-rpc.publicnode.com")
POL_USD = float(os.environ.get("POL_USD", "0") or 0)
SERVICES = int(os.environ.get("SERVICES", "4"))
CONSULTAS = int(os.environ.get("CONSULTAS", "20"))


def _cronometrar(fn):
    inicio = time.perf_counter()
    respuesta = fn()
    return respuesta, time.perf_counter() - inicio


def _percentil(valores, p):
    orden = sorted(valores)
    k = max(0, min(len(orden) - 1, round(p / 100 * (len(orden) - 1))))
    return orden[k]


def main() -> int:
    if not (API and EMAIL and PASSWORD):
        print("Faltan TRAZARG_API, TRAZARG_EMAIL o TRAZARG_PASSWORD.", file=sys.stderr)
        return 1

    sesion = requests.Session()
    # Despierta el servidor para no medir el arranque en frío como latencia de escritura.
    _, arranque = _cronometrar(lambda: sesion.get(f"{API}/publico/stats", timeout=120))

    login = sesion.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=60)
    login.raise_for_status()
    sesion.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

    sufijo = datetime.now(UTC).strftime("%m%d%H%M%S")
    vin, patente = f"TZPRUEBA{sufijo}", f"TZ{sufijo[-5:]}"
    operaciones = []

    alta, t = _cronometrar(lambda: sesion.post(f"{API}/vehiculos", timeout=300, data={
        "vin": vin, "patente": patente, "marca": "Prueba", "modelo": "Medición", "anio": "2026",
        "color": "Gris", "km_inicial": "0",
    }))
    alta.raise_for_status()
    operaciones.append(("Alta 0 km", 0, t, alta.json()["tx_hash_alta"], False))

    km = 0
    for i in range(SERVICES):
        km += 10_000
        r, t = _cronometrar(lambda km=km, i=i: sesion.post(f"{API}/servicios", timeout=300, data={
            "vin": vin, "tipo_servicio": "1", "kilometraje": str(km), "descripcion": f"Medición {i + 1}",
        }))
        r.raise_for_status()
        operaciones.append((f"Service {km:,} km".replace(",", "."), km, t, r.json()["tx_hash"], r.json()["km_regresivo"]))

    regresivo = km - 7_500
    r, t = _cronometrar(lambda: sesion.post(f"{API}/servicios", timeout=300, data={
        "vin": vin, "tipo_servicio": "1", "kilometraje": str(regresivo), "descripcion": "Intento regresivo",
    }))
    r.raise_for_status()
    operaciones.append(("Intento regresivo", regresivo, t, r.json()["tx_hash"], r.json()["km_regresivo"]))

    w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 60}))
    filas = []
    for nombre, km_op, segundos, tx, anomalia in operaciones:
        recibo = w3.eth.get_transaction_receipt(tx)
        costo_pol = recibo.gasUsed * recibo.effectiveGasPrice / 1e18
        filas.append({
            "operacion": nombre, "km": km_op, "latencia_s": round(segundos, 2), "anomalia": anomalia,
            "gas": recibo.gasUsed, "gas_price_gwei": round(recibo.effectiveGasPrice / 1e9, 2),
            "costo_pol": round(costo_pol, 6), "costo_usd": round(costo_pol * POL_USD, 6) if POL_USD else "",
            "bloque": recibo.blockNumber, "tx": tx,
        })

    lecturas = []
    for _ in range(CONSULTAS):
        r, t = _cronometrar(lambda: sesion.get(f"{API}/publico/vehiculo/{patente}", timeout=120))
        r.raise_for_status()
        lecturas.append(t)
    consulta = r.json()

    escrituras = [f["latencia_s"] for f in filas]
    nombre_csv = f"medicion_{sufijo}.csv"
    with open(nombre_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)

    print(f"\nMedición del {datetime.now(UTC):%d/%m/%Y %H:%M} UTC contra {API} (vehículo {vin}, patente {patente})")
    print(f"Primer pedido (arranque del servidor): {arranque:.1f} s\n")
    print("| Operación | Km | Latencia (s) | Gas | Gas price (gwei) | Costo (POL) | Costo (USD) | Anomalía | Tx |")
    print("|---|---|---|---|---|---|---|---|---|")
    for f in filas:
        print(f"| {f['operacion']} | {f['km']} | {f['latencia_s']} | {f['gas']} | {f['gas_price_gwei']} | "
              f"{f['costo_pol']} | {f['costo_usd']} | {'Sí' if f['anomalia'] else 'No'} | {f['tx']} |")
    print(f"\nEscritura: mediana {statistics.median(escrituras):.2f} s, "
          f"percentil 95 {_percentil(escrituras, 95):.2f} s, máximo {max(escrituras):.2f} s")
    print(f"Consulta pública ({CONSULTAS} pedidos): mediana {statistics.median(lecturas):.2f} s, "
          f"percentil 95 {_percentil(lecturas, 95):.2f} s")
    print(f"Anomalías en cadena según la consulta: {consulta['cadena']['anomalias_on_chain']}")
    print(f"Puntaje del vehículo de prueba: {consulta['score']['puntaje']}")
    print(f"\nCSV: {nombre_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
