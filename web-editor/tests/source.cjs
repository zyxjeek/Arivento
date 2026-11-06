const fs=require('node:fs');
const html=fs.readFileSync(__dirname+'/../source.html','utf8');
const script=html.slice(html.indexOf('<script>')+8,html.lastIndexOf('</script>'));
const end="})(typeof window==='undefined'?globalThis:window);",core=script.indexOf(end)+end.length,pitch=script.indexOf(end,core)+end.length;
const load=code=>{const module={exports:{}};new Function('module',code)(module);return module.exports;};
module.exports={html,core:load(script.slice(0,core)),pitch:load(script.slice(core,pitch)),app:script.slice(pitch)};
