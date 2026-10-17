'use strict';

// Disposable synthetic fixtures only. Never replace these with a real key.
const test = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const tty = require('node:tty');
const fs = require('node:fs');
const childProcess = require('node:child_process');
const readline = require('node:readline');
const { promptPrivateKey } = require('../scripts/ephemeral-key.cjs');

const SYNTHETIC = `0x${'11'.repeat(32)}`;
const UPPERCASE = `0x${'AB'.repeat(32)}`;
const SECRET_SENTINEL = 'DISPOSABLE_SECRET_SENTINEL_NEVER_REPORT';

class FakeInput extends EventEmitter {
  constructor() {
    super();
    this.fd = 73;
    this.isTTY = true;
    this.isRaw = false;
    this.readableEncoding = null;
    this.readableFlowing = null;
    this.rawCalls = [];
    this.failEnable = false;
    this.failRestore = 0;
  }

  setRawMode(value) {
    this.rawCalls.push(value);
    if (!value && this.failRestore-- > 0) throw new Error(SECRET_SENTINEL);
    this.isRaw = value;
    if (value && this.failEnable) throw new Error(SECRET_SENTINEL);
    return this;
  }

  pause() { this.readableFlowing = false; return this; }
  resume() { this.readableFlowing = true; return this; }
  send(value) {
    const bytes = Buffer.isBuffer(value) ? value : Buffer.from(value);
    this.emit('data', bytes);
    return bytes;
  }
}

class FakeOutput extends EventEmitter {
  constructor() {
    super();
    this.fd = 74;
    this.isTTY = true;
    this.writes = [];
    this.failWrite = false;
  }

  write(value, callback) {
    this.writes.push(value);
    if (this.failWrite) throw new Error(SECRET_SENTINEL);
    if (callback) callback();
    return true;
  }
}

function fixture(t) {
  // The host descriptor check is mocked, not bypassed by the production API.
  const originalRead = tty.ReadStream;
  const originalWrite = tty.WriteStream;
  tty.ReadStream = FakeInput;
  tty.WriteStream = FakeOutput;
  t.after(() => { tty.ReadStream = originalRead; tty.WriteStream = originalWrite; });
  t.mock.method(tty, 'isatty', (fd) => fd === 73 || fd === 74);
  return { input: new FakeInput(), output: new FakeOutput() };
}

function assertClean(input, expectedRaw = false) {
  assert.equal(input.isRaw, expectedRaw);
  assert.equal(input.readableFlowing, false);
  for (const event of ['data', 'error', 'end', 'close']) assert.equal(input.listenerCount(event), 0);
}

async function assertSanitized(promise, code) {
  await assert.rejects(promise, (error) => {
    assert.equal(error.name, 'PrivateKeyInputError');
    assert.equal(error.code, code);
    assert.equal(Object.hasOwn(error, 'cause'), false);
    assert.equal(JSON.stringify(error).includes(SECRET_SENTINEL), false);
    assert.equal(String(error.stack).includes(SECRET_SENTINEL), false);
    assert.equal(String(error.stack).includes(SYNTHETIC), false);
    return true;
  });
}

test('public API rejects actual redirected streams without changing raw mode', async () => {
  // No terminal/device is opened or inspected beyond the provided descriptors.
  const input = new FakeInput();
  const output = new FakeOutput();
  input.fd = -1;
  output.fd = -1;
  await assertSanitized(promptPrivateKey({ input, output }), 'EPHEMERAL_KEY_TTY');
  assert.deepEqual(input.rawCalls, []);
  assert.deepEqual(output.writes, []);
});

for (const target of ['input', 'output']) {
  test(`rejects non-TTY ${target} without prompting`, async (t) => {
    const streams = fixture(t);
    streams[target].isTTY = false;
    await assertSanitized(promptPrivateKey(streams), 'EPHEMERAL_KEY_TTY');
    assert.deepEqual(streams.input.rawCalls, []);
    assert.deepEqual(streams.output.writes, []);
  });
}

test('requires real host TTY checks even when streams claim isTTY', async (t) => {
  const streams = fixture(t);
  t.mock.method(tty, 'isatty', () => false);
  await assertSanitized(promptPrivateKey(streams), 'EPHEMERAL_KEY_TTY');
  assert.deepEqual(streams.input.rawCalls, []);
});

