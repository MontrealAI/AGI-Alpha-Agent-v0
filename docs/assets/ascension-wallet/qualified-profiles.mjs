// SPDX-License-Identifier: Apache-2.0
// Source-reviewed build registry; never populate from a URL, import or browser storage.
// Entries: {canonicalJSON,sha256,stage}; canary entries additionally bind separate
// {authorizationJSON,authorizationSHA256}. The run scope references the full profile
// digest; the immutable deployment descriptor never includes this changing scope.
// Local fixtures build isolated copies using stage "local", chain 1337 or 31337,
// exact source/ABI/runtime/genesis/deployment pins and mainnetQualification:false.
// Mainnet entries require reviewed external dependency/proxy/authority observations,
// evidence references, expiry and explicit recovery/continuation permissions.
// No replacement Mainnet deployment has been commissioned. Archive policy is unchanged.
export const QUALIFIED_PROFILES = Object.freeze([]);
