'use strict';
// One shared GET for every desktop-status reader in the shell. Concurrent readers
// join the request already in flight; an answer is reused until maxAgeMs after its
// request was SENT. A caller's shorter timeout ends only that caller's wait — the
// shared request keeps its own timeout, so slow engine replies never multiply
// requests. invalidate() (any control) starts a new generation: the remembered
// answer is dropped and a request already in flight can neither refill it nor be
// joined by later readers. The clock is monotonic and a negative age counts as
// expired, so a wall-clock step can never pin an old answer.
const { performance } = require('node:perf_hooks');

function createStatusFlight({ fetch, now = () => performance.now(), maxAgeMs = 1000, requestTimeoutMs = 5000 }) {
 let flight = null, last = null, generation = 0;
 function start() {
  const born = generation, sentAt = now();
  let sent;
  try { sent = Promise.resolve(fetch(requestTimeoutMs)); } catch (error) { sent = Promise.reject(error); }
  const current = sent.then(value => { if (born === generation) last = { at: sentAt, value }; return value; })
   .finally(() => { if (flight === current) flight = null; });
  flight = current;
  return current;
 }
 function fresh(maxAge) {
  if (!last) return false;
  const age = now() - last.at;
  return age >= 0 && age < maxAge;
 }
 function get({ timeout = requestTimeoutMs, maxAge = maxAgeMs } = {}) {
  if (fresh(maxAge)) return Promise.resolve(last.value);
  const shared = flight || start();
  if (!(timeout < requestTimeoutMs)) return shared;
  return new Promise((resolve, reject) => {
   const timer = setTimeout(() => reject(new Error('Request timed out')), timeout);
   shared.then(value => { clearTimeout(timer); resolve(value); }, error => { clearTimeout(timer); reject(error); });
  });
 }
 function invalidate() { generation += 1; last = null; flight = null; }
 return { get, invalidate, get inFlight() { return flight !== null; } };
}

module.exports = { createStatusFlight };
