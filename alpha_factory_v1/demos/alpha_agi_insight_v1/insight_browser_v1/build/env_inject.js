// SPDX-License-Identifier: Apache-2.0
export function injectEnv(env) {
  const enc = (v) => Buffer.from(String(v ?? ''), 'utf8').toString('base64');
  const b64Pinner = enc(env.PINNER_TOKEN);
  const b64Otel = enc(env.OTEL_ENDPOINT);
  const b64Ipfs = enc(env.IPFS_GATEWAY);
  const b64Pyodide = enc(env.PYODIDE_BASE_URL);
  return `<script>window.PINNER_TOKEN=atob('${b64Pinner}');window.OTEL_ENDPOINT=atob('${b64Otel}');window.IPFS_GATEWAY=atob('${b64Ipfs}');window.PYODIDE_BASE_URL=atob('${b64Pyodide}');</script>`;
}
