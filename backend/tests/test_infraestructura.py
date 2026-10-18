"""Pruebas unitarias de los adaptadores de infraestructura: blockchain, almacenamiento y utilidades.

El adaptador de blockchain se prueba sin red: se reemplazan el proveedor web3 y el
contrato por dobles, y se verifica la lógica propia (preflight, manejo de reverts,
conversión de tipos), que es lo que el proyecto agrega sobre web3.py.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import requests
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
    fn.call.side_effect = Exception("execution reverted: Vehiculo no registrado")
    with pytest.raises(RuntimeError, match="Vehiculo no registrado"):
        svc.registrar_servicio(CLAVE, "VIN12", 10, 1, "00" * 32)
    svc.w3.eth.send_raw_transaction.assert_not_called()


def test_registrar_servicio_valido_no_informa_anomalia(svc):
    _preparar_funcion(svc, "registrarServicio")
    svc.contract.events.AnomaliaKilometraje.return_value.process_receipt.return_value = []
    res = svc.registrar_servicio(CLAVE, "VIN12", 10_000, 1, "00" * 32)
    assert res["anomalia"] is False and res["km_vigente"] is None
    assert res["tx_hash"] == "ab" * 32


def test_registrar_servicio_lee_la_anomalia_del_recibo(svc):
    _preparar_funcion(svc, "registrarServicio")
    svc.contract.events.AnomaliaKilometraje.return_value.process_receipt.return_value = [
        {"args": {"kilometrajeVigente": 30_560}}
    ]
    res = svc.registrar_servicio(CLAVE, "VIN12", 18_400, 2, "00" * 32)
    assert res["anomalia"] is True and res["km_vigente"] == 30_560
    svc.w3.eth.send_raw_transaction.assert_called_once()


def test_lectura_de_anomalias(svc):
    svc.contract.functions.obtenerAnomalias.return_value.call.return_value = [
        (18_400, 30_560, 2, b"\x00" * 32, DESTINO, 500),
    ]
    assert svc.obtener_anomalias("VIN12") == [{
        "kilometrajeDeclarado": 18_400, "kilometrajeVigente": 30_560, "tipoServicio": 2,
        "hashEvidencia": "0x" + "00" * 32, "concesionaria": DESTINO, "timestamp": 500,
    }]


# --- Proveedor RPC de respaldo -------------------------------------------------

def test_lee_los_proveedores_de_respaldo(monkeypatch):
    monkeypatch.setattr(bc_mod.settings, "RPC_URL_FALLBACK", "http://respaldo-1, ,http://respaldo-2")
    s = BlockchainService()
    assert s.proveedores == [bc_mod.settings.RPC_URL, "http://respaldo-1", "http://respaldo-2"]


def test_ante_una_falla_de_red_pasa_al_proveedor_de_respaldo(svc):
    svc.proveedores = ["http://principal", "http://respaldo"]
    svc.proveedor_activo = 0
    svc._usar_proveedor = MagicMock(side_effect=lambda i: setattr(svc, "proveedor_activo", i))
    intentos = []

    def operacion():
        intentos.append(svc.proveedor_activo)
        if len(intentos) == 1:
            raise requests.exceptions.ConnectionError("nodo caído")
        return "ok"

    assert svc._con_respaldo(operacion) == "ok"
    assert intentos == [0, 1]


def test_sin_respaldo_informa_que_no_hay_proveedor(svc):
    svc.proveedores = ["http://principal"]
    svc.proveedor_activo = 0

    def operacion():
        raise requests.exceptions.Timeout("sin respuesta")

    with pytest.raises(bc_mod.ProveedorNoDisponible, match="Ningún proveedor RPC responde"):
        svc._con_respaldo(operacion)


def test_una_falla_de_red_en_el_preflight_no_se_confunde_con_un_revert(svc):
    fn = _preparar_funcion(svc, "registrarServicio")
    fn.call.side_effect = requests.exceptions.ConnectionError("nodo caído")
    with pytest.raises(bc_mod.ProveedorNoDisponible):
        svc.registrar_servicio(CLAVE, "VIN12", 10, 1, "00" * 32)
    svc.w3.eth.send_raw_transaction.assert_not_called()


def test_una_falla_de_red_al_pedir_el_nonce_habilita_el_reintento(svc):
    _preparar_funcion(svc, "registrarServicio")
    svc.w3.eth.get_transaction_count.side_effect = requests.exceptions.Timeout("sin respuesta")
    with pytest.raises(bc_mod.ProveedorNoDisponible):
        svc.registrar_servicio(CLAVE, "VIN12", 10, 1, "00" * 32)


def test_cambiar_de_proveedor_reconstruye_el_cliente():
    s = BlockchainService()
    s.proveedores = ["http://principal", "http://respaldo"]
    assert s._pasar_al_respaldo() is True
    assert s.proveedor_activo == 1 and s.contract.address == s.address
    assert s._pasar_al_respaldo() is False


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
    assert svc.info_red()["proveedores_rpc"] == len(svc.proveedores)


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


# --- Cifrado de las claves custodiadas ------------------------------------------

def test_cifrado_con_llave_propia_y_compatibilidad_con_la_anterior(monkeypatch):
    from cryptography.fernet import Fernet, InvalidToken

    from app.services import security

    clave_privada = "0x" + "44" * 32
    monkeypatch.setattr(security.settings, "WALLET_ENCRYPTION_KEY", "")
    cifrada_antes = security.encrypt_pk(clave_privada)

    monkeypatch.setattr(security.settings, "WALLET_ENCRYPTION_KEY", Fernet.generate_key().decode())
    cifrada_ahora = security.encrypt_pk(clave_privada)
    # Lo cifrado con la llave propia no se descifra con la derivada del secreto de sesiones.
    with pytest.raises(InvalidToken):
        security._fernet_legacy().decrypt(cifrada_ahora.encode())
    assert security.decrypt_pk(cifrada_ahora) == clave_privada
    assert security.decrypt_pk(cifrada_antes) == clave_privada
    rotada = security.recifrar_pk(cifrada_antes)
    assert security.decrypt_pk(rotada) == clave_privada
    with pytest.raises(InvalidToken):
        security._fernet_legacy().decrypt(rotada.encode())


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
