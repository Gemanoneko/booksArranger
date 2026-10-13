'use strict';
// Books Arranger desktop shell. Runs the existing Python backend (bundled embeddable
// Python + LGPL FFmpeg) as a sidecar and shows its browser UI in one window.
// Close button: hide to the tray, work continues. Quit (tray): the book in progress
// finishes, nothing new starts, the backend exits, then the shell exits.

const { app, BrowserWindow, Menu, Tray, dialog, nativeImage, session, shell } = require('electron');
const { spawn, spawnSync } = require('node:child_process');
const crypto = require('node:crypto');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');

const PRODUCTION_PORT = 5210; // studio assignment; strict, no fallback
const DEV_PORT = 5212; // desktop dev/test instances (5211 is bound by the unit tests)
const isDev = !app.isPackaged;
const repoRoot = path.resolve(__dirname, '..');
const system32 = path.join(process.env.SystemRoot || 'C:\\Windows', 'System32');

// ── Command line ────────────────────────────────────────────────────────────
// --data-dir=<abs>     catalog/data folder (default: %LOCALAPPDATA%\Books Arranger\data)
// --port=<n>           loopback port (default 5210 packaged, 5212 dev)
// --roots-json=<abs>   library roots file (fixture/test libraries)
// --shell-profile=<abs> Electron profile (test instances keep away from the real one)
// --start-hidden       start in the tray without showing the window
// --show-inactive      show the window without taking focus
// --capture=<abs.png>  after the page loads, save a screenshot of the window
// --quiet-errors       report startup/engine errors on stderr instead of a dialog (test runs)
// Sent to an already running copy: --quit (same Quit as the tray, no prompt),
// --close-window (same as the window close button), --show.
function option(argv, name) {
  const prefix = `--${name}=`;
  const found = argv.find((arg) => arg.startsWith(prefix));
  return found ? found.slice(prefix.length) : null;
}
const flag = (argv, name) => argv.includes(`--${name}`);
const argv = process.argv.slice(1);

function reportError(title, message) {
  if (flag(argv, 'quiet-errors')) process.stderr.write(`${title}: ${message}\n`);
  else dialog.showErrorBox(title, message);
}

function absoluteOption(name) {
  const value = option(argv, name);
  if (value !== null && !path.isAbsolute(value)) {
    reportError('Books Arranger', `--${name} needs an absolute path.`);
    app.exit(2);
  }
  return value ? path.resolve(value) : null;
}

const profileDir = absoluteOption('shell-profile') || (isDev ? path.join(repoRoot, 'scratch', 'desktop-dev', 'electron-profile') : null);
if (profileDir) app.setPath('userData', profileDir);

const state = {
  backend: null,
  backendExited: false,
  baseUrl: '',
  token: crypto.randomBytes(32).toString('hex'),
  win: null,
  tray: null,
  quit: 'none', // none | requested | exiting
  ready: false,
  output: '',
};

function remember(chunk) {
  state.output = (state.output + chunk.toString('utf8')).slice(-16384);
}

function lastLines(text, count = 6) {
  return text.trim().split(/\r?\n/).filter(Boolean).slice(-count).join('\n');
}

