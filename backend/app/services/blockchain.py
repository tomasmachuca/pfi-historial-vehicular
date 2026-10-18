import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
from eth_account import Account
from web3 import Web3
from web3.logs import DISCARD
from web3.middleware import ExtraDataToPOAMiddleware

from app.config import settings
from app.services.hashing import sha256_to_bytes32

# Fallas del proveedor de acceso (nodo caído, timeout), a diferencia de un revert del contrato.
_ERRORES_DE_RED = (requests.exceptions.ConnectionError, requests.exceptions.Timeout)


class ProveedorNoDisponible(RuntimeError):
    """Ningún proveedor RPC respondió antes de enviar la transacción."""


def _hex(valor) -> str:
    return "0x" + valor.hex() if isinstance(valor, (bytes, bytearray)) else str(valor)


def _extract_revert_reason(err: Exception) -> str:
    msg = str(err) or err.__class__.__name__
    for attr in ("message", "args"):
        val = getattr(err, attr, None)
        if isinstance(val, str) and val:
            msg = val
            break
        if isinstance(val, (list, tuple)) and val:
            for item in val:
                if isinstance(item, dict) and isinstance(item.get("message"), str):
                    msg = item["message"]
                    break
                if isinstance(item, str) and item:
                    msg = item
                    break
    if "execution reverted:" in msg:
        msg = msg.split("execution reverted:", 1)[1].strip().strip("'\"")
    return msg.strip() or "transacción revertida"


