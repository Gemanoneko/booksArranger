'use strict';
(()=>{
 // ── App updates: strings and states (ruling 27; Judy's 0.22.1 UX spec, section 2). Pure, so the node tests read
 // them without a window; the shell sends typed causes only, never raw error text. ──
 const cap=s=>s?s[0].toUpperCase()+s.slice(1):s;
 function name(item){return {conversion:item.title?'the conversion of '+item.title:'the conversion',scan:'the library scan',research:'research',lookups:'background lookups',automatic:'automatic processing',approval:'an approval',cleanup:'a cleanup',press:'an action'}[item.kind]||'the running work';}
 function what(waiting){
  const names=[...new Set((waiting||[]).filter(item=>item.kind!=='critical').map(name))];
  if(!names.length)return 'the running work';
  const head=names.slice(0,2).join(' and ');return names.length>2?head+' and '+(names.length-2)+' more':head;
 }
 function checkLine(u){
  const c=u.check||{},n=c.version||u.available;
  switch(c.phase){
   case 'dev':return 'Updates work only in the installed app.';
   case 'checking':return 'Checking for updates…';
   case 'retrying':return `Checking for updates… no answer yet, trying again (try ${c.attempt} of 3).`;
   case 'current':return `Books Arranger ${u.version} is up to date (checked ${c.at}).`;
   case 'available':return `Version ${n} is available (checked ${c.at}).`;
   case 'failed':return {no_answer:`Couldn't check for updates: GitHub didn't answer after 3 tries (tried ${c.at}). Check your internet connection, then try again. Nothing changed.`,
    no_internet:`Couldn't check for updates: no internet connection (tried ${c.at}). Connect, then try again. Nothing changed.`,
    github_error:`Couldn't check for updates: GitHub returned an error, ${c.code} (tried ${c.at}). Try again later. Nothing changed.`}[c.cause]||`Couldn't check for updates (tried ${c.at}). Try again later. Nothing changed.`;
   default:return `Books Arranger ${u.version}. Not checked yet.`;
  }
 }
 function downloadLine(u){
  const d=u.download||{},n=u.available;
  if(d.phase==='downloading')return `Downloading version ${n}… ${Math.round(d.progress||0)}%`;
  if(d.phase==='failed')return {dropped:`Couldn't download version ${n}: the connection dropped (tried ${d.at}). Press Download update to try again.`,
   checksum:`Couldn't use the download: it failed its checksum check, so it was discarded (tried ${d.at}). Press Download update to try again.`,
   disk_full:`Couldn't download version ${n}: not enough disk space (tried ${d.at}). Free some space, then press Download update.`}[d.cause]||`Couldn't download version ${n} (tried ${d.at}). Press Download update to try again.`;
  return u.ready?`Version ${n} is downloaded and verified. Ready to install.`:'';
 }
 // Senua's 0.22.1 review, W3: what Cancel, the engine's bound or a failed close could not start again (the engine's
 // resume_problems, typed by the shell), in the pattern of Judy's failure lines: what happened, then what to do, with
 // the confirm's own words for each kind (2.4). "Running as before" only when everything started again.
 const RESTART={automatic:['automatic processing','Press Start automatic processing to continue.'],
  conversion:['the audiobook jobs','Press Resume audiobook jobs to continue.'],
  scan:['the library scan','Continue the scan with Resume scanning.'],
  lookups:['background lookups','Background lookups start again by themselves the next time Books Arranger opens.']};
 function notRestarted(problems){
  const kinds=[...new Set((problems||[]).map(item=>item&&item.kind).filter(kind=>RESTART[kind]))];
  if(!kinds.length)return '';
  const names=kinds.map(kind=>RESTART[kind][0]);
  const list=names.length>1?names.slice(0,-1).join(', ')+' and '+names[names.length-1]:names[0];
  return `${cap(list)} didn't start again. ${kinds.map(kind=>RESTART[kind][1]).join(' ')}`;
 }
 function installLine(u){
  const i=u.install||{},stopped=notRestarted(i.problems),asBefore=stopped||'Books Arranger is running as before.',also=stopped?stopped+' ':'';
  // Judy 12.4, offer 1: background lookups alone left nothing to press, so the Cancel line keeps its plain tint.
  const toPress=(i.problems||[]).some(item=>item&&RESTART[item.kind]&&item.kind!=='lookups');
  if(i.phase==='cancelled')return stopped?{text:`Update cancelled (tried ${i.at}). ${stopped}`,failed:toPress}:{text:'Update cancelled. Books Arranger is running as before.',failed:false};
  if(i.phase!=='failed')return {text:'',failed:false};
  // M2 (Judy's implementation check): no number; the engine gives up at 150 s and the shell at 180 s.
  // Judy 12.4, offer 2: when the engine has ended (installer_blocked, engine_*), a new engine leaves automatic
  // processing, the audiobook jobs and the scan stopped; the line names what was running, with the same tails.
  const line={bound:`Update cancelled: ${what(i.waiting)} did not stop in time (tried ${i.at}). ${asBefore} Press Restart to update to try again, or choose Quit Books Arranger in the tray, then run the installer.`,
   installer_blocked:`The installer couldn't start (tried ${i.at}). Windows or your antivirus may have blocked it. Books Arranger is running again on ${u.version}. ${also}Run the installer yourself:`,
   checksum:`Update cancelled: the downloaded installer is missing or doesn't match its checksum (tried ${i.at}). Check for updates, then download it again.`,
   verify_timeout:`Update cancelled: the downloaded installer couldn't be verified in time (tried ${i.at}). Press Restart to update to try again.`,
   engine_restart:`Books Arranger couldn't restart its engine (tried ${i.at}). Choose Quit Books Arranger in the tray, then open it again.${stopped?' '+stopped:''}`,
   engine_stuck:`Books Arranger couldn't restart its engine (tried ${i.at}). Choose Quit Books Arranger in the tray, then open it again.${stopped?' '+stopped:''}`,
   // N3: the engine died while stopping and was started again, so the loading strip is back up.
   engine_exit:`The engine stopped during the update and was started again (tried ${i.at}). It is loading now. ${also}Press Restart to update to try again.`}[i.cause]
   ||`Update cancelled (tried ${i.at}). ${asBefore} Press Restart to update to try again.`;
  return {text:line,failed:true,path:i.cause==='installer_blocked'?u.installerPath||'':''};
 }
 // The .desktop-status line while an update runs (2.5); the counter is separate, outside the live region.
 // Futaba's 0.22.1 QA, m-2 (Judy 0.22.2 6.2): Cancel is answered at the press; from 3 s the line names what is slow to
 // resume and the engine's bound for it; the counter is dropped.
 function cancellingLine(i,now){
  if(!(now-(Number(i.cancelAt)||now)>=3000))return {text:'Cancelling the update…',counter:''};
  const work=(i.resuming&&i.resuming.length?i.resuming:i.waiting||[]).filter(item=>item.kind!=='critical'),bound=Number(i.resumeSeconds)||25;
  if(!work.length)return {text:`Cancelling the update… The engine is resuming. This can take up to ${bound} s.`,counter:''};
  return {text:`Cancelling the update… ${cap(what(work))} ${new Set(work.map(name)).size>1?'are':'is'} slow to resume. This can take up to ${bound} s.`,counter:''};
 }
 function phaseLine(u,now=Date.now()){
  const i=u.install||{},critical=(i.critical||[])[0],work=(i.waiting||[]).filter(item=>item.kind!=='critical');
  const finishing={text:`Finishing ${critical} first, so nothing is left half-done. This takes a few seconds.`,counter:''};
  if(i.cancelling&&['starting','pausing','forcing'].includes(i.phase))return cancellingLine(i,now);
  switch(i.phase){
   case 'starting':return {text:'Starting the update…',counter:''};
   case 'pausing':if(critical)return finishing;if(!work.length)return {text:'Starting the update…',counter:''};
    return {text:`Stopping safely for the update. Waiting for ${what(work)} to reach a safe point…`,counter:`(${Math.floor(i.elapsed||0)} s of ${i.safe} s)`};
   case 'forcing':if(critical)return finishing;
    // N2: lookups start with the engine by themselves; there is nothing for Sergei to start again.
    if(work.length&&work.every(item=>item.kind==='lookups'))return {text:`Background lookups didn't reach a safe point in ${i.safe} s. Stopping them now; they continue by themselves after the update.`,counter:''};
    // Judy 0.22.2 6.3 (Futaba m-11): a stopped conversion comes back Paused, so it is continued with Resume audiobook jobs.
    return {text:`${cap(what(work))} didn't reach a safe point in ${i.safe} s. Stopping it now; ${work.length&&work.every(item=>item.kind==='conversion')?'continue it with Resume audiobook jobs':'start it again after the update'}.`,counter:''};
   case 'updating':return {text:'Stopping the engine now. Saved work is kept.',counter:''};
   case 'installing':return {text:`Installing ${u.available}… No installer window opens. Books Arranger reopens by itself and shows its loading progress.`,counter:''};
  }
  return null;
 }
 // What the confirm names (2.4): known only from a fresh engine answer; unknown work confirms too.
 function workLines(desktop){
  const busy=desktop&&desktop.busy;if(!busy)return {known:false,lines:[]};
  const lines=[];
  // Judy 0.22.2 6.3 (Futaba m-11): the job comes back Paused after an update, so the line says how to continue it.
  if(busy.converting)lines.push(`Converting ${busy.current_title||'the current book'}. It stops. Continue it with Resume audiobook jobs.`);
  const approvals=Number(busy.approvals)||0;
  if(approvals)lines.push(approvals===1?'An approval in progress stops, and the book is not approved. Press Approve again afterwards.':`${approvals} approvals in progress stop, and those books are not approved. Press Approve again afterwards.`);
  if(busy.scanning)lines.push('Scanning the library. It stops. Continue it with Resume scanning.');
  if(['Running','Stopping'].includes(busy.automatic))lines.push('Automatic processing stops. Press Start automatic processing to continue.');
  const queued=Array.isArray(desktop.queued_actions)?desktop.queued_actions.length:Number(desktop.queued_actions)||0;
  if(queued)lines.push(queued===1?'1 queued action is dropped. Press it again afterwards.':`${queued} queued actions are dropped. Press them again afterwards.`);
  return {known:true,lines};
 }
 function buttons(u,desktop){
  const b=u.busy||{},n=u.available,work=workLines(desktop),running=!work.known||work.lines.length>0;
  return {
   check:{face:b.check?'Checking…':'Check for updates',busy:!!(b.check||b.install),hidden:false,
    title:b.check?'Checking for updates…':b.install?'Updating Books Arranger…':'Ask GitHub whether a newer version is available. Nothing is downloaded.'},
   download:{face:b.download?`Downloading… ${Math.round((u.download||{}).progress||0)}%`:'Download update',busy:!!(b.download||b.install),hidden:!(b.download||n&&!u.ready&&u.packaged),
    title:b.download?`Downloading version ${n}…`:`Download version ${n} and verify it. Books Arranger isn't changed until you press Restart to update.`},
   restart:{face:b.install?'Updating…':'Restart to update',busy:!!(b.install||b.download),hidden:!u.ready,
    title:b.install?'Updating Books Arranger…':running?`Install version ${n} now. Running work stops safely and restarts afterwards. Your source files are not touched. You confirm first.`:`Install version ${n} now. Books Arranger closes, updates and reopens by itself. No installer window opens.`},
   // Judy 0.22.2 6.2: once pressed, Cancel stays on screen (inert, with its focus) until the engine answers.
   cancel:(u.install||{}).cancelling?{face:'Cancelling…',busy:true,hidden:false,title:'Cancelling can’t be stopped.'}
    :{face:'Cancel update',busy:false,hidden:!u.canCancel,title:'Stop the update. Books Arranger keeps running as before.'},
   installer:{face:'Show installer file',busy:false,hidden:!u.showInstaller,title:'Open the folder that holds the downloaded installer.'},
  };
 }
 // Startup (ruling 28; Judy 3.6): Restart to update waits for loading, unless loading is stuck or stopped (the shell's verdict).
 const NOT_YET_UPDATE='Not yet: Books Arranger is still loading. You can update when it finishes, or if loading gets stuck.';
 const QUIT_LOADING='Stop loading and close Books Arranger. Your files are not touched.',QUIT_NORMAL='Finish the current book and cleanup, keep queued books, then close the app';
 function loadingWaits(value){return !!value&&value.loaded===false&&!['stuck','stopped'].includes(value.verdict);}
 // M1 (Judy's implementation check): during an update the window's Quit is inert with its reason, never silent.
 const QUIT_UPDATE_CANCEL='An update is in progress. Press Cancel update first if you want to quit.',QUIT_UPDATE_INSTALL='Books Arranger is installing an update and reopens by itself.';
 // Judy 0.22.2 6.2: while cancelling, the installing sentence was wrong.
 const QUIT_UPDATE_CANCELLING='The update is being cancelled. Quit works when it finishes.';
 function quitBlock(value){const u=value&&value.update;if(!(u&&(u.busy||{}).install)&&!['updating','installing'].includes(value&&value.quit))return '';
  return u&&(u.install||{}).cancelling?QUIT_UPDATE_CANCELLING:u&&u.canCancel?QUIT_UPDATE_CANCEL:QUIT_UPDATE_INSTALL;}
 globalThis.booksUpdateText=Object.freeze({what,checkLine,downloadLine,installLine,phaseLine,workLines,buttons,loadingWaits,quitBlock,NOT_YET_UPDATE,QUIT_LOADING,QUIT_UPDATE_CANCEL,QUIT_UPDATE_INSTALL,QUIT_UPDATE_CANCELLING});

 const api=window.booksDesktop;if(!api)return;
 const header=document.querySelector('header');const toolbar=document.querySelector('#shutdown')?.parentElement;
 const hint=document.createElement('p');hint.className='field-help';hint.textContent='Closing this window keeps Books Arranger running in the tray. Choose Quit Books Arranger to close the app.';(document.getElementById('load-strip')||header).after(hint);  // the load strip sits directly under the header (Judy 3.3)
 const quit=document.querySelector('#shutdown');if(quit){quit.textContent='Quit Books Arranger';quit.title=QUIT_NORMAL;quit.addEventListener('click',event=>{event.preventDefault();event.stopImmediatePropagation();requestQuit();},true);}
 // A press during an update is answered in the message line; focus stays (M1, rule 3.6). A fresh status decides.
 async function requestQuit(){
  try{render(await api.status());}catch(error){console.warn(error);}  // the tooltip follows the answer at once
  const blocked=quitBlock(last);
  if(blocked){const line=document.getElementById('message');if(line)line.textContent=blocked;return;}
  api.quit().catch(error=>console.warn(error));
 }
 const panel=document.createElement('section');panel.className='panel desktop-status';panel.hidden=true;panel.setAttribute('aria-label','Desktop status');
 const phaseRow=document.createElement('p');const phase=document.createElement('span');phase.setAttribute('role','status');phase.setAttribute('aria-live','polite');
 const counter=document.createElement('span');counter.className='update-counter';phaseRow.append(phase,counter);panel.append(phaseRow);hint.after(panel);
 // Three message lines, one per operation (2.1): each its own polite live region, written only when it changes.
 const update=document.createElement('section');update.className='panel desktop-update';update.setAttribute('aria-label','App updates');
 const heading=document.createElement('h2');heading.textContent='App updates';update.append(heading);
 function messageLine(label){const p=document.createElement('p');p.className='update-line';const tag=document.createElement('span');tag.className='field-help';tag.textContent=label;
  const body=document.createElement('span');body.className='update-text';body.setAttribute('aria-live','polite');p.append(tag,body);update.append(p);return {p,body};}
 const lines={check:messageLine('Check'),download:messageLine('Download'),install:messageLine('Install')};
 const installerPath=document.createElement('p');installerPath.className='path';installerPath.hidden=true;update.append(installerPath);
 const actions=document.createElement('div');actions.className='toolbar';update.append(actions);panel.after(update);
 // Busy buttons use aria-disabled and keep focus (2.1); a press on one does nothing.
 // inert: what an inert press still says (Futaba's 0.22.1 QA, m-5: Restart to update while loading wrote nothing).
 function button(fn,quiet,inert){const b=document.createElement('button');b.type='button';if(quiet)b.className='quiet';b.addEventListener('click',()=>{if(b.getAttribute('aria-disabled')==='true'){if(inert)inert();return;}fn();});actions.append(b);return b;}
 const quietly=promise=>Promise.resolve(promise).catch(error=>console.warn(error));
 const check=button(()=>quietly(api.checkUpdates()).then(poll));const download=button(()=>quietly(api.downloadUpdate()).then(poll));
 const restart=button(()=>requestRestart(),false,()=>{if(loadingWaits(last)){const line=document.getElementById('message');if(line)line.textContent=NOT_YET_UPDATE;}});
 // Judy 0.22.2 6.2 (Futaba m-2): the line is written at the press, not at the engine's answer (up to 35 s later).
 const cancel=button(()=>{const u=last&&last.update;if(u)render({...last,update:{...u,canCancel:false,install:{...(u.install||{}),cancelling:true,cancelAt:Date.now()}}});quietly(api.cancelUpdate()).then(poll);});
 const installer=button(()=>quietly(api.showInstaller()),true);
 const controls={check,download,restart,cancel,installer};
 // Confirm (2.4): the approve-dialog pattern. Cancel is focused; no form, so Enter in the body confirms nothing.
 const dialog=document.createElement('dialog');dialog.id='update-dialog';dialog.setAttribute('aria-labelledby','update-dialog-title');dialog.setAttribute('aria-describedby','update-dialog-lead');
 const title=document.createElement('h2');title.id='update-dialog-title';const lead=document.createElement('p');lead.id='update-dialog-lead';const work=document.createElement('div');work.id='update-dialog-work';
 const closing=document.createElement('p');closing.textContent='Your source files are not touched.';
 const dialogActions=document.createElement('div');dialogActions.className='toolbar';
 const dismiss=document.createElement('button');dismiss.type='button';dismiss.className='quiet';dismiss.autofocus=true;dismiss.textContent='Cancel';dismiss.title='Close without updating. Nothing stops.';
 const confirm=document.createElement('button');confirm.type='button';confirm.textContent='Update now';
 dialogActions.append(dismiss,confirm);dialog.append(title,lead,work,closing,dialogActions);document.body.append(dialog);
 function closeDialog(){if(dialog.open)dialog.close();restart.focus({preventScroll:true});}
 dismiss.addEventListener('click',closeDialog);
 dialog.addEventListener('cancel',event=>{event.preventDefault();closeDialog();});
 dialog.addEventListener('keydown',event=>{if(event.repeat)event.preventDefault();});
 confirm.addEventListener('click',()=>{if(!dialog.open)return;dialog.close();restart.focus({preventScroll:true});startUpdate();});
 let last=null;
 function startUpdate(){quietly(api.installUpdate()).then(poll);setTimeout(poll,100);}
 async function requestRestart(){
  try{last=await api.status();}catch(error){console.warn(error);}
  // A press while loading is answered in the message line; focus stays (Judy 3.6).
  if(loadingWaits(last)){const line=document.getElementById('message');if(line)line.textContent=NOT_YET_UPDATE;return;}
  const u=last&&last.update;if(!u||!u.ready||(u.busy||{}).install||(u.busy||{}).download)return;
  const found=workLines(last.desktop);
  if(found.known&&!found.lines.length)return startUpdate();
  title.textContent=`Update to ${u.available} now?`;lead.textContent=`Books Arranger stops its work safely, installs ${u.available} and reopens by itself.`;
  confirm.title=`Stop work safely, install ${u.available} and reopen Books Arranger.`;
  work.replaceChildren(...found.lines.map(line=>{const p=document.createElement('p');p.textContent=line;return p;}));
  if(!dialog.open)dialog.showModal();dismiss.focus();
 }
 api.onRestartRequest?.(()=>requestRestart());
 function write(node,value){if(node.textContent!==value)node.textContent=value;}
 const mutating=['start-automatic','stop-automatic','start','stop','resume','pause-jobs','resume-jobs','queue-books','find-metadata','find-covers','approve-candidate','save-tracks','create-audiobook','recovery-confirm','retry-job','retry-all','retry-all-go'];
 function render(value){
  last=value;
  if(quit){const blocked=quitBlock(value),title=blocked||(value.loaded===false?QUIT_LOADING:QUIT_NORMAL);if(quit.title!==title)quit.title=title;quit.setAttribute('aria-disabled',blocked?'true':'false');}
  const desktop=value.desktop||{};const u=value.update;const updating=!!(u&&(u.busy||{}).install)||['updating','installing'].includes(value.quit);
  const quitting=value.quit!=='none'||updating||['finishing','parking','pausing','forcing','updating','blocked'].includes(desktop.phase);
  panel.hidden=!quitting;
  const step=u&&updating?phaseLine(u):null;
  if(step){write(phase,step.text);write(counter,step.counter?' '+step.counter:'');}
  else{write(phase,desktop.error||({finishing:'Finishing the current book and cleanup…',parking:'Parking pending work…',blocked:'Quit blocked; ownership remains held.'}[desktop.phase]||'Waiting for the engine checkpoint…'));write(counter,'');}
  if(quitting){for(const id of mutating){const node=document.getElementById(id);if(node)node.disabled=true;}document.querySelector('#review-form button[type=submit]')?.setAttribute('disabled','');}
  update.hidden=!u;if(!u)return;
  write(lines.check.body,checkLine(u));
  const downloaded=downloadLine(u);write(lines.download.body,downloaded);lines.download.p.hidden=!downloaded;lines.download.p.classList.toggle('failed',(u.download||{}).phase==='failed');
  const installed=installLine(u);write(lines.install.body,installed.text);lines.install.p.hidden=!installed.text;lines.install.p.classList.toggle('failed',installed.failed);
  lines.check.p.classList.toggle('failed',(u.check||{}).phase==='failed');
  write(installerPath,installed.path||'');installerPath.hidden=!installed.path;
  const state=buttons(u,desktop);
  if(loadingWaits(value)&&!state.restart.busy)state.restart={...state.restart,busy:true,title:NOT_YET_UPDATE};
  for(const [key,node] of Object.entries(controls)){const s=state[key];write(node,s.face);if(node.title!==s.title)node.title=s.title;node.setAttribute('aria-disabled',s.busy?'true':'false');node.hidden=s.hidden;}
 }
 let polling=false;async function poll(){if(polling)return;polling=true;try{render(await api.status());}catch(e){console.warn(e);}finally{polling=false;}}
 api.onStatus(()=>poll());setInterval(poll,1000);poll();
})();
