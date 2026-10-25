// Startup load strip states (ruling 28; Judy's 0.22.1 UX spec, 3.3-3.8): Working, Waiting, Stuck and Stopped come from
// silence (3 s / 10 s without an answer, 10 s / 30 s without progress), never from total time; a sleep gap restarts the
// clocks. Pure module, fake clock.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const L = require('../web/load-state.js');

const loading = (extra = {}) => ({ step: 'session', n: 3, of: 4, done: 12400, total: 52311, unit: 'files', progress_age_ms: 0, waiting_for: null,
  restart_safe: true, parts: { library: true, status: true, books: false, attention: false, jobs: false }, took_ms: null, ...extra });

test('the thresholds live in one place', () => {
  assert.deepEqual({ ...L.THRESHOLDS }, { answerWaiting: 3000, answerStuck: 10000, progressWaiting: 10000, progressStuck: 30000, sleepGap: 5000 });
});

test('before the first answer the engine-silence row applies from the launch', () => {
  const t = L.createTracker(0);
  for (let at = 0; at <= 12000; at += 1000) t.tick(at);
  assert.equal(L.evaluate(t, 2999).state, 'working');
  assert.equal(L.evaluate(t, 3000).state, 'waiting');
  assert.equal(L.evaluate(t, 10000).state, 'stuck');
  assert.deepEqual(L.stateLine(L.evaluate(t, 3000), null), { word: 'Waiting', text: "Step 1 of 4: Starting the engine. The engine hasn't answered for 3 s." });
  assert.deepEqual(L.detailParts(t, 3000, null, null), ['running 0:03', 'no answer from the engine yet']);
});

test('time alone changes nothing: ten minutes of progress stay Working', () => {
  const t = L.createTracker(0);
  for (let at = 0; at <= 600000; at += 1000) {
    t.tick(at); t.observe({ loading: loading({ progress_age_ms: 400, done: at }) }, at);
    assert.equal(L.evaluate(t, at).state, 'working', `at ${at}`);
  }
  assert.deepEqual(L.stateLine(L.evaluate(t, 600000), loading()), { word: 'Working', text: 'Step 3 of 4: Checking the last session' });
});

test('no progress while answering: Waiting at 10 s, Stuck at 30 s, Working again when it moves', () => {
  const t = L.createTracker(0);
  for (let at = 0; at <= 40000; at += 1000) { t.tick(at); t.observe({ loading: loading({ progress_age_ms: at }) }, at); }
  assert.equal(L.evaluate(t, 9999).state, 'working');
  const waiting = L.evaluate(t, 14000);
  assert.equal(waiting.state, 'waiting');
  assert.equal(L.stateLine(waiting, loading()).text, 'Step 3 of 4: Checking the last session. Nothing new for 14 s. The engine is still answering.');
  const stuck = L.evaluate(t, 34000);
  assert.equal(stuck.state, 'stuck');
  assert.deepEqual(L.stateLine(stuck, loading()), { word: 'Stuck', text: 'Step 3 of 4: Checking the last session. No progress for 34 s. The engine is answering, but this step has not moved.' });
  t.tick(41000); t.observe({ loading: loading({ progress_age_ms: 0 }) }, 41000);
  assert.equal(L.evaluate(t, 41000).state, 'working');
});

test('no answer: Waiting at 3 s, Stuck at 10 s, with the engine-quiet line', () => {
  const t = L.createTracker(0);
  t.observe({ loading: loading() }, 1000);
  for (let at = 1000; at <= 12000; at += 1000) t.tick(at);
  assert.equal(L.evaluate(t, 3999).state, 'working');
  assert.equal(L.evaluate(t, 4000).state, 'waiting');
  assert.equal(L.stateLine(L.evaluate(t, 5000), loading()).text, "Step 3 of 4: Checking the last session. The engine hasn't answered for 4 s.");
  const stuck = L.evaluate(t, 11000);
  assert.equal(stuck.state, 'stuck');
  assert.equal(L.stateLine(stuck, loading()).text, "Step 3 of 4: Checking the last session. The engine hasn't answered for 10 s. It may have stopped responding.");
  t.heard(11500);  // a "still updating" 503 is an answer, though not progress (the last was at 1 s)
  assert.deepEqual(L.evaluate(t, 11500), { state: 'waiting', quiet: 10500, signal: 'progress' });
});

test('a sleep gap restarts both clocks instead of counting the gap', () => {
  const t = L.createTracker(0);
  t.tick(0); t.observe({ loading: loading() }, 0); t.tick(1000);
  t.tick(61000);  // the laptop slept for a minute
  assert.equal(L.evaluate(t, 61000).state, 'working');
  t.tick(62000);
  assert.equal(L.evaluate(t, 62000).state, 'working');
});

