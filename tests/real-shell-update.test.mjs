// PA-1 (Futaba's 0.22.1 QA, M-1): the update failure path in the REAL shell, because the mocks passed while the real
// shell failed (M-1 survived the W5 and W7 fixes). The real Electron (the pinned 44.4.5 build), the real electron-updater
// 6.8.9 and its dependencies (the lockfile's exact tarballs from the npm cache), the real desktop/*.js, the real engine
// (the pinned QA Python, a new empty catalog) and a fake GitHub over HTTPS (a self-signed certificate made here, the
// GitHub hosts mapped to it by --host-resolver-rules, --ignore-certificate-errors). The "installer" is a text file with
// the right checksum, so Windows refuses to start it. Expected (ruling 27, Judy 0.22.2 6.1): the shell stays running,
// the old engine starts again and answers, and the Install line is installer_blocked. Before the M-1 fix the shell
// exited with code 0 about 2 s after "Update now".
//
// Hidden window only (--start-hidden; Sergei may be at the machine): the page is driven over the DevTools protocol, no
// mouse, keyboard or focus. Private LOCALAPPDATA, APPDATA, TEMP and USERPROFILE for the shell, so nothing touches the
// real updater cache or profile. The app copy has one fixed path, so Windows keeps one tray-icon record for it, and
// that record is removed at the end with the copy itself. Inputs are pinned and the test fails closed without them.
import test from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import http from 'node:http';
import https from 'node:https';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SYSTEM32 = path.join(process.env.SystemRoot || 'C:\\Windows', 'System32');
// electron@44.4.5's own checksums.json (node_modules/electron/checksums.json), the version package.json pins.
const ELECTRON = { file: 'electron-v44.4.5-win32-x64.zip', sha256: '11c395820a5aaa8ebcc0686b476d0ac98a730274ebfbdc8cf5538a7c2815cb5d' };
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const sha256 = (file) => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');

function freePort() {
 return new Promise((resolve) => { const server = net.createServer(); server.listen(0, '127.0.0.1', () => { const { port } = server.address(); server.close(() => resolve(port)); }); });
}
function electronZip() {
 const explicit = process.env.BOOKS_ELECTRON_ZIP;
 const roots = [path.join(process.env.LOCALAPPDATA || '', 'electron', 'Cache'), path.join(process.env.LOCALAPPDATA || '', 'electron-builder', 'Cache')];
 const found = explicit ? [explicit] : [];
 for (const root of roots) {
  if (!fs.existsSync(root)) continue;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
   const candidate = entry.isDirectory() ? path.join(root, entry.name, ELECTRON.file) : entry.name === ELECTRON.file ? path.join(root, entry.name) : '';
   if (candidate && fs.existsSync(candidate)) found.push(candidate);
  }
 }
 const pinned = found.find((file) => fs.statSync(file).isFile() && sha256(file) === ELECTRON.sha256);
 if (!pinned) throw new Error('PA-1 needs the pinned ' + ELECTRON.file + ' (SHA-256 ' + ELECTRON.sha256 + ') in the Electron download cache or BOOKS_ELECTRON_ZIP; found: ' + (found.join(', ') || 'none'));
 return pinned;
}
// electron-updater and everything it needs, exactly as package-lock.json pins them, from the npm cache's content store
// (content-v2/sha512/<hex>), each tarball checked against its lockfile integrity before it is used.
function updaterPackages() {
 const lock = JSON.parse(fs.readFileSync(path.join(REPO, 'package-lock.json'), 'utf8')).packages;
 const wanted = new Map();
 const walk = (name) => { const key = 'node_modules/' + name; if (wanted.has(key)) return; const entry = lock[key]; if (!entry) throw new Error('package-lock.json has no ' + key); wanted.set(key, entry); for (const dep of Object.keys(entry.dependencies || {})) walk(dep); };
 walk('electron-updater');
 const cache = process.env.npm_config_cache || path.join(process.env.LOCALAPPDATA || '', 'npm-cache');
 return [...wanted].map(([key, entry]) => {
  const [algorithm, base64] = String(entry.integrity).split('-');
  if (algorithm !== 'sha512') throw new Error(key + ': unsupported integrity ' + entry.integrity);
  const hex = Buffer.from(base64, 'base64').toString('hex');
  const file = path.join(cache, '_cacache', 'content-v2', 'sha512', hex.slice(0, 2), hex.slice(2, 4), hex.slice(4));
  if (!fs.existsSync(file)) throw new Error('PA-1 needs ' + key + '@' + entry.version + ' in the npm cache (' + file + '); run npm ci once on this machine');
  if (crypto.createHash('sha512').update(fs.readFileSync(file)).digest('hex') !== hex) throw new Error(key + ': cached tarball differs from the lockfile');
  return { name: key.slice('node_modules/'.length), file };
 });
}
function qaPython() {
 const pins = JSON.parse(fs.readFileSync(path.join(REPO, 'scripts', 'qa-runtime.json'), 'utf8'));
 const root = process.env.BOOKS_QA_RUNTIME_ROOT || path.dirname(path.dirname(pins.python.path));
 const python = path.join(root, 'python', 'python.exe');
 if (!fs.existsSync(python) || sha256(python) !== pins.python.sha256) throw new Error('PA-1 needs the pinned QA Python (BOOKS_QA_RUNTIME_ROOT): ' + python);
 return root;
}
function tar(args) {
 const result = spawnSync(path.join(SYSTEM32, 'tar.exe'), args, { windowsHide: true, encoding: 'utf8' });
 if (result.status !== 0) throw new Error('tar ' + args.join(' ') + ': ' + (result.stderr || result.error));
}
function copyTree(from, to, keep = () => true) {
 fs.mkdirSync(to, { recursive: true });
 for (const entry of fs.readdirSync(from, { withFileTypes: true })) {
  if (!keep(entry.name, entry)) continue;
  const source = path.join(from, entry.name), target = path.join(to, entry.name);
  if (entry.isDirectory()) copyTree(source, target); else fs.copyFileSync(source, target);
 }
}

