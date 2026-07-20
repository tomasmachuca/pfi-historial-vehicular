import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eth_account import Account
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app.config import settings
from app.services.hashing import sha256_to_bytes32


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

        self.w3 = Web3(Web3.HTTPProvider(settings.RPC_URL))
        # Polygon (y cualquier red PoA) tiene extraData > 32 bytes en los bloques.
        # Sin este middleware web3.py lanza error al leer cabeceras de bloque.
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        self.contract = self.w3.eth.contract(address=self.address, abi=self.abi)
        self.admin = Account.from_key(settings.ADMIN_PRIVATE_KEY)

    @staticmethod
    def crear_wallet() -> tuple[str, str]:
        acct = Account.create()
        return acct.address, acct.key.hex()

    def _send(self, signer_pk: str, fn_name: str, *args) -> dict[str, Any]:
        signer = Account.from_key(signer_pk)
        fn = getattr(self.contract.functions, fn_name)(*args)

        # Pre-flight: simular la llamada para detectar reverts antes de gastar gas.
        # Si revierte, web3 levanta ContractLogicError con el mensaje del require().
        try:
            fn.call({"from": signer.address})
        except Exception as e:
            raise RuntimeError(_extract_revert_reason(e)) from e

        nonce = self.w3.eth.get_transaction_count(signer.address)
        tx = fn.build_transaction({
            "from": signer.address,
            "nonce": nonce,
            "chainId": settings.CHAIN_ID,
            "gas": 500_000,
            "maxFeePerGas": self.w3.to_wei("80", "gwei"),
            "maxPriorityFeePerGas": self.w3.to_wei("30", "gwei"),
        })
        signed = signer.sign_transaction(tx)
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
            "timestamp": datetime.fromtimestamp(block.timestamp, tz=timezone.utc),
            "status": receipt.status,
        }

    def autorizar_concesionaria(self, wallet_address: str, nombre: str) -> dict[str, Any]:
        return self._send(
            settings.ADMIN_PRIVATE_KEY,
            "autorizarConcesionaria",
            Web3.to_checksum_address(wallet_address),
            nombre,
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
        return self._send(
            signer_pk,
            "registrarServicio",
            vin,
            km,
            tipo,
            sha256_to_bytes32(hash_evidencia_hex),
        )

    def obtener_historial(self, vin: str) -> list[dict]:
        eventos = self.contract.functions.obtenerHistorial(vin).call()
        result = []
        for e in eventos:
            result.append({
                "kilometraje": int(e[0]),
                "tipoServicio": int(e[1]),
                "hashEvidencia": "0x" + e[2].hex() if isinstance(e[2], (bytes, bytearray)) else str(e[2]),
                "concesionaria": e[3],
                "timestamp": int(e[4]),
            })
        return result

    def info_vehiculo(self, vin: str) -> dict | None:
        v = self.contract.functions.vehiculos(vin).call()
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
            "rpc_url": settings.RPC_URL,
            "contract_address": settings.CONTRACT_ADDRESS,
            "block_number": self.w3.eth.block_number,
        }


_blockchain: BlockchainService | None = None


def get_blockchain() -> BlockchainService:
    global _blockchain
    if _blockchain is None:
        _blockchain = BlockchainService()
    return _blockchain