test('Stopped is the shell\'s fact and names no threshold; a taken port names the other process', () => {
  const t = L.createTracker(0);
  assert.deepEqual(L.stateLine(L.evaluate(t, 500, { stopped: true }), loading()), { word: 'Stopped', text: 'The engine stopped while loading. Your files are not touched.' });
  assert.deepEqual(L.stateLine(L.evaluate(t, 500, { stopped: true }), null, { portPid: 4321 }),
    { word: 'Stopped', text: 'Another copy of Books Arranger is running (process 4321). Quit it from the tray, then try again.' });
});

test('a named cause changes the wording, never the thresholds', () => {
  const t = L.createTracker(0);
  const drive = loading({ waiting_for: { kind: 'drive', root: 'Z:\\' } }), lock = loading({ waiting_for: { kind: 'file_lock' } });
  for (let at = 0; at <= 35000; at += 1000) { t.tick(at); t.observe({ loading: { ...drive, progress_age_ms: at } }, at); }
  assert.equal(L.evaluate(t, 9000).state, 'working');
  assert.equal(L.stateLine(L.evaluate(t, 12000), drive).text, 'Step 3 of 4: Checking the last session. Waiting for the source drive Z:\\ to answer (12 s).');
  assert.equal(L.stateLine(L.evaluate(t, 31000), drive).text,
    'Step 3 of 4: Checking the last session. Still waiting for the source drive Z:\\ to answer (31 s). Check that the drive is connected. Loading continues by itself when it answers.');
  assert.equal(L.stateLine(L.evaluate(t, 31000), lock).text,
    'Step 3 of 4: Checking the last session. Still waiting for another program to release the catalog (31 s). Close other programs that use the catalog. Loading continues by itself when it lets go.');
});

test('formats: durations, running clock, counts, units, the Ready line', () => {
  assert.equal(L.duration(59999), '59 s'); assert.equal(L.duration(99000), '1 min 39 s'); assert.equal(L.duration(3720000), '1 h 2 min');
  assert.equal(L.running(72000), '1:12'); assert.equal(L.running(3725000), '1:02:05');
  const t = L.createTracker(0); t.observe({ loading: loading() }, 71000);
  assert.deepEqual(L.detailParts(t, 72000, loading(), 99000), [`${(12400).toLocaleString()} of ${(52311).toLocaleString()} files`, 'running 1:12', 'engine answered 1 s ago', 'last load took 1 min 39 s']);
  assert.deepEqual(L.detailParts(t, 72000, loading({ total: null, done: 7, unit: 'pages' }), null), ['7 items so far', 'running 1:12', 'engine answered 1 s ago']);
  assert.deepEqual(L.detailParts(t, 72000, loading({ total: null, done: null }), null), ['running 1:12', 'engine answered 1 s ago']);
  assert.equal(L.readyLine(99000), 'Ready · Loaded in 1 min 39 s'); assert.equal(L.readyLine(42000), 'Ready · Loaded in 42 s');
  assert.equal(L.valueText(loading({ done: 24, total: 100 })), 'Step 3 of 4, Checking the last session, 24%');
  assert.equal(L.valueText(loading({ step: 'catalog', n: 2, done: null, total: null })), 'Step 2 of 4, Opening the catalog');
  assert.equal(L.stepOf(loading({ step: 'later', n: 3 })).words, 'Loading…');
});

test('the tray tooltip per state; loaded means every part and took_ms, or no loading object', () => {
  const t = L.createTracker(0);
  assert.equal(L.trayTooltip(L.evaluate(t, 1000), loading(), false), 'Books Arranger — loading, step 3 of 4');
  assert.equal(L.trayTooltip(L.evaluate(t, 4000), loading(), false), 'Books Arranger — waiting, step 3 of 4');
  assert.equal(L.trayTooltip(L.evaluate(t, 11000), loading(), false), 'Books Arranger — stuck at step 3 of 4');
  assert.equal(L.trayTooltip(L.evaluate(t, 0, { stopped: true }), loading(), false), 'Books Arranger — stopped');
  assert.equal(L.trayTooltip(L.evaluate(t, 0), loading(), true), 'Books Arranger');
  assert.equal(L.loaded({}), true);
  assert.equal(L.loaded({ loading: loading() }), false);
  const all = { library: true, status: true, books: true, attention: true, jobs: true };
  assert.equal(L.loaded({ loading: loading({ parts: all }) }), false, 'every part, and took_ms');
  assert.equal(L.loaded({ loading: loading({ parts: all, took_ms: 42000 }) }), true);
  assert.equal(L.part({ loading: loading() }, 'status'), true); assert.equal(L.part({ loading: loading() }, 'jobs'), false); assert.equal(L.part({}, 'jobs'), true);
});