// A self-signed X.509 certificate in plain DER: the fake GitHub's, accepted only through --ignore-certificate-errors.
function selfSigned(names) {
 const der = (tag, content) => { const length = content.length; const head = length < 128 ? Buffer.from([tag, length]) : length < 256 ? Buffer.from([tag, 0x81, length]) : Buffer.from([tag, 0x82, length >> 8, length & 255]); return Buffer.concat([head, content]); };
 const seq = (...items) => der(0x30, Buffer.concat(items));
 const integer = (bytes) => der(0x02, bytes[0] & 0x80 ? Buffer.concat([Buffer.from([0]), bytes]) : bytes);
 const oid = (dotted) => { const [a, b, ...rest] = dotted.split('.').map(Number); const out = [40 * a + b]; for (let value of rest) { const chunk = [value & 127]; while ((value >>= 7)) chunk.unshift((value & 127) | 128); out.push(...chunk); } return der(0x06, Buffer.from(out)); };
 const time = (date) => der(0x17, Buffer.from(date.toISOString().replace(/[-:T]/g, '').slice(2, 14) + 'Z'));
 const { publicKey, privateKey } = crypto.generateKeyPairSync('rsa', { modulusLength: 2048 });
 const algorithm = seq(oid('1.2.840.113549.1.1.11'), Buffer.from([5, 0]));
 const name = seq(der(0x31, seq(oid('2.5.4.3'), der(0x0c, Buffer.from(names[0])))));
 const now = Date.now();
 const san = seq(...names.map((host) => der(0x82, Buffer.from(host))));
 const tbs = seq(der(0xa0, integer(Buffer.from([2]))), integer(crypto.randomBytes(8)), algorithm, name, seq(time(new Date(now - 86400000)), time(new Date(now + 7 * 86400000))), name,
  publicKey.export({ type: 'spki', format: 'der' }), der(0xa3, seq(seq(oid('2.5.29.17'), der(0x04, san)))));
 const certificate = seq(tbs, algorithm, der(0x03, Buffer.concat([Buffer.from([0]), crypto.sign('sha256', tbs, privateKey)])));
 return { key: privateKey.export({ type: 'pkcs8', format: 'pem' }), cert: '-----BEGIN CERTIFICATE-----\n' + certificate.toString('base64').replace(/.{64}/g, '$&\n') + '\n-----END CERTIFICATE-----\n' };
}

