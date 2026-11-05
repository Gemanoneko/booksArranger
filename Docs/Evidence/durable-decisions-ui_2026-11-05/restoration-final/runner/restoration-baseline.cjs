const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const app=path.resolve('web/app.js'),read=fs.readFileSync;
const baseline=read(path.join(__dirname,'app-before-restoration-guard.js'),'utf8');
if(crypto.createHash('sha256').update(baseline).digest('hex')!=='a6aa6ecb5ee6e43cf372f42d602f40eca8f60cf69baac0da03d133d63a9bd1c2')throw Error('Exact prior frozen source required');
fs.readFileSync=function(file,...args){return typeof file==='string'&&path.resolve(file)===app?baseline:read.call(this,file,...args);};
