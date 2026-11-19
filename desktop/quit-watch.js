'use strict';
// After an accepted Quit the shell waits for its native host to exit. If the engine has already closed its
// server (connections refused) the shell must not wait forever: once refusals have lasted goneAfterMs the
// engine is gone and the shell exits (v0.16.8: a closed engine left the shell running with no window,
// ignoring a second --quit). A reply of any kind, or a timeout, resets the count: the engine is still there.
function createQuitWatch({ now = () => Date.now(), goneAfterMs = 5000 } = {}) {
 let refusedSince = null;
 function observe(outcome) {
  if (outcome !== 'refused') { refusedSince = null; return false; }
  if (refusedSince === null) refusedSince = now();
  return now() - refusedSince >= goneAfterMs;
 }
 return { observe, reset() { refusedSince = null; } };
}
function outcomeOf(error) {
 if (!error) return 'reply';
 return error.code === 'ECONNREFUSED' ? 'refused' : 'other';
}
// 0.22.3 (Sergei 2026-10-27, seen on 0.22.1 under load: "Quit could not be confirmed; ownership remains held. Request
// timed out"): one unanswered request is no refusal. The Quit is sent again (the engine takes a repeated Quit as the same
// one) until it is accepted, the engine is gone, or boundMs pass with no answer ('silent': the shell then stops the
// engine safely through its pipe). An HTTP answer that refuses is 'refused', with the engine's own reason.
async function sendQuit({ post, sleep, now = () => Date.now(), boundMs = 45000, retryMs = 1000, gone = () => false } = {}) {
 const watch = createQuitWatch({ now });
 const deadline = now() + boundMs;
 let last = null;
 while (!gone()) {
  try { await post(); return { outcome: 'accepted' }; }
  catch (error) {
   if (error && error.status) return { outcome: 'refused', error };
   last = error;
   if (watch.observe(outcomeOf(error))) return { outcome: 'gone' };
  }
  if (now() >= deadline) return { outcome: 'silent', error: last };
  await sleep(retryMs);
 }
 return { outcome: 'gone' };
}
// Futaba's 0.22.3 QA, m-2: Quit ends the shell only once its own engine host has exited. Its pipe closes (the engine's
// safe stop); after boundMs the host is ended through its own handle (its kill-on-close job takes the engine with it),
// never by name or PID. 'exited' | 'ended' (it had to be ended) | 'still-running' (even that did not end it in killWaitMs).
// Senua's 0.30.0 review, M4: holdKill (async, true while the engine still names an open file change) keeps the host alive
// past boundMs, polled every second, never past holdMs more (FILE_CHANGE_BOUND_MS): the engine is then ending that change
// itself (its close waits for it with the same bound). A holdKill that fails reads as false.
async function endOwnEngine({ exited, closePipe, kill, sleep, onKill = () => {}, now = () => Date.now(), boundMs = 30000, killWaitMs = 5000,
                              holdKill = async () => false, holdMs = FILE_CHANGE_BOUND_MS } = {}) {
 if (exited()) return 'exited';
 try { closePipe(); } catch { /* host gone */ }
 let deadline = now() + boundMs;
 while (!exited() && now() < deadline) await sleep(200);
 if (exited()) return 'exited';
 const held = now() + holdMs;
 while (!exited() && now() < held) {
  let open = false;
  try { open = await holdKill(); } catch { open = false; }
  if (!open) break;
  await sleep(1000);
 }
 if (exited()) return 'exited';
 onKill();
 try { kill(); } catch { /* already gone */ }
 deadline = now() + killWaitMs;
 while (!exited() && now() < deadline) await sleep(200);
 return exited() ? 'ended' : 'still-running';
}
// 0.30.0 item F (Sergei 2026-11-18: closed at 21:20, the engine still answered "closing" an hour later): what an accepted
// Quit still waits for, as the engine's desktop status gives it (waiting_for: [{kind, title}]). The engine waits only for
// real work now (the book converting, a cleanup at its file checkpoint, a press, a scan or a file change ending), never for
// a read. Any other shape reads as nothing.
function quitWaiting(status) {
 const list = status && Array.isArray(status.waiting_for) ? status.waiting_for : [];
 return list.filter((item) => item && typeof item.kind === 'string')
  .map((item) => ({ kind: item.kind, title: typeof item.title === 'string' ? item.title : '' }));
}
// The facts a Quit-anyway offer is made from, per status poll: the phase, what still runs, since when it has been waiting
// (waitedMs, from the first poll that named work), whether the list changed, and whether the close failed ('blocked').
function createQuitProgress({ now = () => Date.now() } = {}) {
 let since = null;
 let last = '[]';
 return {
  observe(status) {
   const waiting = quitWaiting(status);
   if (!waiting.length) since = null;
   else if (since === null) since = now();
   const key = JSON.stringify(waiting);
   const changed = key !== last;
   last = key;
   return { phase: status && typeof status.phase === 'string' ? status.phase : '', waiting, waitedMs: since === null ? 0 : now() - since,
            changed, blocked: !!status && status.phase === 'blocked', error: status && typeof status.error === 'string' ? status.error : '' };
  },
 };
}
// 0.30.0 item F follow-up: an accepted Quit always ends. Per status poll (createQuitProgress facts) this says when the shell
// stops the engine safely instead of waiting on: 'blocked' at once (the close failed: before, an error box and a half-closed
// app); 'bound' when work is still named QUIT_WAIT_BOUND_MS after it was first named. The book Sergei chose to finish
// ("Quit after this book": keepConversion) is waited for as before; the bound starts when it is no longer named. A poll
// that names nothing resets the clock. null: go on waiting.
const QUIT_WAIT_BOUND_MS = 15000;
// Senua's 0.30.0 review, M4 (ruling 27: a file change finishes once begun): when the bound or a failed close says stop, a
// file change the engine still names ('critical': a tag edit, one original's removal, a Delete book's file loop, a rename)
// is waited for to its own end first, never past FILE_CHANGE_BOUND_MS; then the stop goes on. The engine waits for the same
// changes with the same bound (critical_sections.FILE_CHANGE_BOUND), so an accepted Quit still always ends.
const FILE_CHANGE_BOUND_MS = 300000;
const fileChangeNamed = (waiting) => Array.isArray(waiting) && waiting.some((item) => item && item.kind === 'critical');
function createQuitBound({ keepConversion = false, boundMs = QUIT_WAIT_BOUND_MS, fileChangeMs = FILE_CHANGE_BOUND_MS, now = () => Date.now() } = {}) {
 let since = null;
 let holding = null;
 return {
  observe(facts) {
   const waiting = facts && Array.isArray(facts.waiting) ? facts.waiting : [];
   let stop = null;
   if (facts && facts.blocked) stop = 'blocked';
   else if (!waiting.length || keepConversion && waiting.some((item) => item.kind === 'conversion')) since = null;
   else {
    if (since === null) since = now();
    if (now() - since >= boundMs) stop = 'bound';
   }
   if (!stop || !fileChangeNamed(waiting)) { holding = null; return stop; }
   if (holding === null) holding = now();
   return now() - holding >= fileChangeMs ? stop : null;
  },
 };
}
// Quit anyway: the engine's immediate safe stop (POST /api/desktop/stop-now, as at a Windows sign-out: the book in progress
// converts again next time; an open file change still ends first), then the shell waits for its own engine host and ends
// it past its bound (endEngine: endOwnEngine on our own child). An engine that does not answer is stopped through its pipe.
async function quitNow({ post, endEngine }) {
 let answer = null;
 try { answer = await post(); } catch { /* its pipe closes next: the same safe stop */ }
 return { answer, engine: await endEngine() };
}
module.exports = { createQuitWatch, outcomeOf, sendQuit, endOwnEngine, quitWaiting, createQuitProgress, createQuitBound, QUIT_WAIT_BOUND_MS,
 FILE_CHANGE_BOUND_MS, fileChangeNamed, quitNow };
