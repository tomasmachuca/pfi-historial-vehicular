const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const wallet = process.env.WALLET;
  const nombre = process.env.NOMBRE || "Concesionaria sin nombre";
  if (!wallet) throw new Error("Falta WALLET=0x... en variables de entorno");

  const meta = JSON.parse(
    fs.readFileSync(
      path.join(__dirname, "..", "..", "backend", "app", "abi", "HistorialCeroKM.json"),
      "utf8"
    )
  );

  const contrato = await hre.ethers.getContractAt("HistorialCeroKM", meta.address);
  const tx = await contrato.autorizarConcesionaria(wallet, nombre);
  console.log("Tx:", tx.hash);
  await tx.wait();
  console.log(`Autorizada ${wallet} (${nombre}).`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
