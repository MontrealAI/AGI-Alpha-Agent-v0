const FORBIDDEN_KEYS = new Set(['__proto__', 'prototype', 'constructor']);

/** Deterministic JSON encoding. Ambiguous or non-JSON values are refused. */
export function canonicalize(value) {
  const active = new Set();
  let count = 0;
  const encode = (item, depth) => {
    if (++count > 100000 || depth > 64)
      throw new TypeError('JSON_LIMIT_EXCEEDED');
    if (item === null) return 'null';
    if (typeof item === 'string') {
      if (
        item !== item.normalize('NFC') ||
        /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(
          item
        )
      )
        throw new TypeError('NON_CANONICAL_UNICODE');
      return JSON.stringify(item);
    }
    if (typeof item === 'boolean') return item ? 'true' : 'false';
    if (typeof item === 'number') {
      if (
        !Number.isFinite(item) ||
        Object.is(item, -0) ||
        (Number.isInteger(item) && !Number.isSafeInteger(item))
      )
        throw new TypeError('UNSAFE_NUMBER');
      return JSON.stringify(item);
    }
    if (typeof item !== 'object' || active.has(item))
      throw new TypeError('NON_JSON_VALUE');
    const proto = Object.getPrototypeOf(item);
    if (
      (Array.isArray(item) && proto !== Array.prototype) ||
      (!Array.isArray(item) && proto !== Object.prototype && proto !== null)
    )
      throw new TypeError('NON_JSON_OBJECT');
    active.add(item);
    let encoded;
    if (Object.getOwnPropertySymbols(item).length)
      throw new TypeError('NON_JSON_SYMBOL');
    if (Array.isArray(item)) {
      const names = Object.getOwnPropertyNames(item);
      if (
        names.length !== item.length + 1 ||
        Object.keys(item).length !== item.length
      )
        throw new TypeError('SPARSE_OR_EXTENDED_ARRAY');
      for (let index = 0; index < item.length; index += 1) {
        const descriptor = Object.getOwnPropertyDescriptor(item, String(index));
        if (
          !descriptor ||
          descriptor.get ||
          descriptor.set ||
          !descriptor.enumerable
        )
          throw new TypeError('ACCESSOR_OR_SPARSE_ARRAY');
      }
      encoded = `[${Array.prototype.map
        .call(item, (part) => encode(part, depth + 1))
        .join(',')}]`;
    } else {
      const keys = Object.keys(item).sort();
      for (const key of keys) {
        if (FORBIDDEN_KEYS.has(key) || key !== key.normalize('NFC'))
          throw new TypeError('UNSAFE_OBJECT_KEY');
        if (
          Object.getOwnPropertyDescriptor(item, key)?.get ||
          Object.getOwnPropertyDescriptor(item, key)?.set
        )
          throw new TypeError('ACCESSOR_NOT_ALLOWED');
      }
      encoded = `{${keys
        .map(
          (key) => `${encode(key, depth + 1)}:${encode(item[key], depth + 1)}`
        )
        .join(',')}}`;
    }
    active.delete(item);
    return encoded;
  };
  return encode(value, 0);
}

export async function digestBytes(value) {
  const bytes =
    typeof value === 'string' ? new TextEncoder().encode(value) : value;
  if (!(bytes instanceof Uint8Array)) throw new TypeError('BYTES_REQUIRED');
  if (!globalThis.crypto?.subtle) throw new Error('WEBCRYPTO_UNAVAILABLE');
  const digest = new Uint8Array(
    await globalThis.crypto.subtle.digest('SHA-256', bytes)
  );
  return `sha256:${Array.from(digest, (byte) =>
    byte.toString(16).padStart(2, '0')
  ).join('')}`;
}

export async function digestObject(domain, object) {
  if (
    typeof domain !== 'string' ||
    !/^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,127}$/.test(domain)
  )
    throw new TypeError('INVALID_HASH_DOMAIN');
  return digestBytes(
    canonicalize({ hashFormat: 'successor-canonical-json-v1', domain, object })
  );
}

export function cloneJson(value) {
  return JSON.parse(canonicalize(value));
}