// The DevTools protocol over the hidden window's page: evaluate in the page, the way the panel's buttons call the shell.
async function devtools(port) {
 let socket = null, id = 0; const waiting = new Map();
 async function connect() {
  const end = Date.now() + 30000;
  while (Date.now() < end) {
   try {
    const targets = await (await fetch('http://127.0.0.1:' + port + '/json/list')).json();
    const page = targets.find((target) => target.type === 'page');
    if (page) {
     socket = new WebSocket(page.webSocketDebuggerUrl);
     await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
     socket.onmessage = (event) => { const message = JSON.parse(event.data); if (waiting.has(message.id)) { waiting.get(message.id)(message); waiting.delete(message.id); } };
     socket.onclose = () => { socket = null; for (const resolve of waiting.values()) resolve({ error: { message: 'closed' } }); waiting.clear(); };
     return;
    }
   } catch { /* not up yet */ }
   await sleep(250);
  }
  throw new Error('no DevTools page');
 }
 async function evaluate(expression, awaitPromise = true) {
  if (!socket) await connect();
  const message = await new Promise((resolve) => { const n = ++id; waiting.set(n, resolve); socket.send(JSON.stringify({ id: n, method: 'Runtime.evaluate', params: { expression, awaitPromise, returnByValue: true } })); });
  if (message.error || message.result?.exceptionDetails) throw new Error((message.error && message.error.message) || JSON.stringify(message.result.exceptionDetails).slice(0, 400));
  return message.result.result.value;
 }
 return { evaluate, close: () => { try { socket?.close(); } catch { /* gone */ } } };
}
function alive(pid) { try { process.kill(pid, 0); return true; } catch { return false; } }
function treeKill(pid) { spawnSync(path.join(SYSTEM32, 'taskkill.exe'), ['/PID', String(pid), '/T', '/F'], { windowsHide: true }); }
function forgetTrayRecord(fragment) {
 // Windows remembers each tray icon's exe in HKCU\Control Panel\NotifyIconSettings; remove only this copy's record.
 const reg = path.join(SYSTEM32, 'reg.exe'), base = 'HKCU\\Control Panel\\NotifyIconSettings';
 const found = spawnSync(reg, ['query', base, '/s', '/f', fragment, '/d'], { windowsHide: true, encoding: 'utf8' });
 for (const key of new Set((found.stdout || '').split(/\r?\n/).filter((line) => line.startsWith('HKEY_CURRENT_USER\\Control Panel\\NotifyIconSettings\\'))))
  spawnSync(reg, ['delete', key, '/f'], { windowsHide: true });
}

