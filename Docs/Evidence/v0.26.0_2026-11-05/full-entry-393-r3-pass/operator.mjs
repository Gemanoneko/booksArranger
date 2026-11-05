import fs from 'node:fs';
import path from 'node:path';
import { execFile } from 'node:child_process';

const root = 'C:/Antigravity Projects/q28';
const startedAt = new Date().toISOString();
const file = 'C:/Program Files/nodejs/node.exe';
const args = [
  'C:/Antigravity Projects/Studio Illuminati/.claude/skills/qa-handoff/scripts/run_entry_checks.mjs',
  '--context', `${root}/context/context.json`,
  '--context-sha', '3181ef027e64c0af6ce8746dd0d5ee3d1df3d78a795ec03edb9c371512abd267',
  '--run-root', root,
];
const options = {
  cwd: 'C:/Antigravity Projects/Studio Illuminati',
  env: {
    SystemRoot: 'C:\\Windows',
    WINDIR: 'C:\\Windows',
    PATH: 'C:/Program Files/nodejs;C:/Program Files/Git/cmd;C:/Windows/System32',
    TEMP: `${root}/t`,
    TMP: `${root}/t`,
    TMPDIR: `${root}/t`,
    USERPROFILE: `${root}/profile`,
    APPDATA: `${root}/profile/AppData/Roaming`,
    LOCALAPPDATA: `${root}/profile/AppData/Local`,
    GIT_OPTIONAL_LOCKS: '0',
    NODE_OPTIONS: '',
    NODE_PATH: '',
    BOOKS_QA_RUNTIME_ROOT: 'C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/build-cache/qa-runtime',
    BOOKS_MP3_REAL_FIXTURE: 'C:/Antigravity Projects/q28/media/private.mp3',
  },
  windowsHide: true,
  timeout: 930000,
  maxBuffer: 67108864,
  encoding: 'utf8',
};
const invocation = { file, args, options, source_head: '3932155e9f3ceac00632d2d82a4e91315f7c832f', build_id: '82b4dac4-0aad-453a-a013-d3486cc431eb', context_sha256: args[4], entry_deadline_ms: 900000, transport_eof_only_ms: 930000, artifact_manifest_sha256: '8d170ee68ad1e5cccca5be024cf23aaa0893c4b12b4c8ebdfb1dbd9a4086574f', runtime_pointer_sha256: 'fe93797d34dece7d0bef2426f9e6bffa028ba78b0be5c7e418200c3ce041ca77' };
fs.writeFileSync(path.join(root, 'invocation.json'), `${JSON.stringify(invocation, null, 2)}\n`, { flag: 'wx' });
const child = execFile(file, args, options, (error, stdout, stderr) => {
  const finishedAt = new Date().toISOString();
  fs.writeFileSync(path.join(root, 'outer-stdout.log'), stdout, { flag: 'wx' });
  fs.writeFileSync(path.join(root, 'outer-stderr.log'), stderr, { flag: 'wx' });
  const result = {
    started_at: startedAt,
    finished_at: finishedAt,
    pid: child.pid,
    error: error ? { message: error.message, code: error.code ?? null, signal: error.signal ?? null, killed: error.killed ?? false } : null,
    exit_code: error ? (typeof error.code === 'number' ? error.code : null) : 0,
  };
  fs.writeFileSync(path.join(root, 'outer-result.json'), `${JSON.stringify(result, null, 2)}\n`, { flag: 'wx' });
  process.exitCode = result.exit_code ?? 1;
});
