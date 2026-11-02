// Mandatory native phase PA-1. Refuses before app/registry activity without the
// exact candidate-bound authority and separately reviewed owned invocation.
import test from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import https from 'node:https';
import net from 'node:net';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {hash,NATIVE_CASE,PA1_TITLE,PA1_ASSERTIONS} from '../scripts/qa-phase-contract.mjs';
import {need,readPin,validatePlan,verifyInputs,treeFiles,nativeAdapters,privateEnginePort,createPrivateShellCommands,verifyCloseSession} from './real-shell-update-support.mjs';
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function freePort(requested=0){return new Promise((resolve,reject)=>{const server=net.createServer(),timer=setTimeout(()=>{server.close(()=>{});reject(new Error('Private loopback port check timed out after 5 s'));},5000);server.once('error',error=>{clearTimeout(timer);reject(error);});server.listen(requested,'127.0.0.1',()=>{const port=server.address().port;server.close(error=>{clearTimeout(timer);error?reject(error):resolve(port);});});});}
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
async function devtools(port,monitor,ownerPid) {
 let socket = null, id = 0; const waiting = new Map();
 async function connect() {
  const end = Date.now() + 30000;
  while (Date.now() < end) {
   try {
    monitor.endpoint(port,ownerPid);
    const targets = await (await fetch('http://127.0.0.1:' + port + '/json/list',{signal:AbortSignal.timeout(5000)})).json();
    monitor.endpoint(port,ownerPid);
    const page = targets.find((target) => target.type === 'page');
    if (page) {
     const target=new URL(page.webSocketDebuggerUrl);assert.equal(target.hostname,'127.0.0.1');assert.equal(Number(target.port),port);
     socket = new WebSocket(page.webSocketDebuggerUrl);
     await new Promise((resolve, reject) => {
      const timer=setTimeout(()=>{socket?.close();reject(new Error('DevTools connection timed out'));},Math.max(1,end-Date.now()));
      socket.onopen=()=>{clearTimeout(timer);resolve();};socket.onerror=error=>{clearTimeout(timer);reject(error);};
     });
     monitor.endpoint(port,ownerPid);
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
  monitor.checkWindows();monitor.endpoint(port,ownerPid);
  if (!socket) await connect();
  const message = await new Promise((resolve,reject) => {
   const n=++id,timer=setTimeout(()=>{waiting.delete(n);reject(new Error('DevTools reply timed out after 30 s'));},30000);
   waiting.set(n,value=>{clearTimeout(timer);resolve(value);});
   try{socket.send(JSON.stringify({id:n,method:'Runtime.evaluate',params:{expression,awaitPromise,returnByValue:true}}));}
   catch(error){clearTimeout(timer);waiting.delete(n);reject(error);}
  });
  if (message.error || message.result?.exceptionDetails) throw new Error((message.error && message.error.message) || JSON.stringify(message.result.exceptionDetails).slice(0, 400));
  return message.result.result.value;
 }
 return { evaluate, close: () => { try { socket?.close(); } catch { /* gone */ } } };
}
// The fake release is one patch above package.json's version, read at runtime. A fixed number stops being newer the
// day the version is bumped to it: at 568712e (0.22.2) the real updater rightly answered "current" to a fake 0.22.2.
function nextPatch(version) {
 const match = /^(\d+)\.(\d+)\.(\d+)$/.exec(String(version));
 if (!match) throw new Error('PA-1 needs a plain x.y.z version in package.json, not ' + JSON.stringify(version));
 return match[1] + '.' + match[2] + '.' + (Number(match[3]) + 1);
}

test(PA1_TITLE,{timeout:300000},async()=>{
 need(process.env.BOOKS_PA1_PLAN&&process.env.BOOKS_PA1_PLAN_SHA&&/^[a-f0-9]{64}$/.test(process.env.BOOKS_PA1_NONCE||''),'PA-1 default refused: exact owned phase authority absent');
 const raw=fs.readFileSync(process.env.BOOKS_PA1_PLAN);need(hash(raw)===process.env.BOOKS_PA1_PLAN_SHA,'Worker plan pin differs');const plan=JSON.parse(raw);
 const authority=JSON.parse(await readPin(plan.authority));validatePlan(plan,authority);
 const trace=path.join(plan.evidence_root,'native-progress.private.jsonl');fs.writeFileSync(trace,'',{flag:'wx'});
 let lastStage='input-verification';
 const progress=(stage,detail={})=>{lastStage=stage;fs.appendFileSync(trace,JSON.stringify({stage,at:new Date().toISOString(),...detail})+'\n');};
 progress('input-verification');const manifest=await verifyInputs(plan);progress('inputs-verified');
 need(process.env.BOOKS_PA1_DEADLINE&&Number(process.env.BOOKS_PA1_DEADLINE)>Date.now(),'Original remaining deadline missing');
 const work=plan.fixture_root,app=path.join(work,'app'),home=path.join(work,'home'),pkg={version:plan.binding.version};
 assert.deepEqual(await treeFiles(app),manifest.payload.files,'Actual built candidate payload');
 const {monitor}=nativeAdapters(plan,authority);monitor.checkWindows();progress('explicit-membership-witness-ready');let intrusion=null;
 const timer=setInterval(()=>{try{monitor.checkWindows();}catch(e){intrusion=e;}},100);
 const dirs=Object.fromEntries(['profile','data','local','roaming','temp','Audiobooks','Podcasts','Books'].map(name=>[name,path.join(home,name)]));
 for(const dir of Object.values(dirs))fs.mkdirSync(dir,{recursive:true});const roots=path.join(home,'roots.json'),rootsBytes=JSON.stringify({Audiobooks:dirs.Audiobooks,Podcasts:dirs.Podcasts,Ebooks:dirs.Books});
 if(plan.recovery)assert.equal(fs.readFileSync(roots,'utf8'),rootsBytes,'Same private recovery roots');else fs.writeFileSync(roots,rootsBytes,{flag:'wx'});
 let shell=null,cdp=null,github=null,output='',originalError=null,quitRequested=false,privateQuitOnFailure=null,privateStillRunning=()=>false;const requests=[];
 try{
  // The fake GitHub: a release one patch above this version whose "installer" Windows will not start.
  const next = nextPatch(pkg.version), tag = 'v' + next;
  const installer = Buffer.from('This is no program: Windows refuses to start it (Books Arranger PA-1).\r\n'.repeat(64));
  const sha512 = crypto.createHash('sha512').update(installer).digest('base64');
  const name = 'Books-Arranger-Setup-' + next + '.exe', base = '/Gemanoneko/booksArranger/releases';
  github = https.createServer(selfSigned(['github.com', 'api.github.com', 'objects.githubusercontent.com']), (req, res) => {
   requests.push(req.url);
   const send = (status, type, body) => { res.writeHead(status, { 'Content-Type': type, 'Content-Length': Buffer.byteLength(body) }); res.end(body); };
   if (req.url === base + '.atom') return send(200, 'application/atom+xml', '<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><id>tag:github.com,2008:Repository/1/' + tag + '</id><updated>2026-10-26T00:00:00Z</updated><link rel="alternate" type="text/html" href="https://github.com' + base + '/tag/' + tag + '"/><title>' + tag + '</title><content type="html">PA-1</content></entry></feed>');
   if (req.url === base + '/latest') return send(200, 'application/json', JSON.stringify({ tag_name: tag }));
   if (req.url === base + '/download/' + tag + '/latest.yml') return send(200, 'text/yaml', 'version: ' + next + '\nfiles:\n  - url: ' + name + '\n    sha512: ' + sha512 + '\n    size: ' + installer.length + '\npath: ' + name + '\nsha512: ' + sha512 + "\nreleaseDate: '2026-10-26T00:00:00.000Z'\n");
   if (req.url === base + '/download/' + tag + '/' + name) { res.writeHead(200, { 'Content-Type': 'application/octet-stream', 'Content-Length': installer.length }); return res.end(installer); }
   send(404, 'text/plain', 'Not Found');
  });
  await new Promise((resolve,reject) => {github.once('error',reject);github.listen(0, '127.0.0.1', resolve);});
  const githubPort=github.address().port;
  progress('fake-update-server-ready');
  const enginePort = await privateEnginePort(plan,freePort), debugPort = await freePort();progress('private-engine-port-ready',{port:enginePort});
  const env = { ...process.env, LOCALAPPDATA: dirs.local, APPDATA: dirs.roaming, TEMP: dirs.temp, TMP: dirs.temp, USERPROFILE: home };
  for (const name of Object.keys(env)) if (/^(ELECTRON_|NODE_OPTIONS$)/i.test(name)) delete env[name];  // ELECTRON_RUN_AS_NODE, even empty, turns the shell into Node
  const exe = path.join(app, 'Books Arranger.exe');
  const args = ['--start-hidden', '--quiet-errors', '--data-dir=' + dirs.data, '--catalog-mode='+(plan.recovery?'existing':'new'), '--port=' + enginePort, '--roots-json=' + roots, '--shell-profile=' + dirs.profile,
   '--remote-debugging-port=' + debugPort, '--ignore-certificate-errors',
   '--host-resolver-rules=MAP github.com 127.0.0.1:' + githubPort + ',MAP api.github.com 127.0.0.1:' + githubPort + ',MAP objects.githubusercontent.com 127.0.0.1:' + githubPort+',MAP * ~NOTFOUND,EXCLUDE 127.0.0.1,EXCLUDE localhost'];
  progress('app-starting');
  shell = spawn(exe, args, { env, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  progress('app-started',{pid:shell.pid});
  shell.stdout.on('data', (chunk) => { output += chunk; }); shell.stderr.on('data', (chunk) => { output += chunk; });
  let exitedAt = null; shell.on('exit', () => { exitedAt = Date.now(); });
  privateStillRunning=()=>exitedAt===null&&shell.exitCode===null;
  privateQuitOnFailure=()=>createPrivateShellCommands({spawn,exe,profile:dirs.profile,env,timeoutMs:10000}).quit();
  cdp = await devtools(debugPort,monitor,shell.pid);
  const status = () => cdp.evaluate('window.booksDesktop.status()');
  const until = async (check, ms, what) => { const end = Date.now() + ms; while (Date.now() < end) { monitor.checkWindows();if(intrusion)throw intrusion; if (exitedAt) throw new Error('the shell exited while waiting for ' + what + '\n' + output.slice(-3000)); try { const value = await check(); if (value) return value; } catch { /* the page is changing */ } await sleep(500); } throw new Error('timed out waiting for ' + what + '\n' + output.slice(-3000)); };
  await until(async () => (await status()).loaded, 120000, 'the engine to load');
  progress('engine-loaded');progress('checking-update');
  const checked = await cdp.evaluate('window.booksDesktop.checkUpdates()');
  progress('update-checked',{checked,requests:[...requests]});
  assert.deepEqual([checked.check.phase, checked.available], ['available', next], 'positive control: the real updater read the fake GitHub');
  progress('downloading-update');const downloaded = await cdp.evaluate('window.booksDesktop.downloadUpdate()');
  progress('update-downloaded',{downloaded});
  assert.equal(downloaded.ready, true, 'positive control: downloaded and verified (sha512)');
  const pressed = Date.now();
  progress('installing-invalid-update');await cdp.evaluate('window.booksDesktop.installUpdate(); true', false);  // the page reloads during the install: no await
  const failed = await until(async () => { const value = await status(); return value.update && value.update.install.phase === 'failed' && !value.update.busy.install && value.loaded ? value : null; }, 150000, 'the Install line and the old engine loaded again');
  progress('old-engine-recovered');
  await sleep(5000);  // M-1's queued quit came 1.7 s after the press
  assert.equal(exitedAt, null, 'the shell is still running ' + Math.round((Date.now() - pressed) / 1000) + ' s after Update now');
  assert.equal(failed.update.install.cause, 'installer_blocked');
  assert.match(output, /Installer did not start/, 'positive control: Windows refused to start the installer');
  assert.ok(requests.includes(base + '/download/' + tag + '/' + name), 'the installer came from the fake GitHub');
  const owner=monitor.endpoint(enginePort);
  const health = await (await fetch('http://127.0.0.1:' + enginePort + '/api/health',{signal:AbortSignal.timeout(5000)})).json();
  monitor.endpoint(enginePort,owner.pid);assert.equal(health.pid,owner.pid,'health belongs to private owned engine');
  assert.equal(health.version, pkg.version, 'the old engine answers again');
  // The documented command reaches the same close callback as the window button.
  // The primary stays hidden; this does not claim a physical click or visible-to-hidden transition.
  const fixture=createPrivateShellCommands({spawn,exe,profile:dirs.profile,env});
  monitor.endpoint(debugPort,shell.pid);assert.equal(exitedAt,null);assert.equal(shell.exitCode,null);
  progress('closing-window');await fixture.closeWindow();progress('window-close-command-finished');
  const closeStatus=await status();
  monitor.endpoint(enginePort,owner.pid);
  const closeHealth=await (await fetch('http://127.0.0.1:'+enginePort+'/api/health',{signal:AbortSignal.timeout(5000)})).json();
  monitor.endpoint(enginePort,owner.pid);
  const closeProof=verifyCloseSession({running:exitedAt===null&&shell.exitCode===null,loaded:closeStatus.loaded,quit:closeStatus.quit,health:closeHealth,expectedPid:owner.pid,version:pkg.version,windows:monitor.checkWindows(shell.pid)});
  // Quit through the third invocation, still targeting the same private primary/profile.
  progress('quitting');quitRequested=true;await fixture.quit();progress('quit-command-finished');
  const end = Date.now() + 60000;
  while (!exitedAt && Date.now() < end) await sleep(250);
  assert.ok(exitedAt, 'Quit ends the shell');
  assert.equal(shell.exitCode,0);monitor.checkWindows();assert.equal(intrusion,null);
  assert.deepEqual(await treeFiles(app),manifest.payload.files,'Copied candidate payload remains byte exact');
  const functional={schema:'books-pa1-functional-v1',binding:plan.binding,case:NATIVE_CASE,assertions:[...PA1_ASSERTIONS],fixture_root:work,exe,downloadVerified:true,invalidInstallerRefused:true,oldEngineRecovered:true,shellStayedRunning:true,healthVersionMatched:closeProof.healthVersionMatched,closedByQuit:true,payloadUnchanged:true,endpointsOwned:closeProof.endpointsOwned,noVisibleOwnWindow:closeProof.noVisibleOwnWindow,intrusion:null,window_observations:monitor.view().checks,listener_observations:monitor.view()};
  console.log('BOOKS_PA1_FUNCTIONAL '+JSON.stringify(functional));
  progress('functional-passed');
 }catch(error){
  originalError=error;let diagnostic=null;
  try{if(cdp)diagnostic=await cdp.evaluate('(async()=>({startup:await window.booksDesktop.startup(),status:await window.booksDesktop.status()}))()');}catch(e){diagnostic={error:String(e.message||e)};}
  progress('failed',{failed_stage:lastStage,error:String(error.stack||error),output:output.slice(-65536),requests:[...requests],diagnostic});throw error;
 }finally{
  clearInterval(timer);cdp?.close();
  try{await new Promise((resolve,reject)=>{
   if(!github){resolve();return;}
   const closeTimer=setTimeout(()=>reject(new Error('Fake update server close timed out after 5 s')),5000);
   github.closeAllConnections();github.close(error=>{clearTimeout(closeTimer);error?reject(error):resolve();});
  });}catch(error){progress('server-close-failed',{error:String(error.stack||error)});if(!originalError)throw error;}
  finally{
   if(originalError&&!quitRequested&&privateQuitOnFailure&&privateStillRunning()){
    quitRequested=true;try{progress('failure-quitting-private-app');await privateQuitOnFailure();progress('failure-quit-command-finished');}catch(error){progress('failure-quit-command-failed',{error:String(error.stack||error)});}
   }
   monitor.dispose();
  }
  // No PID kill, directory removal or registry mutation here. On failure the
  // unchanged owner supplies bounded closure; abnormal closure cannot clean keys.
 }
});
