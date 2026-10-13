'use strict';
const api=window.booksDesktop;const folder=document.querySelector('#folder');const accept=document.querySelector('#accept');const error=document.querySelector('#error');let defaultFolder='',existingFolder='';
function mode(){return document.querySelector('[name=mode]:checked').value;}
function render(){folder.value=mode()==='new'?defaultFolder:existingFolder;accept.textContent=mode()==='new'?'Create catalog':'Use this folder';accept.disabled=!folder.value;document.querySelector('#help').textContent=mode()==='new'?'Choose an empty folder. A new catalog starts Paused.':'Select the folder containing inventory.sqlite3.';error.textContent='';}
api.setup().then(value=>{defaultFolder=value.defaultFolder;render();}).catch(e=>error.textContent=e.message);
document.querySelectorAll('[name=mode]').forEach(input=>input.addEventListener('change',render));
document.querySelector('#browse').addEventListener('click',async()=>{const value=await api.browse();if(value){if(mode()==='new')defaultFolder=value;else existingFolder=value;render();}});
accept.addEventListener('click',async()=>{accept.disabled=true;error.textContent='Checking data folder…';try{await api.select({folder:folder.value,mode:mode()});}catch(e){error.textContent=e.message;accept.disabled=false;}});
document.querySelector('#cancel').addEventListener('click',()=>api.quit());
