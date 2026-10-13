#!/usr/bin/env node
// Downloads the pinned Windows embeddable Python and the pinned LGPL FFmpeg build
// (desktop/runtime-pins.json), verifies each SHA-256, and stages them into
// build-cache/runtime/{python,ffmpeg} for electron-builder's extraResources.
// Each download lives in its own folder under build-cache/downloads/. Nothing is
// executed from a download folder; the staged copies are checked from the repo root.
// Re-running is cheap: verified downloads are reused, staging is rebuilt.

import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import https from 'node:https';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const pins = JSON.parse(fs.readFileSync(path.join(root, 'desktop', 'runtime-pins.json'), 'utf8'));
const cache = path.join(root, 'build-cache');
const system32 = path.join(process.env.SystemRoot || 'C:\\Windows', 'System32');
const TAR = path.join(system32, 'tar.exe');

function fail(message) {
  console.error(`[fetch-runtime] ${message}`);
  process.exit(1);
}

function sha256(file) {
  const hash = createHash('sha256');
  const fd = fs.openSync(file, 'r');
  try {
    const buffer = Buffer.alloc(1 << 20);
    let read;
    while ((read = fs.readSync(fd, buffer, 0, buffer.length, null)) > 0) hash.update(buffer.subarray(0, read));
  } finally {
    fs.closeSync(fd);
  }
  return hash.digest('hex');
}

function download(url, destination, redirects = 0) {
  return new Promise((resolve, reject) => {
    if (!url.startsWith('https://')) return reject(new Error(`Refusing non-HTTPS URL ${url}`));
    if (redirects > 5) return reject(new Error('Too many redirects'));
    const request = https.get(url, { headers: { 'User-Agent': 'books-arranger-build' } }, (response) => {
      if ([301, 302, 303, 307, 308].includes(response.statusCode) && response.headers.location) {
        response.resume();
        resolve(download(new URL(response.headers.location, url).toString(), destination, redirects + 1));
        return;
      }
      if (response.statusCode !== 200) {
        response.resume();
        reject(new Error(`HTTP ${response.statusCode} for ${url}`));
        return;
      }
      const out = fs.createWriteStream(destination, { flags: 'wx' });
      response.pipe(out);
      out.on('finish', () => out.close(resolve));
      out.on('error', reject);
      response.on('error', reject);
    });
    request.setTimeout(120000, () => request.destroy(new Error('Download timed out')));
    request.on('error', reject);
  });
}

async function fetchPinned(name, pin) {
  const folder = path.join(cache, 'downloads', `${name}-${pin.version}`);
  const file = path.join(folder, pin.file);
  fs.mkdirSync(folder, { recursive: true });
  if (fs.existsSync(file)) {
    const actual = sha256(file);
    if (actual === pin.sha256) {
      console.log(`[fetch-runtime] ${pin.file}: cached, SHA-256 verified`);
      return file;
    }
    fail(`${file} exists with SHA-256 ${actual}, expected ${pin.sha256}. Inspect it; nothing was replaced.`);
  }
  const partial = `${file}.partial`;
  fs.rmSync(partial, { force: true });
  console.log(`[fetch-runtime] downloading ${pin.url}`);
  await download(pin.url, partial);
  const actual = sha256(partial);
  if (actual !== pin.sha256) {
    fs.rmSync(partial, { force: true });
    fail(`${pin.file}: SHA-256 ${actual} does not match the pin ${pin.sha256}. Download discarded.`);
  }
  fs.renameSync(partial, file);
  console.log(`[fetch-runtime] ${pin.file}: downloaded, SHA-256 verified`);
  return file;
}

function extract(name, version, archive) {
  const target = path.join(cache, 'extract', `${name}-${version}`);
  fs.rmSync(target, { recursive: true, force: true });
  fs.mkdirSync(target, { recursive: true });
  const result = spawnSync(TAR, ['-xf', archive, '-C', target], { cwd: root, stdio: 'inherit', windowsHide: true });
  if (result.status !== 0) fail(`Could not extract ${archive} (tar exit ${result.status})`);
  return target;
}