test('rejects stream-shaped objects without genuine TTY stream classes', async (t) => {
  t.mock.method(tty, 'isatty', () => true);
  const streams = { input: new FakeInput(), output: new FakeOutput() };
  await assertSanitized(promptPrivateKey(streams), 'EPHEMERAL_KEY_TTY');
  assert.deepEqual(streams.input.rawCalls, []);
});

test('accepts a bounded synthetic key in memory without echoing', async (t) => {
  const { input, output } = fixture(t);
  const promise = promptPrivateKey({ input, output });
  assert.equal(input.isRaw, true);
  const bytes = input.send(SYNTHETIC);
  assert.equal(bytes.every((byte) => byte === 0), true);
  input.send('\r');
  assert.equal(await promise, SYNTHETIC);
  assert.deepEqual(input.rawCalls, [true, false]);
  assertClean(input);
  assert.equal(output.writes.join('').includes(SYNTHETIC), false);
  assert.equal(output.writes.join('').includes('11'.repeat(32)), false);
  assert.equal(output.listenerCount('error'), 0);
});

test('canonicalizes hex case and supports LF submission', async (t) => {
  const streams = fixture(t);
  const promise = promptPrivateKey(streams);
  streams.input.send(`${UPPERCASE}\n`);
  assert.equal(await promise, UPPERCASE.toLowerCase());
  assertClean(streams.input);
});

test('supports both terminal backspace bytes without echo', async (t) => {
  const { input, output } = fixture(t);
  const promise = promptPrivateKey({ input, output });
  input.send('\b\x7f');
  input.send(`${SYNTHETIC.slice(0, -2)}AB\b\x7f11`);
  input.send('\r');
  assert.equal(await promise, SYNTHETIC);
  assertClean(input);
  assert.equal(output.writes.join('').includes('\b'), false);
});

const invalidCases = [
  ['empty', '\r'],
  ['missing prefix', `${'11'.repeat(32)}\r`],
  ['uppercase prefix', `0X${'11'.repeat(32)}\r`],
  ['too short', '0x11\r'],
  ['too long', `${SYNTHETIC}1\r`],
  ['invalid hex', `0x${'g'.repeat(64)}\r`],
  ['zero scalar', `0x${'00'.repeat(32)}\r`],
  ['curve order', '0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141\r'],
  ['above curve order', `0x${'ff'.repeat(32)}\r`],
  ['embedded newline', `${SYNTHETIC}\n0x11`],
  ['multiline paste', `${SYNTHETIC}\n${SYNTHETIC}\n`],
  ['CRLF paste', `${SYNTHETIC}\r\n`],
  ['bracketed paste', `\x1b[200~${SYNTHETIC}\x1b[201~`],
  ['escape sequence', '\x1b[A'],
  ['tab', '0x\t'],
  ['NUL', '0x\0'],
  ['non-ASCII', '0xé'],
];

for (const [name, data] of invalidCases) {
  test(`rejects ${name}, restoring raw mode and redacting output`, async (t) => {
    const { input, output } = fixture(t);
    const promise = promptPrivateKey({ input, output });
    const bytes = input.send(data);
    await assertSanitized(promise, 'EPHEMERAL_KEY_INVALID');
    assertClean(input);
    assert.equal(bytes.every((byte) => byte === 0), true);
    assert.equal(output.writes.join('').includes(SYNTHETIC), false);
    assert.equal(output.writes.join('').includes(data), false);
  });
}

test('accepts order minus one, a valid disposable scalar boundary', async (t) => {
  const streams = fixture(t);
  const key = '0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364140';
  const promise = promptPrivateKey(streams);
  streams.input.send(`${key}\r`);
  assert.equal(await promise, key);
  assertClean(streams.input);
});

test('rejects overlong batches without allocating an input-sized candidate', async (t) => {
  const streams = fixture(t);
  const promise = promptPrivateKey(streams);
  const bytes = streams.input.send(Buffer.alloc(100_000, 49));
  await assertSanitized(promise, 'EPHEMERAL_KEY_INVALID');
  assert.equal(bytes.every((byte) => byte === 0), true);
  assertClean(streams.input);
});

test('rejects extra data and split CRLF before deferred submission', async (t) => {
  const streams = fixture(t);
  const promise = promptPrivateKey(streams);
  streams.input.send(SYNTHETIC);
  streams.input.send('\r');
  streams.input.send('\n');
  await assertSanitized(promise, 'EPHEMERAL_KEY_INVALID');
  assertClean(streams.input);
});

