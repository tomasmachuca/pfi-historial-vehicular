"""Dobles de prueba para la capa on-chain y el almacén de objetos.

FakeBlockchain reproduce las reglas del contrato HistorialCeroKM (autorización,
alta única, sellado del kilometraje regresivo como anomalía, tipo 0 reservado) sin red: permite probar
la API de punta a punta sin Polygon. Los mensajes de error son los del contrato.
"""
from datetime import UTC, datetime
from types import SimpleNamespace

from eth_account import Account


class FakeBlockchain:
    address = "0x00000000000000000000000000000000000000Ab"

    def __init__(self):
        self.autorizadas: set[str] = set()
        self.vehiculos: dict[str, dict] = {}
        self.historial: dict[str, list[dict]] = {}
        self.anomalias: dict[str, list[dict]] = {}
        self.bloque = 1000
        self.w3 = SimpleNamespace(eth=SimpleNamespace(chain_id=80002))
        # Permite simular fallas de la red en una operación concreta.
        self.fallar: dict[str, Exception] = {}
        # Si es False, autorizar "no queda registrado" (falla silenciosa del nodo).
        self.autorizar_persiste = True

    def _quizas_fallar(self, operacion: str) -> None:
        if operacion in self.fallar:
            raise self.fallar[operacion]

    def _tx(self) -> dict:
        self.bloque += 1
        return {
            "tx_hash": f"0x{self.bloque:064x}",
            "block_number": self.bloque,
            "timestamp": datetime.now(UTC),
            "status": 1,
        }

    @staticmethod
    def crear_wallet() -> tuple[str, str]:
        acct = Account.create()
        return acct.address, acct.key.hex()

    def autorizar_concesionaria(self, wallet_address: str, nombre: str) -> dict:
        self._quizas_fallar("autorizar")
        if self.autorizar_persiste:
            self.autorizadas.add(wallet_address)
        return self._tx()

    def revocar_concesionaria(self, wallet_address: str) -> dict:
        self._quizas_fallar("revocar")
        self.autorizadas.discard(wallet_address)
        return self._tx()

    def es_concesionaria_autorizada(self, wallet_address: str) -> bool:
        return wallet_address in self.autorizadas

    def admin_address(self) -> str:
        return "0x0000000000000000000000000000000000000AdA"

    def fondear_wallet(self, wallet_address: str, monto_matic: str) -> dict:
        self._quizas_fallar("fondear")
        return {"tx_hash": self._tx()["tx_hash"], "status": 1}

    def balance_matic(self, address: str) -> float:
        return 0.5

    def info_red(self) -> dict:
        return {"chain_id": 80002, "rpc_url": "http://fake", "contract_address": self.address, "block_number": self.bloque}

    def _firmante(self, signer_pk: str) -> str:
        direccion = Account.from_key(signer_pk).address
        if direccion not in self.autorizadas:
            raise RuntimeError("No autorizado. Solo red oficial.")
        return direccion

    def registrar_vehiculo(self, signer_pk: str, vin: str, km_inicial: int, hash_hex: str) -> dict:
        self._quizas_fallar("registrar_vehiculo")
        direccion = self._firmante(signer_pk)
        if vin in self.vehiculos:
            raise RuntimeError("Vehiculo ya registrado")
        tx = self._tx()
        self.vehiculos[vin] = {"existe": True, "kmInicial": km_inicial, "concesionariaAlta": direccion, "fechaAlta": 0}
        self.historial[vin] = [{"kilometraje": km_inicial, "tipoServicio": 0, "hashEvidencia": "0x" + hash_hex,
                                "concesionaria": direccion, "timestamp": 0}]
        return tx

    def registrar_servicio(self, signer_pk: str, vin: str, km: int, tipo: int, hash_hex: str) -> dict:
        self._quizas_fallar("registrar_servicio")
        direccion = self._firmante(signer_pk)
        if vin not in self.vehiculos:
            raise RuntimeError("Vehiculo no registrado")
        tx = self._tx()
        vigente = self.historial[vin][-1]["kilometraje"]
        if km < vigente:
            # Como el contrato: el intento regresivo se sella como anomalía, no como evento válido.
            self.anomalias.setdefault(vin, []).append({
                "kilometrajeDeclarado": km, "kilometrajeVigente": vigente, "tipoServicio": tipo,
                "hashEvidencia": "0x" + hash_hex, "concesionaria": direccion, "timestamp": 1_760_000_000,
            })
            return {**tx, "anomalia": True, "km_vigente": vigente}
        self.historial[vin].append({"kilometraje": km, "tipoServicio": tipo, "hashEvidencia": "0x" + hash_hex,
                                    "concesionaria": direccion, "timestamp": 0})
        return {**tx, "anomalia": False, "km_vigente": None}

    def obtener_historial(self, vin: str) -> list[dict]:
        return list(self.historial.get(vin, []))

    def obtener_anomalias(self, vin: str) -> list[dict]:
        return list(self.anomalias.get(vin, []))

    def info_vehiculo(self, vin: str) -> dict | None:
        return self.vehiculos.get(vin)


class FakeStorage:
    """Registra los archivos subidos y devuelve una URL pública ficticia."""

    def __init__(self):
        self.subidos: dict[str, bytes] = {}

    def upload(self, file_bytes: bytes, key: str, content_type: str) -> str:
        self.subidos[key] = file_bytes
        return f"https://evidencias.test/{key}"
