const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("HistorialCeroKM", function () {
  let contrato, admin, conces1, conces2, terceroNoAutorizado;
  const VIN_DEMO = "8AP1234567ABC8901";
  const HASH_DEMO = ethers.keccak256(ethers.toUtf8Bytes("evidencia-demo"));

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
  });
});
