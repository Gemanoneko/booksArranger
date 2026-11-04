import fs from 'node:fs';
import path from 'node:path';
import { execFile } from 'node:child_process';

const root = 'C:/Antigravity Projects/q';
const startedAt = new Date().toISOString();
const file = 'C:/Program Files/nodejs/node.exe';
const args = [
  'C:/Antigravity Projects/Studio Illuminati/.claude/skills/qa-handoff/scripts/run_entry_checks.mjs',
  '--context', `${root}/context/context.json`,
  '--context-sha', '15b078673e26249f600de676bedf5c48f0253e9327fda48faef4b8209a6ad441',
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
    BOOKS_MP3_REAL_FIXTURE: 'C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/build-cache/qa-fixtures/ba-mp3-fixture/fixture.mp3',
  },
  windowsHide: true,
  timeout: 930000,
  maxBuffer: 67108864,
  encoding: 'utf8',
};
const invocation = { file, args, options, source_head: 'f6553e7b78bf9d7f011b5728b2d219ad48732add', build_id: '27b521b3-3d89-40b6-889b-5350d862d08e', context_sha256: args[4], entry_deadline_ms: 900000, transport_eof_only_ms: 930000, artifact_manifest_sha256: 'a44358f11c9fb7284ec07d1351867808f262edf5c7ab1d87494fbd4f6070c657', runtime_pointer_sha256: '58a6e6a326194d8712afdf34e98a70f99909bfec93a4d1edabbc9853333b58e9' };
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
