// Engineering lookup only. Never changes a user/library/native runtime path.
import fs from 'node:fs';
import path from 'node:path';
export function studioRoot(from,{explicit=process.env.BOOKS_STUDIO_ROOT}={}){
  const recognize=root=>fs.existsSync(path.join(root,'Team','Docs','ProcessRules.md'))&&
    fs.existsSync(path.join(root,'.claude','skills','qa-handoff','scripts','run_entry_checks.mjs'));
  if(explicit!==undefined){
    if(!path.isAbsolute(explicit))throw Error('BOOKS_STUDIO_ROOT must be an absolute path');
    const physical=fs.realpathSync.native(explicit);
    if(!recognize(physical))throw Error('Configured studio root is unavailable or unrecognized');
    return physical;
  }
  let current=fs.realpathSync.native(from);
  if(!fs.statSync(current).isDirectory())current=path.dirname(current);
  while(true){if(recognize(current))return current;const parent=path.dirname(current);if(parent===current)break;current=parent;}
  throw Error('Studio root was not found. Provide BOOKS_STUDIO_ROOT or the explicit checker path for this independent checkout.');
}
