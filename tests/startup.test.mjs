// The shell's startup pieces (ruling 28; Judy 3.2, 3.7, 3.8): the startup record the page reads, health ownership,
// "last load took" memory and the tray's Restart to update. No Electron.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

test('admission telemetry remains pre-ready, refuses stale events, preserves final refusal',()=>{
 let now=1000;const startup=S.createStartup({now:()=>now});
 startup.beginAdmission();
 assert.equal(startup.value.admission.updatedAt,null);
 const event={state:'active',phase:'retained',done:2,total:8134,bytes:4096,elapsed_ms:16000,progress_age_ms:0,limit_ms:597000};
 now=17000;assert.equal(startup.admission(event),true);
 assert.equal(startup.value.phase,'launching');
 now=22000;startup.admission({...event,elapsed_ms:21000,progress_age_ms:5000});
 assert.equal(startup.value.admission.progressAt,17000);
 assert.equal(startup.admission(event),false);
 assert.equal(startup.admission({state:'complete',elapsed_ms:22000,limit_ms:597000}),true);
 assert.equal(startup.value.phase,'launching');
 assert.equal(startup.admission({...event,elapsed_ms:23000}),false);
 assert.equal(startup.admission({state:'failed',elapsed_ms:23000,limit_ms:597000,error:'pipe closed'}),true);
 startup.stopped({code:1});
 assert.equal(startup.admission({...event,elapsed_ms:24000}),false);
 startup.launch();assert.equal(startup.value.admission,undefined);
});
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const S = require('../desktop/startup.js');

test('the startup record: launching, running, stopped once, a new launch keeps the last load', () => {
 let clock = 1000;
 const startup = S.createStartup({ now: () => clock, lastLoadMs: 99000 });
 assert.deepEqual(startup.value, { phase: 'launching', startedAt: 1000, lastLoadMs: 99000, exited: null, portPid: null });
 assert.equal(startup.running().phase, 'running');
 assert.deepEqual(startup.stopped({ code: 1, lastLines: 'RuntimeError: boom', portPid: 4321 }).exited, { code: 1, lastLines: 'RuntimeError: boom' });
 assert.equal(startup.value.portPid, 4321);
 assert.equal(startup.stopped({ code: 0 }).exited.code, 1, 'the first cause stays');
 clock = 5000;
 assert.deepEqual(startup.launch(), { phase: 'launching', startedAt: 5000, lastLoadMs: 99000, exited: null, portPid: null });
 assert.equal(startup.loaded(42000).lastLoadMs, 42000);
 assert.equal(startup.loaded(-1).lastLoadMs, 42000);
});

test('health is ours only with our process and version; another copy means the port is taken', () => {
 const owner = { pid: 77 };
 assert.equal(S.classifyHealth({ application: 'Books Arranger', pid: 77, version: '0.22.1', instance: 'a'.repeat(32) }, owner, '0.22.1'), 'ours');
 assert.equal(S.classifyHealth({ application: 'Books Arranger', pid: 88, version: '0.22.1', instance: 'a'.repeat(32) }, owner, '0.22.1'), 'other');
 assert.equal(S.classifyHealth({ application: 'Books Arranger', pid: 77, version: '0.22.0', instance: 'a'.repeat(32) }, owner, '0.22.1'), 'other');
 assert.equal(S.classifyHealth({ application: 'Books Arranger', pid: 88 }, null, '0.22.1'), 'unknown', 'no ownership proof yet: ask again');
 assert.equal(S.classifyHealth({ application: 'Something else' }, owner, '0.22.1'), 'unknown');
});

test('last load took: saved only for a completed load, read back on the next start', () => {
 const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'books-startup-'));
 try {
  const file = S.loadTimeFile(dir);
  assert.equal(S.readLastLoad(file), null, 'absent on a first start');
  assert.equal(S.saveLastLoad(file, Number.NaN), false);
  assert.equal(S.saveLastLoad(file, 99400.4), true);
  assert.equal(S.readLastLoad(file), 99400);
  fs.writeFileSync(file, '{"lastLoadMs":"soon"}');
  assert.equal(S.readLastLoad(file), null);
 } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('the tray Restart to update waits for loading unless it is stuck or stopped', () => {
 assert.deepEqual(S.restartItem({ loaded: false, verdict: 'working' }), { label: 'Restart to update (after loading)', enabled: false });
 assert.deepEqual(S.restartItem({ loaded: false, verdict: 'waiting' }), { label: 'Restart to update (after loading)', enabled: false });
 assert.deepEqual(S.restartItem({ loaded: false, verdict: 'stuck' }), { label: 'Restart to update', enabled: true });
 assert.deepEqual(S.restartItem({ loaded: false, verdict: 'stopped' }), { label: 'Restart to update', enabled: true });
 assert.deepEqual(S.restartItem({ loaded: true, verdict: 'working' }), { label: 'Restart to update', enabled: true });
});
