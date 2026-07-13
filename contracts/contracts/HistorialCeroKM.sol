// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/// @title HistorialCeroKM
/// @notice Registro inmutable de eventos de mantenimiento vehicular.
/// @dev Solo concesionarias autorizadas pueden registrar eventos.
contract HistorialCeroKM is Ownable, Pausable {
    struct Evento {
        uint256 kilometraje;
        uint8 tipoServicio;
        bytes32 hashEvidencia;
        address concesionaria;
        uint256 timestamp;
    }

    // Mapping VIN -> arreglo de eventos
    mapping(string => Evento[]) private historial;
    // Mapping de concesionarias autorizadas
    mapping(address => bool) public concesionariasOficiales;
    // Metricas operativas por concesionaria
    mapping(address => uint256) public operacionesPorConcesionaria;
    mapping(address => uint256) public ultimaOperacionConcesionaria;

    // ========= Events =========
    event ConcesionariaAutorizada(address indexed dealer, uint256 ts);
    event ConcesionariaRevocada(address indexed dealer, uint256 ts);
    event ServicioRegistrado(
        string indexed vin,
        uint256 km,
        uint8 tipoServicio,
        address indexed concesionaria,
        bytes32 hashEvidencia,
        uint256 timestamp,
        uint256 indiceEvento
    );

    // ========= Modificadores =========
    modifier soloConcesionaria() {
        require(concesionariasOficiales[msg.sender], "No autorizado");
        _;
    }

    constructor() Ownable(msg.sender) {}

    // ========= Administracion =========
    function autorizarConcesionaria(address dealer) external onlyOwner {
        require(dealer != address(0), "Direccion invalida");
        concesionariasOficiales[dealer] = true;
        emit ConcesionariaAutorizada(dealer, block.timestamp);
    }

    function revocarConcesionaria(address dealer) external onlyOwner {
        concesionariasOficiales[dealer] = false;
        emit ConcesionariaRevocada(dealer, block.timestamp);
    }

    function pausar() external onlyOwner {
        _pause();
    }

    function reanudar() external onlyOwner {
        _unpause();
    }

    // ========= Operacion =========
    function registrarServicio(
        string memory vin,
        uint256 kilometraje,
        uint8 tipoServicio,
        bytes32 hashEvidencia
    ) external whenNotPaused soloConcesionaria {
        require(bytes(vin).length > 0, "VIN vacio");
        require(hashEvidencia != bytes32(0), "Hash invalido");
        Evento[] storage h = historial[vin];
        if (h.length > 0) {
            require(
                kilometraje > h[h.length - 1].kilometraje,
                "Kilometraje invalido"
            );
        }
        h.push(Evento({
            kilometraje: kilometraje,
            tipoServicio: tipoServicio,
            hashEvidencia: hashEvidencia,
            concesionaria: msg.sender,
            timestamp: block.timestamp
        }));
        operacionesPorConcesionaria[msg.sender] += 1;
        ultimaOperacionConcesionaria[msg.sender] = block.timestamp;
        emit ServicioRegistrado(
            vin, kilometraje, tipoServicio, msg.sender,
            hashEvidencia, block.timestamp, h.length - 1
        );
    }

    // ========= Consultas =========
    function obtenerHistorial(string memory vin)
        external view returns (Evento[] memory) {
        return historial[vin];
    }

    function cantidadEventos(string memory vin)
        external view returns (uint256) {
        return historial[vin].length;
    }

    function ultimoEvento(string memory vin)
        external view returns (Evento memory) {
        Evento[] storage h = historial[vin];
        require(h.length > 0, "Sin eventos");
        return h[h.length - 1];
    }

    function estaAutorizada(address dealer)
        external view returns (bool) {
        return concesionariasOficiales[dealer];
    }
}
