'use strict';
// Startup, the shell's half (ruling 28; Judy's 0.22.1 UX spec, section 3). The window opens at once and the engine
// fills it in; the shell tells the page what only it knows (launch time, the process has exited, the port is taken,
// the last load's duration) and keeps the tray in step. Pure pieces, so node tests cover them without Electron.
const fs = require('node:fs');
const path = require('node:path');

// What the page reads through the preload: {phase, startedAt, lastLoadMs, exited, portPid}.
function createStartup({ now = Date.now, lastLoadMs = null } = {}) {
 let value = { phase: 'launching', startedAt: now(), lastLoadMs, exited: null, portPid: null };
 return {
  get value() { return { ...value, exited: value.exited ? { ...value.exited } : null }; },
  // Restart engine and Try again start a new launch; "last load took" stays.
  launch() { value = { phase: 'launching', startedAt: now(), lastLoadMs: value.lastLoadMs, exited: null, portPid: null }; return this.value; },
  running() { if (value.phase === 'launching') value = { ...value, phase: 'running' }; return this.value; },
  beginAdmission() { value={...value,admission:{state:'pending',phase:'pending',done:0,total:null,startedAt:now(),updatedAt:null,limit_ms:597000}};return this.value; },
  admission(event) {
   if(value.phase!=='launching'||!event||!['active','complete','failed'].includes(event.state)||event.limit_ms!==597000||!Number.isSafeInteger(event.elapsed_ms)||event.elapsed_ms<0)return false;
   if(value.admission&&!['active','pending'].includes(value.admission.state)&&!(value.admission.state==='complete'&&event.state==='failed'))return false;
   if(value.admission?.elapsed_ms>event.elapsed_ms)return false;
   if(event.state==='active'&&(!['records','database','source','namespace','retained'].includes(event.phase)||!Number.isSafeInteger(event.done)||event.done<0||!(event.total===null||Number.isSafeInteger(event.total)&&event.total>=event.done)||!Number.isSafeInteger(event.bytes)||event.bytes<0||!Number.isSafeInteger(event.progress_age_ms)||event.progress_age_ms<0||event.progress_age_ms>event.elapsed_ms))return false;
   const at=now();
   value={...value,admission:{...value.admission,...event,error:String(event.error||'').slice(0,4096),updatedAt:at,progressAt:at-(event.progress_age_ms||0),startedAt:at-event.elapsed_ms}};
   return true;
  },
  // The shell's fact: the engine process exited, or another copy holds the port. The first cause stays.
  stopped({ code = null, lastLines = '', portPid = null } = {}) {
   if (value.phase === 'stopped') return this.value;
   value = { ...value, phase: 'stopped', exited: { code, lastLines: String(lastLines || '') }, portPid: Number.isInteger(portPid) && portPid > 0 ? portPid : null };
   return this.value;
  },
  loaded(tookMs) { if (Number.isFinite(tookMs) && tookMs >= 0) value = { ...value, lastLoadMs: tookMs }; return this.value; },
 };
}

// A health answer is ours only with our engine's process and version; another Books Arranger means the port is taken.
function classifyHealth(health, owner, version) {
 if (!health || health.application !== 'Books Arranger') return 'unknown';
 if (owner && health.pid === owner.pid && health.version === version && typeof health.instance === 'string') return 'ours';
 return owner ? 'other' : 'unknown';
}

// "Last load took": only a completed load counts (3.7); one small file in the shell profile.
function loadTimeFile(userData) { return path.join(userData, 'last-load.json'); }
function readLastLoad(file, io = fs) {
 try {
  const info = io.lstatSync(file);
  if (!info.isFile() || info.isSymbolicLink() || info.size > 1024) return null;
  const value = JSON.parse(io.readFileSync(file, 'utf8'));
  return Number.isFinite(value.lastLoadMs) && value.lastLoadMs >= 0 ? value.lastLoadMs : null;
 } catch { return null; }
}
function saveLastLoad(file, ms, io = fs) {
 if (!Number.isFinite(ms) || ms < 0) return false;
 const temp = file + '.tmp';
 try { io.writeFileSync(temp, JSON.stringify({ lastLoadMs: Math.round(ms) })); io.renameSync(temp, file); return true; }
 catch { return false; }
}

// The tray's Restart to update (3.8): live once loading is finished, or in Stuck or Stopped.
function restartItem({ loaded, verdict }) {
 if (loaded || verdict === 'stuck' || verdict === 'stopped') return { label: 'Restart to update', enabled: true };
 return { label: 'Restart to update (after loading)', enabled: false };
}

module.exports = { createStartup, classifyHealth, loadTimeFile, readLastLoad, saveLastLoad, restartItem };
