'use strict';
function refuseCapture(argv){
 if(argv.some(arg=>arg==='--capture'||arg.startsWith('--capture=')))throw new Error('Screenshot capture flags are unavailable. Existing files are never capture targets.');
}
module.exports={refuseCapture};
