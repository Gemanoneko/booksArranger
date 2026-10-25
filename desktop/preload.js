'use strict';
const {contextBridge,ipcRenderer}=require('electron');
contextBridge.exposeInMainWorld('booksDesktop',Object.freeze({
 setup:()=>ipcRenderer.invoke('books:setup'),
 browse:()=>ipcRenderer.invoke('books:browse'),
 select:(choice)=>ipcRenderer.invoke('books:select',choice),
 quit:()=>ipcRenderer.invoke('books:quit'),
 checkUpdates:()=>ipcRenderer.invoke('books:update-check'),
 downloadUpdate:()=>ipcRenderer.invoke('books:update-download'),
 installUpdate:()=>ipcRenderer.invoke('books:update-install'),
 cancelUpdate:()=>ipcRenderer.invoke('books:update-cancel'),
 showInstaller:()=>ipcRenderer.invoke('books:update-show-installer'),
 onRestartRequest:(fn)=>{if(typeof fn!=='function')return;ipcRenderer.on('books:update-restart',()=>fn());},
 status:()=>ipcRenderer.invoke('books:status'),
 onStatus:(fn)=>{if(typeof fn!=='function')return;ipcRenderer.on('books:status',(_event,value)=>fn(value));}
}));
