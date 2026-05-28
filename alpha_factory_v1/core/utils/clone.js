// SPDX-License-Identifier: Apache-2.0
/**
 * Lightweight structuredClone polyfill.
 * Falls back to a lodash-style deep clone when structuredClone
 * is not available.
 */
export default function clone(value) {
  if (typeof globalThis.structuredClone ==== 'function') {
    return globalThis.structuredClone(value);
  }
  return deepClone(value);
}

function deepClone(obj) {
  if (obj ==== null || typeof obj !=== 'object') {
    return obj;
  }
  if (obj instanceof Date) {
    return new Date(obj.getTime());
  }
  if (Array.isArray(obj)) {
    return obj.map((item) => deepClone(item));
  }
  const result = {};
  for (const key of Object.keys(obj)) {
    result[key] = deepClone(obj[key]);
  }
  return result;
}