function freshDir(dir) {
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function run(file, args) {
  const result = spawnSync(file, args, { cwd: root, encoding: 'utf8', windowsHide: true,
    env: { SystemRoot: process.env.SystemRoot, PATH: system32, NoDefaultCurrentDirectoryInExePath: '1' } });
  if (result.status !== 0) fail(`${path.basename(file)} ${args.join(' ')} failed (exit ${result.status}): ${result.stderr}`);
  return result.stdout;
}

async function main() {
  // Python: the whole embeddable package is the runtime.
  const pythonZip = await fetchPinned('python', pins.python);
  const pythonExtract = extract('python', pins.python.version, pythonZip);
  const pythonRuntime = freshDir(path.join(cache, 'runtime', 'python'));
  fs.cpSync(pythonExtract, pythonRuntime, { recursive: true });
  const pythonExe = path.join(pythonRuntime, 'python.exe');
  const probe = run(pythonExe, ['-I', '-B', '-c',
    'import sys,sqlite3,ctypes,ssl,hashlib,zlib,json,http.server,msvcrt;print(sys.version.split()[0],sqlite3.sqlite_version)']);
  if (!probe.startsWith(pins.python.version + ' ')) fail(`Staged Python reports ${probe.trim()}, expected ${pins.python.version}`);
  console.log(`[fetch-runtime] staged Python ${probe.trim()} (SQLite)`);

  // FFmpeg: only the two executables, their shared libraries and the license.
  const ffmpegZip = await fetchPinned('ffmpeg', pins.ffmpeg);
  const ffmpegExtract = extract('ffmpeg', pins.ffmpeg.version, ffmpegZip);
  const top = fs.readdirSync(ffmpegExtract).filter((n) => fs.statSync(path.join(ffmpegExtract, n)).isDirectory());
  if (top.length !== 1) fail('Unexpected FFmpeg archive layout');
  const unpacked = path.join(ffmpegExtract, top[0]);
  const ffmpegRuntime = freshDir(path.join(cache, 'runtime', 'ffmpeg'));
  const bin = path.join(unpacked, 'bin');
  for (const name of fs.readdirSync(bin)) {
    if (name === 'ffmpeg.exe' || name === 'ffprobe.exe' || name.toLowerCase().endsWith('.dll')) {
      fs.copyFileSync(path.join(bin, name), path.join(ffmpegRuntime, name));
    }
  }
  fs.copyFileSync(path.join(unpacked, 'LICENSE.txt'), path.join(ffmpegRuntime, 'LICENSE.txt'));
  const ffmpegExe = path.join(ffmpegRuntime, 'ffmpeg.exe');
  const ffprobeExe = path.join(ffmpegRuntime, 'ffprobe.exe');
  const version = run(ffmpegExe, ['-hide_banner', '-version']);
  run(ffprobeExe, ['-hide_banner', '-version']);
  const config = (version.match(/^configuration: (.*)$/m) || [])[1] || '';
  if (/--enable-gpl\b/.test(config) || /--enable-nonfree\b/.test(config)) fail('FFmpeg build is not an LGPL build (GPL or nonfree enabled)');
  const license = run(ffmpegExe, ['-hide_banner', '-L']).trim();
  fs.writeFileSync(path.join(ffmpegRuntime, 'BUILD.txt'), [
    `Books Arranger bundles this FFmpeg build unmodified.`,
    `Build: ${pins.ffmpeg.build}`,
    `Archive: ${pins.ffmpeg.url}`,
    `Archive SHA-256: ${pins.ffmpeg.sha256}`,
    `Corresponding source: ${pins.ffmpeg.source} (build scripts: https://github.com/BtbN/FFmpeg-Builds)`,
    '',
    version.trim(),
    '',
    license,
    '',
  ].join('\r\n'));
  console.log(`[fetch-runtime] staged FFmpeg ${version.split('\n')[0].trim()}`);
  console.log(`[fetch-runtime] license: ${license.split('\n')[0].trim()}`);
}

main().catch((error) => fail(error.message));
