#!/usr/bin/env node
// Empties dist/ before a build so old installers don't accumulate.
// electron-builder does NOT clean its output dir between runs, and each
// Windows NSIS installer is 100+ MB, so stale builds pile up quickly.
// Uses only native Node (fs.rmSync) to keep the tool dependency-free.

const fs   = require('fs');
const path = require('path');

const distDir = path.join(__dirname, '..', 'dist');

try {
  fs.rmSync(distDir, { recursive: true, force: true });
  console.log(`clean-dist: removed ${distDir}`);
} catch (err) {
  // force:true already swallows ENOENT; anything else is a real problem.
  console.error(`clean-dist: failed to remove ${distDir}:`, err.message);
  process.exit(1);
}
