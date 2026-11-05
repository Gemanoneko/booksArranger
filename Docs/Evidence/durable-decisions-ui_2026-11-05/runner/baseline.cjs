const fs=require('node:fs'),path=require('node:path'),{execFileSync}=require('node:child_process');
const app=path.resolve('web/app.js'),read=fs.readFileSync;
const baseline=execFileSync('git',['show','9bcc58b5876e0ad2e6de8e4de39597f2bb9b7ac5:web/app.js'],{encoding:'utf8',windowsHide:true,maxBuffer:4*1024*1024});
fs.readFileSync=function(file,...args){return typeof file==='string'&&path.resolve(file)===app?baseline:read.call(this,file,...args);};
