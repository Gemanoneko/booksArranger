// The shell's startup (ruling 28; Judy 3.2, 3.4, 3.7, 3.8), driven end to end: desktop/main.js under a fake Electron and
// a fake engine (an owner-proof line on the host's stdout and a loopback HTTP answer on the configured port). The window
// opens before the engine answers, the engine's page takes over, a stop is the strip's Stopped (no error box), a taken
// port names the other process, Quit while loading closes at once, Restart engine starts a new launch, the completed
// load's time is kept. No Electron, no Python, no catalog.
import test from 'node:test';
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import fs from 'node:fs';
import http from 'node:http';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const Module = require('node:module');
const MAIN = require.resolve('../desktop/main.js');
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function until(check, ms = 6000, what = 'condition') {
 const end = Date.now() + ms;
 while (Date.now() < end) { const value = check(); if (value) return value; await sleep(25); }
 throw new Error('timed out waiting for ' + what);
}
function freePort() {
 return new Promise((resolve) => { const server = net.createServer(); server.listen(0, '127.0.0.1', () => { const { port } = server.address(); server.close(() => resolve(port)); }); });
}

async function boot({ setup = false, flags = ['--show-inactive'], lock = true, updaterLike = null } = {}) {
 const root = fs.mkdtempSync(path.join(os.tmpdir(), 'books-main-'));
 const resources = path.join(root, 'resources'), data = path.join(root, 'data'), profile = path.join(root, 'profile');
 for (const dir of [path.join(resources, 'python'), path.join(resources, 'ffmpeg'), path.join(resources, 'backend', 'web'), data, profile]) fs.mkdirSync(dir, { recursive: true });
 fs.writeFileSync(path.join(resources, 'python', 'python.exe'), 'fixture');
 fs.writeFileSync(path.join(resources, 'ffmpeg', 'ffmpeg.exe'), 'fixture');
 fs.writeFileSync(path.join(resources, 'backend', 'web', 'index.html'), '<!doctype html><title>Books Arranger</title>');
 fs.copyFileSync(path.resolve(path.dirname(MAIN), '../web/load-state.js'), path.join(resources, 'backend', 'web', 'load-state.js'));
 const port = await freePort();
 const log = { windows: [], trays: [], errors: [], exits: [], spawns: [], sends: [] };
 const handlers = {}, appEvents = {};
 class BrowserWindow extends EventEmitter {
  constructor(options) {
   super(); this.options = options; this.loads = []; this.visible = false; this.destroyed = false;
   const win = this;
   this.webContents = Object.assign(new EventEmitter(), { send: (channel, value) => log.sends.push({ channel, value }), setWindowOpenHandler() {}, getURL: () => win.loads.at(-1) || '' });
   log.windows.push(this);
   setImmediate(() => this.emit('ready-to-show'));
  }
  loadURL(url) { this.loads.push(url); return Promise.resolve(); }
  loadFile(file) { this.loads.push(require('node:url').pathToFileURL(file).href); return Promise.resolve(); }
  close() { this.destroyed = true; this.emit('closed'); }
  show() { this.visible = true; } showInactive() { this.visible = true; } hide() { this.visible = false; } focus() {}
  isDestroyed() { return this.destroyed; } isMinimized() { return false; } isVisible() { return this.visible; } restore() {} reload() {}
 }
 class Tray extends EventEmitter {
  constructor() { super(); this.tips = []; this.destroyed = false; log.trays.push(this); }
  setToolTip(text) { this.tips.push(text); } setContextMenu(menu) { this.menu = menu; } destroy() { this.destroyed = true; } isDestroyed() { return this.destroyed; }
 }
 const app = { isPackaged: true, paths: {}, getVersion: () => '0.22.1', setPath(name, value) { this.paths[name] = value; }, getPath(name) { return this.paths[name] || profile; },
  requestSingleInstanceLock: () => lock, on: (name, fn) => { appEvents[name] = fn; }, whenReady: () => Promise.resolve(), exit: (code) => log.exits.push(code),
  // Electron's app.quit(): before-quit first; the quit goes ahead unless a handler prevented it.
  quit() { const event = { prevented: false, preventDefault() { this.prevented = true; } }; log.quits = (log.quits || 0) + 1; if (appEvents['before-quit']) appEvents['before-quit'](event); if (!event.prevented) log.exits.push(0); } };
 const electron = { app, BrowserWindow, Tray, Menu: { buildFromTemplate: (items) => items }, dialog: { showErrorBox: (...args) => log.errors.push(args), showMessageBox: async () => ({ response: 1 }) },
  nativeImage: { createFromPath: () => ({ resize: () => ({}) }) }, session: { defaultSession: { setPermissionRequestHandler() {} } }, shell: { openExternal() {}, showItemInFolder() {} },
  ipcMain: { handle: (name, fn) => { handlers[name] = fn; } } };
 const updater = updaterLike ? updaterLike(app) : Object.assign(new EventEmitter(), { setFeedURL() {}, checkForUpdates: async () => ({}) });
 log.updater = updater;
 let pids = 7000;
 class Child extends EventEmitter {
  constructor(command, args) {
   super(); this.pid = ++pids; this.exitCode = null; this.signalCode = null; this.command = command; this.args = args;
   // The read-only helpers (folder check, settings) answer at once, as their scripts do.
   if (/desktop_(catalog|settings).py$/.test(args[2] || '')) setImmediate(() => { this.stdout.emit('data', Buffer.from('{"ok":true}')); this.finish(0); });
   // The installer lease helper answers its proof and holds until its pipe closes.
   if (/desktop_update_lease.py$/.test(args[2] || '')) setImmediate(() => this.stdout.emit('data', Buffer.from(JSON.stringify({ type: 'books-update-lease-v1', sha512: args[4] }) + '\n')));
   this.stdout = new EventEmitter(); this.stderr = new EventEmitter();
   const child = this; this.stdin = Object.assign(new EventEmitter(), { ended: false, end() { this.ended = true; child.emit('stdin-end'); if (!child.deaf) setTimeout(() => child.finish(0), 20); } });
  }
  kill() { this.killed = true; this.finish(null, 'SIGTERM'); }
  finish(code, signal = null) { if (this.exitCode !== null || this.signalCode !== null) return; this.exitCode = code; this.signalCode = signal; this.emit('exit', code, signal); }
  prove(pid) { this.stdout.emit('data', Buffer.from('BOOKS_ENGINE_OWNER ' + JSON.stringify({ type: 'books-native-owner-v1', host_pid: this.pid, pid, creation_filetime: '1', image: this.command }) + '\n')); }
 }
 const childProcess = { ...require('node:child_process'), spawn: (command, args) => { const child = new Child(command, args); log.spawns.push(child); return child; } };
 const load = Module._load;
 Module._load = function (request, parent, isMain) {
  if (request === 'electron') return electron;
  if (request === 'electron-updater') return { autoUpdater: updater };
  if (request === 'node:child_process' && parent && parent.filename === MAIN) return childProcess;
  return load.call(this, request, parent, isMain);
 };
 const argv = process.argv, resourcesPath = process.resourcesPath;
 process.argv = [process.execPath, MAIN, ...(setup ? [] : ['--data-dir=' + data]), '--port=' + port, '--shell-profile=' + profile, '--quiet-errors', ...flags];
 Object.defineProperty(process, 'resourcesPath', { value: resources, configurable: true, writable: true });
 delete require.cache[MAIN];
 try { require(MAIN); } finally { process.argv = argv; }  // the hook stays: main.js requires electron-updater lazily
 // The fake engine: answers as our engine (owner pid) or another copy, with a loading object it is told.
 const engine = { pid: 4242, loading: { step: 'session', n: 3, of: 4, done: 1, total: 9, unit: 'items', progress_age_ms: 0, waiting_for: null, restart_safe: true,
  parts: { library: true, status: true, books: false, attention: false, jobs: false }, took_ms: null }, requests: [] };
 const server = http.createServer((req, res) => {
  engine.requests.push(req.url);
  const body = req.url === '/api/health' ? { application: 'Books Arranger', version: '0.22.1', pid: engine.pid, instance: 'a'.repeat(32), port }
   : req.url === '/api/desktop/status' ? { phase: engine.phase || 'running', error: '', busy: null, idle: false, loading: engine.loading, update: engine.update || null }
   : req.url === '/api/desktop/update' ? (engine.phase = 'pausing', engine.update = { phase: 'pausing', waiting: [], critical: [], elapsed: 0, safe_seconds: 90, stopped: [] }, { phase: 'pausing', update: engine.update }) : { error: 'no' };
  res.writeHead(body.error ? 404 : 200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(body));
 });
 const answer = () => new Promise((resolve) => server.listen(port, '127.0.0.1', resolve));
 const invoke = (name, ...args) => handlers[name]({ sender: log.windows[0].webContents }, ...args);
 const startups = () => log.sends.filter((item) => item.channel === 'books:startup').map((item) => item.value);
 // Ends this shell (as Quit would) so none of its watchers outlives the test.
 const close = async () => { if (!log.exits.length) for (const child of log.spawns) child.finish(0); await new Promise((resolve) => server.close(() => resolve())); server.closeAllConnections?.(); if (resourcesPath === undefined) delete process.resourcesPath; else process.resourcesPath = resourcesPath; Module._load = load; fs.rmSync(root, { recursive: true, force: true }); };
 return { log, data, handlers, appEvents, engine, answer, invoke, startups, close, port, profile, firstFrame: require('node:url').pathToFileURL(path.join(resources, 'backend', 'web', 'index.html')).href };
}