// ── Configuration ───────────────────────────────────────────────────────────
function inside(child, parent) {
  const relative = path.relative(parent, child);
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

function readSettings() {
  try {
    return JSON.parse(fs.readFileSync(path.join(app.getPath('userData'), 'desktop-settings.json'), 'utf8'));
  } catch {
    return {};
  }
}

function configuration() {
  const settings = readSettings();
  const installDir = path.dirname(process.execPath);
  let dataDir = absoluteOption('data-dir');
  if (!dataDir && typeof settings.dataDir === 'string' && path.isAbsolute(settings.dataDir)) dataDir = path.resolve(settings.dataDir);
  if (!dataDir) {
    dataDir = isDev
      ? path.join(repoRoot, 'scratch', 'desktop-dev', 'data')
      : path.join(process.env.LOCALAPPDATA || app.getPath('userData'), 'Books Arranger', 'data');
  }
  if (app.isPackaged && (inside(dataDir, installDir) || inside(dataDir, process.resourcesPath))) {
    throw new Error('The data folder must be outside the install folder.');
  }
  const portText = option(argv, 'port');
  const port = portText === null ? (isDev ? DEV_PORT : PRODUCTION_PORT) : Number(portText);
  if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('--port must be a number from 1024 to 65535.');

  let rootsJson = absoluteOption('roots-json');
  if (!rootsJson && isDev) rootsJson = devRoots();

  // Dev runs use the same pinned runtime the installer bundles (npm run fetch-runtime).
  const runtime = isDev ? path.join(repoRoot, 'build-cache', 'runtime') : process.resourcesPath;
  const python = path.join(runtime, 'python', 'python.exe');
  const ffmpegDir = path.join(runtime, 'ffmpeg');
  if (!fs.existsSync(python) || !fs.existsSync(path.join(ffmpegDir, 'ffmpeg.exe'))) {
    throw new Error(isDev ? 'The bundled runtime is missing. Run: npm run fetch-runtime' : 'The installation is incomplete. Reinstall Books Arranger.');
  }
  const backendDir = isDev ? repoRoot : path.join(process.resourcesPath, 'backend');
  return { dataDir, port, rootsJson, python, backendDir, ffmpegDir };
}

// Dev runs never touch the real libraries unless --roots-json says so.
function devRoots() {
  const base = path.join(repoRoot, 'scratch', 'desktop-dev', 'library');
  const roots = { Audiobooks: path.join(base, 'Audiobooks'), Podcasts: path.join(base, 'Audiobooks', 'Podcasts'), Ebooks: path.join(base, 'Books') };
  for (const folder of Object.values(roots)) fs.mkdirSync(folder, { recursive: true });
  const file = path.join(repoRoot, 'scratch', 'desktop-dev', 'roots.json');
  fs.writeFileSync(file, JSON.stringify(roots, null, 2));
  return file;
}

// ── Backend process ─────────────────────────────────────────────────────────
function startBackend(config) {
  fs.mkdirSync(config.dataDir, { recursive: true });
  const args = ['-I', '-B', path.join(config.backendDir, 'desktop_backend.py'),
    '--database', path.join(config.dataDir, 'inventory.sqlite3'), '--port', String(config.port)];
  if (config.rootsJson) args.push('--roots-json', config.rootsJson);
  const pathEntries = [config.ffmpegDir, system32, process.env.SystemRoot || 'C:\\Windows'];
  const env = {};
  for (const key of ['SystemRoot', 'windir', 'TEMP', 'TMP', 'USERPROFILE', 'LOCALAPPDATA', 'APPDATA', 'HOMEDRIVE', 'HOMEPATH', 'ProgramData', 'COMPUTERNAME', 'USERNAME', 'PATHEXT', 'NUMBER_OF_PROCESSORS', 'PROCESSOR_ARCHITECTURE']) {
    if (process.env[key]) env[key] = process.env[key];
  }
  // Only the bundled FFmpeg is found; the current directory is never searched for executables.
  env.PATH = pathEntries.join(';');
  env.NoDefaultCurrentDirectoryInExePath = '1';
  env.BOOKS_ARRANGER_DESKTOP_TOKEN = state.token;
  state.baseUrl = `http://127.0.0.1:${config.port}`;
  // detached: not in libuv's kill-on-close job, so if the shell dies the engine sees its
  // standard input close and stops at a safe point (removing its ownership record)
  // instead of being terminated mid-write.
  const child = spawn(config.python, args, { cwd: config.backendDir, env, windowsHide: true, detached: true, stdio: ['pipe', 'pipe', 'pipe'] });
  child.stdout.on('data', remember);
  child.stderr.on('data', remember);
  child.stdin.on('error', () => {});
  child.on('error', (error) => remember(`\n${error.message}\n`));
  child.on('exit', (code) => {
    state.backendExited = true;
    if (!state.ready) return; // startup reports it: waitForBackend sees the exit
    if (state.quit !== 'none') return finishExit(0);
    if (code === 0) return finishExit(0); // the backend's own Stop server control
    reportError('Books Arranger stopped', `The Books Arranger engine stopped unexpectedly (exit ${code}).\n\n${lastLines(state.output)}`);
    finishExit(1);
  });
  state.backend = child;
  return child;
}

function request(method, route, { desktop = false, timeout = 5000 } = {}) {
  return new Promise((resolve, reject) => {
    const body = method === 'POST' ? '{}' : null;
    const headers = { Accept: 'application/json' };
    if (desktop) headers['X-Books-Desktop'] = state.token;
    if (body) Object.assign(headers, { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) });
    const req = http.request(`${state.baseUrl}${route}`, { method, headers, timeout }, (res) => {
      let data = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          if (res.statusCode >= 400) reject(new Error(parsed.error || `HTTP ${res.statusCode}`));
          else resolve(parsed);
        } catch (error) {
          reject(error);
        }
      });
    });
    req.on('timeout', () => req.destroy(new Error('Request timed out')));
    req.on('error', reject);
    if (body) req.write(body);
    req.end();
  });
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function waitForBackend(child) {
  const deadline = Date.now() + 180000;
  while (Date.now() < deadline) {
    if (state.backendExited) {
      await sleep(300); // let the last output arrive
      // The engine's own message, without the Python exception name.
      throw new Error(lastLines(state.output, 1).replace(/^[\w.]*(Error|Exception): /, '') || 'The engine exited during startup.');
    }
    try {
      const health = await request('GET', '/api/health', { timeout: 2000 });
      // Never attach to some other program (or another copy) that holds the port.
      if (health.application === 'Books Arranger' && health.pid === child.pid) return health;
      if (health.application) throw new Error(`Port ${new URL(state.baseUrl).port} belongs to another Books Arranger (PID ${health.pid}).`);
    } catch (error) {
      if (/belongs to another/.test(error.message)) throw error;
    }
    await sleep(250);
  }
  throw new Error('The engine did not become ready within 3 minutes.');
}

