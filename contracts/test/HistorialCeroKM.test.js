const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("HistorialCeroKM", function () {
  let contrato, owner, dealer, otro;

  beforeEach(async function () {
    [owner, dealer, otro] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("HistorialCeroKM");
    contrato = await Factory.deploy();
    await contrato.waitForDeployment();
  });

  it("designa como owner a quien despliega el contrato", async function () {
    expect(await contrato.owner()).to.equal(owner.address);
  });

  it("permite al owner autorizar y revocar una concesionaria", async function () {
    await contrato.autorizarConcesionaria(dealer.address);
    expect(await contrato.estaAutorizada(dealer.address)).to.equal(true);
    await contrato.revocarConcesionaria(dealer.address);
    expect(await contrato.estaAutorizada(dealer.address)).to.equal(false);
  });

  it("rechaza registrar un servicio desde una direccion no autorizada", async function () {
    const hash = ethers.encodeBytes32String("evidencia");
    await expect(
      contrato.connect(otro).registrarServicio("VIN123", 1000, 1, hash)
    ).to.be.revertedWith("No autorizado");
  });

  it("registra un servicio desde una concesionaria autorizada", async function () {
    await contrato.autorizarConcesionaria(dealer.address);
    const hash = ethers.encodeBytes32String("evidencia");
    await contrato.connect(dealer).registrarServicio("VIN123", 1000, 1, hash);
    expect(await contrato.cantidadEventos("VIN123")).to.equal(1n);
    const evento = await contrato.ultimoEvento("VIN123");
    expect(evento.kilometraje).to.equal(1000n);
  });

  it("rechaza un kilometraje menor o igual al ultimo registrado", async function () {
    await contrato.autorizarConcesionaria(dealer.address);
    const hash = ethers.encodeBytes32String("evidencia");
    await contrato.connect(dealer).registrarServicio("VIN123", 1000, 1, hash);
    await expect(
      contrato.connect(dealer).registrarServicio("VIN123", 500, 1, hash)
    ).to.be.revertedWith("Kilometraje invalido");
  });
});