test('the window opens at app ready with the first frame, before the engine answers; the engine page takes over', async () => {
 const t = await boot();
 try {
  const win = await until(() => t.log.windows[0], 3000, 'a window');
  assert.equal(win.loads[0], t.firstFrame, 'the first frame is the page from disk');
  assert.equal(win.options.backgroundColor, '#121820');
  assert.equal(t.log.spawns.length, 1, 'the engine is launched beside the window');
  await until(() => win.visible, 3000, 'the window shown');
  assert.equal(t.engine.requests.length, 0, 'nothing has answered yet');
  assert.match(t.log.trays[0].tips.at(-1), /^Books Arranger — loading, step 1 of 4$/);
  const first = await t.invoke('books:startup');
  assert.equal(first.phase, 'launching'); assert.equal(first.lastLoadMs, null, 'no last load on a first start');
  t.log.spawns[0].prove(t.engine.pid); await t.answer();
  await until(() => win.loads.includes(`http://127.0.0.1:${t.port}/`), 6000, 'the engine page');
  assert.equal((await t.invoke('books:startup')).phase, 'running');
  // The load completes: its time is kept for the next start and the tray says Books Arranger again.
  t.engine.loading = { ...t.engine.loading, step: 'done', parts: { library: true, status: true, books: true, attention: true, jobs: true }, took_ms: 41000 };
  await until(() => fs.existsSync(path.join(t.profile, 'last-load.json')), 6000, 'the load time saved');
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(t.profile, 'last-load.json'), 'utf8')), { lastLoadMs: 41000 });
  assert.equal(t.log.trays[0].tips.at(-1), 'Books Arranger');
  assert.equal(t.log.errors.length, 0); assert.deepEqual(t.log.exits, []);
 } finally { await t.close(); }
});

