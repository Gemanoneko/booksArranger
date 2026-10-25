'use strict';
// Startup load strip (ruling 28; Judy's 0.22.1 UX spec, section 3): Working, Waiting, Stuck or Stopped, from silence,
// never from total time. Pure, so the page (load strip), the shell (tray tooltip) and the node tests share one copy.
(function(root){
 // The thresholds live here only (3.4): retune them without touching the copy.
 const THRESHOLDS=Object.freeze({answerWaiting:3000,answerStuck:10000,progressWaiting:10000,progressStuck:30000,sleepGap:5000});
 const STEPS=Object.freeze({engine:'Starting the engine',catalog:'Opening the catalog',session:'Checking the last session',books:'Loading your books'});
 const UNITS=new Set(['files','books','items']);
 const CAUSES={drive:root=>root?`the source drive ${root} to answer`:'the source drive to answer',file_lock:()=>'another program to release the catalog'};
 const HINTS={drive:'Check that the drive is connected. Loading continues by itself when it answers.',file_lock:'Close other programs that use the catalog. Loading continues by itself when it lets go.'};
 const count=n=>Number(n).toLocaleString();
 // {s} s under a minute; {m} min {s} s from a minute; {h} h {m} min from an hour.
 function duration(ms){
  const s=Math.max(0,Math.floor(ms/1000));
  if(s<60)return `${s} s`;
  if(s<3600)return `${Math.floor(s/60)} min ${s%60} s`;
  return `${Math.floor(s/3600)} h ${Math.floor(s%3600/60)} min`;
 }
 // m:ss; h:mm:ss from one hour.
 function running(ms){
  const s=Math.max(0,Math.floor(ms/1000)),two=n=>String(n).padStart(2,'0');
  return s<3600?`${Math.floor(s/60)}:${two(s%60)}`:`${Math.floor(s/3600)}:${two(Math.floor(s%3600/60))}:${two(s%60)}`;
 }
 function stepOf(loading){
  // Before the engine's first answer the shell's step is the only one: Step 1, the process is launching.
  if(!loading)return {id:'engine',n:1,of:4,words:STEPS.engine};
  const of=Number.isInteger(loading.of)&&loading.of>0?loading.of:4,n=Number.isInteger(loading.n)&&loading.n>0?Math.min(loading.n,of):1;
  return {id:loading.step,n,of,words:STEPS[loading.step]||'Loading…'};
 }
 // The clocks: the last engine answer, and the last progress (the engine reports its age; an age, so a clock change
 // cannot fake progress). A gap of more than 5 s in this clock (sleep, a frozen page) restarts both.
 function createTracker(launchedAt){
  const t={launchedAt,answerAt:launchedAt,progressAt:launchedAt,lastTick:launchedAt,answered:false,loading:null,
   observe(answer,at){
    t.answerAt=at;t.answered=true;
    const loading=answer&&answer.loading;
    if(loading&&typeof loading==='object'){
     const age=Number.isFinite(loading.progress_age_ms)&&loading.progress_age_ms>=0?loading.progress_age_ms:0;
     t.progressAt=Math.max(t.progressAt,at-age);t.loading=loading;
    }
   },
   // An answer without a body (a "still updating" 503) is an answer too.
   heard(at){t.answerAt=at;t.answered=true;},
   tick(at){
    if(at-t.lastTick>THRESHOLDS.sleepGap){t.answerAt=at;t.progressAt=at;}
    t.lastTick=at;
   },
   restart(at){t.launchedAt=at;t.answerAt=at;t.progressAt=at;t.lastTick=at;t.answered=false;t.loading=null;},
  };
  return t;
 }
 // The worse of the two signals (3.4). stopped: the shell's fact, which wins.
 function evaluate(t,at,{stopped=false}={}){
  if(stopped)return {state:'stopped',quiet:0,signal:'exit'};
  const answer=Math.max(0,at-t.answerAt),progress=Math.max(0,at-t.progressAt);
  const rank=(ms,waiting,stuck)=>ms>=stuck?2:ms>=waiting?1:0;
  const a=rank(answer,THRESHOLDS.answerWaiting,THRESHOLDS.answerStuck);
  // Before the first answer only the engine-silence row applies, from the launch.
  const p=t.answered?rank(progress,THRESHOLDS.progressWaiting,THRESHOLDS.progressStuck):0;
  const worst=Math.max(a,p),state=['working','waiting','stuck'][worst];
  if(!worst)return {state,quiet:0,signal:''};
  const signal=a>=p?'answer':'progress';
  return {state,quiet:signal==='answer'?answer:progress,signal};
 }
 function cause(loading){
  const w=loading&&loading.waiting_for;
  return w&&CAUSES[w.kind]?{text:CAUSES[w.kind](w.root),hint:HINTS[w.kind]}:null;
 }
 // The state line (3.4): the state word, the step, the state's own sentence.
 function stateLine(verdict,loading,{portPid=null}={}){
  const step=stepOf(loading),head=`Step ${step.n} of ${step.of}: ${step.words}`,x=duration(verdict.quiet),named=cause(loading);
  switch(verdict.state){
   case 'stopped':return portPid?{word:'Stopped',text:`Another copy of Books Arranger is running (process ${portPid}). Quit it from the tray, then try again.`}
    :{word:'Stopped',text:'The engine stopped while loading. Your files are not touched.'};
   case 'stuck':
    if(named&&verdict.signal==='progress')return {word:'Stuck',text:`${head}. Still waiting for ${named.text} (${x}). ${named.hint}`};
    return {word:'Stuck',text:verdict.signal==='answer'?`${head}. The engine hasn't answered for ${x}. It may have stopped responding.`
     :`${head}. No progress for ${x}. The engine is answering, but this step has not moved.`};
   case 'waiting':
    if(named&&verdict.signal==='progress')return {word:'Waiting',text:`${head}. Waiting for ${named.text} (${x}).`};
    return {word:'Waiting',text:verdict.signal==='answer'?`${head}. The engine hasn't answered for ${x}.`:`${head}. Nothing new for ${x}. The engine is still answering.`};
   default:return {word:'Working',text:head};
  }
 }
 // The detail line (3.3): parts wrap between, never inside.
 function detailParts(t,at,loading,lastLoadMs){
  const parts=[];
  if(loading){
   const unit=UNITS.has(loading.unit)?loading.unit:'items';
   if(Number.isFinite(loading.done)&&Number.isFinite(loading.total)&&loading.total>0)parts.push(`${count(loading.done)} of ${count(loading.total)} ${unit}`);
   else if(Number.isFinite(loading.done)&&loading.done>0)parts.push(`${count(loading.done)} ${unit} so far`);
  }
  parts.push(`running ${running(at-t.launchedAt)}`);
  parts.push(t.answered?`engine answered ${Math.floor(Math.max(0,at-t.answerAt)/1000)} s ago`:'no answer from the engine yet');
  if(Number.isFinite(lastLoadMs)&&lastLoadMs>0)parts.push(`last load took ${duration(lastLoadMs)}`);
  return parts;
 }
 // "Ready · Loaded in {m} min {s} s" (or "{s} s"), 3.7.
 function readyLine(tookMs){return Number.isFinite(tookMs)&&tookMs>=0?`Ready · Loaded in ${duration(tookMs)}`:'Ready';}
 function fraction(loading){
  return loading&&Number.isFinite(loading.done)&&Number.isFinite(loading.total)&&loading.total>0?Math.max(0,Math.min(1,loading.done/loading.total)):null;
 }
 // aria-valuetext: "Step 3 of 4, Checking the last session, 24%" (no percentage when the step cannot count).
 function valueText(loading){
  const step=stepOf(loading),f=fraction(loading);
  return `Step ${step.n} of ${step.of}, ${step.words}${f===null?'':`, ${Math.round(f*100)}%`}`;
 }
 // The tray tooltip (3.8).
 function trayTooltip(verdict,loading,ready){
  if(ready)return 'Books Arranger';
  const step=stepOf(loading);
  return {working:`Books Arranger — loading, step ${step.n} of ${step.of}`,waiting:`Books Arranger — waiting, step ${step.n} of ${step.of}`,
   stuck:`Books Arranger — stuck at step ${step.n} of ${step.of}`,stopped:'Books Arranger — stopped'}[verdict.state]||'Books Arranger';
 }
 // Loaded: every part ready, or no loading object at all (an engine that loads before it answers).
 function loaded(answer){
  const loading=answer&&answer.loading;
  if(!loading)return true;
  return !!loading.parts&&['library','status','books','attention','jobs'].every(name=>loading.parts[name]===true)&&loading.took_ms!==null&&loading.took_ms!==undefined;
 }
 function part(answer,name){const loading=answer&&answer.loading;return !loading||!!(loading.parts&&loading.parts[name]===true);}
 const api=Object.freeze({THRESHOLDS,STEPS,duration,running,stepOf,createTracker,evaluate,stateLine,detailParts,readyLine,fraction,valueText,trayTooltip,loaded,part});
 root.booksLoadState=api;
 if(typeof module==='object'&&module.exports)module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
