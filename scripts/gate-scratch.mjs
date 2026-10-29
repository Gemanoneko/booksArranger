// The gate's own scratch (2026-10-29). check-desktop.mjs makes one source copy per Python worker at <root>/scratch/<i>
// (each holding its own scratch/tmp TEMP and scratch/f fixtures), plus <root>/scratch/source-fallback-2026-10-11, and its
// side chain points BOOKS_QA_FIXTURE_ROOT at <root>/scratch/f. Every run used to leave all of that behind (13 worker
// copies), and the next run in the same root then refused at scratch/0 ("fresh or refuse"). Now the gate removes what it
// made when it ends, pass or fail. On a failure it keeps only the copies the failure names as its evidence (a worker whose
// source copy differs from the gate inputs) and says so in its output.
// Only entries this run created are claimed: anything already in <root>/scratch before the run (retained proofs, an
// earlier run's kept evidence) is never touched. Links inside a claimed entry are unlinked, never followed.
import fs from 'node:fs';import path from 'node:path';

const present=p=>{try{fs.lstatSync(p);return true;}catch{return false;}};

// Remove one claimed entry: every link in it is removed as a link first (its target is never entered), then Node's own
// recursive removal. Returns null when it is gone, else why it is still there.
export function removeGateEntry(root){
 let top;try{top=fs.lstatSync(root);}catch{return null;}
 if(top.isSymbolicLink()){try{fs.rmdirSync(root);}catch{try{fs.unlinkSync(root);}catch(error){return 'could not unlink '+root+' ('+error.code+')';}}return present(root)?'link still present':null;}
 const links=[],stack=top.isDirectory()?[root]:[];
 while(stack.length){
  const dir=stack.pop();let entries;
  try{entries=fs.readdirSync(dir,{withFileTypes:true});}catch(error){return 'unreadable '+dir+' ('+(error.code||error.message)+')';}
  for(const entry of entries){const p=path.join(dir,entry.name);let st;try{st=fs.lstatSync(p);}catch{continue;}if(entry.isSymbolicLink()||st.isSymbolicLink())links.push(p);else if(st.isDirectory())stack.push(p);}
 }
 for(const link of links){try{fs.rmdirSync(link);}catch{try{fs.unlinkSync(link);}catch(error){return 'could not unlink '+link+' ('+error.code+')';}}}
 try{fs.rmSync(root,{recursive:true,force:true,maxRetries:5,retryDelay:200});}catch(error){return (error.code||error.message)+', a file in it may still be in use';}
 return present(root)?'still present after removal':null;
}

export function trackGateScratch(root){
 const dir=path.join(root,'scratch'),before=new Set();let existed=true;
 try{for(const name of fs.readdirSync(dir))before.add(name.toLowerCase());}catch(error){if(error.code!=='ENOENT')throw error;existed=false;}
 const owned=new Map();
 const nameOf=relative=>{const m=/^scratch\/([^/\\]+)$/.exec(relative);if(!m||m[1]==='.'||m[1]==='..')throw Error('A gate scratch entry is scratch/<name>: '+relative);return m[1];};
 return {
  dir,
  // Register an entry this run is about to make; returns its absolute path. One that was there before is not claimed.
  claim(relative){const name=nameOf(relative);if(!before.has(name.toLowerCase())&&!owned.has(name))owned.set(name,{name,evidence:null});return path.join(dir,name);},
  // Mark a claimed entry as the evidence a failure points to: it stays when the run fails.
  evidence(relative,why){const o=owned.get(nameOf(relative));if(o)o.evidence=why;},
  finish(failed){
   const removed=[],kept=[],left=[];
   for(const o of owned.values()){
    const p=path.join(dir,o.name);
    if(!present(p))continue;
    if(failed&&o.evidence){kept.push(o);continue;}
    const why=removeGateEntry(p);
    if(why)left.push({...o,why});else removed.push(o);
   }
   let removedDir=false;
   if(!existed&&present(dir)){try{if(!fs.readdirSync(dir).length){fs.rmdirSync(dir);removedDir=true;}}catch{/* kept */}}
   const lines=[];
   if(removed.length)lines.push('Gate scratch removed: '+removed.map(o=>'scratch/'+o.name).join(', ')+(removedDir?', then the empty scratch folder':''));
   for(const o of kept)lines.push('Gate scratch kept as the evidence this failure names: '+path.join(dir,o.name)+' ('+o.evidence+'). Read it, then delete it: the next gate run in this folder refuses while it is there.');
   for(const o of left)lines.push('Gate scratch NOT removed: '+path.join(dir,o.name)+' ('+o.why+')');
   return {removed:removed.map(o=>o.name),kept:kept.map(o=>({name:o.name,evidence:o.evidence})),left:left.map(o=>({name:o.name,why:o.why})),removedDir,lines};
  },
 };
}
