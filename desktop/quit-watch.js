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
module.exports = { createQuitWatch, outcomeOf };
