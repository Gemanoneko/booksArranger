// Rulings 69 and 70: the Windows folder picker behind "Choose folder…" (desktop/folder-picker.js). The dialog, the IPC and
// the window are fakes: no real dialog, window or focus change.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { choose, register, existingFolder } = require('../desktop/folder-picker.js');

function fakeDialog(answer) {
  const calls = [];
  return { calls, showOpenDialog: async (...args) => { calls.push(args); return answer; } };
}

test('cancel returns null', async () => {
  const dialog = fakeDialog({ canceled: true, filePaths: [] });
  assert.equal(await choose({ dialog, win: { id: 1 }, title: 'Choose a folder for Криг' }), null);
});

test('a pick returns the absolute path and the dialog is modal to the app window', async () => {
  const win = { id: 7 };
  const dialog = fakeDialog({ canceled: false, filePaths: ['D:\\Books\\Horror'] });
  assert.equal(await choose({ dialog, win, title: 'Choose a folder for Криг', buttonLabel: 'Select folder' }), 'D:\\Books\\Horror');
  const [owner, options] = dialog.calls[0];
  assert.equal(owner, win);
  assert.deepEqual(options.properties, ['openDirectory', 'createDirectory', 'dontAddToRecent']);
  assert.equal(options.title, 'Choose a folder for Криг');
  assert.equal(options.buttonLabel, 'Select folder');
});

test('defaultPath is passed through when absolute and dropped otherwise', async () => {
  const dialog = fakeDialog({ canceled: true, filePaths: [] });
  await choose({ dialog, win: {}, defaultPath: 'Z:\\Audiobooks Sorted\\Без автора' });
  assert.equal(dialog.calls[0][1].defaultPath, 'Z:\\Audiobooks Sorted\\Без автора');
  await choose({ dialog, win: {}, defaultPath: 'relative\\folder' });
  assert.equal('defaultPath' in dialog.calls[1][1], false);
});

test('invalid native answers reject and are distinguishable from user cancellation', async () => {
  await assert.rejects(choose({ dialog: fakeDialog({ canceled: false, filePaths: ['relative'] }), win: {} }), /absolute folder/);
  await assert.rejects(choose({ dialog: fakeDialog({ canceled: false, filePaths: ['C:\\a', 'C:\\b'] }), win: {} }), /return a folder/);
  await assert.rejects(choose({ dialog: fakeDialog(null), win: {} }), /return a folder/);
});

test('IPC answers the app window only; another sender is refused before any dialog', async () => {
  const handlers = {};
  const ipcMain = { handle: (channel, fn) => { handlers[channel] = fn; } };
  const dialog = fakeDialog({ canceled: false, filePaths: ['E:\\Audio'] });
  const appEvent = { sender: 'app' }, setupEvent = { sender: 'setup' }, strangerEvent = { sender: 'other' };
  const sender = (event) => { if (event.sender === 'app') return 'app'; if (event.sender === 'setup') return 'setup'; throw new Error('Unknown desktop control sender'); };
  register({ ipcMain, dialog, sender, window: () => ({ isDestroyed: () => false }) });
  assert.deepEqual(Object.keys(handlers), ['books:choose-folder','books:choose-audio-files','books:choose-audiobook-output']);
  assert.equal(await handlers['books:choose-folder'](appEvent, { title: 'Choose a folder for X', defaultPath: 'C:\\', buttonLabel: 'Move here', extra: 1 }), 'E:\\Audio');
  assert.equal(dialog.calls.length, 1);
  await assert.rejects(handlers['books:choose-folder'](setupEvent, {}), /unavailable/);
  await assert.rejects(handlers['books:choose-folder'](strangerEvent, {}), /Unknown desktop control sender/);
  assert.equal(dialog.calls.length, 1);
});

test('the bridge answers nothing but the chosen path or null', async () => {
  const handlers = {};
  register({ ipcMain: { handle: (c, fn) => { handlers[c] = fn; } }, dialog: fakeDialog({ canceled: true, filePaths: ['C:\\x'] }), sender: () => 'app', window: () => null });
  assert.equal(await handlers['books:choose-folder']({}, null), null);
});

test('concurrent trusted requests share one native picker until cancellation settles', async () => {
  const handlers = {}, calls = []; let finish;
  const dialog = { showOpenDialog: (...args) => { calls.push(args); return new Promise(resolve => { finish = resolve; }); } };
  register({ ipcMain: { handle: (c, fn) => { handlers[c] = fn; } }, dialog, sender: () => 'app', window: () => ({}) });
  const first = handlers['books:choose-folder']({}, { title: 'First book' });
  await assert.rejects(handlers['books:choose-folder']({}, { title: 'Second book' }), /already open/);
  assert.equal(calls.length, 1);
  finish({ canceled: true, filePaths: [] }); assert.equal(await first, null);
  const next = handlers['books:choose-folder']({}, {});
  assert.equal(calls.length, 2); finish({ canceled: false, filePaths: ['C:\\Private fixture'] });
  assert.equal(await next, 'C:\\Private fixture');
});

