// The update panel and Quit while loading (ruling 28; Judy 3.6, 3.4): Restart to update waits for loading unless it is
// stuck or stopped, a press is answered in the message line, Quit says it stops loading, and the desktop hint sits
// under the load strip. desktop-ui.js in a vm with a small fake DOM.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

function element(tag = 'div', id = '') {
 const node = { tagName: tag.toUpperCase(), id, children: [], attributes: {}, handlers: {}, hidden: false, title: '', className: '', textContent: '', open: false, after: [],
  classList: { toggle() {}, add() {}, remove() {} },
  append(...items) { this.children.push(...items); }, setAttribute(name, value) { this.attributes[name] = String(value); },
  getAttribute(name) { return name in this.attributes ? this.attributes[name] : null; },
  addEventListener(type, fn) { (this.handlers[type] ||= []).push(fn); }, focus() {}, showModal() { this.open = true; }, close() { this.open = false; },
  replaceChildren(...items) { this.children = items; } };
 node.after = function (...items) { this.placed = items; };
 return node;
}
function page(statuses) {
 const byId = { shutdown: element('button', 'shutdown'), message: element('p', 'message'), 'load-strip': element('section', 'load-strip') };
 byId.shutdown.parentElement = element('div');
 const header = element('header');
 const document = { body: element('body'), createElement: (tag) => element(tag), getElementById: (id) => byId[id] || null,
  querySelector: (selector) => selector === 'header' ? header : selector === '#shutdown' ? byId.shutdown : null };
 let restartRequest = null, installs = 0;
 const api = { quit: async () => {}, checkUpdates: async () => {}, downloadUpdate: async () => {}, installUpdate: async () => { installs++; }, cancelUpdate: async () => {},
  showInstaller: async () => {}, onRestartRequest: (fn) => { restartRequest = fn; }, onStatus: () => {}, status: async () => statuses.shift() || statuses.last };
 const context = { window: { booksDesktop: api }, document, console, setInterval: () => 0, setTimeout: () => 0 };
 vm.createContext(context);
 vm.runInContext(fs.readFileSync(new URL('../web/desktop-ui.js', import.meta.url), 'utf8'), context);
 return { byId, header, context, restart: () => findRestart(context), request: () => restartRequest(), installs: () => installs };
}
function findRestart(context) {
 // The update panel is the section after the desktop-status panel; its buttons carry their faces.
 const sections = [];
 const walk = (node) => { if (!node || typeof node !== 'object') return; if (node.tagName === 'BUTTON' && node.textContent.startsWith('Restart to update')) sections.push(node); for (const child of node.children || []) walk(child); for (const child of node.placed || []) walk(child); };
 walk(context.document.getElementById('load-strip'));
 return sections[0];
}
const flush = () => new Promise((resolve) => setImmediate(resolve));
const update = { version: '0.22.1', available: '0.22.2', ready: true, packaged: true, busy: {}, check: {}, download: {}, install: {}, canCancel: false, showInstaller: false };

test('loadingWaits: loading holds Restart to update unless the load is stuck or stopped', () => {
 const { context } = page([{ quit: 'none' }]);
 const t = context.booksUpdateText;
 assert.equal(t.loadingWaits({ loaded: false, verdict: 'working' }), true);
 assert.equal(t.loadingWaits({ loaded: false, verdict: 'waiting' }), true);
 assert.equal(t.loadingWaits({ loaded: false, verdict: 'stuck' }), false);
 assert.equal(t.loadingWaits({ loaded: false, verdict: 'stopped' }), false);
 assert.equal(t.loadingWaits({ loaded: true, verdict: 'working' }), false);
 assert.equal(t.loadingWaits({}), false, 'an older shell without the fields never holds it');
 assert.equal(t.NOT_YET_UPDATE, 'Not yet: Books Arranger is still loading. You can update when it finishes, or if loading gets stuck.');
});

test('while loading: the hint sits under the strip, Quit stops loading, Restart to update is inert and answered', async () => {
 const loading = { loaded: false, verdict: 'working', quit: 'none', update, desktop: { phase: 'running', loading: { step: 'session' } } };
 const p = page([loading, loading, loading]);
 await flush(); await flush();
 assert.equal(p.byId['load-strip'].placed[0].textContent, 'Closing this window keeps Books Arranger running in the tray. Choose Quit Books Arranger to close the app.');
 assert.equal(p.byId.shutdown.title, 'Stop loading and close Books Arranger. Your files are not touched.');
 const restart = p.restart();
 assert.equal(restart.getAttribute('aria-disabled'), 'true');
 assert.equal(restart.title, p.context.booksUpdateText.NOT_YET_UPDATE);
 await p.request(); await flush();
 assert.equal(p.byId.message.textContent, p.context.booksUpdateText.NOT_YET_UPDATE);
 assert.equal(p.installs(), 0, 'nothing starts');
});

test('stuck, then loaded: Restart to update is live again and Quit keeps its normal tooltip', async () => {
 const stuck = { loaded: false, verdict: 'stuck', quit: 'none', update, desktop: { phase: 'running' } };
 const loaded = { loaded: true, verdict: 'working', quit: 'none', update, desktop: { phase: 'running', busy: { converting: false } } };
 const p = page([stuck]);
 await flush(); await flush();
 assert.equal(p.restart().getAttribute('aria-disabled'), 'false');
 assert.equal(p.byId.shutdown.title, 'Stop loading and close Books Arranger. Your files are not touched.');
 const q = page([loaded]);
 await flush(); await flush();
 assert.equal(q.restart().getAttribute('aria-disabled'), 'false');
 assert.equal(q.byId.shutdown.title, 'Finish the current book and cleanup, keep queued books, then close the app');
});
