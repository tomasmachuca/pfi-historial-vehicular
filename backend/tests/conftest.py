"""Configuracion de entorno para la suite de tests.

La app lee su configuracion con pydantic-settings al importarse (app.config),
por lo que sin estas variables no se puede ni importar app.main fuera de un
entorno con .env. Se definen aqui, antes de cualquier import de la app, con
valores ficticios: ninguna prueba abre conexiones reales contra la base ni
contra la red Polygon.
"""
import os

_ENTORNO_DE_PRUEBA = {
    # SQLite en memoria: create_engine no conecta al importar, solo valida la URL.
    "DATABASE_URL": "sqlite:///:memory:",
    "JWT_SECRET": "clave-solo-para-tests-no-usar-en-produccion",
    "RPC_URL": "http://localhost:8545",
    "CHAIN_ID": "31337",
    "CONTRACT_ADDRESS": "0x0000000000000000000000000000000000000000",
    "ADMIN_PRIVATE_KEY": "0x" + "11" * 32,
    "FRONTEND_ORIGIN": "http://localhost:5173",
}

for _clave, _valor in _ENTORNO_DE_PRUEBA.items():
    os.environ.setdefault(_clave, _valor)
