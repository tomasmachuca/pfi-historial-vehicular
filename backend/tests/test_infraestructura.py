"""Pruebas unitarias de los adaptadores de infraestructura: blockchain, almacenamiento y utilidades.

El adaptador de blockchain se prueba sin red: se reemplazan el proveedor web3 y el
contrato por dobles, y se verifica la lógica propia (preflight, manejo de reverts,
conversión de tipos), que es lo que el proyecto agrega sobre web3.py.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from eth_account import Account
from web3 import Web3

from app.services import blockchain as bc_mod
from app.services import storage
from app.services.blockchain import BlockchainService, _extract_revert_reason
from app.services.hashing import sha256_bytes, sha256_to_bytes32

CLAVE = "0x" + "22" * 32
DESTINO = Web3.to_checksum_address("0x" + "33" * 20)


# --- Extracción del motivo de un revert ----------------------------------------

@pytest.mark.parametrize(
    ("error", "esperado"),
    [
        (Exception("execution reverted: Kilometraje regresivo"), "Kilometraje regresivo"),
        (Exception("execution reverted: 'No autorizado. Solo red oficial.'"), "No autorizado. Solo red oficial."),
        (Exception({"message": "execution reverted: Vehiculo ya registrado"}), "Vehiculo ya registrado"),
        (Exception(""), "Exception"),
    ],
)
def test_extract_revert_reason(error, esperado):
    assert _extract_revert_reason(error) == esperado


def test_extract_revert_reason_usa_el_atributo_message():
    error = Exception("genérico")
    error.message = "execution reverted: Tipo 0 reservado para alta"
    assert _extract_revert_reason(error) == "Tipo 0 reservado para alta"


# --- Adaptador de blockchain --------------------------------------------------

@pytest.fixture()
def svc():
    """Servicio real, construido con la configuración de prueba, con red y contrato simulados."""
    s = BlockchainService()
    s.w3 = MagicMock()
    s.w3.to_wei = Web3.to_wei
    s.w3.from_wei = Web3.from_wei
    s.w3.eth.get_transaction_count.return_value = 0
    s.w3.eth.send_raw_transaction.return_value = bytes.fromhex("ab" * 32)
    s.w3.eth.wait_for_transaction_receipt.return_value = SimpleNamespace(status=1, blockNumber=77)
    s.w3.eth.get_block.return_value = SimpleNamespace(timestamp=1_760_000_000)
    s.contract = MagicMock()
    return s


def _preparar_funcion(s, nombre):
    fn = getattr(s.contract.functions, nombre).return_value
    fn.build_transaction.return_value = {
        "to": DESTINO, "data": "0x", "value": 0, "gas": 500_000, "maxFeePerGas": 1,
        "maxPriorityFeePerGas": 1, "nonce": 0, "chainId": 80002,
    }
    return fn


def test_construccion_lee_abi_y_direccion():
    s = BlockchainService()
    assert any(item.get("name") == "registrarServicio" for item in s.abi)
    assert Web3.is_checksum_address(s.address)


def test_registrar_vehiculo_envia_y_devuelve_el_recibo(svc):
    fn = _preparar_funcion(svc, "registrarVehiculo")
    res = svc.registrar_vehiculo(CLAVE, "8AP1234567ABC8901", 0, "ab" * 32)
    assert res["block_number"] == 77 and res["status"] == 1
    assert res["tx_hash"] == "ab" * 32
    fn.call.assert_called_once()
    args = svc.contract.functions.registrarVehiculo.call_args.args
    assert args[0] == "8AP1234567ABC8901" and args[2] == bytes.fromhex("ab" * 32)


def test_registrar_servicio_detecta_el_revert_antes_de_gastar_gas(svc):
    fn = _preparar_funcion(svc, "registrarServicio")
    fn.call.side_effect = Exception("execution reverted: Kilometraje regresivo")
    with pytest.raises(RuntimeError, match="Kilometraje regresivo"):
        svc.registrar_servicio(CLAVE, "VIN12", 10, 1, "00" * 32)
    svc.w3.eth.send_raw_transaction.assert_not_called()


def test_transaccion_revertida_en_cadena_informa_el_motivo(svc):
    _preparar_funcion(svc, "registrarServicio")
    svc.w3.eth.wait_for_transaction_receipt.return_value = SimpleNamespace(status=0, blockNumber=78)
    svc.w3.eth.call.side_effect = Exception("execution reverted: No autorizado. Solo red oficial.")
    with pytest.raises(RuntimeError, match="No autorizado"):
        svc.registrar_servicio(CLAVE, "VIN12", 10, 1, "00" * 32)


def test_transaccion_revertida_sin_motivo(svc):
    _preparar_funcion(svc, "registrarServicio")
    svc.w3.eth.wait_for_transaction_receipt.return_value = SimpleNamespace(status=0, blockNumber=78)
    with pytest.raises(RuntimeError, match="sin razón"):
        svc.registrar_servicio(CLAVE, "VIN12", 10, 1, "00" * 32)


def test_autorizar_y_revocar_firman_con_la_clave_de_admin(svc):
    svc._send = MagicMock(return_value={"tx_hash": "0x1"})
    svc.autorizar_concesionaria(DESTINO.lower(), "Concesionaria")
    svc.revocar_concesionaria(DESTINO.lower())
    llamadas = [c.args[1] for c in svc._send.call_args_list]
    assert llamadas == ["autorizarConcesionaria", "revocarConcesionaria"]
    assert all(c.args[2] == DESTINO for c in svc._send.call_args_list)


def test_lecturas_del_contrato(svc):
    svc.contract.functions.concesionariasOficiales.return_value.call.return_value = True
    svc.contract.functions.admin.return_value.call.return_value = DESTINO
    assert svc.es_concesionaria_autorizada(DESTINO) is True
    assert svc.admin_address() == DESTINO

    svc.contract.functions.obtenerHistorial.return_value.call.return_value = [
        (0, 0, b"\x00" * 32, DESTINO, 100),
        (10_000, 1, "0xabc", DESTINO, 200),
    ]
    historial = svc.obtener_historial("VIN12")
    assert historial[0]["hashEvidencia"] == "0x" + "00" * 32
    assert historial[1] == {"kilometraje": 10_000, "tipoServicio": 1, "hashEvidencia": "0xabc",
                            "concesionaria": DESTINO, "timestamp": 200}

    svc.contract.functions.vehiculos.return_value.call.return_value = (False, 0, DESTINO, 0)
    assert svc.info_vehiculo("VIN12") is None
    svc.contract.functions.vehiculos.return_value.call.return_value = (True, 5, DESTINO, 300)
    assert svc.info_vehiculo("VIN12") == {"existe": True, "kmInicial": 5, "concesionariaAlta": DESTINO, "fechaAlta": 300}


def test_fondear_balance_e_info_de_red(svc):
    assert svc.fondear_wallet(DESTINO, "0.5") == {"tx_hash": "ab" * 32, "status": 1}
    svc.w3.eth.get_balance.return_value = Web3.to_wei(1.5, "ether")
    assert svc.balance_matic(DESTINO) == 1.5
    svc.w3.eth.block_number = 123
    assert svc.info_red()["block_number"] == 123


def test_crear_wallet_genera_un_par_valido():
    direccion, clave = BlockchainService.crear_wallet()
    assert Account.from_key(clave).address == direccion


def test_get_blockchain_es_un_singleton(monkeypatch):
    monkeypatch.setattr(bc_mod, "_blockchain", None)
    monkeypatch.setattr(bc_mod, "BlockchainService", lambda: object())
    assert bc_mod.get_blockchain() is bc_mod.get_blockchain()


# --- Almacenamiento de evidencia (Cloudflare R2) -------------------------------

def test_sin_r2_configurado_no_sube_nada(monkeypatch):
    monkeypatch.setattr(storage.settings, "R2_ACCOUNT_ID", "")
    assert storage.upload_evidencia(b"x", "k", "text/plain") == ""
    assert storage.generate_presigned_url("k") is None


def test_con_r2_sube_y_firma_urls(monkeypatch):
    cliente = MagicMock()
    cliente.generate_presigned_url.return_value = "https://firmada"
    monkeypatch.setattr(storage.settings, "R2_ACCOUNT_ID", "cuenta")
    monkeypatch.setattr(storage.boto3, "client", lambda *a, **k: cliente)

    monkeypatch.setattr(storage.settings, "R2_PUBLIC_URL", "https://evidencias.example/")
    assert storage.upload_evidencia(b"x", "vehiculos/a.pdf", "application/pdf") == "https://evidencias.example/vehiculos/a.pdf"
    monkeypatch.setattr(storage.settings, "R2_PUBLIC_URL", "")
    assert storage.upload_evidencia(b"x", "vehiculos/a.pdf", "application/pdf").startswith("r2://")
    assert cliente.put_object.call_count == 2
    assert storage.generate_presigned_url("vehiculos/a.pdf") == "https://firmada"


# --- Utilidades ---------------------------------------------------------------

def test_hash_a_bytes32():
    h = sha256_bytes(b"comprobante")
    assert sha256_to_bytes32(h) == sha256_to_bytes32("0x" + h) == bytes.fromhex(h)
    with pytest.raises(ValueError):
        sha256_to_bytes32("abc")


def test_get_db_entrega_y_cierra_la_sesion():
    from app.database import get_db

    generador = get_db()
    sesion = next(generador)
    assert sesion is not None
    with pytest.raises(StopIteration):
        next(generador)
