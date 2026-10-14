# Pinned browser dependency

`ethers-6.17.0.min.mjs` is the unmodified ES module distribution
`ethers@6.17.0/dist/ethers.min.js`, copied from the package installed by
`npm ci --prefix tests/contracts` using the repository lockfile.
Its MIT license is included in `ETHERS-LICENSE.md`.

SHA-256: `b016b0c3898c78fd8156466eb1ff1f42c9df951c2f0d64c9bdf799fe745b0a6c`.

Nova Studio imports only its ABI encoding, UTF-8 and Keccak functions. No
dependency CDN or remote executable is used. The original Ascension capsule
encryption module is reused without changes. Update this copy only together
with the pinned contract-test dependency and the differential tests.
