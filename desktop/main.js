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
  updateIdle: false,
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
  const file=path.join(app.getPath('userData'),'desktop-settings.json');
  if(!fs.existsSync(file))return {};
  const info=fs.lstatSync(file);
  if(!info.isFile()||info.isSymbolicLink()||info.size>8192)throw new Error('Desktop settings are not an ordinary bounded file; retained unchanged.');
  const value=JSON.parse(fs.readFileSync(file,'utf8'));
  if(!value||typeof value.dataDir!=='string'||!path.isAbsolute(value.dataDir))throw new Error('Desktop settings need an explicit absolute data folder; retained unchanged.');
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
  return { dataDir, requiresSetup, catalogMode: settings.catalogMode || (option(argv,'catalog-mode') || 'existing'), port, rootsJson, python, backendDir, ffmpegDir };
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
  child.on('exit', (code) => {
    state.backendExited = true;
    if (!state.ready) return; // startup reports it: waitForBackend sees the exit
    if (state.quit === 'updating') return;
    if (state.quit !== 'none') return finishExit(code === 0 ? 0 : 1);
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
      if (state.owner && health.application === 'Books Arranger' && health.pid === state.owner.pid &&
          health.version === app.getVersion() && typeof health.instance === 'string') {
        state.engineVersion = health.version;
        return health;
      }
      if (health.application) throw new Error(`Port ${new URL(state.baseUrl).port} belongs to another Books Arranger (PID ${health.pid}).`);
    } catch (error) {
      if (/belongs to another/.test(error.message)) throw error;
    }
    await sleep(250);
  }
  throw new Error('The engine did not become ready within 3 minutes.');
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
      : { label: 'Quit Books Arranger', click: () => requestQuit({ confirmed: false }) },
    { type:'separator' },
    { label:'Check for updates',enabled:!!updateController&&!quitting,click:()=>updateController.check().catch(error=>reportError('Update check failed',error.message)) },
    ...(updateController&&updateController.ready&&!quitting&&state.updateIdle?[{label:'Restart to update',click:()=>updateController.restart().catch(error=>reportError('Update could not install',error.message))}]:[]),
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
  if(state.backendExited)return finishExit(state.backend?.exitCode===0?0:1);
  if (state.quit !== 'none') return;
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

// HTTP failure never proves a safe checkpoint. The native host remains alive.
async function watchQuit() {
  while (!state.backendExited && state.quit === 'requested') {
    await sleep(1000);
    try {
      const status = await desktopStatus.get({ timeout: 3000, maxAge: 0 });
      refreshTray('Books Arranger — ' + status.phase);
      if (status.phase === 'blocked') {
        state.quit = 'none';
        refreshTray('Books Arranger — Quit blocked');
        reportError('Books Arranger is still running', status.error || 'A worker has not reached its safe checkpoint. Try Quit again.');
        return;
      }
    } catch { refreshTray('Books Arranger — waiting for engine checkpoint'); }
  }
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

// IPC accepts only this app's current page or the local first-run selector.
let currentConfig=null;
let setupWindow=null;
let updateController=null;
function trustedSender(event){
  const wc=event.sender;
  if(setupWindow&&!setupWindow.isDestroyed()&&wc===setupWindow.webContents&&wc.getURL()===require('node:url').pathToFileURL(path.join(__dirname,'setup.html')).href)return 'setup';
  if(state.win&&!state.win.isDestroyed()&&wc===state.win.webContents&&new URL(wc.getURL()).origin===state.baseUrl)return 'app';
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
  const value={engineVersion:state.engineVersion,quit:state.quit,update:updateController?{...updateController.value,ready:!!updateController.ready}:null};
  if(state.win&&!state.win.isDestroyed())state.win.webContents.send('books:status',value);
  refreshTray('Books Arranger'+(state.quit==='none'?'':' — '+state.quit));
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
  updateController=new UpdateController({provider:autoUpdater,packaged:app.isPackaged,notify:broadcastStatus,
    acquireArtifact:artifact=>acquireUpdateArtifact(config,artifact),
    parkEngine:()=>require('./engine-update').parkOwnedEngine({state,request:engineRequest,sleep,broadcast:broadcastStatus}),
    install:async()=>{state.quit='exiting';autoUpdater.quitAndInstall(false,true);await sleep(250);if(!autoUpdater.quitAndInstallCalled){state.quit='none';throw new Error('Installer did not start; reopen Books Arranger and try again');}}
  });
  setInterval(async()=>{
    if(state.backendExited||state.quit!=='none'){state.updateIdle=false;return;}
    try{const status=await desktopStatus.get();state.updateIdle=status.idle===true;}catch{state.updateIdle=false;}
    refreshTray('Books Arranger');
  },1000);
  broadcastStatus();
}
ipcMain.handle('books:update-check',async event=>{if(trustedSender(event)!=='app'||!updateController)throw new Error('Update controls unavailable');return updateController.check();});
ipcMain.handle('books:update-download',async event=>{if(trustedSender(event)!=='app'||!updateController)throw new Error('Update controls unavailable');return updateController.download();});
ipcMain.handle('books:update-install',async event=>{if(trustedSender(event)!=='app'||!updateController)throw new Error('Update controls unavailable');return updateController.restart();});
async function startConfigured(config){
  currentConfig=config;
  const child=startBackend(config);
  if(!state.tray)createTray();
  await waitForBackend(child);
  state.ready=true;
  if(state.backendExited)throw new Error(lastLines(state.output)||'Engine exited during startup');
  createWindow();
  configureUpdater(config);
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
  await runReadOnlyPython(config,'desktop_catalog.py',args);
  try{await startConfigured(config);}catch(error){if(state.backend&&!state.backendExited)state.backend.stdin.end();throw error;}
  // Persist only after owner/version verified healthy startup. CREATE_NEW refuses
  // unexpected existing settings; no fallback or migration of selected data.
  const settingsFile=path.join(app.getPath('userData'),'desktop-settings.json');
  await runReadOnlyPython(config,'desktop_settings.py',[settingsFile,config.dataDir]);
  if(setupWindow){setupWindow.close();setupWindow=null;}
  return {opened:true};
});
ipcMain.handle('books:quit',async event=>{const source=trustedSender(event);if(source==='setup'){if(state.backend)throw new Error('Catalog is still opening');finishExit(0);return;}return requestQuit({confirmed:false});});
ipcMain.handle('books:status',async event=>{trustedSender(event);let desktop=null;if(state.ready&&!state.backendExited){try{desktop=await desktopStatus.get();}catch{desktop={phase:'unavailable',idle:false};}}return {desktop,engineVersion:state.engineVersion,quit:state.quit,update:updateController?{...updateController.value,ready:!!updateController.ready}:null};});

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
      currentConfig=config;
      if(config.requiresSetup)await chooseCatalog();
      else await startConfigured(config);
    } catch (error) {
      // Close the private host pipe only on startup failure. Its retained native
      // job requests checkpoint shutdown; no numeric-PID kill or port assumption.
      if (state.backend && !state.backendExited) state.backend.stdin.end();
      reportError('Books Arranger could not start', error.message);
      finishExit(1);
    }
  });
}
