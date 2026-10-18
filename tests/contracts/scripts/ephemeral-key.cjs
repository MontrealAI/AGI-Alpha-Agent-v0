'use strict';

const tty = require('node:tty');

const WIDTH = 66; // Exactly "0x" followed by 32 bytes of hexadecimal.
const ORDER = Buffer.from('fffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141', 'hex');
const MESSAGES = Object.freeze({
  EPHEMERAL_KEY_TTY: 'Interactive terminal input and output are required.',
  EPHEMERAL_KEY_BUSY: 'Terminal input must be unused and undecoded.',
  EPHEMERAL_KEY_INVALID: 'Enter one 0x-prefixed 32-byte secp256k1 private key.',
  EPHEMERAL_KEY_CANCELLED: 'Private key input was cancelled.',
  EPHEMERAL_KEY_IO: 'Terminal private key input failed.',
});

function failure(code) {
  const error = new Error(MESSAGES[code]);
  error.name = 'PrivateKeyInputError';
  error.code = code;
  return error; // Never attach the input, original exception, or its cause.
}

function nibble(byte) {
  if (byte >= 48 && byte <= 57) return byte - 48;
  if (byte >= 65 && byte <= 70) return byte - 55;
  if (byte >= 97 && byte <= 102) return byte - 87;
  return -1;
}

function canonicalKey(candidate, length) {
  if (length !== WIDTH || candidate[0] !== 48 || candidate[1] !== 120) return null;
  const scalar = Buffer.alloc(32);
  try {
    let nonzero = false;
    for (let index = 0; index < 32; index += 1) {
      const high = nibble(candidate[2 + index * 2]);
      const low = nibble(candidate[3 + index * 2]);
      if (high < 0 || low < 0) return null;
      scalar[index] = high * 16 + low;
      nonzero ||= scalar[index] !== 0;
    }
    if (!nonzero || Buffer.compare(scalar, ORDER) >= 0) return null;
    return `0x${scalar.toString('hex')}`;
  } finally {
    scalar.fill(0);
  }
}

/**
 * Read an ephemeral creator key locally, without echo or subprocesses.
 *
 * Only genuine, idle, undecoded TTY streams are accepted. The key is never read
 * from arguments, environment variables, files, or redirected standard input.
 * The caller must keep the returned value in this process and never log it.
 *
 * Bounded mutable input buffers are cleared on every settlement. JavaScript
 * strings and an ethers signer cannot be guaranteed to be zeroized. This is a
 * narrow input helper, not protection against a compromised Ubuntu host,
 * terminal, clipboard, debugger, process, or dependency. SIGKILL and a terminal
 * driver that refuses restoration cannot be repaired by JavaScript.
 */
