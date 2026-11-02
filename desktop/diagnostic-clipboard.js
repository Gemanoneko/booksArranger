'use strict';
// Only an explicit diagnostic-copy request from this app may write the clipboard.
function register({ipcMain,clipboard,sender}){
 ipcMain.handle('books:copy-diagnostics',(event,text)=>{
  if(sender(event)!=='app')throw new Error('Diagnostic copying is unavailable');
  if(typeof text!=='string'||text.length>65536)throw new Error('Diagnostic text is invalid or too long');
  clipboard.writeText(text);return true;
 });
}
module.exports={register};
