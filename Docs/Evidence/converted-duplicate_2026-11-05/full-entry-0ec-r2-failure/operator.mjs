import fs from 'node:fs';
import path from 'node:path';
import { execFile } from 'node:child_process';

const root = 'C:/Antigravity Projects/q3';
const startedAt = new Date().toISOString();
const file = 'C:/Program Files/nodejs/node.exe';
const args = [
  'C:/Antigravity Projects/Studio Illuminati/.claude/skills/qa-handoff/scripts/run_entry_checks.mjs',
  '--context', `${root}/context/context.json`,
  '--context-sha', 'fb3181e4c169835a8e083608b048c0e9d5b0cc2dc5ad7411bb34b58ae7b12179',
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
const invocation = { file, args, options, source_head: '0ec4971169a70d57a407ae1a9ef6bf96227724d4', build_id: '140014b8-b350-4a3e-a99b-05d24349f139', context_sha256: args[4], entry_deadline_ms: 900000, transport_eof_only_ms: 930000, artifact_manifest_sha256: '8f055521103f91f9417331091b971c423f7da483980364ee7a020016c99a9ca9', runtime_pointer_sha256: 'fe2e42723bbf6c5f7bfec0ad7d77b84255907a363ecf4d2c612ce432e61ec130' };
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
