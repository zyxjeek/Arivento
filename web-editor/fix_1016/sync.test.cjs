const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const code=fs.readFileSync(__dirname+'/../hold-app.js','utf8'),C=require('../hold-core.js');
function setup(offset=0,rate=1){
 const events=[],sources=[],controls={speed:{value:String(rate)},hitSound:{checked:true},metronome:{checked:false},musicInfo:{},playButton:{setAttribute(){}}};
 const audioContext={currentTime:10,state:'running',destination:{},async resume(){},createBufferSource(){const source={playbackRate:{value:1},connect(){},start(at,offset){this.at=at;this.offset=offset;},stop(){this.stopped=true;},disconnect(){}};sources.push(source);return source;}};
 const s={C,audioContext,notes:[1,2,3,4].map((lane,id)=>({id,lane,time:6000.125})),meta:{duration:20000,bpm:120,offset:0,beats:4},playing:true,startAudio:10.06,startTime:offset,playRate:rate,musicBuffer:{duration:12},musicSource:null,nextNote:0,nextBeat:0,oscillators:new Set(),soundTimer:0,cursor:offset,$:id=>controls[id],setInterval:()=>1,clearInterval(){},beep:(...a)=>events.push(a),clamp:(v,a,b)=>Math.max(a,Math.min(b,v))};
 Object.assign(s,{preparedMusic:{duration:12/rate},audioReady:true,starting:false,playToken:0,usingAudio:false,dirty:false,PitchAudio:{cancel(){},async prepare(a,input,rate){return {duration:12/rate};}},context:()=>audioContext,audio:{pause(){}},cancelHold(){},selectionUI(){},timeUI(){},toast(){},document:{querySelectorAll:()=>[]}});
 vm.createContext(s);
 for(const name of ['playbackTime','stopMusic','startMusic','changeSpeed','togglePlay','pause','resetSchedule','scheduleSounds']){const line=code.split('\n').find(l=>l.trim().startsWith('function '+name+'(')||l.trim().startsWith('async function '+name+'('));assert.ok(line,name);vm.runInContext(line,s);}
 s.startMusic();return {s,events,sources,controls};
}
test('开头与第四小节起播，同一四押与音乐采样位置一致',()=>{
 for(const offset of [0,6000,4500,6000.125]){const {s,events,sources}=setup(offset);const target=s.startAudio+(6000.125-offset)/1000;s.audioContext.currentTime=Math.max(10,target-.1);s.resetSchedule(offset);assert.equal(events.length,4);for(const [at] of events){assert.ok(Math.abs(at-target)<1e-10);assert.ok(Math.abs((at-sources[0].at)*1000+sources[0].offset*1000-6000.125)<1e-8);}}
});
test('所有试听速度都保持同一音乐位置',()=>{
 for(const rate of [.5,.75,1,1.25]){const {s,events,sources}=setup(5500,rate);s.audioContext.currentTime=s.startAudio+.45/rate;s.resetSchedule(5500);assert.equal(events.length,4);assert.equal(sources[0].playbackRate.value,1);assert.equal(sources[0].offset,5.5/rate);assert.ok(Math.abs(((events[0][0]-sources[0].at)+sources[0].offset)*1000*rate-6000.125)<1e-8);}
});
test('画面未刷新仍按音频时钟前进，时钟暂停时不前进',()=>{
 const {s}=setup(2000);s.audioContext.currentTime=15.06;assert.equal(Math.round(s.playbackTime()),7000);assert.equal(Math.round(s.playbackTime()),7000);
});
test('零秒首键与音乐都在预定起点开始',()=>{
 const {s,events,sources}=setup();s.notes=[{id:1,lane:1,time:0}];s.resetSchedule(0);assert.equal(events[0][0],sources[0].at);assert.equal(s.playbackTime(),0);
});
test('调速等待保调完成后重建音乐源与时间锚点，音符不漂移',async()=>{
 const {s,events,sources,controls}=setup();s.audioContext.currentTime=15.56;controls.speed.value='.5';await s.changeSpeed();assert.equal(sources[0].stopped,true);assert.equal(sources[1].offset,11);s.audioContext.currentTime=s.startAudio+.9;s.scheduleSounds();assert.ok(Math.abs((events[0][0]-sources[1].at)*500+5500-6000.125)<1e-8);
});
test('暂停取消键音，重播建立新起点',()=>{
 const {s,events,sources}=setup(6000);s.resetSchedule(6000);s.playing=false;s.stopMusic();s.resetSchedule();assert.equal(sources[0].stopped,true);s.audioContext.currentTime=80;s.startAudio=80.06;s.playing=true;s.startMusic();s.resetSchedule(6000);assert.equal(events.length,8);assert.ok(Math.abs(events[4][0]-80.060125)<1e-9);
});
test('保留用户5000%音量上限，并按输入控件上限恢复',()=>{
 const html=fs.readFileSync(__dirname+'/../source.html','utf8');assert.match(html,/id="hitVolume"[^>]*max="5000"/);assert.ok(code.includes("clamp(v, 0, Number($('hitVolume').max))"));assert.ok(!code.includes('await audio.play()'));
});
test('准备音频时暂停，旧的异步结果不会重新播放',async()=>{
 const {s,sources}=setup();s.pause();let finish,entered;const ready=new Promise(r=>entered=r);s.PitchAudio.prepare=()=>new Promise(r=>{finish=r;entered();});const pending=s.togglePlay();await ready;assert.equal(s.starting,true);s.pause();finish({duration:12});await pending;assert.equal(s.playing,false);assert.equal(sources.length,1);
});
test('处理时间不算入谱面，准备失败保持暂停',async()=>{
 const {s,sources}=setup(4500,.5);s.pause();s.PitchAudio.prepare=async()=>{s.audioContext.currentTime=100;return {duration:24};};await s.togglePlay();assert.equal(sources[1].at,100.06);assert.equal(s.playbackTime(),4500);s.pause();s.PitchAudio.prepare=async()=>{throw Error('test');};await s.togglePlay();assert.equal(s.playing,false);assert.equal(sources.length,2);
});
