// Verifica el código fuente de HistorialCeroKM en Sourcify (API v2), sin API key.
// Uso: node scripts/verificarSourcify.js <direccion> [chainId]
const fs = require("fs");
const path = require("path");

const SERVIDOR = "https://sourcify.dev/server";
const CABECERAS = { "Content-Type": "application/json", "User-Agent": "trazarg-pfi/1.0 (UADE)" };

async function main() {
  const direccion = process.argv[2];
  const chainId = process.argv[3] || "80002";
  if (!direccion) throw new Error("Falta la dirección del contrato");

  // El build-info de Hardhat guarda el input estándar de solc con el que se compiló.
  const dir = path.join(__dirname, "..", "artifacts", "build-info");
  const build = fs
    .readdirSync(dir)
    .map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")))
    .find((b) => b.output.contracts["contracts/HistorialCeroKM.sol"]);
  if (!build) throw new Error("No hay build-info: correr npx hardhat compile");

  const r = await fetch(`${SERVIDOR}/v2/verify/${chainId}/${direccion}`, {
    method: "POST",
    headers: CABECERAS,
    body: JSON.stringify({
      stdJsonInput: build.input,
      compilerVersion: build.solcLongVersion,
      contractIdentifier: "contracts/HistorialCeroKM.sol:HistorialCeroKM",
    }),
  });
  const cuerpo = await r.json();
  if (!r.ok) throw new Error(`Sourcify rechazó la verificación (${r.status}): ${JSON.stringify(cuerpo)}`);

  // La verificación es asíncrona: se consulta hasta que termina.
  for (let i = 0; i < 30; i += 1) {
    await new Promise((ok) => setTimeout(ok, 3000));
    const estado = await (await fetch(`${SERVIDOR}/v2/verify/${cuerpo.verificationId}`, { headers: CABECERAS })).json();
    if (estado.isJobCompleted) {
      if (estado.error) throw new Error(JSON.stringify(estado.error));
      console.log("Verificado en Sourcify:", estado.contract?.match || estado.contract?.runtimeMatch);
      console.log(`https://repo.sourcify.dev/${chainId}/${direccion}`);
      return;
    }
  }
  throw new Error("La verificación no terminó a tiempo");
}

main().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