test('a rejected native picker releases its single-flight lock for the next request', async () => {
  const handlers = {}; let calls = 0;
  const dialog = { showOpenDialog: async () => { if (++calls === 1) throw new Error('Native opening failed'); return { canceled: true, filePaths: [] }; } };
  register({ ipcMain: { handle: (c, fn) => { handlers[c] = fn; } }, dialog, sender: () => 'app', window: () => ({}) });
  await assert.rejects(handlers['books:choose-folder']({}, {}), /Native opening failed/);
  assert.equal(await handlers['books:choose-folder']({}, {}), null);
  assert.equal(calls, 2);
});

test('manual file and export pickers return exact selections, stay modal and share the folder lock', async () => {
  const handlers = {}, calls = [], win = {id: 10};
  const tracks = ['Z:\\Аудиокниги\\02.MP3','Z:\\Аудиокниги\\10.flac'];
  const output = '\\\\server\\share\\Аудиокнига.m4b';
  let finish;
  const dialog = {
    showOpenDialog: (...args) => { calls.push(args); return new Promise(resolve => {finish=resolve;}); },
    showSaveDialog: async (...args) => { calls.push(args); return {filePath:output}; },
  };
  register({ipcMain:{handle:(channel,fn)=>{handlers[channel]=fn;}},dialog,sender:event=>event.sender,window:()=>win});
  const event = {sender:'app'}, files = handlers['books:choose-audio-files'], save = handlers['books:choose-audiobook-output'];
  await assert.rejects(files({sender:'setup'}), /unavailable/);
  await assert.rejects(save({sender:'setup'}), /unavailable/);
  const pending = files(event);
  assert.equal(calls[0][0],win);
  assert.deepEqual(calls[0][1].properties,['openFile','multiSelections','dontAddToRecent']);
  assert.deepEqual(calls[0][1].filters[0].extensions,['mp3','m4a','m4b','aac','flac','ogg','opus','wav','wma']);
  await assert.rejects(save(event), /already open/);
  finish({filePaths:tracks});
  assert.deepEqual(await pending, tracks);
  assert.equal(await save(event, {suggestedName:'Аудиокнига.m4b'}), output);
  assert.equal(calls[1][0],win);
  assert.equal(calls[1][1].defaultPath,'Аудиокнига.m4b');
  assert.deepEqual(calls[1][1].filters[0].extensions,['m4b']);
  await save(event, {defaultPath:output});
  assert.equal(calls[2][1].defaultPath,output);
});

test('manual pickers distinguish cancellation from wrong extensions and incomplete paths', async () => {
  const handlers = {};
  let pick, destination;
  register({ipcMain:{handle:(channel,fn)=>{handlers[channel]=fn;}},sender:()=> 'app',window:()=>null,
    dialog:{showOpenDialog:async()=>pick,showSaveDialog:async()=>destination}});
  const files=handlers['books:choose-audio-files'], save=handlers['books:choose-audiobook-output'];
  pick={canceled:true};destination={canceled:true};
  assert.equal(await files({}),null);
  assert.equal(await save({}),null);
  pick={filePaths:['C:\\foo\\story.txt']};destination={filePath:'C:\\foo\\story.mp3'};
  await assert.rejects(files({}), /supported audio files/);
  await assert.rejects(save({}), /ending in .m4b/);
  pick={filePaths:['\\foo\\story.mp3']};destination={filePath:'C:story.m4b'};
  await assert.rejects(files({}), /absolute paths/);
  await assert.rejects(save({}), /absolute path/);
});

