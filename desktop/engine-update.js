'use strict';
// Restart to update, the shell's half of stopping the engine (ruling 27, 0.22.1). 0.21.1 entered update mode only
// after the engine answered within 5 s; on the 706 MB catalog it did not, the engine stopped anyway, exited 0 and the
// app closed without installing. Now update mode starts before the request is sent, a slow answer is not a failure
// (the request is sent again; the engine treats a repeat as the same update), and the engine's own native exit is
// the only "done". Status polls feed the progress line only. One overall bound: past it the shell cancels and the
// old app runs on. Every failure is typed (error.updateCause) so the page shows its own line, never raw text.
const BOUND_MS = 180000; // T_safe 90 s + T_force 60 s (desktop_backend.py UPDATE_SAFE/UPDATE_FORCE) + 30 s
const POST_TIMEOUT_MS = 15000;
// Cancel answers once the engine has started again what the update stopped: it waits up to 25 s for each stopped worker
// to end (desktop_backend.py UPDATE_RESUME; Senua's 0.22.1 review, W3) inside its own 30 s wait for the update thread.
const CANCEL_TIMEOUT_MS = 35000;
const POLL_MS = 500;
const EXIT_GRACE_MS = 60000; // too late to cancel (the engine is ending): wait this long for its exit
const CANCEL_TRIES = 3;

function stopped(cause, message, details = {}) {
 return Object.assign(new Error(message), { updateCause: cause }, details);
}
// What Cancel, the bound or a failed close could not start again (the engine's resume_problems), typed only: the kind
// of work and why ('still_stopping' or 'refused'); the engine's own wording stays in its log.
const RESUME_KINDS = ['automatic', 'conversion', 'scan', 'lookups'];
function problemsOf(outcome) {
 const list = outcome && Array.isArray(outcome.resume_problems) ? outcome.resume_problems : [];
 return list.filter(item => item && RESUME_KINDS.includes(item.kind)).map(item => ({ kind: item.kind, cause: item.cause === 'refused' ? 'refused' : 'still_stopping' }));
}

async function parkOwnedEngine({ state, request, sleep, broadcast, now = Date.now, progress = () => {}, cancelRequested = () => false,
 boundMs = BOUND_MS, postTimeoutMs = POST_TIMEOUT_MS, cancelTimeoutMs = CANCEL_TIMEOUT_MS, pollMs = POLL_MS, exitGraceMs = EXIT_GRACE_MS }) {
 if (state.quit !== 'none' || state.backendExited || !state.owner) throw stopped('refused', 'Owned running engine is required before restarting to update');
 // Update mode first: from here an engine exit with code 0 means "install", never "close the app".
 state.quit = 'updating'; state.lateUpdateExit = false; progress({ phase: 'starting' }); broadcast();
 const deadline = now() + boundMs;
 let last = null, tooLate = false;
 const exited = () => state.backendExited;
 async function cancel(cause) {
  // The engine undoes the update and starts again what it stopped; a 409 'started' means it is already ending.
  for (let attempt = 1; attempt <= CANCEL_TRIES; attempt++) {
   try {
    // Judy 0.22.2 6.2: the engine answers Cancel once the work has started again (up to its 25 s resume bound); meanwhile
    // its status says what is still to resume, which the page names from 3 s on.
    const posting = request('POST', '/api/desktop/update-cancel', { desktop: true, timeout: cancelTimeoutMs });
    let settled = false; posting.then(() => { settled = true; }, () => { settled = true; });
    (async () => {
     while (!settled && !exited()) {
      await sleep(pollMs); if (settled) break;
      try { const status = await request('GET', '/api/desktop/status', { desktop: true, timeout: 3000 }); if (!settled && status && status.update) progress(status.update); } catch { /* busy */ }
     }
    })();
    const answer = await posting;
    const outcome = answer && answer.update && answer.update.outcome;
    return stopped(cause, cause === 'bound' ? 'The engine did not stop within the update bound' : 'Update cancelled',
     { waiting: (outcome && outcome.waiting) || (last && last.waiting) || [], resumeProblems: problemsOf(outcome) });
   } catch (error) {
    if (error.status === 409) { tooLate = true; return null; }
    if (exited()) return null;
   }
  }
  return stopped('engine_stuck', 'The engine did not answer the update cancel');
 }
 try {
  let accepted = false;
  while (!accepted && !exited()) {
   if (cancelRequested() || now() >= deadline) { const error = await cancel(cancelRequested() ? 'cancelled' : 'bound'); if (error) throw error; break; }
   try {
    const answer = await request('POST', '/api/desktop/update', { desktop: true, timeout: postTimeoutMs });
    accepted = true; last = (answer && answer.update) || last; if (last) progress(last);
   } catch (error) {
    if (error.status) throw stopped('refused', error.message); // the engine answered no (a Quit is under way)
    await sleep(pollMs); // no answer yet: the engine may already have it; send it again
   }
  }
  while (!exited()) {
   if (!tooLate && (cancelRequested() || now() >= deadline)) { const error = await cancel(cancelRequested() ? 'cancelled' : 'bound'); if (error) throw error; }
   if (tooLate && now() >= deadline + exitGraceMs) throw stopped('engine_stuck', 'The engine did not end after the update began');
   await sleep(pollMs); if (exited()) break;
   let status = null;
   try { status = await request('GET', '/api/desktop/status', { desktop: true, timeout: 3000 }); } catch { /* busy or ending: the exit decides */ }
   const update = status && status.update;
   if (update) { last = update; progress(update); if (['updating', 'exiting'].includes(update.phase)) tooLate = true; }
   if (status && status.phase === 'running' && update && update.outcome) {
    // The engine undid the update by itself: its own bound, or a close that failed.
    throw stopped(update.outcome.result === 'bound' ? 'bound' : 'blocked', update.outcome.reason || 'The engine cancelled the update',
     { waiting: update.outcome.waiting || [], resumeProblems: problemsOf(update.outcome) });
   }
  }
  if (state.backend.exitCode !== 0) throw stopped('engine_exit', 'The engine exited with code ' + state.backend.exitCode + ' while stopping for the update');
 } catch (error) {
  // Senua's 0.22.1 review, W5: given up while the engine was already ending for the update (too late to cancel, still
  // in its close): its later exit is that ending, never the engine's own Stop, so it must not close the app.
  if (!exited()) { state.quit = 'none'; state.lateUpdateExit = tooLate; broadcast(); }
  throw error;
 }
}
// The engine's exit as the update sees it (main.js's exit handler asks first): 'update' while the update flow reads
// the exit, 'late' for the ending the update gave up on (W5; once: the old engine starts again), else null.
function updateExit(state) {
 if (state.quit === 'updating' || state.quit === 'installing') return 'update';
 if (state.lateUpdateExit && state.quit === 'none') { state.lateUpdateExit = false; return 'late'; }
 return null;
}
module.exports = { parkOwnedEngine, updateExit, problemsOf, BOUND_MS, POST_TIMEOUT_MS, CANCEL_TIMEOUT_MS, EXIT_GRACE_MS };
