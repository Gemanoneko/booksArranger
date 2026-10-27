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
module.exports = { createQuitWatch, outcomeOf, sendQuit };
