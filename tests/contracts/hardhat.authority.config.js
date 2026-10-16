// Offline qualification harness. The original unforked fixture guard remains active.
const base = require("./hardhat.config");
module.exports = { ...base, networks: { hardhat: { chainId: 1, hardfork: "osaka", blockGasLimit: 30000000 } } };
