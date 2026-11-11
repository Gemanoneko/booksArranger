'use strict';
// Rulings 69 and 70 (Sergei 2026-10-29): "Choose folder…" on any book row opens the regular Windows folder picker.
// The picker belongs to the app window only (never the setup window or any other page), it never types or edits a path,
// and it returns one absolute folder or null (Cancel). The engine validates the folder; this module only asks Windows.
// dialog is injected (Electron's in the app, a fake in tests): no real dialog, focus change or window in a test.
const path = require('node:path');

const MAX = 1000;
const AUDIO_EXTENSIONS = ['mp3', 'm4a', 'm4b', 'aac', 'flac', 'ogg', 'opus', 'wav', 'wma'];

function text(value, fallback) {
  return typeof value === 'string' && value.trim() && value.length <= 300 ? value : fallback;
}

function absoluteFile(value, extensions) {
  return typeof value === 'string' && value.length <= MAX && !/[\x00-\x1f]/.test(value) &&
    /^(?:[a-z]:[\\/]|[\\/]{2}[^\\/]+[\\/][^\\/]+[\\/])/i.test(value) &&
    extensions.includes(path.win32.extname(value).slice(1).toLowerCase());
}

async function chooseAudioFiles({ dialog, win } = {}) {
  const options = { title: 'Choose audio files', properties: ['openFile', 'multiSelections', 'dontAddToRecent'],
    filters: [{ name: 'Audio files', extensions: AUDIO_EXTENSIONS }] };
  const result = win ? await dialog.showOpenDialog(win, options) : await dialog.showOpenDialog(options);
  if (result?.canceled === true) return null;
  if (!Array.isArray(result?.filePaths) || !result.filePaths.length || !result.filePaths.every(file => absoluteFile(file, AUDIO_EXTENSIONS))) {
    throw new Error('Choose supported audio files with absolute paths.');
  }
  return result.filePaths;
}

async function chooseAudiobookOutput({ dialog, win, defaultPath, suggestedName } = {}) {
  const options = { title: 'Save audiobook as', properties: ['createDirectory', 'dontAddToRecent'],
    filters: [{ name: 'Audiobook (M4B)', extensions: ['m4b'] }] };
  if (absoluteFile(defaultPath, ['m4b'])) options.defaultPath = defaultPath;
  else if (typeof suggestedName === 'string' && suggestedName.length <= 240 && /^[^<>:"/\\|?*\x00-\x1f]+\.m4b$/i.test(suggestedName)) {
    options.defaultPath = suggestedName;
  }
  const result = win ? await dialog.showSaveDialog(win, options) : await dialog.showSaveDialog(options);
  if (result?.canceled === true) return null;
  if (!absoluteFile(result?.filePath, ['m4b'])) throw new Error('Choose an absolute path ending in .m4b.');
  return result.filePath;
}

async function choose({ dialog, win, title, defaultPath, buttonLabel } = {}) {
  if (!dialog || typeof dialog.showOpenDialog !== 'function') throw new Error('The folder picker is unavailable');
  const options = { title: text(title, 'Choose a folder'), properties: ['openDirectory', 'createDirectory', 'dontAddToRecent'] };
  const label = text(buttonLabel, '');
  if (label) options.buttonLabel = label;
  if (typeof defaultPath === 'string' && defaultPath.length <= MAX && path.win32.isAbsolute(defaultPath)) options.defaultPath = defaultPath;
  const result = win ? await dialog.showOpenDialog(win, options) : await dialog.showOpenDialog(options);
  if (result?.canceled === true) return null;
  if (!result || !Array.isArray(result.filePaths) || result.filePaths.length !== 1) throw new Error('The folder picker did not return a folder');
  const chosen = result.filePaths[0];
  if (typeof chosen !== 'string' || chosen.length > MAX || !path.win32.isAbsolute(chosen)) throw new Error('The folder picker did not return an absolute folder');
  return chosen;
}

// ipcMain: Electron's (or a fake); sender(event) answers 'app' for the app window's own page and throws for anything
// else (main.js trustedSender); window() is the app window the dialog is modal to.
function register({ ipcMain, dialog, sender, window }) {
  let picking = false;
  function handle(channel, unavailable, picker) {
    ipcMain.handle(channel, async (event, request) => {
      if (sender(event) !== 'app') throw new Error(unavailable);
      if (picking) throw new Error('A picker is already open. Finish or cancel it first.');
      const value = request && typeof request === 'object' ? request : {};
      const win = typeof window === 'function' ? window() : null;
      picking = true;
      try {
        return await picker({ dialog, win: win && !win.isDestroyed?.() ? win : null,
          title: value.title, defaultPath: value.defaultPath, buttonLabel: value.buttonLabel, suggestedName: value.suggestedName });
      } finally { picking = false; }
    });
  }
  handle('books:choose-folder', 'Choosing a folder is unavailable', choose);
  handle('books:choose-audio-files', 'Choosing audio files is unavailable', chooseAudioFiles);
  handle('books:choose-audiobook-output', 'Choosing an audiobook output is unavailable', chooseAudiobookOutput);
}

module.exports = { choose, register };