test('an engine that exits while loading is the strip\'s Stopped, with its last lines; no error box, the app stays', async () => {
 const t = await boot();
 try {
  await until(() => t.log.spawns[0], 3000, 'the engine launch');
  t.log.spawns[0].stderr.emit('data', Buffer.from('Traceback...\nRuntimeError: Pending output moves need recovery first\n'));
  t.log.spawns[0].finish(1);
  const stopped = await until(() => t.startups().find((item) => item.phase === 'stopped'), 3000, 'Stopped');
  assert.equal(stopped.exited.code, 1); assert.match(stopped.exited.lastLines, /Pending output moves need recovery first/);
  assert.equal(t.log.errors.length, 0, 'no error box'); assert.deepEqual(t.log.exits, [], 'the app stays open');
  assert.equal(t.log.trays[0].tips.at(-1), 'Books Arranger — stopped');
  // Try again: a new launch from Step 1.
  assert.equal(await t.invoke('books:restart-engine'), true);
  await until(() => t.log.spawns.length === 2, 3000, 'a second launch');
  assert.equal((await t.invoke('books:startup')).phase, 'launching');
  // ...and the new engine is attached when it answers.
  t.log.spawns[1].prove(t.engine.pid); await t.answer();
  await until(() => t.log.windows[0].loads.includes(`http://127.0.0.1:${t.port}/`), 6000, 'the new engine page');
  assert.equal((await t.invoke('books:startup')).phase, 'running');
 } finally { await t.close(); }
});

