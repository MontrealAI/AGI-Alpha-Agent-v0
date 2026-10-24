const USDC_DECIMALS = 6;
const USDC_ADDRESSES = Object.freeze({
  1: '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
  11155111: '0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238',
});

function parseUSDC(value) {
  const text = String(value);
  if (!/^(0|[1-9]\d*)(\.\d{1,6})?$/.test(text)) {
    throw new Error('USDC amount must be a non-negative decimal with at most six decimal places.');
  }
  const [whole, fraction = ''] = text.split('.');
  const raw = BigInt(whole) * 1000000n + BigInt(fraction.padEnd(6, '0'));
  if (raw > (1n << 256n) - 1n) throw new Error('USDC amount exceeds uint256.');
  return raw.toString();
}

function formatUSDC(value) {
  const raw = BigInt(value);
  const sign = raw < 0n ? '-' : '';
  const magnitude = raw < 0n ? -raw : raw;
  const fraction = (magnitude % 1000000n).toString().padStart(6, '0').replace(/0+$/, '');
  return `${sign}${magnitude / 1000000n}${fraction ? '.' + fraction : ''}`;
}

function requireCanonicalUSDC(chainId, address) {
  const expected = USDC_ADDRESSES[Number(chainId)];
  if (!expected) throw new Error(`Unsupported USDC deployment chain: ${chainId}`);
  if (String(address).toLowerCase() !== expected.toLowerCase()) {
    throw new Error(`Only Circle USDC at ${expected} is supported on chain ${chainId}.`);
  }
  return expected;
}

module.exports = { USDC_DECIMALS, USDC_ADDRESSES, parseUSDC, formatUSDC, requireCanonicalUSDC };