for (const [name, event] of [['Ctrl-C', '\x03'], ['Ctrl-D', '\x04']]) {
  test(`${name} cancels and restores the terminal`, async (t) => {
    const streams = fixture(t);
    const promise = promptPrivateKey(streams);
    streams.input.send(SYNTHETIC.slice(0, 15));
    streams.input.send(event);
    await assertSanitized(promise, 'EPHEMERAL_KEY_CANCELLED');
    assertClean(streams.input);
  });
}

for (const event of ['end', 'close']) {
  test(`stream ${event} cancels and restores the terminal`, async (t) => {
    const streams = fixture(t);
    const promise = promptPrivateKey(streams);
    streams.input.send(SYNTHETIC.slice(0, 15));
    streams.input.emit(event);
    await assertSanitized(promise, 'EPHEMERAL_KEY_CANCELLED');
    assertClean(streams.input);
  });
}

test('restores an already-raw terminal to its original mode', async (t) => {
  const streams = fixture(t);
  streams.input.isRaw = true;
  const promise = promptPrivateKey(streams);
  streams.input.send('\x03');
  await assertSanitized(promise, 'EPHEMERAL_KEY_CANCELLED');
  assert.deepEqual(streams.input.rawCalls, [true, true]);
  assertClean(streams.input, true);
});

for (const kind of ['encoding', 'data listener', 'readable listener', 'flowing']) {
  test(`rejects input already used by ${kind}`, async (t) => {
    const streams = fixture(t);
    if (kind === 'encoding') streams.input.readableEncoding = 'utf8';
    if (kind === 'data listener') streams.input.on('data', () => {});
    if (kind === 'readable listener') streams.input.on('readable', () => {});
    if (kind === 'flowing') streams.input.readableFlowing = true;
    await assertSanitized(promptPrivateKey(streams), 'EPHEMERAL_KEY_BUSY');
    assert.deepEqual(streams.input.rawCalls, []);
    assert.deepEqual(streams.output.writes, []);
  });
}

for (const target of ['input', 'output']) {
  test(`sanitizes a secret-bearing ${target} stream error`, async (t) => {
    const streams = fixture(t);
    const promise = promptPrivateKey(streams);
    streams.input.send(SYNTHETIC.slice(0, 15));
    streams[target].emit('error', new Error(`${SECRET_SENTINEL} ${SYNTHETIC}`));
    await assertSanitized(promise, 'EPHEMERAL_KEY_IO');
    assertClean(streams.input);
    assert.equal(streams.output.writes.join('').includes(SECRET_SENTINEL), false);
  });
}

test('sanitizes errors while enabling raw mode and still restores it', async (t) => {
  const streams = fixture(t);
  streams.input.failEnable = true;
  await assertSanitized(promptPrivateKey(streams), 'EPHEMERAL_KEY_IO');
  assert.deepEqual(streams.input.rawCalls, [true, false]);
  assertClean(streams.input);
});

test('refuses to prompt if the stream does not report raw mode enabled', async (t) => {
  const streams = fixture(t);
  streams.input.setRawMode = (value) => { streams.input.rawCalls.push(value); return streams.input; };
  await assertSanitized(promptPrivateKey(streams), 'EPHEMERAL_KEY_IO');
  assert.deepEqual(streams.input.rawCalls, [true, false]);
  assertClean(streams.input);
  assert.equal(streams.output.writes.join('').includes('input hidden'), false);
});

test('retries a transient restoration error without exposing it', async (t) => {
  const streams = fixture(t);
  streams.input.failRestore = 1;
  const promise = promptPrivateKey(streams);
  streams.input.send('\x03');
  await assertSanitized(promise, 'EPHEMERAL_KEY_CANCELLED');
  assert.deepEqual(streams.input.rawCalls, [true, false, false]);
  assertClean(streams.input);
});

test('restoration refusal reports sanitized I/O failure and retains an exit fallback', async (t) => {
  const streams = fixture(t);
  const before = process.listeners('exit');
  streams.input.failRestore = 2;
  const promise = promptPrivateKey(streams);
  streams.input.send('\x03');
  await assertSanitized(promise, 'EPHEMERAL_KEY_IO');
  assert.equal(streams.input.isRaw, true);
  const ownExit = process.listeners('exit').find((listener) => !before.includes(listener));
  assert.equal(typeof ownExit, 'function');
  ownExit();
  assertClean(streams.input);
  assert.deepEqual(process.listeners('exit'), before);
});