test('a port held by another copy names its process', async () => {
 const t = await boot();
 try {
  await until(() => t.log.spawns[0], 3000, 'the engine launch');
  t.engine.pid = 9999; t.log.spawns[0].prove(4242); await t.answer();
  const stopped = await until(() => t.startups().find((item) => item.phase === 'stopped'), 6000, 'Stopped');
  assert.equal(stopped.portPid, 9999);
  assert.ok(!t.log.windows[0].loads.includes(`http://127.0.0.1:${t.port}/`), 'never attaches to another copy');
 } finally { await t.close(); }
});

test('Quit while loading closes at once: no confirmation, the window and tray go, the engine pipe closes', async () => {
 const t = await boot();
 try {
  const child = await until(() => t.log.spawns[0], 3000, 'the engine launch');
  child.on('stdin-end', () => setTimeout(() => child.finish(0), 50));
  const quitting = t.invoke('books:quit');
  assert.equal(t.log.windows[0].visible, false, 'the window goes at once');
  assert.equal(t.log.trays[0].destroyed, true);
  await quitting;
  assert.equal(child.stdin.ended, true); assert.deepEqual(t.log.exits, [0]);
  assert.ok(!t.engine.requests.includes('/api/desktop/quit'), 'no drain request: nothing runs but loading');
 } finally { await t.close(); }
});

test('Restart engine ends the stuck engine, shows the first frame and launches again', async () => {
 const t = await boot();
 try {
  const child = await until(() => t.log.spawns[0], 3000, 'the engine launch');
  child.prove(t.engine.pid); await t.answer();
  const win = t.log.windows[0];
  await until(() => win.loads.includes(`http://127.0.0.1:${t.port}/`), 6000, 'the engine page');
  const before = (await t.invoke('books:startup')).startedAt;
  child.on('stdin-end', () => setTimeout(() => child.finish(0), 50));
  assert.equal(await t.invoke('books:restart-engine'), true);
  assert.equal(child.stdin.ended, true);
  assert.equal(win.loads.at(-1), t.firstFrame, 'the old page goes with its engine');
  await until(() => t.log.spawns.length === 2, 3000, 'a new launch');
  const after = await t.invoke('books:startup');
  assert.equal(after.phase, 'launching'); assert.ok(after.startedAt >= before, 'the running clock restarts');
  assert.deepEqual(t.log.exits, []);
 } finally { await t.close(); }
});

test('first run: "Use this folder" closes the setup window and the main window opens at Step 1; the folder is kept once loaded', async () => {
 const t = await boot({ setup: true });
 try {
  const setupWindow = await until(() => t.log.windows[0], 3000, 'the setup window');
  assert.match(setupWindow.loads[0], /setup\.html$/);
  assert.equal(t.log.spawns.length, 0, 'no engine before a folder is chosen');
  const opened = await t.handlers['books:select']({ sender: setupWindow.webContents }, { folder: t.data, mode: 'new' });
  assert.deepEqual(opened, { opened: true });
  assert.equal(setupWindow.destroyed, true, 'the setup window closes');
  const main = t.log.windows[1];
  assert.equal(main.loads[0], t.firstFrame, 'the main window opens at Step 1');
  const engine = t.log.spawns.find((child) => /desktop_host\.py$/.test(child.args[2] || ''));
  assert.ok(engine.args.includes('--catalog-mode=new'));
  const settings = () => t.log.spawns.some((child) => /desktop_settings\.py$/.test(child.args[2] || ''));
  assert.equal(settings(), false, 'the folder is remembered only once its catalog has loaded');
  engine.prove(t.engine.pid); await t.answer();
  t.engine.loading = { ...t.engine.loading, step: 'done', parts: { library: true, status: true, books: true, attention: true, jobs: true }, took_ms: 2000 };
  await until(settings, 6000, 'the settings saved');
 } finally { await t.close(); }
});

