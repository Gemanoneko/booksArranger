import fs from 'node:fs';
import path from 'node:path';
import { execFile } from 'node:child_process';

const root = 'C:/Antigravity Projects/q26';
const startedAt = new Date().toISOString();
const file = 'C:/Program Files/nodejs/node.exe';
const args = [
  'C:/Antigravity Projects/Studio Illuminati/.claude/skills/qa-handoff/scripts/run_entry_checks.mjs',
  '--context', `${root}/context/context.json`,
  '--context-sha', 'c9a979022a33967c5e29535c3b242f0df5af7a72bd249277bb07f6e769853365',
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
    BOOKS_MP3_REAL_FIXTURE: 'C:/Antigravity Projects/q26/media/private.mp3',
  },
  windowsHide: true,
  timeout: 930000,
  maxBuffer: 67108864,
  encoding: 'utf8',
};
const invocation = { file, args, options, source_head: 'd6753c69ae01468693d8c77964893b1e259c9190', build_id: '7e1ce2b4-e87b-43c5-b2c1-cc5cd798c1e9', context_sha256: args[4], entry_deadline_ms: 900000, transport_eof_only_ms: 930000, artifact_manifest_sha256: '137258122f81fe9c365bbc11a7d5265c9b22354d46d6f0034b12a6baf84e125b', runtime_pointer_sha256: '04bcb999b14343f36f9e8932cb6b0d32253feb7270c4de7d15cc5019a32d28d0' };
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