test('sanitizes prompt write errors and restores raw mode', async (t) => {
  const streams = fixture(t);
  streams.output.failWrite = true;
  await assertSanitized(promptPrivateKey(streams), 'EPHEMERAL_KEY_IO');
  assertClean(streams.input);
});

test('sanitizes a delayed prompt callback error', async (t) => {
  const streams = fixture(t);
  const originalWrite = streams.output.write.bind(streams.output);
  let first = true;
  streams.output.write = (value, callback) => {
    if (!first) return originalWrite(value, callback);
    first = false;
    streams.output.writes.push(value);
    setImmediate(() => callback(new Error(SECRET_SENTINEL)));
    return true;
  };
  await assertSanitized(promptPrivateKey(streams), 'EPHEMERAL_KEY_IO');
  assertClean(streams.input);
  assert.equal(streams.output.listenerCount('error'), 0);
});

test('catches output error emitted after the cleanup write callback', async (t) => {
  const streams = fixture(t);
  const originalWrite = streams.output.write.bind(streams.output);
  streams.output.write = (value, callback) => {
    const result = originalWrite(value, callback);
    if (value === '\n') process.nextTick(() => streams.output.emit('error', new Error(SECRET_SENTINEL)));
    return result;
  };
  const promise = promptPrivateKey(streams);
  streams.input.send(`${SYNTHETIC}\r`);
  await assertSanitized(promise, 'EPHEMERAL_KEY_IO');
  assertClean(streams.input);
  assert.equal(streams.output.listenerCount('error'), 0);
});

test('rejects decoded string events without reporting their contents', async (t) => {
  const streams = fixture(t);
  const promise = promptPrivateKey(streams);
  streams.input.emit('data', SECRET_SENTINEL);
  await assertSanitized(promise, 'EPHEMERAL_KEY_INVALID');
  assertClean(streams.input);
});

test('sanitizes unexpected option getter and descriptor-check exceptions', async (t) => {
  await assertSanitized(promptPrivateKey({ get input() { throw new Error(SECRET_SENTINEL); } }), 'EPHEMERAL_KEY_TTY');
  const hostileError = new Proxy({}, { get() { throw new Error(SECRET_SENTINEL); } });
  await assertSanitized(promptPrivateKey({ get input() { throw hostileError; } }), 'EPHEMERAL_KEY_TTY');
  const streams = fixture(t);
  t.mock.method(tty, 'isatty', () => { throw new Error(SECRET_SENTINEL); });
  await assertSanitized(promptPrivateKey(streams), 'EPHEMERAL_KEY_TTY');
});

test('signal and exit hooks restore state and are removed on completion', async (t) => {
  const streams = fixture(t);
  const events = ['SIGINT', 'SIGTERM', 'SIGHUP', 'SIGQUIT', 'exit'];
  const before = new Map(events.map((event) => [event, process.listeners(event)]));
  const promise = promptPrivateKey(streams);
  const ownSignal = process.listeners('SIGINT').find((listener) => !before.get('SIGINT').includes(listener));
  assert.equal(typeof ownSignal, 'function');
  ownSignal(); // Never signal a process or real terminal in a synthetic test.
  await assertSanitized(promise, 'EPHEMERAL_KEY_CANCELLED');
  assertClean(streams.input);
  for (const event of events) assert.deepEqual(process.listeners(event), before.get(event));
});

test('exit hook performs synchronous best-effort restoration', async (t) => {
  const streams = fixture(t);
  const before = process.listeners('exit');
  const promise = promptPrivateKey(streams);
  const ownExit = process.listeners('exit').find((listener) => !before.includes(listener));
  streams.input.send(SYNTHETIC.slice(0, 15));
  ownExit(); // Invoke only this helper's hook; do not exit or emit process.exit.
  assert.equal(streams.input.isRaw, false);
  streams.input.send('\x03');
  await assertSanitized(promise, 'EPHEMERAL_KEY_CANCELLED');
  assertClean(streams.input);
});

