'use strict';
// Rulings 69 and 70 (Sergei 2026-10-29): "Choose folder…" on any book row opens the regular Windows folder picker.
// The picker belongs to the app window only (never the setup window or any other page), it never types or edits a path,
// and it returns one absolute folder or null (Cancel). The engine validates the folder; this module only asks Windows.
// dialog is injected (Electron's in the app, a fake in tests): no real dialog, focus change or window in a test.
const fs = require('node:fs');
const path = require('node:path');

const MAX = 1000;
const AUDIO_EXTENSIONS = ['mp3', 'm4a', 'm4b', 'aac', 'flac', 'ogg', 'opus', 'wav', 'wma'];
const START_CHECK_MS = 1500;

function text(value, fallback) {
  return typeof value === 'string' && value.trim() && value.length <= 300 ? value : fallback;
}

function absoluteFile(value, extensions) {
  return typeof value === 'string' && value.length <= MAX && !/[\x00-\x1f]/.test(value) &&
    /^(?:[a-z]:[\\/]|[\\/]{2}[^\\/]+[\\/][^\\/]+[\\/])/i.test(value) &&
    extensions.includes(path.win32.extname(value).slice(1).toLowerCase());
}

function absoluteFolder(value) {
  return typeof value === 'string' && value.length <= MAX && !/[\x00-\x1f]/.test(value) &&
    /^(?:[a-z]:[\\/]|[\\/]{2}[^\\/]+[\\/][^\\/]+)/i.test(value);
}

// Sergei 2026-11-16: the manual conversion pickers (Source Browse… in Folder and Files mode, Export Save As) open where
// they were last used. The page remembers the folders (web/app.js, localStorage in the Electron profile) and sends one
// as `remembered`; a request that carries `remembered` (even '') is a manual picker. Its start folder is used only if
// it still is a folder: every candidate is checked together, off the main thread, within one bound, so a missing folder
// or an offline drive (Z:) silently leaves the picker at Windows' own default, with no error and no long wait.
function existingFolder(folder, { stat = fs.promises.stat, timeoutMs = START_CHECK_MS } = {}) {
  if (!absoluteFolder(folder)) return Promise.resolve(false);
  let timer;
  const bound = new Promise(resolve => { timer = setTimeout(() => resolve(false), timeoutMs); });
  const check = Promise.resolve().then(() => stat(folder)).then(info => !!info?.isDirectory?.(), () => false);
  return Promise.race([check, bound]).finally(() => clearTimeout(timer));
}

async function firstFolder(candidates, check) {
  const answers = await Promise.all(candidates.map(folder => check(folder)));
  const index = answers.indexOf(true);
  return index < 0 ? null : candidates[index];
}

// Folder mode starts one level above the remembered folder (Sergei 2026-11-16, "Yes, one level up", after Judy), so the
// next sibling is one click away: Windows opens a folder defaultPath inside it. If the parent is gone, the nearest
// existing ancestor; a remembered drive or share root opens at the root itself.
function ancestors(folder) {
  if (!absoluteFolder(folder)) return [];
  const list = [];
  for (let current = folder, i = 0; i < 64; i++) {
    const parent = path.win32.dirname(current);
    if (parent === current) break;
    list.push(parent);
    current = parent;
  }
  return list.length ? list : [folder];
}

// The draft's own choice comes first (the folder in Folder path, used as it is; the export path already chosen), then
// the remembered folder. The export keeps its file name (the chosen one, else the suggestion) whichever folder it opens in.
async function rememberedStart(channel, value, check) {
  if (channel === 'books:choose-folder') return { defaultPath: await firstFolder([value.defaultPath, ...ancestors(value.remembered)], check) ?? undefined };
  if (channel === 'books:choose-audio-files') return { defaultPath: await firstFolder([value.remembered], check) ?? undefined };
  const chosen = absoluteFile(value.defaultPath, ['m4b']) ? value.defaultPath : null;
  const name = chosen ? path.win32.basename(chosen) : value.suggestedName;
  const folder = await firstFolder([chosen ? path.win32.dirname(chosen) : null, value.remembered], check);
  if (chosen && folder === path.win32.dirname(chosen)) return { defaultPath: chosen, suggestedName: value.suggestedName };
  const joined = folder && m4bName(name) ? path.win32.join(folder, name) : null;
  return absoluteFile(joined, ['m4b']) ? { defaultPath: joined, suggestedName: value.suggestedName } : { defaultPath: undefined, suggestedName: name };
}

function m4bName(value) {
  return typeof value === 'string' && value.length <= 240 && /^[^<>:"/\\|?*\x00-\x1f]+\.m4b$/i.test(value);
}

async function chooseAudioFiles({ dialog, win, defaultPath } = {}) {
  const options = { title: 'Choose audio files', properties: ['openFile', 'multiSelections', 'dontAddToRecent'],
    filters: [{ name: 'Audio files', extensions: AUDIO_EXTENSIONS }] };
  if (absoluteFolder(defaultPath)) options.defaultPath = defaultPath;
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
  else if (m4bName(suggestedName)) {
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
// else (main.js trustedSender); window() is the app window the dialog is modal to. stat and startCheckMs are injected
// by tests (no real filesystem or network lookup there); the app uses fs.promises.stat and START_CHECK_MS.
function register({ ipcMain, dialog, sender, window, stat, startCheckMs }) {
  let picking = false;
  const check = folder => existingFolder(folder, { stat, timeoutMs: startCheckMs });
  function handle(channel, unavailable, picker) {
    ipcMain.handle(channel, async (event, request) => {
      if (sender(event) !== 'app') throw new Error(unavailable);
      if (picking) throw new Error('A picker is already open. Finish or cancel it first.');
      const value = request && typeof request === 'object' ? request : {};
      const win = typeof window === 'function' ? window() : null;
      picking = true;
      try {
        const start = typeof value.remembered === 'string' ? await rememberedStart(channel, value, check)
          : { defaultPath: value.defaultPath, suggestedName: value.suggestedName };
        return await picker({ dialog, win: win && !win.isDestroyed?.() ? win : null,
          title: value.title, defaultPath: start.defaultPath, buttonLabel: value.buttonLabel, suggestedName: start.suggestedName });
      } finally { picking = false; }
    });
  }
  handle('books:choose-folder', 'Choosing a folder is unavailable', choose);
  handle('books:choose-audio-files', 'Choosing audio files is unavailable', chooseAudioFiles);
  handle('books:choose-audiobook-output', 'Choosing an audiobook output is unavailable', chooseAudiobookOutput);
}

module.exports = { choose, register, existingFolder };
