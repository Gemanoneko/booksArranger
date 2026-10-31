'use strict';
// Judy's 0.24.1 spec, section 8 item 1: wording that is no longer true never reaches the window again. Recovery copies are
// deleted straight after verification (ruling 74g), so nothing in the page or the desktop shell may promise a retention
// window. Reads every shipped page and shell file; a positive control proves the scan sees their text.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.join(__dirname,'..');
const files=['web','desktop'].flatMap(folder=>fs.readdirSync(path.join(root,folder)).filter(name=>/\.(js|html|css)$/.test(name)).map(name=>path.join(folder,name)));
// 74e (Judy section 5): a folder holding a cover is removed too, so no string may call the removed folders "empty".
const stale=[/24 hours/i,/overdue copies/i,/empty source folders/i];
let seen=0;
for(const file of files){
  const text=fs.readFileSync(path.join(root,file),'utf8');
  if(text.includes('Recovery copies'))seen++;
  for(const pattern of stale)assert.equal(pattern.test(text),false,`${file} still says ${pattern}`);
}
assert(files.includes(path.join('web','app.js')) && seen>0,'the scan reads the page that shows the Recovery copies panel');
console.log(`PASS no stale retention wording in ${files.length} page and shell files`);
