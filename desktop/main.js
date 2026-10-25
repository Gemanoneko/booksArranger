'use strict';
// Books Arranger desktop shell. Runs the existing Python backend (bundled embeddable
// Python + LGPL FFmpeg) as a sidecar and shows its browser UI in one window.
// Close button: hide to the tray, work continues. Quit (tray): the book in progress
// finishes, nothing new starts, the backend exits, then the shell exits.

const { app, BrowserWindow, Menu, Tray, dialog, nativeImage, session, shell, ipcMain } = require('electron');
const { spawn } = require('node:child_process');
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
require('./launch-options').refuseCapture(argv);

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
  owner: null,
  hostOutput: '',
  engineVersion: '',
  updateLog: '',
  baseUrl: '',
  token: crypto.randomBytes(32).toString('hex'),
  win: null,
  tray: null,
  quit: 'none', // none | requested | updating | installing | exiting
  ready: false, // the engine answered with our ownership proof
  loaded: false, // ...and reported its catalog loaded (ruling 28): until then Quit is immediate and the strip is up
  startup: null, // desktop/startup.js record: what the page's load strip needs from the shell
  generation: 0, // one per engine launch; a Restart engine leaves the old launch's watchers behind
  verdict: 'working', // the shell's own Working/Waiting/Stuck/Stopped, for the tray
  firstFrame: '', // file URL of the page the window shows before the engine answers
  output: '',
};
const startupKit = require('./startup');
let loadState = null; // web/load-state.js, shared with the page

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
  const file=path.join(app.getPath('userData'),'desktop-settings.json');
  if(!fs.existsSync(file))return {};
  const info=fs.lstatSync(file);
  if(!info.isFile()||info.isSymbolicLink()||info.size>8192)throw new Error('Desktop settings are not an ordinary bounded file; retained unchanged.');
  const value=JSON.parse(fs.readFileSync(file,'utf8'));
  if(!value||typeof value.dataDir!=='string'||!path.isAbsolute(value.dataDir))throw new Error('Desktop settings need an explicit absolute data folder; retained unchanged.');
  const sourcesFile=path.join(app.getPath('userData'),'audiobook-sources.json');
  if(fs.existsSync(sourcesFile)){
    const sourceInfo=fs.lstatSync(sourcesFile);
    if(!sourceInfo.isFile()||sourceInfo.isSymbolicLink()||sourceInfo.size>16384)throw Error('Audiobook source settings are not an ordinary bounded file.');
    const sources=JSON.parse(fs.readFileSync(sourcesFile,'utf8'));
    if(!sources||Array.isArray(sources)||Object.keys(sources).some(key=>!['audiobook_sources','audiobook_output_root'].includes(key)))throw Error('Unknown audiobook source settings.');
    for(const key of ['audiobook_sources','audiobook_output_root'])if(key in sources){
      if(key in value&&JSON.stringify(value[key])!==JSON.stringify(sources[key]))throw Error('Conflicting source settings preserved; review configuration.');
      value[key]=sources[key];
    }
  }
  return value;
}