class BlockchainService:
    def __init__(self):
        abi_path = Path(settings.CONTRACT_ABI_PATH)
        if not abi_path.is_absolute():
            abi_path = Path(__file__).resolve().parent.parent.parent / abi_path
        with open(abi_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.abi = data["abi"]
        self.address = Web3.to_checksum_address(settings.CONTRACT_ADDRESS)

        # Proveedor principal y, opcionalmente, proveedores de respaldo. La conexión
        # no se prueba al construir: se pasa al siguiente solo ante una falla de red.
        self.proveedores = [settings.RPC_URL] + [
            u.strip() for u in settings.RPC_URL_FALLBACK.split(",") if u.strip()
        ]
        self._usar_proveedor(0)
        self.admin = Account.from_key(settings.ADMIN_PRIVATE_KEY)

    def _usar_proveedor(self, indice: int) -> None:
        self.proveedor_activo = indice
        self.w3 = Web3(Web3.HTTPProvider(self.proveedores[indice], request_kwargs={"timeout": 30}))
        # Polygon (y cualquier red PoA) tiene extraData > 32 bytes en los bloques.
        # Sin este middleware web3.py lanza error al leer cabeceras de bloque.
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        self.contract = self.w3.eth.contract(address=self.address, abi=self.abi)

    def _pasar_al_respaldo(self) -> bool:
        if self.proveedor_activo + 1 >= len(self.proveedores):
            return False
        self._usar_proveedor(self.proveedor_activo + 1)
        return True

    def _con_respaldo(self, operacion):
        """Ejecuta una operación y, si falla la red, la reintenta con el proveedor siguiente."""
        while True:
            try:
                return operacion()
            except (*_ERRORES_DE_RED, ProveedorNoDisponible) as e:
                if not self._pasar_al_respaldo():
                    raise ProveedorNoDisponible(f"Ningún proveedor RPC responde: {e}") from e

    @staticmethod
    def crear_wallet() -> tuple[str, str]:
        acct = Account.create()
        return acct.address, acct.key.hex()

    def _send(self, signer_pk: str, fn_name: str, *args) -> dict[str, Any]:
        return self._send_con_recibo(signer_pk, fn_name, *args)[0]

    def _send_con_recibo(self, signer_pk: str, fn_name: str, *args) -> tuple[dict[str, Any], Any]:
        return self._con_respaldo(lambda: self._send_una_vez(signer_pk, fn_name, *args))

    def _send_una_vez(self, signer_pk: str, fn_name: str, *args) -> tuple[dict[str, Any], Any]:
        signer = Account.from_key(signer_pk)
        fn = getattr(self.contract.functions, fn_name)(*args)

        # Pre-flight: simular la llamada para detectar reverts antes de gastar gas.
        # Si revierte, web3 levanta ContractLogicError con el mensaje del require().
        # Una falla de red, en cambio, habilita el reintento con otro proveedor.
        try:
            fn.call({"from": signer.address})
        except _ERRORES_DE_RED as e:
            raise ProveedorNoDisponible(str(e)) from e
        except Exception as e:
            raise RuntimeError(_extract_revert_reason(e)) from e

        try:
            nonce = self.w3.eth.get_transaction_count(signer.address)
        except _ERRORES_DE_RED as e:
            raise ProveedorNoDisponible(str(e)) from e
        tx = fn.build_transaction({
            "from": signer.address,
            "nonce": nonce,
            "chainId": settings.CHAIN_ID,
            "gas": 500_000,
            "maxFeePerGas": self.w3.to_wei("80", "gwei"),
            "maxPriorityFeePerGas": self.w3.to_wei("30", "gwei"),
        })
        signed = signer.sign_transaction(tx)
        # A partir del envío no se reintenta: reenviar podría duplicar la transacción.
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

        if receipt.status != 1:
            # Reintento como eth_call al bloque del receipt para extraer la razón.
            try:
                self.w3.eth.call(
                    {
                        "to": tx["to"],
                        "from": signer.address,
                        "data": tx["data"],
                        "value": tx.get("value", 0),
                    },
                    block_identifier=receipt.blockNumber,
                )
                reason = "transacción revertida sin razón"
            except Exception as e:
                reason = _extract_revert_reason(e)
            raise RuntimeError(
                f"Transacción revertida on-chain ({tx_hash.hex()}): {reason}"
            )

        block = self.w3.eth.get_block(receipt.blockNumber)
        return {
            "tx_hash": tx_hash.hex(),
            "block_number": receipt.blockNumber,
            "timestamp": datetime.fromtimestamp(block.timestamp, tz=UTC),
            "status": receipt.status,
            "gas_used": getattr(receipt, "gasUsed", None),
        }, receipt

    def autorizar_concesionaria(self, wallet_address: str, nombre: str) -> dict[str, Any]:
        return self._send(
            settings.ADMIN_PRIVATE_KEY,
            "autorizarConcesionaria",
            Web3.to_checksum_address(wallet_address),
            nombre,
        )

    def revocar_concesionaria(self, wallet_address: str) -> dict[str, Any]:
        return self._send(
            settings.ADMIN_PRIVATE_KEY,
            "revocarConcesionaria",
            Web3.to_checksum_address(wallet_address),
        )

    def es_concesionaria_autorizada(self, wallet_address: str) -> bool:
        return bool(
            self.contract.functions.concesionariasOficiales(
                Web3.to_checksum_address(wallet_address)
            ).call()
        )

    def admin_address(self) -> str:
        return self.contract.functions.admin().call()

    def fondear_wallet(self, wallet_address: str, monto_matic: str) -> dict[str, Any]:
        nonce = self.w3.eth.get_transaction_count(self.admin.address)
        tx = {
            "to": Web3.to_checksum_address(wallet_address),
            "value": self.w3.to_wei(monto_matic, "ether"),
            "gas": 21000,
            "maxFeePerGas": self.w3.to_wei("80", "gwei"),
            "maxPriorityFeePerGas": self.w3.to_wei("30", "gwei"),
            "nonce": nonce,
            "chainId": settings.CHAIN_ID,
        }
        signed = self.admin.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        return {"tx_hash": tx_hash.hex(), "status": receipt.status}

    def registrar_vehiculo(self, signer_pk: str, vin: str, km_inicial: int, hash_evidencia_hex: str):
        return self._send(
            signer_pk,
            "registrarVehiculo",
            vin,
            km_inicial,
            sha256_to_bytes32(hash_evidencia_hex),
        )

    def registrar_servicio(
        self, signer_pk: str, vin: str, km: int, tipo: int, hash_evidencia_hex: str
    ):
        """Sella un service. El contrato decide si es válido o una anomalía de
        kilometraje regresivo; la decisión se lee del evento emitido en el recibo."""
        res, recibo = self._send_con_recibo(
            signer_pk,
            "registrarServicio",
            vin,
            km,
            tipo,
            sha256_to_bytes32(hash_evidencia_hex),
        )
        anomalias = self.contract.events.AnomaliaKilometraje().process_receipt(recibo, errors=DISCARD)
        res["anomalia"] = len(anomalias) > 0
        res["km_vigente"] = int(anomalias[0]["args"]["kilometrajeVigente"]) if anomalias else None
        return res

    def obtener_historial(self, vin: str) -> list[dict]:
        eventos = self._con_respaldo(lambda: self.contract.functions.obtenerHistorial(vin).call())
        return [
            {
                "kilometraje": int(e[0]),
                "tipoServicio": int(e[1]),
                "hashEvidencia": _hex(e[2]),
                "concesionaria": e[3],
                "timestamp": int(e[4]),
            }
            for e in eventos
        ]

    def obtener_anomalias(self, vin: str) -> list[dict]:
        anomalias = self._con_respaldo(lambda: self.contract.functions.obtenerAnomalias(vin).call())
        return [
            {
                "kilometrajeDeclarado": int(a[0]),
                "kilometrajeVigente": int(a[1]),
                "tipoServicio": int(a[2]),
                "hashEvidencia": _hex(a[3]),
                "concesionaria": a[4],
                "timestamp": int(a[5]),
            }
            for a in anomalias
        ]

    def info_vehiculo(self, vin: str) -> dict | None:
        v = self._con_respaldo(lambda: self.contract.functions.vehiculos(vin).call())
        if not v[0]:
            return None
        return {
            "existe": v[0],
            "kmInicial": int(v[1]),
            "concesionariaAlta": v[2],
            "fechaAlta": int(v[3]),
        }

    def balance_matic(self, address: str) -> float:
        wei = self.w3.eth.get_balance(Web3.to_checksum_address(address))
        return float(self.w3.from_wei(wei, "ether"))

    def info_red(self) -> dict:
        return {
            "chain_id": settings.CHAIN_ID,
            "rpc_url": self.proveedores[self.proveedor_activo],
            "proveedores_rpc": len(self.proveedores),
            "contract_address": settings.CONTRACT_ADDRESS,
            "block_number": self.w3.eth.block_number,
        }


_blockchain: BlockchainService | None = None


def get_blockchain() -> BlockchainService:
    global _blockchain
    if _blockchain is None:
        _blockchain = BlockchainService()
    return _blockchain