test('PA-1: in the real shell, an installer that cannot start keeps the app running; the old engine starts again', { timeout: 300000 }, async () => {
 const zip = electronZip(), packages = updaterPackages(), runtime = qaPython();
 const pkg = JSON.parse(fs.readFileSync(path.join(REPO, 'package.json'), 'utf8'));
 const work = path.join(os.tmpdir(), 'books-pa1');  // one fixed path: one tray-icon record, removed below
 fs.rmSync(work, { recursive: true, force: true });
 const app = path.join(work, 'app'), resources = path.join(app, 'resources'), home = path.join(work, 'home');
 let shell = null, cdp = null, github = null;
 try {
  // The app: the stock Electron runtime, renamed; our shell as resources/app; the backend as the build stages it.
  fs.mkdirSync(app, { recursive: true });
  tar(['-xf', zip, '-C', app]);
  fs.renameSync(path.join(app, 'electron.exe'), path.join(app, 'Books Arranger.exe'));
  const shellApp = path.join(resources, 'app');
  copyTree(path.join(REPO, 'desktop'), path.join(shellApp, 'desktop'));
  fs.writeFileSync(path.join(shellApp, 'package.json'), JSON.stringify({ name: pkg.name, productName: pkg.productName, version: pkg.version, main: 'desktop/main.js', dependencies: pkg.dependencies }));
  for (const { name, file } of packages) {
   const unpack = path.join(work, 'unpack', name); fs.mkdirSync(unpack, { recursive: true });
   tar(['-xzf', file, '-C', unpack]);
   copyTree(path.join(unpack, 'package'), path.join(shellApp, 'node_modules', name));
  }
  fs.writeFileSync(path.join(resources, 'app-update.yml'), 'owner: Gemanoneko\nrepo: booksArranger\nprovider: github\nupdaterCacheDirName: books-arranger-updater\n');
  const backend = path.join(resources, 'backend');
  copyTree(REPO, backend, (name, entry) => entry.isFile() && name.endsWith('.py') && !['app.py', 'install_app_entries.py'].includes(name) || ['public_source_leads.json', 'replacement_eye_plan.json'].includes(name));
  copyTree(path.join(REPO, 'web'), path.join(backend, 'web'));
  fs.writeFileSync(path.join(backend, 'VERSION'), pkg.version + '\n');
  copyTree(path.join(runtime, 'python'), path.join(resources, 'python'));
  copyTree(path.join(runtime, 'ffmpeg'), path.join(resources, 'ffmpeg'));
  // A private everything: profile, data, library roots, LOCALAPPDATA (the updater's cache), APPDATA, TEMP, home.
  const dirs = Object.fromEntries(['profile', 'data', 'local', 'roaming', 'temp', 'Audiobooks', 'Podcasts', 'Books'].map((name) => [name, path.join(home, name)]));
  for (const dir of Object.values(dirs)) fs.mkdirSync(dir, { recursive: true });
  const roots = path.join(home, 'roots.json');
  fs.writeFileSync(roots, JSON.stringify({ Audiobooks: dirs.Audiobooks, Podcasts: dirs.Podcasts, Ebooks: dirs.Books }));

  // The fake GitHub: a release 0.22.2 whose "installer" Windows will not start.
  const installer = Buffer.from('This is no program: Windows refuses to start it (Books Arranger PA-1).\r\n'.repeat(64));
  const sha512 = crypto.createHash('sha512').update(installer).digest('base64');
  const name = 'Books-Arranger-Setup-0.22.2.exe', base = '/Gemanoneko/booksArranger/releases';
  const requests = [];
  github = https.createServer(selfSigned(['github.com', 'api.github.com', 'objects.githubusercontent.com']), (req, res) => {
   requests.push(req.url);
   const send = (status, type, body) => { res.writeHead(status, { 'Content-Type': type, 'Content-Length': Buffer.byteLength(body) }); res.end(body); };
   if (req.url === base + '.atom') return send(200, 'application/atom+xml', '<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><id>tag:github.com,2008:Repository/1/v0.22.2</id><updated>2026-10-26T00:00:00Z</updated><link rel="alternate" type="text/html" href="https://github.com' + base + '/tag/v0.22.2"/><title>v0.22.2</title><content type="html">PA-1</content></entry></feed>');
   if (req.url === base + '/latest') return send(200, 'application/json', JSON.stringify({ tag_name: 'v0.22.2' }));
   if (req.url === base + '/download/v0.22.2/latest.yml') return send(200, 'text/yaml', 'version: 0.22.2\nfiles:\n  - url: ' + name + '\n    sha512: ' + sha512 + '\n    size: ' + installer.length + '\npath: ' + name + '\nsha512: ' + sha512 + "\nreleaseDate: '2026-10-26T00:00:00.000Z'\n");
   if (req.url === base + '/download/v0.22.2/' + name) { res.writeHead(200, { 'Content-Type': 'application/octet-stream', 'Content-Length': installer.length }); return res.end(installer); }
   send(404, 'text/plain', 'Not Found');
  });
  const githubPort = await freePort();
  await new Promise((resolve) => github.listen(githubPort, '127.0.0.1', resolve));
  const enginePort = await freePort(), debugPort = await freePort();
  const env = { ...process.env, LOCALAPPDATA: dirs.local, APPDATA: dirs.roaming, TEMP: dirs.temp, TMP: dirs.temp, USERPROFILE: home };
  for (const name of Object.keys(env)) if (/^(ELECTRON_|NODE_OPTIONS$)/i.test(name)) delete env[name];  // ELECTRON_RUN_AS_NODE, even empty, turns the shell into Node
  const exe = path.join(app, 'Books Arranger.exe');
  const args = ['--start-hidden', '--quiet-errors', '--data-dir=' + dirs.data, '--catalog-mode=new', '--port=' + enginePort, '--roots-json=' + roots, '--shell-profile=' + dirs.profile,
   '--remote-debugging-port=' + debugPort, '--ignore-certificate-errors',
   '--host-resolver-rules=MAP github.com 127.0.0.1:' + githubPort + ',MAP api.github.com 127.0.0.1:' + githubPort + ',MAP objects.githubusercontent.com 127.0.0.1:' + githubPort];
  let output = '';
  shell = spawn(exe, args, { env, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  shell.stdout.on('data', (chunk) => { output += chunk; }); shell.stderr.on('data', (chunk) => { output += chunk; });
  let exitedAt = null; shell.on('exit', () => { exitedAt = Date.now(); });
  cdp = await devtools(debugPort);
  const status = () => cdp.evaluate('window.booksDesktop.status()');
  const until = async (check, ms, what) => { const end = Date.now() + ms; while (Date.now() < end) { if (exitedAt) throw new Error('the shell exited while waiting for ' + what + '\n' + output.slice(-3000)); try { const value = await check(); if (value) return value; } catch { /* the page is changing */ } await sleep(500); } throw new Error('timed out waiting for ' + what + '\n' + output.slice(-3000)); };
  await until(async () => (await status()).loaded, 120000, 'the engine to load');
  const checked = await cdp.evaluate('window.booksDesktop.checkUpdates()');
  assert.deepEqual([checked.check.phase, checked.available], ['available', '0.22.2'], 'positive control: the real updater read the fake GitHub');
  const downloaded = await cdp.evaluate('window.booksDesktop.downloadUpdate()');
  assert.equal(downloaded.ready, true, 'positive control: downloaded and verified (sha512)');
  const pressed = Date.now();
  await cdp.evaluate('window.booksDesktop.installUpdate(); true', false);  // the page reloads during the install: no await
  const failed = await until(async () => { const value = await status(); return value.update && value.update.install.phase === 'failed' && !value.update.busy.install && value.loaded ? value : null; }, 150000, 'the Install line and the old engine loaded again');
  await sleep(5000);  // M-1's queued quit came 1.7 s after the press
  assert.equal(exitedAt, null, 'the shell is still running ' + Math.round((Date.now() - pressed) / 1000) + ' s after Update now');
  assert.equal(failed.update.install.cause, 'installer_blocked');
  assert.match(output, /Installer did not start/, 'positive control: Windows refused to start the installer');
  assert.ok(requests.includes(base + '/download/v0.22.2/' + name), 'the installer came from the fake GitHub');
  const health = await (await fetch('http://127.0.0.1:' + enginePort + '/api/health')).json();
  assert.equal(health.version, pkg.version, 'the old engine answers again');
  // Quit through a second copy (m-12, the ready state): nothing is left running.
  const quit = spawn(exe, ['--quit', '--shell-profile=' + dirs.profile], { env, windowsHide: true, stdio: 'ignore' });
  await new Promise((resolve) => quit.on('exit', resolve));
  const end = Date.now() + 60000;
  while (!exitedAt && Date.now() < end) await sleep(250);
  assert.ok(exitedAt, 'Quit ends the shell');
 } finally {
  cdp?.close();
  if (shell && shell.exitCode === null && alive(shell.pid)) treeKill(shell.pid);
  await new Promise((resolve) => (github ? github.close(() => resolve()) : resolve()));
  for (let n = 0; n < 20 && fs.existsSync(work); n++) { try { fs.rmSync(work, { recursive: true, force: true }); } catch { await sleep(500); } }
  forgetTrayRecord('books-pa1');
 }
});
