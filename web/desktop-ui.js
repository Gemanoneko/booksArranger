'use strict';
(()=>{const api=window.booksDesktop;if(!api)return;
 const header=document.querySelector('header');const toolbar=document.querySelector('#shutdown')?.parentElement;
 const hint=document.createElement('p');hint.className='field-help';hint.textContent='Closing this window keeps Books Arranger running in the tray. Choose Quit Books Arranger to close the app.';header.after(hint);
 const quit=document.querySelector('#shutdown');if(quit){quit.textContent='Quit Books Arranger';quit.title='Finish the current book and cleanup, keep queued books, then close the app';quit.addEventListener('click',event=>{event.preventDefault();event.stopImmediatePropagation();api.quit().catch(showError);},true);}
 const panel=document.createElement('section');panel.className='panel desktop-status';panel.hidden=true;panel.setAttribute('aria-label','Desktop status');const phase=document.createElement('p');phase.setAttribute('role','status');phase.setAttribute('aria-live','polite');panel.append(phase);hint.after(panel);
 const update=document.createElement('section');update.className='panel desktop-update';update.setAttribute('aria-label','App updates');const text=document.createElement('p');text.setAttribute('aria-live','polite');const actions=document.createElement('div');actions.className='toolbar';update.append(text,actions);panel.after(update);
 function button(label,fn){const b=document.createElement('button');b.type='button';b.textContent=label;b.title=label;b.addEventListener('click',()=>fn().catch(showError));actions.append(b);return b;}
 const check=button('Check for updates',()=>api.checkUpdates());const download=button('Download update',()=>api.downloadUpdate());const restart=button('Restart to update',()=>api.installUpdate());
 function showError(error){text.textContent=String(error.message||error);}
 const mutating=['start-automatic','stop-automatic','start','stop','resume','pause-jobs','resume-jobs','queue-books','find-metadata','find-covers','approve-candidate','save-tracks','create-audiobook','recovery-confirm','retry-job','retry-all','retry-all-go'];
 function render(value){
  const desktop=value.desktop||{};const quitting=value.quit!=='none'||(desktop.phase&&desktop.phase!=='running');
  panel.hidden=!quitting;phase.textContent=desktop.error||({finishing:'Finishing the current book and cleanup…',parking:'Parking pending work…',updating:'Parking the idle engine for update…',blocked:'Quit blocked; ownership remains held.'}[desktop.phase]||'Waiting for the engine checkpoint…');
  if(quitting){for(const id of mutating){const node=document.getElementById(id);if(node)node.disabled=true;}document.querySelector('#review-form button[type=submit]')?.setAttribute('disabled','');}
  const u=value.update||{phase:'idle'};check.disabled=quitting||['checking','downloading','installing'].includes(u.phase);download.hidden=u.phase!=='available';restart.hidden=!u.ready||quitting;restart.disabled=!desktop.idle;restart.title=desktop.idle?'Restart to update':'Wait until scanning, research, publication, cleanup and recovery are idle';
  text.textContent=u.error||({idle:'Check for app updates.',checking:'Checking for updates…',current:'Books Arranger is up to date.',available:'Version '+u.version+' is available.',downloading:'Downloading update… '+Math.round(u.progress)+'%',ready:desktop.idle?'Version '+u.version+' is ready to install.':'Version '+u.version+' is ready. It can install when all work is idle.',installing:'Starting the verified installer…',error:'Update failed. Check for updates to retry.'}[u.phase]||'');
 }
 let polling=false;async function poll(){if(polling)return;polling=true;try{render(await api.status());}catch(e){showError(e);}finally{polling=false;}}
 api.onStatus(()=>poll());setInterval(poll,1000);poll();
})();
