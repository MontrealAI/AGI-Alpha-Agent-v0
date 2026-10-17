// Additive user-run creator configuration. Never load a key into Hardhat configuration.
require('./scripts/creator-terminal').assertTerminalEnvironment();
require('@nomicfoundation/hardhat-ethers');
const { SOLC_VERSION, SETTINGS } = require('./scripts/compiler-policy');
const endpoint = process.env.ALPHA_READ_ONLY_RPC_URL;
let parsed;
try { parsed = new URL(endpoint); } catch { throw Error('Explicit HTTPS read-only endpoint required'); }
if (parsed.protocol !== 'https:' || parsed.username || parsed.password || parsed.hash) throw Error('Explicit HTTPS read-only endpoint required');
module.exports = {
    solidity: { version: SOLC_VERSION, settings: SETTINGS },
    paths: { sources: './contracts', tests: './test' },
    networks: { mainnet: { url: endpoint, chainId: 1, accounts: [] } }
};
