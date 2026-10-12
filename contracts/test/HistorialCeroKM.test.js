const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("HistorialCeroKM", function () {
  let contrato, admin, conces1, conces2, terceroNoAutorizado;
  const VIN_DEMO = "8AP1234567ABC8901";
  const HASH_DEMO = ethers.keccak256(ethers.toUtf8Bytes("evidencia-demo"));
  // El comprobante es opcional: sin archivo, el backend sella con hash nulo.
  const HASH_NULO = ethers.ZeroHash;

  beforeEach(async () => {
    [admin, conces1, conces2, terceroNoAutorizado] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("HistorialCeroKM");
    contrato = await Factory.deploy();
    await contrato.waitForDeployment();
  });

  describe("Administracion", () => {
    it("setea el admin al deployer", async () => {
      expect(await contrato.admin()).to.equal(admin.address);
    });

    it("permite al admin autorizar concesionarias", async () => {
      await expect(contrato.autorizarConcesionaria(conces1.address, "Concesionaria SA"))
        .to.emit(contrato, "ConcesionariaAutorizada")
        .withArgs(conces1.address, "Concesionaria SA");
      expect(await contrato.concesionariasOficiales(conces1.address)).to.equal(true);
    });

    it("rechaza autorizacion desde no-admin", async () => {
      await expect(
        contrato.connect(conces1).autorizarConcesionaria(conces2.address, "X")
      ).to.be.revertedWith("Solo el administrador");
    });

    it("permite revocar concesionarias", async () => {
      await contrato.autorizarConcesionaria(conces1.address, "C1");
      await contrato.revocarConcesionaria(conces1.address);
      expect(await contrato.concesionariasOficiales(conces1.address)).to.equal(false);
    });

    it("emite el evento de revocacion", async () => {
      await contrato.autorizarConcesionaria(conces1.address, "C1");
      await expect(contrato.revocarConcesionaria(conces1.address))
        .to.emit(contrato, "ConcesionariaRevocada")
        .withArgs(conces1.address);
    });

    it("rechaza revocacion desde no-admin", async () => {
      await contrato.autorizarConcesionaria(conces1.address, "C1");
      await expect(
        contrato.connect(conces2).revocarConcesionaria(conces1.address)
      ).to.be.revertedWith("Solo el administrador");
    });

    it("rechaza autorizar la direccion cero", async () => {
      await expect(
        contrato.autorizarConcesionaria(ethers.ZeroAddress, "X")
      ).to.be.revertedWith("Address invalida");
    });

    it("transfiere la administracion", async () => {
      await contrato.transferirAdmin(conces2.address);
      expect(await contrato.admin()).to.equal(conces2.address);
      await expect(
        contrato.autorizarConcesionaria(conces1.address, "C1")
      ).to.be.revertedWith("Solo el administrador");
      await contrato.connect(conces2).autorizarConcesionaria(conces1.address, "C1");
      expect(await contrato.concesionariasOficiales(conces1.address)).to.equal(true);
    });

    it("rechaza transferir la administracion desde no-admin", async () => {
      await expect(
        contrato.connect(conces1).transferirAdmin(conces1.address)
      ).to.be.revertedWith("Solo el administrador");
    });

    it("rechaza transferir la administracion a la direccion cero", async () => {
      await expect(contrato.transferirAdmin(ethers.ZeroAddress)).to.be.revertedWith("Address invalida");
    });
  });

  describe("Alta de vehiculo", () => {
    beforeEach(async () => {
      await contrato.autorizarConcesionaria(conces1.address, "Conces 1");
    });

    it("registra un vehiculo nuevo", async () => {
      await expect(contrato.connect(conces1).registrarVehiculo(VIN_DEMO, 0, HASH_DEMO))
        .to.emit(contrato, "VehiculoRegistrado");
      const v = await contrato.vehiculos(VIN_DEMO);
      expect(v.existe).to.equal(true);
      expect(v.concesionariaAlta).to.equal(conces1.address);
    });

    it("rechaza duplicados", async () => {
      await contrato.connect(conces1).registrarVehiculo(VIN_DEMO, 0, HASH_DEMO);
      await expect(
        contrato.connect(conces1).registrarVehiculo(VIN_DEMO, 0, HASH_DEMO)
      ).to.be.revertedWith("Vehiculo ya registrado");
    });

    it("rechaza wallets no autorizadas", async () => {
      await expect(
        contrato.connect(terceroNoAutorizado).registrarVehiculo(VIN_DEMO, 0, HASH_DEMO)
      ).to.be.revertedWith("No autorizado. Solo red oficial.");
    });

    it("rechaza VIN invalido", async () => {
      await expect(
        contrato.connect(conces1).registrarVehiculo("1234", 0, HASH_DEMO)
      ).to.be.revertedWith("VIN invalido");
    });

    it("acepta el alta sin comprobante (hash nulo)", async () => {
      await contrato.connect(conces1).registrarVehiculo(VIN_DEMO, 5, HASH_NULO);
      const evento = await contrato.eventoPorIndice(VIN_DEMO, 0);
      expect(evento.hashEvidencia).to.equal(HASH_NULO);
      expect(evento.tipoServicio).to.equal(0);
    });
  });

  describe("Registro de servicios", () => {
    beforeEach(async () => {
      await contrato.autorizarConcesionaria(conces1.address, "Conces 1");
      await contrato.connect(conces1).registrarVehiculo(VIN_DEMO, 0, HASH_DEMO);
    });

    it("registra un service oficial", async () => {
      await expect(
        contrato.connect(conces1).registrarServicio(VIN_DEMO, 10000, 1, HASH_DEMO)
      ).to.emit(contrato, "ServicioRegistrado");
      expect(await contrato.cantidadEventos(VIN_DEMO)).to.equal(2);
    });

    it("rechaza kilometraje regresivo", async () => {
      await contrato.connect(conces1).registrarServicio(VIN_DEMO, 10000, 1, HASH_DEMO);
      await expect(
        contrato.connect(conces1).registrarServicio(VIN_DEMO, 5000, 2, HASH_DEMO)
      ).to.be.revertedWith("Kilometraje regresivo");
    });

    it("rechaza tipo 0 (reservado para alta)", async () => {
      await expect(
        contrato.connect(conces1).registrarServicio(VIN_DEMO, 10000, 0, HASH_DEMO)
      ).to.be.revertedWith("Tipo 0 reservado para alta");
    });

    it("rechaza vehiculo no registrado", async () => {
      await expect(
        contrato.connect(conces1).registrarServicio("NO_EXISTE", 10000, 1, HASH_DEMO)
      ).to.be.revertedWith("Vehiculo no registrado");
    });

    it("acepta un kilometraje igual al ultimo registrado", async () => {
      await contrato.connect(conces1).registrarServicio(VIN_DEMO, 10000, 1, HASH_DEMO);
      await contrato.connect(conces1).registrarServicio(VIN_DEMO, 10000, 3, HASH_DEMO);
      expect(await contrato.cantidadEventos(VIN_DEMO)).to.equal(3);
    });

    it("acepta un service sin comprobante (hash nulo)", async () => {
      await contrato.connect(conces1).registrarServicio(VIN_DEMO, 10000, 1, HASH_NULO);
      const evento = await contrato.eventoPorIndice(VIN_DEMO, 1);
      expect(evento.hashEvidencia).to.equal(HASH_NULO);
    });

    it("permite que otra concesionaria autorizada continue el historial", async () => {
      await contrato.autorizarConcesionaria(conces2.address, "Conces 2");
      await contrato.connect(conces2).registrarServicio(VIN_DEMO, 12000, 1, HASH_DEMO);
      const evento = await contrato.eventoPorIndice(VIN_DEMO, 1);
      expect(evento.concesionaria).to.equal(conces2.address);
    });

    it("impide escribir a una concesionaria revocada", async () => {
      await contrato.revocarConcesionaria(conces1.address);
      await expect(
        contrato.connect(conces1).registrarServicio(VIN_DEMO, 10000, 1, HASH_DEMO)
      ).to.be.revertedWith("No autorizado. Solo red oficial.");
    });
  });

  describe("Consulta", () => {
    beforeEach(async () => {
      await contrato.autorizarConcesionaria(conces1.address, "Conces 1");
      await contrato.connect(conces1).registrarVehiculo(VIN_DEMO, 0, HASH_DEMO);
      await contrato.connect(conces1).registrarServicio(VIN_DEMO, 10000, 1, HASH_DEMO);
      await contrato.connect(conces1).registrarServicio(VIN_DEMO, 20000, 2, HASH_DEMO);
    });

    it("retorna el historial completo", async () => {
      const eventos = await contrato.obtenerHistorial(VIN_DEMO);
      expect(eventos.length).to.equal(3);
      expect(eventos[2].kilometraje).to.equal(20000);
    });

    it("permite consulta sin estar autorizado", async () => {
      const eventos = await contrato.connect(terceroNoAutorizado).obtenerHistorial(VIN_DEMO);
      expect(eventos.length).to.equal(3);
    });

    it("devuelve un evento por indice", async () => {
      const evento = await contrato.eventoPorIndice(VIN_DEMO, 1);
      expect(evento.kilometraje).to.equal(10000);
      expect(evento.tipoServicio).to.equal(1);
    });

    it("rechaza un indice fuera de rango", async () => {
      await expect(contrato.eventoPorIndice(VIN_DEMO, 3)).to.be.revertedWith("Indice fuera de rango");
    });

    it("informa cero eventos para un VIN inexistente", async () => {
      expect(await contrato.cantidadEventos("NO_EXISTE")).to.equal(0);
    });
  });
});
