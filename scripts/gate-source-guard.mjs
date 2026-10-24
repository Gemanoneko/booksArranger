// The gate's source root must not be a live checkout. check-desktop.mjs copies every top-level folder of its root
// (except scratch, node_modules, .git, dist, build-cache) into each Python worker, and runs its node and frontend
// checks with that root as the working folder. A checkout that holds data/ is a live one: data/inventory.sqlite3 is
// the catalog app.py, app_launcher.py and the browser launch open there. On 2026-10-24 a gate run in the main
// checkout copied that live catalog into its workers. The gate now refuses before it touches anything.
// Any data entry counts (folder, file or link), empty or not: refusing costs a worktree, copying costs the catalog.
import fs from 'node:fs';import path from 'node:path';

export function liveCatalogRefusal(root){
 const data=path.join(root,'data');
 try{fs.lstatSync(data);}
 catch(error){if(error.code==='ENOENT')return null;throw error;}  // unreadable: fail closed with the real error
 return 'Refusing to run the gate: '+data+' exists, so '+root+' is a live checkout (its catalog is data'+path.sep+'inventory.sqlite3), '+
  'and the gate would copy it into every worker. Nothing was copied or written. Run the gate in a separate worktree '+
  'without data'+path.sep+', for example: git worktree add --detach "C:/Antigravity Projects/Worktrees/Books Arranger/<purpose>" HEAD';
}