// Sergei 2026-11-16: the manual pickers open where they were last used. The page sends the remembered folder as
// `remembered`; the shell opens it only if it still is a folder (stat is a fake here: no real drive or network lookup).
const SOURCE = 'Z:\\Audiobooks\\Unsorted\\Ужасы и трэшатинка. Сборник рассказов\\Сборник 2';
const PARENT = 'Z:\\Audiobooks\\Unsorted\\Ужасы и трэшатинка. Сборник рассказов';
const EXPORT = 'Z:\\Audiobooks Sorted\\Сборники\\Пять Вечеров';
function remembering({ folders = [], hang = () => false, startCheckMs } = {}) {
  const handlers = {}, calls = [], stats = [];
  const stat = folder => {
    stats.push(folder);
    if (hang(folder)) return new Promise(() => {});
    if (folders.includes(folder)) return Promise.resolve({ isDirectory: () => true });
    return Promise.reject(Object.assign(new Error('ENOENT: no such file or directory'), { code: 'ENOENT' }));
  };
  const dialog = {
    showOpenDialog: async (...args) => { calls.push(args); return { canceled: true, filePaths: [] }; },
    showSaveDialog: async (...args) => { calls.push(args); return { canceled: true }; },
  };
  register({ ipcMain: { handle: (c, fn) => { handlers[c] = fn; } }, dialog, sender: () => 'app', window: () => ({}), stat, startCheckMs });
  const options = () => calls.at(-1)[1];
  return { handlers, calls, stats, options };
}

test('Folder mode opens one level up, at the remembered folder\'s parent; Files mode opens inside it; Cyrillic exact', async () => {
  const t = remembering({ folders: [SOURCE, PARENT, 'Z:\\Audiobooks\\Unsorted', 'Z:\\Audiobooks', 'Z:\\'] });
  await t.handlers['books:choose-folder']({}, { title: 'Choose a source folder', defaultPath: '', buttonLabel: 'Choose folder', remembered: SOURCE });
  assert.equal(t.options().defaultPath, PARENT, 'the next sibling (Сборник 3) is one click away');
  assert.equal(t.options().buttonLabel, 'Choose folder');
  await t.handlers['books:choose-audio-files']({}, { remembered: SOURCE });
  assert.equal(t.options().defaultPath, SOURCE);
  assert.deepEqual(t.options().properties, ['openFile', 'multiSelections', 'dontAddToRecent']);
  // Files mode remembers the folder holding the files with a trailing separator; its parent is the same one.
  await t.handlers['books:choose-folder']({}, { defaultPath: '', remembered: SOURCE + '\\' });
  assert.equal(t.options().defaultPath, PARENT);
});

test('Folder mode falls back to the nearest existing ancestor, then the Windows default', async () => {
  const t = remembering({ folders: ['Z:\\Audiobooks', 'Z:\\'] });
  await t.handlers['books:choose-folder']({}, { defaultPath: '', remembered: SOURCE });
  assert.equal(t.options().defaultPath, 'Z:\\Audiobooks');
  assert.equal(t.stats.includes(SOURCE), false, 'the remembered folder itself is never the start');
  const root = remembering({ folders: ['Z:\\', SOURCE] });
  await root.handlers['books:choose-folder']({}, { defaultPath: '', remembered: SOURCE });
  assert.equal(root.options().defaultPath, 'Z:\\');
  const none = remembering({ folders: [SOURCE] });
  await none.handlers['books:choose-folder']({}, { defaultPath: '', remembered: SOURCE });
  assert.equal('defaultPath' in none.options(), false);
});

test('a remembered drive or share root opens at the root itself', async () => {
  const t = remembering({ folders: ['Z:\\', '\\\\nas\\Audiobooks'] });
  await t.handlers['books:choose-folder']({}, { defaultPath: '', remembered: 'Z:\\' });
  assert.equal(t.options().defaultPath, 'Z:\\');
  await t.handlers['books:choose-folder']({}, { defaultPath: '', remembered: '\\\\nas\\Audiobooks' });
  assert.equal(t.options().defaultPath, '\\\\nas\\Audiobooks');
  const offline = remembering({ folders: [] });
  await offline.handlers['books:choose-folder']({}, { defaultPath: '', remembered: 'Z:\\' });
  assert.equal('defaultPath' in offline.options(), false);
});

test('the folder already in Folder path comes first, used as it is; the remembered parent when it is gone', async () => {
  const typed = 'D:\\Другая книга';
  const t = remembering({ folders: [SOURCE, PARENT, typed] });
  await t.handlers['books:choose-folder']({}, { defaultPath: typed, remembered: SOURCE });
  assert.equal(t.options().defaultPath, typed);
  const gone = remembering({ folders: [SOURCE, PARENT] });
  await gone.handlers['books:choose-folder']({}, { defaultPath: typed, remembered: SOURCE });
  assert.equal(gone.options().defaultPath, PARENT);
});

test('a missing remembered folder silently leaves the picker at the Windows default', async () => {
  const t = remembering({ folders: [] });
  assert.equal(await t.handlers['books:choose-folder']({}, { defaultPath: '', remembered: SOURCE }), null);
  assert.equal('defaultPath' in t.options(), false);
  assert.equal(await t.handlers['books:choose-audio-files']({}, { remembered: SOURCE }), null);
  assert.equal('defaultPath' in t.options(), false);
  assert.equal(t.calls.length, 2);
});

