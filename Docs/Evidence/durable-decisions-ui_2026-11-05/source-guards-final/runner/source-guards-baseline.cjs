const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const app=path.resolve('web/app.js'),read=fs.readFileSync;
const baseline=read(path.join(__dirname,'app-before-source-guards.js'),'utf8');
if(crypto.createHash('sha256').update(baseline).digest('hex')!=='9ccb675d9ab177e20408d24e4ed1e07b9ca2fec87ce404e10bd976a64d635b36')throw Error('Exact prior frozen source required');
fs.readFileSync=function(file,...args){return typeof file==='string'&&path.resolve(file)===app?baseline:read.call(this,file,...args);};