// electron-updater 6.8.9 as it really behaves (node_modules/electron-updater/out/BaseUpdater.js:13-27 and NsisUpdater.js:
// 101-141): quitAndInstall() calls install(); doInstall() answers true at once and starts the installer asynchronously;
// then setImmediate(() => this.app.quit()) quits the app whatever the spawn does. Futaba's 0.22.1 QA, M-1.
function electronUpdaterLike({ spawnError = 'UNKNOWN' } = {}) {
 return (electronApp) => {
  const updater = Object.assign(new EventEmitter(), { setFeedURL() {}, checkForUpdates: async () => ({}), downloadUpdate: async () => {}, quitAndInstallCalled: false, spawned: [],
   downloadedUpdateHelper: { file: 'C:/owned/Books-Arranger-Setup-0.22.2.exe', downloadedFileInfo: { sha512: 'c'.repeat(88), isAdminRightsRequired: false } },
   app: { quit: () => electronApp.quit() } });
  updater.spawnLog = function (cmd) {
   this.spawned.push(cmd);
   return new Promise((resolve, reject) => { try { if (spawnError) throw Object.assign(new Error('spawn ' + spawnError), { code: spawnError }); resolve(true); } catch (error) { reject(error); } });
  };
  updater.doInstall = function () { this.spawnLog(this.downloadedUpdateHelper.file, ['--updated', '/S', '--force-run']).catch(() => {}); return true; };
  updater.install = function () { if (this.quitAndInstallCalled) return false; this.quitAndInstallCalled = true; return this.doInstall(); };
  updater.quitAndInstall = function (isSilent, isForceRunAfter) { if (this.install(isSilent, isForceRunAfter)) setImmediate(() => this.app.quit()); else this.quitAndInstallCalled = false; };
  return updater;
 };
}
const hosts = (t) => t.log.spawns.filter((child) => /desktop_host\.py$/.test(child.args[2] || ''));
async function loaded(t, child) {
 child.prove(t.engine.pid);
 if (!t.listening) { await t.answer(); t.listening = true; }
 t.engine.loading = { ...t.engine.loading, step: 'done', parts: { library: true, status: true, books: true, attention: true, jobs: true }, took_ms: 1000 };
 const end = Date.now() + 6000;
 while (Date.now() < end) { if ((await t.invoke('books:status')).loaded) return; await sleep(50); }
 throw new Error('timed out waiting for the load');
}
async function failedInstall(t) {
 t.log.updater.emit('update-downloaded', { version: '0.22.2' });
 const restart = t.invoke('books:update-install');
 await until(() => t.engine.requests.includes('/api/desktop/update'), 6000, 'the update request');
 t.engine.phase = 'updating'; hosts(t)[0].finish(0);  // the engine ends for the update
 const next = await until(() => hosts(t)[1], 8000, 'the old engine launched again');
 next.prove(t.engine.pid);
 await Promise.race([restart, sleep(8000)]);  // with M-1 the app has quit and the relaunch never answers
 await sleep(100);  // electron-updater's queued quit runs now
 return { next };
}
const NOT_INSTALLED = 'Books Arranger \u2014 update didn\u2019t install';

test('M-1: an installer that cannot start keeps the app open: the old engine starts again and the Install line says so', { timeout: 30000 }, async () => {
 const t = await boot({ updaterLike: electronUpdaterLike() });
 try {
  await loaded(t, await until(() => hosts(t)[0], 3000, 'the engine launch'));
  t.log.windows[0].hide();  // the window is closed to the tray
  const { next } = await failedInstall(t);
  assert.deepEqual(t.log.exits, [], 'the app stays open');
  assert.ok(t.log.updater.spawned.length >= 1, 'positive control: the installer start was attempted');
  const status = await t.invoke('books:status');
  assert.deepEqual([status.update.install.phase, status.update.install.cause, status.update.ready], ['failed', 'installer_blocked', true]);
  assert.ok(next.args.includes('--catalog-mode=existing'));
  // Judy 0.22.2 6.1: hidden at that moment, nothing is raised; the tray says it until the window is shown.
  assert.equal(t.log.windows[0].visible, false, 'nothing is raised');
  assert.equal(t.log.trays[0].tips.at(-1), NOT_INSTALLED);
  t.log.trays[0].emit('click');
  assert.equal(t.log.windows[0].visible, true);
  assert.notEqual(t.log.trays[0].tips.at(-1), NOT_INSTALLED, 'the tooltip goes once the window is shown');
 } finally { await t.close(); }
});