async function promptPrivateKey(options = {}) {
  let input;
  let output;
  let originalRaw;
  let boundaryFailure = 'EPHEMERAL_KEY_TTY';
  try {
    input = options.input === undefined ? process.stdin : options.input;
    output = options.output === undefined ? process.stderr : options.output;
    if (!input || !output || !(input instanceof tty.ReadStream) || !(output instanceof tty.WriteStream)
      || input.isTTY !== true || output.isTTY !== true
      || !Number.isInteger(input.fd) || !Number.isInteger(output.fd)
      || !tty.isatty(input.fd) || !tty.isatty(output.fd)
      || typeof input.setRawMode !== 'function' || typeof input.pause !== 'function'
      || typeof input.resume !== 'function' || typeof input.on !== 'function'
      || typeof input.removeListener !== 'function' || typeof input.listenerCount !== 'function'
      || typeof output.on !== 'function' || typeof output.removeListener !== 'function'
      || typeof output.write !== 'function' || typeof input.isRaw !== 'boolean') {
      throw failure('EPHEMERAL_KEY_TTY');
    }
    if (input.readableEncoding != null || input.readableFlowing === true
      || input.listenerCount('data') !== 0 || input.listenerCount('readable') !== 0) {
      boundaryFailure = 'EPHEMERAL_KEY_BUSY';
      throw failure(boundaryFailure);
    }
    if (input.destroyed || input.readableEnded || output.destroyed) {
      boundaryFailure = 'EPHEMERAL_KEY_IO';
      throw failure(boundaryFailure);
    }
    originalRaw = input.isRaw;
  } catch {
    // Even an exception object with hostile getters is never inspected.
    throw failure(boundaryFailure);
  }

  return new Promise((resolve, reject) => {
    const candidate = Buffer.alloc(WIDTH);
    let length = 0;
    let settled = false;
    let ioFailed = false;
    let outputListening = false;
    let rawAttempted = false;
    let submission = null;
    const signals = ['SIGINT', 'SIGTERM', 'SIGHUP', 'SIGQUIT'];

    function restoreRaw() {
      if (!rawAttempted) return true;
      // A second best-effort attempt also handles a transient stream failure.
      for (let attempt = 0; attempt < 2; attempt += 1) {
        try {
          input.setRawMode(originalRaw);
          if (input.isRaw !== originalRaw) continue;
          rawAttempted = false;
          return true;
        } catch {
          // Do not retain or disclose the terminal exception.
        }
      }
      return false;
    }

    function onExit() {
      candidate.fill(0);
      if (restoreRaw()) process.removeListener('exit', onExit);
    }

    function cleanup() {
      if (submission !== null) clearImmediate(submission);
      candidate.fill(0);
      length = 0;
      let clean = true;
      try { input.pause(); } catch { clean = false; }
      if (!restoreRaw()) clean = false;
      try {
        input.removeListener('data', onData);
        input.removeListener('error', onError);
        input.removeListener('end', onCancel);
        input.removeListener('close', onCancel);
      } catch { clean = false; }
      for (const signal of signals) process.removeListener(signal, onCancel);
      // Keep only a best-effort exit restoration if the driver refused it now.
      if (!rawAttempted) process.removeListener('exit', onExit);
      return clean;
    }

    function finish(code, key) {
      if (settled) return;
      settled = true;
      const clean = cleanup();
      ioFailed ||= !clean;
      let queued = false;
      const complete = (error) => {
        if (error) ioFailed = true;
        if (queued) return;
        queued = true;
        // Writable streams can emit an error just after their write callback.
        // Retain our redacting listener through that turn before releasing it.
        setImmediate(() => {
          try {
            if (outputListening) output.removeListener('error', onError);
          } catch { ioFailed = true; }
          if (ioFailed) reject(failure('EPHEMERAL_KEY_IO'));
          else if (code) reject(failure(code));
          else resolve(key);
        });
      };
      if (!outputListening) { complete(); return; }
      try { output.write('\n', complete); } catch { ioFailed = true; complete(); }
    }

    function onCancel() { finish('EPHEMERAL_KEY_CANCELLED'); }
    function onError() { ioFailed = true; finish('EPHEMERAL_KEY_IO'); }

    function onData(chunk) {
      try {
        if (settled) return;
        if (!Buffer.isBuffer(chunk) || chunk.length === 0 || submission !== null) {
          finish('EPHEMERAL_KEY_INVALID');
          return;
        }
        // Inspect the entire batch before accepting any terminator. This rejects
        // multiline paste, CRLF, escape/bracketed-paste sequences, and trailing
        // data. Raw bytes cannot identify the origin of arbitrarily fragmented
        // input, so this does not claim universal paste-origin detection.
        for (let index = 0; index < chunk.length; index += 1) {
          const byte = chunk[index];
          if ((byte === 13 || byte === 10) && index !== chunk.length - 1) {
            finish('EPHEMERAL_KEY_INVALID');
            return;
          }
          if (byte !== 3 && byte !== 4 && byte !== 8 && byte !== 127
            && byte !== 13 && byte !== 10 && byte !== 120 && nibble(byte) < 0) {
            finish('EPHEMERAL_KEY_INVALID');
            return;
          }
        }
        for (const byte of chunk) {
          if (byte === 3 || byte === 4) { onCancel(); return; }
          if (byte === 8 || byte === 127) {
            if (length > 0) candidate[--length] = 0;
          } else if (byte === 13 || byte === 10) {
            // Reject any additional data observed before the deferred commit,
            // including split CRLF and synchronously fragmented paste.
            submission = setImmediate(() => {
              let key;
              try { key = canonicalKey(candidate, length); } catch { onError(); return; }
              if (key === null) finish('EPHEMERAL_KEY_INVALID');
              else finish(null, key);
            });
          } else {
            if (length >= WIDTH || (length === 0 && byte !== 48)
              || (length === 1 && byte !== 120) || (length >= 2 && nibble(byte) < 0)) {
              finish('EPHEMERAL_KEY_INVALID');
              return;
            }
            candidate[length++] = byte;
          }
        }
      } catch {
        onError();
      } finally {
        // Node owns other possible copies; clearing this batch is best-effort.
        if (Buffer.isBuffer(chunk)) chunk.fill(0);
      }
    }

    try {
      output.on('error', onError);
      outputListening = true;
      process.on('exit', onExit);
      for (const signal of signals) process.on(signal, onCancel);
      input.pause();
      rawAttempted = true;
      input.setRawMode(true); // Node/libuv only; no shell, stty, or child process.
      if (input.isRaw !== true) throw failure('EPHEMERAL_KEY_IO');
      input.on('data', onData);
      input.on('error', onError);
      input.on('end', onCancel);
      input.on('close', onCancel);
      output.write('Ephemeral creator private key (0x + 64 hex; input hidden): ', (error) => {
        if (error) onError();
      });
      if (!settled) input.resume();
    } catch {
      onError();
    }
  });
}

module.exports = { promptPrivateKey };