function killBackendTree() {
  if (!state.backend || state.backendExited) return;
  spawnSync(path.join(system32, 'taskkill.exe'), ['/PID', String(state.backend.pid), '/T', '/F'], { windowsHide: true });
}

// ── Window and tray ─────────────────────────────────────────────────────────
function iconImage() {
  return nativeImage.createFromPath(path.join(__dirname, 'icon.png'));
}

function createWindow() {
  const origin = state.baseUrl;
  const win = new BrowserWindow({
    width: 1280, height: 860, minWidth: 950, minHeight: 650,
    show: false, title: 'Books Arranger', backgroundColor: '#121820', autoHideMenuBar: true, icon: iconImage(),
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true, spellcheck: false },
  });
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//i.test(url) && !url.startsWith(`${origin}/`)) shell.openExternal(url);
    return { action: 'deny' };
  });
  win.webContents.on('will-navigate', (event, url) => {
    if (url.startsWith(`${origin}/`)) return;
    event.preventDefault();
    if (/^https?:\/\//i.test(url)) shell.openExternal(url);
  });
  win.webContents.on('render-process-gone', () => { if (!win.isDestroyed()) win.reload(); });
  // Close button: hide to the tray; conversions continue. No renderer round-trip.
  win.on('close', (event) => {
    if (state.quit === 'exiting') return;
    event.preventDefault();
    win.hide();
  });
  win.on('session-end', () => stopNowAndExit());
  win.once('ready-to-show', () => {
    if (flag(argv, 'start-hidden')) return;
    if (flag(argv, 'show-inactive')) win.showInactive();
    else win.show();
  });
  const capture = absoluteOption('capture');
  if (capture) {
    win.webContents.once('did-finish-load', () => setTimeout(async () => {
      try {
        const image = await win.webContents.capturePage();
        fs.writeFileSync(capture, image.toPNG());
      } catch (error) {
        remember(`\ncapture failed: ${error.message}\n`);
      }
    }, 3000));
  }
  win.loadURL(`${origin}/`);
  state.win = win;
}

function showWindow() {
  if (!state.win || state.win.isDestroyed()) return;
  if (state.win.isMinimized()) state.win.restore();
  state.win.show();
  state.win.focus();
}

function trayMenu() {
  const quitting = state.quit !== 'none';
  return Menu.buildFromTemplate([
    { label: 'Open Books Arranger', click: showWindow },
    { type: 'separator' },
    quitting
      ? { label: 'Quitting after the current book…', enabled: false }
      : { label: 'Quit', click: () => requestQuit({ confirmed: false }) },
  ]);
}

