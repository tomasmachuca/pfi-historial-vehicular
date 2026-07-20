const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying con la wallet:", deployer.address);
  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("Balance:", hre.ethers.formatEther(balance), "MATIC");

  const Factory = await hre.ethers.getContractFactory("HistorialCeroKM");
  const contrato = await Factory.deploy();
  await contrato.waitForDeployment();

  const address = await contrato.getAddress();
  console.log("\nHistorialCeroKM deployado en:", address);
  console.log("Red:", hre.network.name);

  const artifact = await hre.artifacts.readArtifact("HistorialCeroKM");
  const outDir = path.join(__dirname, "..", "..", "backend", "app", "abi");
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(
    path.join(outDir, "HistorialCeroKM.json"),
    JSON.stringify({ address, abi: artifact.abi }, null, 2)
  );
  console.log("ABI exportado a backend/app/abi/HistorialCeroKM.json");

  const frontDir = path.join(__dirname, "..", "..", "frontend", "src", "lib");
  fs.mkdirSync(frontDir, { recursive: true });
  fs.writeFileSync(
    path.join(frontDir, "contractMeta.json"),
    JSON.stringify({ address, network: hre.network.name }, null, 2)
  );
  console.log("Metadata exportada a frontend/src/lib/contractMeta.json");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