test('an offline drive that never answers is given up after the bound, and the picker still opens', async () => {
  const t = remembering({ hang: folder => folder.startsWith('Z:'), startCheckMs: 20 });
  const started = Date.now();
  await t.handlers['books:choose-audio-files']({}, { remembered: SOURCE });
  await t.handlers['books:choose-folder']({}, { defaultPath: '', remembered: SOURCE });
  assert.ok(Date.now() - started < 2000, 'the ancestors are checked together within one bound');
  assert.equal(t.calls.length, 2);
  assert.equal('defaultPath' in t.calls[0][1], false);
  assert.equal('defaultPath' in t.calls[1][1], false);
});

test('a remembered value that is not an absolute folder is never looked up', async () => {
  const t = remembering({ folders: ['relative\\folder'] });
  for (const remembered of ['', 'relative\\folder', 'C:folder', '\\rooted', 'Z:\\bad\u0000name', 'Z:\\' + 'x'.repeat(1001)]) {
    await t.handlers['books:choose-audio-files']({}, { remembered });
    assert.equal('defaultPath' in t.options(), false);
  }
  assert.deepEqual(t.stats, []);
});

test('a picker request without `remembered` (Choose folder… on a book row) is unchanged and never looked up', async () => {
  const t = remembering({ folders: [] });
  await t.handlers['books:choose-folder']({}, { title: 'Choose a folder for X', defaultPath: 'Z:\\Audiobooks Sorted\\Без автора' });
  assert.equal(t.options().defaultPath, 'Z:\\Audiobooks Sorted\\Без автора');
  await t.handlers['books:choose-audio-files']({}, {});
  assert.equal('defaultPath' in t.options(), false);
  await t.handlers['books:choose-audiobook-output']({}, { suggestedName: 'Книга.m4b' });
  assert.equal(t.options().defaultPath, 'Книга.m4b');
  assert.deepEqual(t.stats, []);
});

test('Save As opens in the remembered export folder with the suggested name when the draft has no export path', async () => {
  const t = remembering({ folders: [EXPORT, SOURCE] });
  await t.handlers['books:choose-audiobook-output']({}, { defaultPath: undefined, suggestedName: 'Сборник 2.m4b', remembered: EXPORT });
  assert.equal(t.options().defaultPath, EXPORT + '\\Сборник 2.m4b');
  assert.deepEqual(t.options().filters[0].extensions, ['m4b']);
  // The export folder is its own: with none remembered, the picker keeps today's suggested name only.
  const none = remembering({ folders: [SOURCE] });
  await none.handlers['books:choose-audiobook-output']({}, { suggestedName: 'Сборник 2.m4b', remembered: '' });
  assert.equal(none.options().defaultPath, 'Сборник 2.m4b');
});

test('Save As keeps the export path the draft already has; if its folder is gone the remembered folder takes its name', async () => {
  const chosen = 'D:\\Готово\\Мой сборник.m4b';
  const kept = remembering({ folders: ['D:\\Готово', EXPORT] });
  await kept.handlers['books:choose-audiobook-output']({}, { defaultPath: chosen, suggestedName: 'Other.m4b', remembered: EXPORT });
  assert.equal(kept.options().defaultPath, chosen);
  const moved = remembering({ folders: [EXPORT] });
  await moved.handlers['books:choose-audiobook-output']({}, { defaultPath: chosen, suggestedName: 'Other.m4b', remembered: EXPORT });
  assert.equal(moved.options().defaultPath, EXPORT + '\\Мой сборник.m4b');
  const offline = remembering({ folders: [] });
  await offline.handlers['books:choose-audiobook-output']({}, { defaultPath: chosen, suggestedName: 'Other.m4b', remembered: EXPORT });
  assert.equal(offline.options().defaultPath, 'Мой сборник.m4b');
});

test('existingFolder reads the real filesystem: a Unicode folder is found, a removed folder and a file are not', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'books-picker-'));
  try {
    const folder = path.join(dir, 'Ужасы и трэшатинка. Сборник рассказов', 'Сборник 2');
    fs.mkdirSync(folder, { recursive: true });
    const file = path.join(folder, '01 Глава.mp3');
    fs.writeFileSync(file, '');
    assert.equal(await existingFolder(folder), true);
    assert.equal(await existingFolder(folder + '\\'), true);
    assert.equal(await existingFolder(file), false);
    fs.rmSync(folder, { recursive: true, force: true });
    assert.equal(await existingFolder(folder), false);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});
