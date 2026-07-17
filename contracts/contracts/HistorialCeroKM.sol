// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * HistorialCeroKM
 * Registro inmutable de eventos de mantenimiento oficial sobre vehículos 0km.
 * Solo billeteras de concesionarias autorizadas pueden registrar eventos.
 */
contract HistorialCeroKM {
    struct Evento {
        uint256 kilometraje;
        uint8   tipoServicio;
        bytes32 hashEvidencia;
        address concesionaria;
        uint256 timestamp;
    }

    struct Vehiculo {
        bool   existe;
        uint256 kmInicial;
        address concesionariaAlta;
        uint256 fechaAlta;
    }

    address public admin;

    mapping(string  => Evento[])  private historial;
    mapping(string  => Vehiculo)  public  vehiculos;
    mapping(address => bool)      public  concesionariasOficiales;
    mapping(address => string)    public  nombreConcesionaria;

    event ConcesionariaAutorizada(address indexed wallet, string nombre);
    event ConcesionariaRevocada(address indexed wallet);
    event VehiculoRegistrado(string indexed vin, address indexed concesionaria, uint256 kmInicial);
    event ServicioRegistrado(
        string  indexed vin,
        address indexed concesionaria,
        uint256 kilometraje,
        uint8   tipoServicio,
        bytes32 hashEvidencia,
        uint256 timestamp
    );

    modifier soloAdmin() {
        require(msg.sender == admin, "Solo el administrador");
        _;
    }

    modifier soloConcesionaria() {
        require(concesionariasOficiales[msg.sender], "No autorizado. Solo red oficial.");
        _;
    }

    constructor() {
        admin = msg.sender;
    }

    function transferirAdmin(address nuevo) external soloAdmin {
        require(nuevo != address(0), "Address invalida");
        admin = nuevo;
    }

    function autorizarConcesionaria(address wallet, string memory nombre) external soloAdmin {
        require(wallet != address(0), "Address invalida");
        concesionariasOficiales[wallet] = true;
        nombreConcesionaria[wallet] = nombre;
        emit ConcesionariaAutorizada(wallet, nombre);
    }

    function revocarConcesionaria(address wallet) external soloAdmin {
        concesionariasOficiales[wallet] = false;
        emit ConcesionariaRevocada(wallet);
    }

    function registrarVehiculo(
        string memory vin,
        uint256 kilometrajeInicial,
        bytes32 hashEvidencia
    ) external soloConcesionaria {
        require(!vehiculos[vin].existe, "Vehiculo ya registrado");
        require(bytes(vin).length >= 5, "VIN invalido");

        vehiculos[vin] = Vehiculo({
            existe: true,
            kmInicial: kilometrajeInicial,
            concesionariaAlta: msg.sender,
            fechaAlta: block.timestamp
        });

        historial[vin].push(Evento({
            kilometraje:   kilometrajeInicial,
            tipoServicio:  0,
            hashEvidencia: hashEvidencia,
            concesionaria: msg.sender,
            timestamp:     block.timestamp
        }));

        emit VehiculoRegistrado(vin, msg.sender, kilometrajeInicial);
        emit ServicioRegistrado(vin, msg.sender, kilometrajeInicial, 0, hashEvidencia, block.timestamp);
    }

    function registrarServicio(
        string memory vin,
        uint256 kilometraje,
        uint8 tipoServicio,
        bytes32 hashEvidencia
    ) external soloConcesionaria {
        require(vehiculos[vin].existe, "Vehiculo no registrado");
        require(tipoServicio > 0, "Tipo 0 reservado para alta");

        Evento[] storage eventos = historial[vin];
        if (eventos.length > 0) {
            require(kilometraje >= eventos[eventos.length - 1].kilometraje, "Kilometraje regresivo");
        }

        eventos.push(Evento({
            kilometraje:   kilometraje,
            tipoServicio:  tipoServicio,
            hashEvidencia: hashEvidencia,
            concesionaria: msg.sender,
            timestamp:     block.timestamp
        }));

        emit ServicioRegistrado(vin, msg.sender, kilometraje, tipoServicio, hashEvidencia, block.timestamp);
    }

    function obtenerHistorial(string memory vin) external view returns (Evento[] memory) {
        return historial[vin];
    }

    function cantidadEventos(string memory vin) external view returns (uint256) {
        return historial[vin].length;
    }

    function eventoPorIndice(string memory vin, uint256 indice) external view returns (Evento memory) {
        require(indice < historial[vin].length, "Indice fuera de rango");
        return historial[vin][indice];
    }
}
