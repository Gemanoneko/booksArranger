import fs from 'node:fs';
import path from 'node:path';
import { execFile } from 'node:child_process';

const root = 'C:/Antigravity Projects/q';
const startedAt = new Date().toISOString();
const file = 'C:/Program Files/nodejs/node.exe';
const args = [
  'C:/Antigravity Projects/Studio Illuminati/.claude/skills/qa-handoff/scripts/run_entry_checks.mjs',
  '--context', `${root}/context/context.json`,
  '--context-sha', 'd69afc8c0240ea4a80ac8353f0a2ff6db7775f6b135090d6e35b4128ec0cc0f3',
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
const invocation = { file, args, options, source_head: 'cc5ea7f9deb3b2843cb75b1392e24314532a0f2a', build_id: '3369d944-a8e3-4513-a758-5e006309cf9b', context_sha256: args[4], entry_deadline_ms: 900000, transport_eof_only_ms: 930000, artifact_manifest_sha256: '233f2a17919e596a63a16a7661df7ce2c5972b65a84f8c1823aeaacee9a8c1dc', runtime_pointer_sha256: 'f93162afd9dcfaacdfc7cd68c2267028c713b441ac97ea91c8419e0cc9b8a20a' };
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