test('no environment, filesystem, child-process, or console use during collection', async (t) => {
  const streams = fixture(t);
  const calls = [];
  for (const name of ['writeFile', 'writeFileSync', 'appendFile', 'appendFileSync', 'createWriteStream']) {
    t.mock.method(fs, name, () => { calls.push(`fs.${name}`); throw new Error(SECRET_SENTINEL); });
  }
  for (const name of ['spawn', 'spawnSync', 'exec', 'execSync', 'execFile', 'execFileSync', 'fork']) {
    t.mock.method(childProcess, name, () => { calls.push(`child.${name}`); throw new Error(SECRET_SENTINEL); });
  }
  for (const name of ['log', 'info', 'warn', 'error', 'debug']) {
    t.mock.method(console, name, () => { calls.push(`console.${name}`); });
  }
  const originalEnvironment = process.env;
  try {
    process.env = new Proxy({}, {
      get() { calls.push('env.read'); throw new Error(SECRET_SENTINEL); },
      set() { calls.push('env.write'); throw new Error(SECRET_SENTINEL); },
    });
    const promise = promptPrivateKey(streams);
    streams.input.send(`${SYNTHETIC}\r`);
    assert.equal(await promise, SYNTHETIC);
  } finally {
    process.env = originalEnvironment;
  }
  assert.deepEqual(calls, []);
  assertClean(streams.input);
});

test('sequential prompts leave no input or signal listeners behind', async (t) => {
  const streams = fixture(t);
  const events = ['SIGINT', 'SIGTERM', 'SIGHUP', 'SIGQUIT', 'exit'];
  const before = events.map((event) => process.listeners(event));
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const promise = promptPrivateKey(streams);
    streams.input.send(`${SYNTHETIC}\r`);
    assert.equal(await promise, SYNTHETIC);
    assertClean(streams.input);
  }
  for (let index = 0; index < events.length; index += 1) assert.deepEqual(process.listeners(events[index]), before[index]);
});

test('terminal readline confirmation leaves a consumer, so private key entry is refused', async (t) => {
  const streams = fixture(t);
  const confirmation = 'DEPLOY fixed-disposable-plan-hash';
  const confirmed = new Promise((resolve) => {
    const reader = readline.createInterface({ ...streams, terminal: true, historySize: 0 });
    reader.question('Confirm public plan: ', (answer) => {
      reader.close();
      resolve(answer);
    });
  });
  streams.input.send(`${confirmation}\r`);
  assert.equal(await confirmed, confirmation);
  assert.equal(streams.input.readableEncoding, null);
  assert.equal(streams.input.readableFlowing, false);
  assert.equal(streams.input.listenerCount('data'), 1);
  assert.equal(streams.input.listenerCount('readable'), 0);
  await assertSanitized(promptPrivateKey(streams), 'EPHEMERAL_KEY_BUSY');
  // Never send even a synthetic key through this rejected public reader.
});

test('non-terminal readline public confirmation releases the key input boundary', async (t) => {
  const streams = fixture(t);
  const confirmation = 'DEPLOY fixed-disposable-plan-hash';
  const confirmed = new Promise((resolve) => {
    const reader = readline.createInterface({ ...streams, terminal: false, historySize: 0 });
    reader.question('Confirm public plan: ', (answer) => {
      reader.close();
      resolve(answer);
    });
  });
  streams.input.send(`${confirmation}\r`);
  assert.equal(await confirmed, confirmation);
  assert.equal(streams.input.readableEncoding, null);
  assert.equal(streams.input.readableFlowing, false);
  assert.equal(streams.input.listenerCount('data'), 0);
  assert.equal(streams.input.listenerCount('readable'), 0);
  const promise = promptPrivateKey(streams);
  streams.input.send(`${SYNTHETIC}\r`);
  assert.equal(await promise, SYNTHETIC);
  assertClean(streams.input);
  assert.equal(streams.output.writes.join('').includes(SYNTHETIC), false);
});

test('helper imports only Node tty and contains no persistence or subprocess APIs', () => {
  const source = fs.readFileSync(require.resolve('../scripts/ephemeral-key.cjs'), 'utf8');
  assert.deepEqual([...source.matchAll(/require\((['"])(.*?)\1\)/g)].map((match) => match[2]), ['node:tty']);
  assert.equal(/process\.(?:env|argv|stdout)|(?:writeFile|appendFile|createWriteStream)|child_process|execFile|\.spawn\(/.test(source), false);
});
