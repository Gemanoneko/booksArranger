'use strict';
// Rulings 69 and 70 (Sergei 2026-10-29): "Choose folder…" on any book row opens the regular Windows folder picker.
// The picker belongs to the app window only (never the setup window or any other page), it never types or edits a path,
// and it returns one absolute folder or null (Cancel). The engine validates the folder; this module only asks Windows.
// dialog is injected (Electron's in the app, a fake in tests): no real dialog, focus change or window in a test.
const path = require('node:path');

const MAX = 1000;

function text(value, fallback) {
  return typeof value === 'string' && value.trim() && value.length <= 300 ? value : fallback;
}

async function choose({ dialog, win, title, defaultPath, buttonLabel } = {}) {
  if (!dialog || typeof dialog.showOpenDialog !== 'function') throw new Error('The folder picker is unavailable');
  const options = { title: text(title, 'Choose a folder'), properties: ['openDirectory', 'createDirectory', 'dontAddToRecent'] };
  const label = text(buttonLabel, '');
  if (label) options.buttonLabel = label;
  if (typeof defaultPath === 'string' && defaultPath.length <= MAX && path.win32.isAbsolute(defaultPath)) options.defaultPath = defaultPath;
  const result = win ? await dialog.showOpenDialog(win, options) : await dialog.showOpenDialog(options);
  if (!result || result.canceled || !Array.isArray(result.filePaths) || result.filePaths.length !== 1) return null;
  const chosen = result.filePaths[0];
  return typeof chosen === 'string' && chosen.length <= MAX && path.win32.isAbsolute(chosen) ? chosen : null;
}

// ipcMain: Electron's (or a fake); sender(event) answers 'app' for the app window's own page and throws for anything
// else (main.js trustedSender); window() is the app window the dialog is modal to.
function register({ ipcMain, dialog, sender, window }) {
  ipcMain.handle('books:choose-folder', async (event, request) => {
    if (sender(event) !== 'app') throw new Error('Choosing a folder is unavailable');
    const value = request && typeof request === 'object' ? request : {};
    const win = typeof window === 'function' ? window() : null;
    return choose({ dialog, win: win && !(typeof win.isDestroyed === 'function' && win.isDestroyed()) ? win : null,
      title: value.title, defaultPath: value.defaultPath, buttonLabel: value.buttonLabel });
  });
}

module.exports = { choose, register };
