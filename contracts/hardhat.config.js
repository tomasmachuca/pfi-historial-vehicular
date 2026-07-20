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
  etherscan: {
    apiKey: {
      polygonAmoy: process.env.POLYGONSCAN_API_KEY || "",
      polygon: process.env.POLYGONSCAN_API_KEY || "",
    },
  },
};
