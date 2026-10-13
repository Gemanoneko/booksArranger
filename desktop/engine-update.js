'use strict';
// Shell state transition for the real authenticated idle-fence route. An error
// keeps the backend's closing/ownership latch intact but restores supported Quit.
async function parkOwnedEngine({state,request,sleep,broadcast,now=Date.now,timeoutMs=60000}){
 if(state.quit!=='none'||state.backendExited||!state.owner)throw new Error('Owned running engine is required before restarting to update');
 await request('POST','/api/desktop/update',{desktop:true});
 state.quit='updating';broadcast();
 try{
  const deadline=now()+timeoutMs;
  while(!state.backendExited&&now()<deadline){
   await sleep(200);if(state.backendExited)break;
   let status=null;try{status=await request('GET','/api/desktop/status',{desktop:true,timeout:1000});}catch{/* Serving absence alone never proves safe exit. */}
   if(status?.phase==='blocked')throw new Error(status.error||'Engine checkpoint blocked');
  }
  if(!state.backendExited||state.backend.exitCode!==0)throw new Error('The exact owned engine did not exit safely; update cancelled');
 }catch(error){state.quit='none';broadcast();throw error;}
}
module.exports={parkOwnedEngine};
