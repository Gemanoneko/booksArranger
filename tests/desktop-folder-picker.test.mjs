// Rulings 69 and 70: the Windows folder picker behind "Choose folder…" (desktop/folder-picker.js). The dialog, the IPC and
// the window are fakes: no real dialog, window or focus change.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { choose, register } = require('../desktop/folder-picker.js');

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