function createTray() {
  state.tray = new Tray(iconImage().resize({ width: 16, height: 16 }));
  state.tray.setToolTip('Books Arranger');
  state.tray.setContextMenu(trayMenu());
  state.tray.on('click', showWindow);
}

function refreshTray(tooltip) {
  if (!state.tray || state.tray.isDestroyed()) return;
  state.tray.setContextMenu(trayMenu());
  state.tray.setToolTip(tooltip);
}

// ── Quit ────────────────────────────────────────────────────────────────────
async function requestQuit({ confirmed }) {
  if (state.quit !== 'none') return;
  let status;
  try {
    status = await request('GET', '/api/desktop/status', { desktop: true });
  } catch {
    return forceExit(); // engine unreachable: nothing to finish
  }
  const busy = status.busy || {};
  if (busy.converting && !confirmed) {
    const title = busy.current_title ? `“${busy.current_title}”` : 'The current book';
    const choice = await dialog.showMessageBox({
      type: 'question', title: 'Quit Books Arranger',
      message: 'Quit after the current book?',
      detail: `${title} finishes converting first, then Books Arranger closes. Queued books stay queued for next time.`,
      buttons: ['Quit after this book', 'Cancel'], defaultId: 0, cancelId: 1, noLink: true,
    });
    if (choice.response !== 0 || state.quit !== 'none') return;
  }
  state.quit = 'requested';
  refreshTray(busy.converting ? 'Books Arranger — quitting after the current book' : 'Books Arranger — quitting');
  try {
    await request('POST', '/api/desktop/quit', { desktop: true });
  } catch {
    return forceExit();
  }
  watchQuit();
}

// The engine exits on its own once parked; the child 'exit' handler then ends the app.
// If it stops answering and does not exit, end its process tree after a grace period.
async function watchQuit() {
  let silentSince = null;
  while (!state.backendExited) {
    await sleep(1000);
    try {
      await request('GET', '/api/desktop/status', { desktop: true, timeout: 3000 });
      silentSince = null;
    } catch {
      silentSince = silentSince || Date.now();
      if (Date.now() - silentSince > 90000) return forceExit();
    }
  }
}

function forceExit() {
  killBackendTree();
  finishExit(0);
}

async function stopNowAndExit() {
  if (state.quit === 'exiting') return;
  state.quit = 'requested';
  try { await request('POST', '/api/desktop/stop-now', { desktop: true, timeout: 2000 }); } catch { /* engine gone */ }
  const deadline = Date.now() + 8000;
  while (!state.backendExited && Date.now() < deadline) await sleep(200);
  finishExit(0);
}

function finishExit(code) {
  if (state.quit === 'exiting') return;
  state.quit = 'exiting';
  if (state.tray && !state.tray.isDestroyed()) state.tray.destroy();
  app.exit(code);
}

function handleCommand(args) {
  if (flag(args, 'quit')) requestQuit({ confirmed: true });
  else if (flag(args, 'close-window')) { if (state.win && !state.win.isDestroyed()) state.win.close(); }
  else showWindow();
}

// ── Startup ─────────────────────────────────────────────────────────────────
if (!app.requestSingleInstanceLock()) {
  app.exit(0);
} else {
  app.on('second-instance', (_event, args) => handleCommand(args));
  // Tray tool: closing the window never ends the app (ProcessRules tray exception).
  app.on('window-all-closed', () => {});
  // Any other quit path (menu accelerator, system) goes through the same Quit.
  app.on('before-quit', (event) => {
    if (state.quit === 'exiting') return;
    event.preventDefault();
    requestQuit({ confirmed: false });
  });
  app.whenReady().then(async () => {
    session.defaultSession.setPermissionRequestHandler((_wc, _permission, callback) => callback(false));
    let config;
    try {
      config = configuration();
      const child = startBackend(config);
      createTray();
      await waitForBackend(child);
      state.ready = true;
      if (state.backendExited) throw new Error(lastLines(state.output) || 'The engine exited during startup.');
      createWindow();
    } catch (error) {
      killBackendTree();
      reportError('Books Arranger could not start', error.message);
      finishExit(1);
    }
  });
}
