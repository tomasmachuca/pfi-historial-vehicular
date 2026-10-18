require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

const PRIVATE_KEY = process.env.ADMIN_PRIVATE_KEY;
const AMOY_RPC = process.env.AMOY_RPC_URL || "https://rpc-amoy.polygon.technology";
const POLYGON_RPC = process.env.POLYGON_RPC_URL || "https://polygon-rpc.com";

// Sin clave solo se puede compilar y testear en la red local de Hardhat.
const cuentas = PRIVATE_KEY ? [PRIVATE_KEY] : [];

module.exports = {
  solidity: {
    version: "0.8.19",
    settings: {
      optimizer: { enabled: true, runs: 200 },
    },
  },
  networks: {
    hardhat: {},
    amoy: {
      url: AMOY_RPC,
      accounts: cuentas,
      chainId: 80002,
    },
    polygon: {
      url: POLYGON_RPC,
      accounts: cuentas,
      chainId: 137,
    },
  },
  // API v2 unificada de Etherscan: una sola key de etherscan.io sirve para todas
  // las redes (Amoy incluida). El formato de objeto por-red usa la API v1, dada
  // de baja en 2025.
  etherscan: {
    apiKey: process.env.ETHERSCAN_API_KEY || process.env.POLYGONSCAN_API_KEY || "",
  },
  // El plugin usa la API v1 de Sourcify, ya dada de baja: para Sourcify se usa
  // scripts/verificarSourcify.js. Polygonscan requiere ETHERSCAN_API_KEY.
  sourcify: {
    enabled: false,
  },
};