function configuration() {
  const settings = readSettings();
  const installDir = path.dirname(process.execPath);
  let dataDir = absoluteOption('data-dir');
  if (!dataDir && typeof settings.dataDir === 'string' && path.isAbsolute(settings.dataDir)) dataDir = path.resolve(settings.dataDir);
  const requiresSetup = !dataDir;
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

  const audiobookSources=(!isDev && !rootsJson)?settings.audiobook_sources:null;
  const audiobookOutputRoot=(!isDev && !rootsJson)?settings.audiobook_output_root:null;
  if(audiobookSources!==null && audiobookSources!==undefined && (!Array.isArray(audiobookSources)||!audiobookSources.length||audiobookSources.length>32||audiobookSources.some(root=>typeof root!=='string'||!path.isAbsolute(root))))throw Error('Audiobook source settings need an ordered list of absolute paths.');
  if(audiobookOutputRoot!==null && audiobookOutputRoot!==undefined && (typeof audiobookOutputRoot!=='string'||!path.isAbsolute(audiobookOutputRoot)))throw Error('Audiobook output setting needs an absolute path.');

  // Dev runs use the same pinned runtime the installer bundles (npm run fetch-runtime).
  let runtime=process.resourcesPath;
  if(isDev){
    const pointerPath=path.join(repoRoot,'build-cache','runtime-pointer.json');
    const info=fs.lstatSync(pointerPath);if(!info.isFile()||info.isSymbolicLink()||info.size>1024*1024)throw new Error('Runtime pointer is not an ordinary bounded file');
    const pointer=JSON.parse(fs.readFileSync(pointerPath,'utf8'));
    if(pointer.schema!=='books-runtime-pointer-v1'||!path.isAbsolute(pointer.root)||!inside(pointer.root,path.join(repoRoot,'build-cache','builds'))||!pointer.files)throw new Error('Runtime pointer differs from the owned build layout');
    const digest=crypto.createHash('sha256').update(JSON.stringify(pointer.files)).digest('hex');
    if(digest!==pointer.manifest_sha256)throw new Error('Runtime pointer manifest differs');
    runtime=pointer.root;
    for(const [name,expected] of Object.entries(pointer.files)){
      const candidate=path.resolve(runtime,name);if(!inside(candidate,runtime))throw new Error('Runtime file escapes owned layout');
      const stat=fs.lstatSync(candidate);if(!stat.isFile()||stat.isSymbolicLink()||stat.size!==expected.size||crypto.createHash('sha256').update(fs.readFileSync(candidate)).digest('hex')!==expected.sha256)throw new Error('Runtime file differs from pinned build');
    }
  }
  const python = path.join(runtime, 'python', 'python.exe');
  const ffmpegDir = path.join(runtime, 'ffmpeg');
  if (!fs.existsSync(python) || !fs.existsSync(path.join(ffmpegDir, 'ffmpeg.exe'))) {
    throw new Error(isDev ? 'The bundled runtime is missing. Run: npm run fetch-runtime' : 'The installation is incomplete. Reinstall Books Arranger.');
  }
  const backendDir = isDev ? repoRoot : path.join(process.resourcesPath, 'backend');
  return { dataDir, requiresSetup, catalogMode: settings.catalogMode || (option(argv,'catalog-mode') || 'existing'), port, rootsJson, audiobookSources, audiobookOutputRoot, python, backendDir, ffmpegDir };
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
  state.backendExited=false;state.owner=null;state.hostOutput='';
  const args = ['-I', '-B', path.join(config.backendDir, 'desktop_host.py'),
    '--database', path.join(config.dataDir, 'inventory.sqlite3'), '--port', String(config.port), '--catalog-mode=' + config.catalogMode];
  if (config.rootsJson) args.push('--roots-json', config.rootsJson);
  for(const root of config.audiobookSources || [])args.push('--audiobook-source',root);
  if(config.audiobookOutputRoot)args.push('--audiobook-output-root',config.audiobookOutputRoot);
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
  // The detached native host retains the engine's Job and process HANDLE.
  // Shell-pipe loss requests checkpoint shutdown; HTTP failures never kill it.
  const child = spawn(config.python, args, { cwd: config.backendDir, env, windowsHide: true, detached: true, stdio: ['pipe', 'pipe', 'pipe'] });
  child.stdout.on('data', (chunk) => {
    remember(chunk);
    state.hostOutput += chunk.toString('utf8');
    if (state.hostOutput.length > 32768) state.hostOutput = state.hostOutput.slice(-32768);
    let end;
    while ((end = state.hostOutput.indexOf('\n')) !== -1) {
      const line = state.hostOutput.slice(0, end).trim();
      state.hostOutput = state.hostOutput.slice(end + 1);
      if (!line.startsWith('BOOKS_ENGINE_OWNER ')) continue;
      try {
        const proof = JSON.parse(line.slice('BOOKS_ENGINE_OWNER '.length));
        if (state.owner || proof.type !== 'books-native-owner-v1' || proof.host_pid !== child.pid ||
            !Number.isInteger(proof.pid) || proof.pid <= 0 || !/^\d+$/.test(String(proof.creation_filetime)) ||
            path.resolve(proof.image).toLowerCase() !== path.resolve(config.python).toLowerCase()) {
          throw new Error('Engine native ownership proof differs');
        }
        state.owner = proof;
      } catch (error) { remember('\n' + error.message + '\n'); }
    }
  });
  child.stderr.on('data', remember);
  child.stdin.on('error', () => {});
  child.on('error', (error) => remember(`\n${error.message}\n`));
  const generation = state.generation;
  child.on('exit', (code) => {
    if (generation !== state.generation) return; // a launch Restart engine already replaced
    state.backendExited = true;
    // Restart to update: the update flow reads the exit (code 0 installs; anything else starts the old engine again).
    if (state.quit === 'updating' || state.quit === 'installing') return;
    if (state.quit !== 'none') return finishExit(code === 0 ? 0 : 1);
    // While loading, an exit is the strip's Stopped (Try again), never an error box (Judy 3.4).
    if (!state.loaded) return setTimeout(() => engineStopped({ code, lastLines: lastLines(state.output) }), 300); // the last output first
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
          // The status marks an answer (a refusal), as against no answer at all: the update tells them apart.
          if (res.statusCode >= 400) reject(Object.assign(new Error(parsed.error || `HTTP ${res.statusCode}`), { status: res.statusCode, code: parsed.code }));
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

// Every desktop status reader shares one in-flight request and reuses its answer
// until 1 s after it was sent (the engine also shares one state computation):
// polls cannot pile up. Controls invalidate it before and after they run.
const desktopStatus = require('./status-flight').createStatusFlight({
  fetch: (timeout) => request('GET', '/api/desktop/status', { desktop: true, timeout }),
});
// The update park loop receives this instead of raw request(): its status reads
// join the shared flight; its POST changes the phase, so the cached answer is dropped.
function engineRequest(method, route, options = {}) {
  if (method === 'GET' && route === '/api/desktop/status') return desktopStatus.get({ timeout: options.timeout, maxAge: 0 });
  if (method !== 'POST') return request(method, route, options);
  desktopStatus.invalidate();
  return request(method, route, options).finally(() => desktopStatus.invalidate());
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// ── Startup (ruling 28) ─────────────────────────────────────────────────────
// The window opens at app ready and the engine fills it in. There is no total time limit: the shell waits for the
// engine's first answer, then watches; the page's strip says Working, Waiting or Stuck from silence, and Stopped when
// the process has exited or another copy holds the port. A Restart engine is the way out of a stuck load.
function pushStartup() {
  if (state.win && !state.win.isDestroyed()) state.win.webContents.send('books:startup', state.startup.value);
}
function engineStopped({ code = null, lastLines: lines = '', portPid = null } = {}) {
  if (state.loaded || state.quit !== 'none') return;
  state.startup.stopped({ code, lastLines: lines, portPid });
  state.verdict = 'stopped';
  pushStartup(); loadTip(loadState ? loadState.trayTooltip({ state: 'stopped' }, null, false) : 'Books Arranger — stopped');
  if (pendingLaunch) { pendingLaunch.reject(Object.assign(new Error('The engine stopped while loading'), { lastLines: lines })); pendingLaunch = null; }
}
let pendingLaunch = null;
// Resolves when our engine answers (the page is then served by it); rejects when it stops first.
function watchEngine(generation) {
  return new Promise((resolve, reject) => {
    pendingLaunch = { resolve, reject };
    (async () => {
      while (generation === state.generation && state.startup.value.phase === 'launching') {
        if (state.backendExited) return; // the exit handler reports Stopped
        try {
          const health = await request('GET', '/api/health', { timeout: 2000 });
          if (generation !== state.generation) return;
          // Never attach to some other program (or another copy) that holds the port.
          const verdict = startupKit.classifyHealth(health, state.owner, app.getVersion());
          if (verdict === 'ours') return attachEngine(health);
          if (verdict === 'other') return engineStopped({ portPid: health.pid, lastLines: `Port ${new URL(state.baseUrl).port} belongs to another Books Arranger (process ${health.pid}).` });
        } catch { /* not answering yet */ }
        await sleep(250);
      }
    })();
  });
}
function attachEngine(health) {
  state.engineVersion = health.version;
  state.ready = true;
  state.startup.running();
  if (state.win && !state.win.isDestroyed()) state.win.loadURL(`${state.baseUrl}/`).catch((error) => remember(`\n${error.message}\n`)); // the engine's page takes over the first frame
  pushStartup(); broadcastStatus();
  watchLoad(state.generation);
  if (pendingLaunch) { pendingLaunch.resolve(health); pendingLaunch = null; }
}
// The tray follows the load (3.8), refreshed every 5 s; the completed load's time is kept for the next start (3.7).
async function watchLoad(generation) {
  const tracker = loadState.createTracker(state.startup.value.startedAt);
  let lastTray = 0;
  while (generation === state.generation && !state.loaded && state.quit === 'none' && !state.backendExited) {
    const at = Date.now();
    tracker.tick(at);
    try {
      const status = await desktopStatus.get({ timeout: 3000 });
      tracker.observe(status, Date.now());
      if (!status.loading || loadState.loaded({ loading: status.loading })) return engineLoaded(status.loading && status.loading.took_ms);
    } catch (error) { if (error.status) tracker.heard(Date.now()); }
    const before = state.verdict;
    state.verdict = loadState.evaluate(tracker, Date.now()).state;
    if (state.verdict !== before || Date.now() - lastTray >= 5000) { lastTray = Date.now(); loadTip(loadState.trayTooltip({ state: state.verdict }, tracker.loading, false)); }
    await sleep(1000);
  }
}
function engineLoaded(tookMs) {
  state.loaded = true; state.verdict = 'working';
  if (Number.isFinite(tookMs)) { state.startup.loaded(tookMs); startupKit.saveLastLoad(startupKit.loadTimeFile(app.getPath('userData')), tookMs); }
  pushStartup(); loadTip('Books Arranger');
  if (pendingSettings) { const save = pendingSettings; pendingSettings = null; save().catch((error) => remember(`\nSettings were not saved: ${error.message}\n`)); }
}
let pendingSettings = null; // first run: the chosen folder is remembered once its catalog has loaded
function launchEngine(config, { fresh = true } = {}) {
  state.generation += 1;
  state.ready = false; state.loaded = false; state.verdict = 'working';
  state.output = '';
  if (fresh) state.startup.launch(); // a Restart engine started its launch (and its clock) at the press
  pushStartup(); loadTip(loadState.trayTooltip({ state: 'working' }, null, false));
  startBackend(config); // first: the watch reads this launch's exit flag, never the last launch's
  return watchEngine(state.generation);
}
// Ends the current engine: its pipe closes (a checkpoint stop, as at a failed start); an engine still there after the
// bound is ended through its native host (its kill-on-close job). Only while loading: nothing else runs yet.
async function endLoadingEngine(boundMs = 15000) {
  const child = state.backend;
  if (!child || state.backendExited) return;
  try { child.stdin.end(); } catch { /* host gone */ }
  const deadline = Date.now() + boundMs;
  while (child.exitCode === null && child.signalCode === null && Date.now() < deadline) await sleep(200);
  if (child.exitCode === null && child.signalCode === null) {
    remember('\nThe engine did not stop within ' + Math.round(boundMs / 1000) + ' s; ending it.\n');
    try { child.kill(); } catch { /* already gone */ }
    const end = Date.now() + 5000;
    while (child.exitCode === null && child.signalCode === null && Date.now() < end) await sleep(200);
  }
}
async function restartEngine(config) {
  if (state.loaded || state.quit !== 'none' || state.restarting) return false;
  state.restarting = true;
  // A new catalog the first launch already created is opened as an existing one.
  if (config.catalogMode === 'new' && fs.existsSync(path.join(config.dataDir, 'inventory.sqlite3'))) config = currentConfig = { ...config, catalogMode: 'existing' };
  try {
    state.generation += 1; // the old launch's exit and watchers no longer speak
    state.startup.launch(); state.verdict = 'working'; pushStartup();
    await endLoadingEngine();
    if (state.win && !state.win.isDestroyed()) await state.win.loadURL(state.firstFrame).catch(() => {}); // the old page's token died with its engine
    launchEngine(config, { fresh: false }).catch(() => { /* the strip shows Stopped */ });
    return true;
  } finally { state.restarting = false; }
}

// ── Window and tray ─────────────────────────────────────────────────────────
function iconImage() {
  return nativeImage.createFromPath(path.join(__dirname, 'icon.png'));
}

// The window exists from app ready (Judy 3.2): its first frame is the app's own page from disk (the same markup and
// script, showing Step 1 and every placeholder) until the engine answers and serves the page itself.
function createWindow() {
  const origin = state.baseUrl;
  const win = new BrowserWindow({
    width: 1280, height: 860, minWidth: 950, minHeight: 650,
    show: false, title: 'Books Arranger', backgroundColor: '#121820', autoHideMenuBar: true, icon: iconImage(),
    webPreferences: { preload:path.join(__dirname,'preload.js'), contextIsolation: true, nodeIntegration: false, sandbox: true, spellcheck: false },
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
  // The page asks for the shell's startup record when it loads (the first frame, then the engine's page).
  win.webContents.on('did-finish-load', () => { if (state.startup) pushStartup(); });
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
  state.win = win;
  win.loadURL(state.firstFrame).catch((error) => remember(`\n${error.message}\n`));
}

function showWindow() {
  if (!state.win || state.win.isDestroyed()) return;
  if (state.win.isMinimized()) state.win.restore();
  state.win.show();
  state.win.focus();
}

function trayMenu() {
  const updating = state.quit === 'updating' || state.quit === 'installing' || !!updateController?.busy.install;
  const quitting = state.quit !== 'none' && !updating;
  // Judy 0.22.1 2.7: tray Check and Restart show the window and run into the panel; failures appear only there.
  return Menu.buildFromTemplate([
    { label: 'Open Books Arranger', click: showWindow },
    { type: 'separator' },
    quitting
      ? { label: 'Quitting after the current book…', enabled: false }
      : { label: 'Quit Books Arranger', enabled: !updating, click: () => requestQuit({ confirmed: false }) },
    { type:'separator' },
    { label:'Check for updates',enabled:!!updateController&&!quitting&&!updating,click:()=>{showWindow();updateController.check().catch(error=>logUpdate('Tray check: '+error.message));} },
    ...(updating?[{label:'Updating…',enabled:false}]
      :updateController&&updateController.ready&&!quitting?[{...startupKit.restartItem({loaded:state.loaded,verdict:state.verdict}),click:()=>{showWindow();if(state.win&&!state.win.isDestroyed())state.win.webContents.send('books:update-restart');}}]:[]),
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
// The load's tooltip (3.8) is kept, so an update broadcast during loading repeats it instead of "Books Arranger".
function loadTip(tooltip) {
  state.trayTip = tooltip === 'Books Arranger' ? '' : tooltip;
  refreshTray(tooltip);
}

// ── Quit ────────────────────────────────────────────────────────────────────
async function requestQuit({ confirmed }) {
  if(state.backendExited)return finishExit(state.backend?.exitCode===0?0:1);
  if (state.quit !== 'none') return;
  if (!state.loaded) return quitWhileLoading();
  let status;
  try {
    status = await desktopStatus.get();
  } catch (error) {
    reportError('Books Arranger is still running', 'The engine did not confirm a safe Quit. Try Quit again when it responds.\n\n' + error.message);
    return;
  }
  const busy = status.busy || {};
  if (busy.converting && !confirmed) {
    const title = busy.current_title ? `“${busy.current_title}”` : 'The current book';
    const choice = await dialog.showMessageBox({
      type: 'question', title: 'Quit Books Arranger',
      message: 'Quit after the current book?',
      detail: `${title} finishes converting first, then Books Arranger closes. Queued books stay queued for next time.`,
      buttons: ['Quit after this book', 'Cancel'], defaultId: 1, cancelId: 1, noLink: true,
    });
    if (choice.response !== 0 || state.quit !== 'none') return;
  }
  state.quit = 'requested';
  refreshTray(busy.converting ? 'Books Arranger — quitting after the current book' : 'Books Arranger — quitting');
  try {
    await engineRequest('POST', '/api/desktop/quit', { desktop: true });
  } catch (error) {
    state.quit = 'none';
    refreshTray('Books Arranger — Quit could not be confirmed');
    reportError('Books Arranger is still running', 'Quit could not be confirmed; ownership remains held.\n\n' + error.message);
    return;
  }
  watchQuit();
}

// HTTP failure never proves a safe checkpoint, but a closed server after an accepted Quit is the engine's
// own last step: once connections are refused for a few seconds the engine is gone and the shell exits.
const { createQuitWatch, outcomeOf } = require('./quit-watch');
async function engineGoneExit() {
  // Tell the host the shell is done, give it a moment to report the engine's exit, then leave.
  try { if (state.backend && !state.backendExited) state.backend.stdin.end(); } catch { /* host gone */ }
  const deadline = Date.now() + 5000;
  while (!state.backendExited && Date.now() < deadline) await sleep(200);
  finishExit(state.backendExited && state.backend?.exitCode !== 0 ? 1 : 0);
}
async function watchQuit() {
  const watch = createQuitWatch();
  while (!state.backendExited && state.quit === 'requested') {
    await sleep(1000);
    try {
      const status = await desktopStatus.get({ timeout: 3000, maxAge: 0 });
      watch.observe('reply');
      refreshTray('Books Arranger — ' + status.phase);
      if (status.phase === 'blocked') {
        state.quit = 'none';
        refreshTray('Books Arranger — Quit blocked');
        reportError('Books Arranger is still running', status.error || 'A worker has not reached its safe checkpoint. Try Quit again.');
        return;
      }
    } catch (error) {
      if (watch.observe(outcomeOf(error))) return engineGoneExit();
      refreshTray('Books Arranger — waiting for engine checkpoint');
    }
  }
}

// Quit while loading closes at once, with no confirmation: nothing runs but loading (Judy 3.2). The window and tray go
// now; the engine stops at its next checkpoint (its pipe closes, as at a failed start), bounded by endLoadingEngine.
async function quitWhileLoading() {
  state.quit = 'requested';
  if (state.win && !state.win.isDestroyed()) state.win.hide();
  if (state.tray && !state.tray.isDestroyed()) state.tray.destroy();
  await endLoadingEngine();
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

async function repeatQuit() {
  // A second --quit while a Quit is under way: if the engine no longer answers at all, it is gone.
  try { await request('GET', '/api/health', { timeout: 2000 }); }
  catch (error) { if (outcomeOf(error) === 'refused') return engineGoneExit(); }
}
function handleCommand(args) {
  if (flag(args, 'quit')) { if (state.quit === 'requested') repeatQuit(); else requestQuit({ confirmed: true }); }
  else if (flag(args, 'close-window')) { if (state.win && !state.win.isDestroyed()) state.win.close(); }
  else showWindow();
}

// IPC accepts only this app's current page or the local first-run selector.
let currentConfig=null;
let setupWindow=null;
let updateController=null;
function trustedSender(event){
  const wc=event.sender;
  if(setupWindow&&!setupWindow.isDestroyed()&&wc===setupWindow.webContents&&wc.getURL()===require('node:url').pathToFileURL(path.join(__dirname,'setup.html')).href)return 'setup';
  if(state.win&&!state.win.isDestroyed()&&wc===state.win.webContents&&(new URL(wc.getURL()).origin===state.baseUrl||state.firstFrame&&wc.getURL()===state.firstFrame))return 'app';
  throw new Error('Unknown desktop control sender');
}
function runReadOnlyPython(config,script,args){return new Promise((resolve,reject)=>{
  const child=spawn(config.python,['-I','-B',path.join(config.backendDir,script),...args],{cwd:config.backendDir,windowsHide:true,stdio:['ignore','pipe','pipe']});
  let output='',error='';const timer=setTimeout(()=>{child.kill();reject(new Error('Data folder check timed out'));},15000);
  child.stdout.on('data',b=>{output+=b.toString('utf8');if(output.length>16384)child.kill();});
  child.stderr.on('data',b=>{error=(error+b.toString('utf8')).slice(-4096);});
  child.on('error',e=>{clearTimeout(timer);reject(e);});
  child.on('exit',code=>{clearTimeout(timer);try{const result=JSON.parse(output);if(code||!result.ok)reject(new Error(result.error||error||'Data folder check failed'));else resolve(result);}catch(e){reject(new Error(error||e.message));}});
});}
function broadcastStatus(){
  const value={engineVersion:state.engineVersion,quit:state.quit,update:updateController?updateController.value:null};
  if(state.win&&!state.win.isDestroyed())state.win.webContents.send('books:status',value);
  const updating=state.quit==='updating'||state.quit==='installing'||!!updateController?.busy.install;
  refreshTray(updating?'Books Arranger — updating':state.quit!=='none'?'Books Arranger — '+state.quit:state.trayTip||'Books Arranger');
}
// The updater's raw error text goes to the shell's own log, never to the page (Judy 0.22.1 2.2).
function logUpdate(line){
  state.updateLog=(state.updateLog+new Date().toISOString()+' '+String(line)+'\n').slice(-16384);
  if(flag(argv,'quiet-errors'))process.stderr.write('[update] '+line+'\n');
}
function acquireUpdateArtifact(config,artifact){return new Promise((resolve,reject)=>{
  const child=spawn(config.python,['-I','-B',path.join(config.backendDir,'desktop_update_lease.py'),artifact.path,artifact.sha512],{cwd:config.backendDir,windowsHide:true,detached:true,stdio:['pipe','pipe','pipe']});
  let output='',error='',settled=false;const timer=setTimeout(()=>{child.stdin.end();reject(new Error('Installer integrity check timed out'));},30000);
  child.stdin.on('error',()=>{});
  child.stderr.on('data',b=>error=(error+b.toString('utf8')).slice(-4096));
  child.stdout.on('data',b=>{output+=b.toString('utf8');if(!output.includes('\n'))return;
    try{const proof=JSON.parse(output.trim());if(proof.type!=='books-update-lease-v1'||proof.sha512!==artifact.sha512)throw new Error('Installer lease differs');
      clearTimeout(timer);settled=true;resolve({isAlive:()=>child.exitCode===null,close:async()=>{child.stdin.end();}});
    }catch(e){clearTimeout(timer);child.stdin.end();reject(e);}});
  child.on('error',e=>{clearTimeout(timer);reject(e);});
  child.on('exit',code=>{clearTimeout(timer);if(!settled)reject(new Error(error||'Installer integrity check failed ('+code+')'));});
});}
function configureUpdater(config){
  const {autoUpdater}=require('electron-updater');
  const {UpdateController}=require('./update-controller');
  if(app.isPackaged)autoUpdater.setFeedURL({provider:'github',owner:'Gemanoneko',repo:'booksArranger',private:false});
  updateController=new UpdateController({provider:autoUpdater,packaged:app.isPackaged,version:app.getVersion(),notify:broadcastStatus,log:logUpdate,
    exists:file=>fs.existsSync(file),
    acquireArtifact:artifact=>acquireUpdateArtifact(config,artifact),
    // Stopped while loading (Judy 3.6): no engine to stop, the update installs at once.
    parkEngine:options=>!state.loaded&&state.backendExited&&state.quit==='none'?(state.quit='updating',broadcastStatus(),Promise.resolve())
      :require('./engine-update').parkOwnedEngine({state,request:engineRequest,sleep,broadcast:broadcastStatus,...options}),
    install:()=>installUpdate(autoUpdater),
    restartEngine:()=>restartEngineAfterUpdate(config),
  });
  broadcastStatus();
}
// Silent install (Sergei 2026-10-25, Q2: no installer window), reopening by itself. electron-updater quits the app
// as soon as it has asked for the installer, before a failed start is known; the quit is held while 'installing' and
// the app exits only once the installer process exists. Otherwise the old engine starts again (0.21.1 left the
// shell with no engine at all when the installer did not start).
async function installUpdate(autoUpdater){
  const original=autoUpdater.spawnLog;let spawned=null;
  autoUpdater.spawnLog=function(...args){spawned=original.apply(this,args);return spawned;};
  state.quit='installing';broadcastStatus();
  try{
    autoUpdater.quitAndInstall(true,true);
    if(!autoUpdater.quitAndInstallCalled||!spawned)throw new Error('The updater did not start the installer');
    await Promise.race([spawned,sleep(10000).then(()=>{throw new Error('The installer process did not start within 10 s');})]);
  }catch(error){
    autoUpdater.quitAndInstallCalled=false;state.quit='updating';
    throw Object.assign(error,{updateCause:'installer_blocked'});
  }finally{autoUpdater.spawnLog=original;}
  finishExit(0);
}
// The update did not install: the old version starts again from Step 1 and loads as at launch (no time limit).
async function restartEngineAfterUpdate(config){
  try{
    state.quit='none';
    if(state.win&&!state.win.isDestroyed())await state.win.loadURL(state.firstFrame).catch(()=>{});
    await launchEngine(config); // resolves when the new engine answers; it serves the page with its own token
  }finally{state.quit='none';broadcastStatus();}
}
ipcMain.handle('books:update-check',async event=>{if(trustedSender(event)!=='app'||!updateController)throw new Error('Update controls unavailable');return updateController.check();});
ipcMain.handle('books:update-download',async event=>{if(trustedSender(event)!=='app'||!updateController)throw new Error('Update controls unavailable');return updateController.download();});
ipcMain.handle('books:update-install',async event=>{if(trustedSender(event)!=='app'||!updateController)throw new Error('Update controls unavailable');return updateController.restart();});
ipcMain.handle('books:update-cancel',async event=>{if(trustedSender(event)!=='app'||!updateController)throw new Error('Update controls unavailable');return updateController.cancel();});
ipcMain.handle('books:update-show-installer',async event=>{if(trustedSender(event)!=='app'||!updateController)throw new Error('Update controls unavailable');
  const {showInstaller,installerPath}=updateController.value;if(!showInstaller)return false;shell.showItemInFolder(installerPath);return true;});
// The window, the tray and the updater exist from the first frame; the engine is launched beside them and the page
// shows its load (ruling 28). Returns the launch: it resolves when the engine answers, rejects if it stops first.
function startConfigured(config){
  currentConfig=config;
  loadState=require(path.join(config.backendDir,'web','load-state.js'));
  state.firstFrame=require('node:url').pathToFileURL(path.join(config.backendDir,'web','index.html')).href;
  state.baseUrl=`http://127.0.0.1:${config.port}`;
  state.startup=startupKit.createStartup({lastLoadMs:startupKit.readLastLoad(startupKit.loadTimeFile(app.getPath('userData')))});
  if(!state.tray)createTray();
  createWindow();
  if(!updateController)configureUpdater(config);
  const launch=launchEngine(config,{fresh:false});
  launch.catch(()=>{}); // a stop shows in the strip (Stopped, Try again), never as an error box
  return launch;
}
async function chooseCatalog(){
  setupWindow=new BrowserWindow({width:1280,height:860,minWidth:950,minHeight:650,title:'Books Arranger — Choose data folder',backgroundColor:'#1B2530',autoHideMenuBar:true,
    webPreferences:{preload:path.join(__dirname,'preload.js'),contextIsolation:true,nodeIntegration:false,sandbox:true}});
  setupWindow.webContents.setWindowOpenHandler(()=>({action:'deny'}));
  setupWindow.webContents.on('will-navigate',event=>event.preventDefault());
  setupWindow.on('closed',()=>{setupWindow=null;if(!state.ready&&!state.backend)finishExit(0);});
  await setupWindow.loadFile(path.join(__dirname,'setup.html'));
}
ipcMain.handle('books:setup',event=>{if(trustedSender(event)!=='setup')throw new Error('Setup is unavailable');return {defaultFolder:currentConfig.dataDir};});
ipcMain.handle('books:browse',async event=>{if(trustedSender(event)!=='setup')throw new Error('Setup is unavailable');const result=await dialog.showOpenDialog(setupWindow,{title:'Choose data folder',properties:['openDirectory','createDirectory']});return result.canceled?null:result.filePaths[0];});
ipcMain.handle('books:select',async(event,choice)=>{
  if(trustedSender(event)!=='setup'||state.backend)throw new Error('Catalog selection is unavailable');
  if(!choice||Object.keys(choice).sort().join(',')!=='folder,mode'||typeof choice.folder!=='string'||!path.isAbsolute(choice.folder)||!['existing','new'].includes(choice.mode))throw new Error('Choose an absolute data folder');
  const config={...currentConfig,dataDir:path.resolve(choice.folder),catalogMode:choice.mode,requiresSetup:false};
  const args=['--folder',config.dataDir,'--mode',choice.mode,'--install-root',path.dirname(process.execPath),'--install-root',process.resourcesPath];
  if(config.rootsJson)args.push('--roots-json',config.rootsJson);
  await runReadOnlyPython(config,'desktop_catalog.py',args); // an unusable folder is refused here, on the form (Judy 3.2)
  // Persist only after the chosen catalog has loaded. CREATE_NEW refuses unexpected
  // existing settings; no fallback or migration of selected data.
  const settingsFile=path.join(app.getPath('userData'),'desktop-settings.json');
  pendingSettings=()=>runReadOnlyPython(config,'desktop_settings.py',[settingsFile,config.dataDir]);
  // The setup window closes and the main window opens at Step 1; a failure after this is the strip's Stopped.
  startConfigured(config);
  if(setupWindow){setupWindow.close();setupWindow=null;}
  return {opened:true};
});
ipcMain.handle('books:quit',async event=>{const source=trustedSender(event);if(source==='setup'){if(state.backend)throw new Error('Catalog is still opening');finishExit(0);return;}return requestQuit({confirmed:false});});
ipcMain.handle('books:startup',event=>{trustedSender(event);return state.startup?state.startup.value:null;});
// Restart engine (Stuck) and Try again (Stopped): a new launch from Step 1; only while loading.
ipcMain.handle('books:restart-engine',async event=>{if(trustedSender(event)!=='app'||!currentConfig)throw new Error('Restart engine is unavailable');return restartEngine(currentConfig);});
ipcMain.handle('books:status',async event=>{trustedSender(event);let desktop=null;if(state.ready&&!state.backendExited){try{desktop=await desktopStatus.get();}catch{desktop={phase:'unavailable',idle:false};}}return {desktop,engineVersion:state.engineVersion,quit:state.quit,update:updateController?updateController.value:null,loaded:state.loaded,verdict:state.verdict};});

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
    if (state.quit === 'installing' || state.quit === 'updating') return; // the update flow decides when the app exits
    requestQuit({ confirmed: false });
  });
  app.whenReady().then(async () => {
    session.defaultSession.setPermissionRequestHandler((_wc, _permission, callback) => callback(false));
    let config;
    try {
      config = configuration();
      currentConfig=config;
      if(config.requiresSetup)await chooseCatalog();
      else startConfigured(config); // the engine's own failures show in the window's load strip (Stopped)
    } catch (error) {
      // Only a configuration the shell cannot run at all (no runtime, a bad option) ends here, before any window.
      // Close the private host pipe only on startup failure. Its retained native
      // job requests checkpoint shutdown; no numeric-PID kill or port assumption.
      if (state.backend && !state.backendExited) state.backend.stdin.end();
      reportError('Books Arranger could not start', error.message);
      finishExit(1);
    }
  });
}