test('M-1: after a first-run New catalog, the relaunch after a failed install opens the existing catalog', { timeout: 30000 }, async () => {
 const t = await boot({ setup: true, updaterLike: electronUpdaterLike() });
 try {
  const setupWindow = await until(() => t.log.windows[0], 3000, 'the setup window');
  await t.handlers['books:select']({ sender: setupWindow.webContents }, { folder: t.data, mode: 'new' });
  const first = await until(() => hosts(t)[0], 3000, 'the engine launch');
  assert.ok(first.args.includes('--catalog-mode=new'), 'positive control: the first launch creates the catalog');
  fs.writeFileSync(path.join(t.data, 'inventory.sqlite3'), 'created by the engine');
  t.log.windows.shift();  // invoke() speaks for the main window from here
  await loaded(t, first);
  const { next } = await failedInstall(t);
  assert.ok(next.args.includes('--catalog-mode=existing'), next.args.join(' '));
  assert.deepEqual(t.log.exits, []);
 } finally { await t.close(); }
});

test('first run with --start-hidden: no form shows; the tray says choose a data folder and opens the form', async () => {
 const t = await boot({ setup: true, flags: ['--start-hidden'] });
 try {
  const form = await until(() => t.log.windows[0], 3000, 'the setup window');
  await sleep(30);  // ready-to-show has fired
  assert.equal(form.options.show, false, 'created hidden');
  assert.equal(form.visible, false, 'never shown by itself');
  const tray = await until(() => t.log.trays[0], 3000, 'the tray');
  assert.equal(tray.tips.at(-1), 'Books Arranger \u2014 choose a data folder');
  const labels = tray.menu.filter((item) => item.label).map((item) => item.label);
  assert.deepEqual(labels, ['Choose data folder\u2026', 'Quit Books Arranger']);
  tray.menu.find((item) => item.label === 'Choose data folder\u2026').click();
  assert.equal(form.visible, true, 'his own action opens it');
  tray.menu.find((item) => item.label === 'Quit Books Arranger').click();
  await until(() => t.log.exits.length, 3000, 'the quit');
  assert.deepEqual(t.log.exits, [0]);
 } finally { await t.close(); }
});

test('first run with --show-inactive shows the form without taking focus', async () => {
 const t = await boot({ setup: true, flags: ['--show-inactive'] });
 try {
  const form = await until(() => t.log.windows[0], 3000, 'the setup window');
  let focused = false; form.show = function () { this.visible = true; focused = true; };
  await until(() => form.visible, 3000, 'the form shown');
  assert.equal(focused, false, 'shown inactive');
 } finally { await t.close(); }
});

test('m-12: a copy started with --quit and no copy running exits at once, quietly: no window, no tray, no engine', async () => {
 const t = await boot({ flags: ['--quit'] });
 try {
  await until(() => t.log.exits.length, 3000, 'the exit');
  await sleep(50);
  assert.deepEqual(t.log.exits, [0]);
  assert.deepEqual([t.log.windows.length, t.log.trays.length, t.log.spawns.length], [0, 0, 0]);
 } finally { await t.close(); }
});

test('m-12: --quit sent to the first-run form ends it after the second copy has its answer', async () => {
 const t = await boot({ setup: true });
 try {
  await until(() => t.log.windows[0], 3000, 'the setup window');
  t.appEvents['second-instance']({}, ['--quit']);
  assert.deepEqual(t.log.exits, [], 'not inside the handler: the second copy gets its answer first');
  await until(() => t.log.exits.length, 3000, 'the exit');
  assert.deepEqual(t.log.exits, [0]);
 } finally { await t.close(); }
});
