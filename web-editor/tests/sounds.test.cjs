const assert=require('node:assert/strict'),test=require('node:test'),fs=require('node:fs'),vm=require('node:vm'),C=require('../dist/core.js');
const source=fs.readFileSync(require('node:path').join(__dirname,'../dist/app.js'),'utf8');
function setup(notes){
 const events=[],controls={speed:{value:'1'},hitSound:{checked:true},metronome:{checked:false}};
 const s={C,notes,playing:true,usingAudio:true,audio:{currentTime:0},audioContext:{state:'running',currentTime:10},cursor:0,startTime:0,startWall:0,meta:{duration:5000,bpm:120,offset:0,beats:4},oscillators:new Set(),soundTimer:0,nextNote:0,nextBeat:0,performance:{now:()=>0},$:id=>controls[id],setInterval:f=>(s.timer=f,1),clearInterval:()=>{s.timer=null;},beep:(...args)=>events.push(args)};
 const funcs=source.slice(source.indexOf(' function playbackTime()'),source.indexOf(' async function togglePlay()')).replace(/ function beep\([^\n]*\n/,'');
 vm.createContext(s);vm.runInContext(funcs,s);return {s,events,controls};
}
test('起播稍晚仍播放零秒四押，后续不会重复',()=>{
 const {s,events}=setup([1,2,3,4].map((lane,id)=>({id,lane,time:0})));
 s.audio.currentTime=.03;s.resetSchedule(0);assert.equal(events.length,4);assert.ok(events.every(e=>e[0]===10));s.scheduleSounds();assert.equal(events.length,4);
});
test('音符小数时间和慢速试听按音乐时间安排',()=>{
 const {s,events,controls}=setup([{id:1,lane:1,time:123.456}]);controls.speed.value='.5';s.audio.currentTime=.1;s.resetSchedule();assert.ok(Math.abs(events[0][0]-10.046912)<1e-9);
});
test('界面不刷新时独立定时器继续发声',()=>{
 const {s,events}=setup([{id:1,lane:1,time:500}]);s.resetSchedule();assert.equal(events.length,0);s.audio.currentTime=.4;s.timer();assert.equal(events.length,1);assert.equal(events[0][0],10.1);
});
test('键音关闭时静音，开启后不补播过去音符',()=>{
 const {s,events,controls}=setup([{id:1,lane:1,time:100},{id:2,lane:2,time:600}]);controls.hitSound.checked=false;s.resetSchedule();assert.equal(events.length,0);s.audio.currentTime=.5;controls.hitSound.checked=true;s.resetSchedule();assert.equal(events.length,1);assert.equal(events[0][1],1240);
});
test('暂停取消待播放音效，定位后重新播放',()=>{
 const {s,events}=setup([{id:1,lane:1,time:100}]);s.resetSchedule();let stopped=0;s.oscillators.add({stop:()=>stopped++});s.playing=false;s.resetSchedule();assert.equal(stopped,1);assert.equal(s.timer,null);s.scheduleSounds();assert.equal(events.length,1);s.playing=true;s.resetSchedule();assert.equal(events.length,2);
});
test('短暂卡顿不会漏掉跨过的音符，长跳转不爆发补播',()=>{
 const {s,events}=setup([{id:1,lane:1,time:200},{id:2,lane:2,time:1000}]);s.resetSchedule();s.audio.currentTime=.22;s.timer();assert.equal(events.length,1);s.audio.currentTime=2;s.timer();assert.equal(events.length,1);
});
test('节拍器独立于键音，调速后取消旧安排并重新对齐',()=>{
 const {s,events,controls}=setup([{id:1,lane:1,time:100}]);controls.hitSound.checked=false;controls.metronome.checked=true;s.resetSchedule();assert.equal(events.length,1);assert.equal(events[0][1],1800);controls.metronome.checked=false;controls.hitSound.checked=true;controls.speed.value='1.25';s.resetSchedule();assert.equal(events.length,2);assert.equal(events[1][0],10.08);
});
test('键音音量实时调整、归零静音并保存设置',()=>{
 const values=[],stored=[],controls={hitVolume:{value:'100'},hitVolumeValue:{textContent:''}};
 const s={$:id=>controls[id],hitGain:{gain:{setTargetAtTime:v=>values.push(v)}},audioContext:{currentTime:10},localStorage:{setItem:(...v)=>stored.push(v)}};
 vm.createContext(s);vm.runInContext(source.slice(source.indexOf(' function hitVolume()'),source.indexOf(' function playbackTime()')),s);
 for(const value of ['100','200','0']){controls.hitVolume.value=value;s.hitVolume();}
 assert.deepEqual(values,[4,8,0]);assert.equal(controls.hitVolumeValue.textContent,'0%');assert.equal(stored.at(-1)[1],'0');
});
