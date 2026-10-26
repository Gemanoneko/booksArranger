'use strict';
const api=window.booksDesktop;const folder=document.querySelector('#folder');const accept=document.querySelector('#accept');const error=document.querySelector('#error');let defaultFolder='',existingFolder='',checking=false;
// Futaba's 0.22.1 QA, m-10: Electron prefixes a refused IPC call ("Error invoking remote method 'books:select': Error: ");
// the form shows only the sentence the shell refused it with.
function plain(e){return String((e&&e.message)||e||'').replace(/^Error invoking remote method '[^']*': (?:[A-Za-z]*Error: )?/,'');}
function mode(){return document.querySelector('[name=mode]:checked').value;}
// Judy 0.22.2 section 7: every control has its tooltip; with no folder, and while the folder is checked, the main button is
// aria-disabled (never disabled), so focus stays on it.
const TIPS={'#existing-label':'Use a catalog you already have. Its files stay where they are.','#new-label':'Start an empty catalog in the folder below.',
  '#folder':'The folder that holds the catalog. Press Browse… to change it.','#browse':'Choose the data folder.','#cancel':'Close without choosing a folder. Books Arranger closes.'};
for(const [selector,tip] of Object.entries(TIPS)){const node=document.querySelector(selector);if(node)node.title=tip;}
function inert(){return checking||!folder.value;}
function face(){
  accept.textContent=mode()==='new'?'Create catalog':'Use this folder';
  accept.setAttribute('aria-disabled',inert()?'true':'false');
  accept.title=checking?'Checking the data folder…':!folder.value?'Choose a data folder first.':mode()==='new'?'Check this folder and create an empty catalog in it.':'Check this folder and open its catalog.';
}
function render(){folder.value=mode()==='new'?defaultFolder:existingFolder;document.querySelector('#help').textContent=mode()==='new'?'Choose an empty folder. A new catalog starts Paused.':'Select the folder containing inventory.sqlite3.';error.textContent='';face();}
api.setup().then(value=>{defaultFolder=value.defaultFolder;render();}).catch(e=>error.textContent=plain(e));
document.querySelectorAll('[name=mode]').forEach(input=>input.addEventListener('change',render));
document.querySelector('#browse').addEventListener('click',async()=>{const value=await api.browse();if(value){if(mode()==='new')defaultFolder=value;else existingFolder=value;render();}});
accept.addEventListener('click',async()=>{if(inert())return;checking=true;face();error.textContent='Checking data folder…';
  try{await api.select({folder:folder.value,mode:mode()});}catch(e){error.textContent=plain(e);}finally{checking=false;face();}});
document.querySelector('#cancel').addEventListener('click',()=>api.quit());
face();
