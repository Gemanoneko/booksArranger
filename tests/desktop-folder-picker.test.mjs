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

test('a relative or several answers return null (the page never types a path)', async () => {
  assert.equal(await choose({ dialog: fakeDialog({ canceled: false, filePaths: ['relative'] }), win: {} }), null);
  assert.equal(await choose({ dialog: fakeDialog({ canceled: false, filePaths: ['C:\\a', 'C:\\b'] }), win: {} }), null);
});

test('IPC answers the app window only; another sender is refused before any dialog', async () => {
  const handlers = {};
  const ipcMain = { handle: (channel, fn) => { handlers[channel] = fn; } };
  const dialog = fakeDialog({ canceled: false, filePaths: ['E:\\Audio'] });
  const appEvent = { sender: 'app' }, setupEvent = { sender: 'setup' }, strangerEvent = { sender: 'other' };
  const sender = (event) => { if (event.sender === 'app') return 'app'; if (event.sender === 'setup') return 'setup'; throw new Error('Unknown desktop control sender'); };
  register({ ipcMain, dialog, sender, window: () => ({ isDestroyed: () => false }) });
  assert.deepEqual(Object.keys(handlers), ['books:choose-folder']);
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
