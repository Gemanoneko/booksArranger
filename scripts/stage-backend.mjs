#!/usr/bin/env node
// Stages the Python backend for packaging into build-cache/backend:
// every top-level runtime module, the browser assets and the runtime data files,
// plus a VERSION file generated from package.json (the single version source).
// Bytecode is precompiled with the bundled Python so a read-only install never
// needs to write __pycache__. Run after scripts/fetch-runtime.mjs.

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const target = path.join(root, 'build-cache', 'backend');
const python = path.join(root, 'build-cache', 'runtime', 'python', 'python.exe');
const system32 = path.join(process.env.SystemRoot || 'C:\\Windows', 'System32');

// Source-checkout launchers (Tk window, Start-menu entries) are not part of the desktop app.
const EXCLUDED = new Set(['app.py', 'install_app_entries.py']);
const DATA_FILES = ['public_source_leads.json', 'replacement_eye_plan.json'];

function fail(message) {
  console.error(`[stage-backend] ${message}`);
  process.exit(1);
}

if (!fs.existsSync(python)) fail('Bundled Python is missing. Run: node scripts/fetch-runtime.mjs');
const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
if (typeof pkg.version !== 'string' || !/^\d+\.\d+\.\d+$/.test(pkg.version)) fail('package.json has no x.y.z version');

fs.rmSync(target, { recursive: true, force: true });
fs.mkdirSync(path.join(target, 'web'), { recursive: true });

const modules = fs.readdirSync(root).filter((name) => name.endsWith('.py') && !EXCLUDED.has(name)
  && fs.statSync(path.join(root, name)).isFile());
for (const name of modules) fs.copyFileSync(path.join(root, name), path.join(target, name));
for (const name of DATA_FILES) fs.copyFileSync(path.join(root, name), path.join(target, name)); // byte-exact
for (const name of fs.readdirSync(path.join(root, 'web'))) fs.copyFileSync(path.join(root, 'web', name), path.join(target, 'web', name));
fs.writeFileSync(path.join(target, 'VERSION'), `${pkg.version}\n`);

// The bundled interpreter checks the staged code imports cleanly without Tkinter.
const env = { SystemRoot: process.env.SystemRoot, PATH: system32, NoDefaultCurrentDirectoryInExePath: '1' };
const compile = spawnSync(python, ['-I', '-m', 'compileall', '-q', '-j', '0', '--invalidation-mode', 'unchecked-hash', target],
  { cwd: root, encoding: 'utf8', windowsHide: true, env });
if (compile.status !== 0) fail(`Bytecode compilation failed: ${compile.stdout}${compile.stderr}`);
const probe = spawnSync(python, ['-I', '-c',
  'import sys;sys.path.insert(0,sys.argv[1]);import desktop_backend,web_server;print(web_server.version())', target],
  { cwd: root, encoding: 'utf8', windowsHide: true, env });
if (probe.status !== 0 || probe.stdout.trim() !== pkg.version) fail(`Staged backend import check failed: ${probe.stdout}${probe.stderr}`);
console.log(`[stage-backend] ${modules.length} modules + web assets staged, version ${pkg.version}, imports OK on bundled Python`);
