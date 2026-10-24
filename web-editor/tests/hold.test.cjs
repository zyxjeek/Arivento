const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const C=require('../hold-core.js'),html=fs.readFileSync(__dirname+'/../source.html','utf8');
const source=html.slice(html.indexOf('        (() => {'),html.lastIndexOf('</script>'));
const chart=notes=>['Hold','song.mp3',500,2,120,4,2000,notes];
const plain=v=>JSON.parse(JSON.stringify(v));
function editor(){
 const s={C,notes:[],selected:new Set(),history:[],future:[],clipboard:[],nextId:1,cursor:0,pendingHold:null,laneNotes:[[],[],[],[]],gesture:null,playing:false,meta:{...C.defaults()},gutter:112,width:512,pxMs:.192,tool:'hold',dirty:false,errors:[],point:e=>e,selectionUI(){},toast:t=>s.errors.push(t),fail:e=>s.errors.push(e.message),cloneNotes:()=>s.notes.map(n=>({...n})),setTimeout,clearTimeout};
 s.refresh=()=>{s.laneNotes=[1,2,3,4].map(lane=>s.notes.filter(n=>n.lane===lane));};s.edited=()=>{s.notes=C.normalize(s.notes);s.refresh();};
 vm.createContext(s);
 for(const name of ['action','holdClick','cancelHold','visibleNotes','nearest','place','safePlace','finishPointer','copySelected','paste','snapSelected','undo']){
  const line=source.split('\n').find(l=>l.trim().startsWith('function '+name+'('));assert.ok(line,name);vm.runInContext(line,s);
 }
 s.click=(lane,time)=>{s.gesture={id:1,moved:false,touch:true,before:s.cloneNotes()};s.finishPointer({pointerId:1,lane,time,x:150});};return s;
}
test('混合格式、小数头尾往返及结束时间延长',()=>{
 const raw=chart([[1,1000],[2,1234.56789,6000.12345]]),p=C.parse(JSON.stringify(raw)),out=JSON.parse(C.serialize(p.meta,p.notes));assert.deepEqual(out[7],raw[7]);assert.equal(out[6],6500.12345);
});
test('非法长条、同轨重叠与尾部同时间音符均拒绝',()=>{
 for(const notes of [[[1,1000,1000]],[[1,1000,999]],[[1,1000,2000],[1,1500]],[[1,1000,2000],[1,2000]],[[1,1000],[1,1000,2000]],[[1,1000,2000],[1,1500,3000]],[[1,'1000']],[[true,1000]],[[1,2000],[2,1000]]])assert.throws(()=>C.parse(JSON.stringify(chart(notes))));
 assert.throws(()=>C.normalize([{lane:1,time:0,end:Infinity}]));assert.throws(()=>C.normalize([{lane:1,time:0,end:NaN}]));
});
test('Tap 去重、跨轨重叠与尾后音符合法',()=>{
 const p=C.parse(JSON.stringify(chart([[1,1000],[1,1000],[2,1000,2000],[3,1000,3000],[2,2001]])));assert.equal(p.notes.length,4);
});
test('移动头尾保持时长，碰撞和越界拒绝',()=>{
 const notes=[{id:1,lane:1,time:1000,end:2000},{id:2,lane:2,time:1500}];const moved=C.move(notes,new Set([1]),0,123.456);assert.ok(Math.abs(moved[0].end-moved[0].time-1000)<1e-6);assert.throws(()=>C.move(notes,new Set([1]),1,0));assert.throws(()=>C.move(notes,new Set([1]),0,-1001));
});
test('鼠标/触控两次 pointerup 创建长条，错误尾部保留头部',()=>{
 const s=editor();s.click(1,1000);assert.deepEqual(plain(s.pendingHold),{lane:1,time:1000});s.click(2,2000);s.click(1,999);assert.equal(s.notes.length,0);assert.ok(s.pendingHold);s.click(1,2000);assert.deepEqual(plain(s.notes.map(C.pack)),[[1,1000,2000]]);assert.equal(s.pendingHold,null);assert.equal(s.history.length,1);
});
test('冲突创建不提交，不改变已有选择或撤销栈',()=>{
 const s=editor();s.notes=[{id:1,lane:1,time:1500}];s.nextId=2;s.selected=new Set([1]);s.refresh();s.click(1,1000);s.click(1,2000);assert.equal(s.notes.length,1);assert.equal(s.history.length,0);assert.ok(s.selected.has(1));assert.ok(s.pendingHold);
});
test('长条头部屏外仍可选中条身并擦除整根',()=>{
 const s=editor();s.notes=[{id:1,lane:1,time:1000,end:9000}];s.refresh();assert.equal(s.visibleNotes(4000,4500).length,1);assert.equal(s.nearest({lane:1,time:4500}).id,1);s.action(()=>s.place({lane:1,time:4500,x:150},true));assert.equal(s.notes.length,0);s.undo();assert.equal(s.notes[0].end,9000);
});
test('粘贴和撤销重做保留 Hold 尾部',()=>{
 const s=editor();s.notes=[{id:1,lane:1,time:1000,end:2000}];s.nextId=2;s.selected=new Set([1]);s.refresh();s.copySelected();s.cursor=3000;s.paste();assert.deepEqual(plain(s.notes.map(C.pack)),[[1,1000,2000],[1,3000,4000]]);s.undo();assert.equal(s.notes.length,1);s.undo(true);assert.equal(s.notes[1].end,4000);
});
test('吸附后零长度或冲突时整组回滚',()=>{
 const s=editor();s.notes=[{id:1,lane:1,time:1001,end:1010},{id:2,lane:2,time:1110}];s.selected=new Set([1,2]);const before=plain(s.notes);s.snapSelected();assert.deepEqual(plain(s.notes),before);assert.equal(s.history.length,0);
});
test('批量框选覆盖条身',()=>{
 const s=editor();s.notes=[{id:1,lane:1,time:1000,end:9000}];s.refresh();s.tool='select';s.gesture={id:1,moved:true,add:false,start:{time:3000,x:120}};s.finishPointer({pointerId:1,time:4000,x:200});assert.ok(s.selected.has(1));
});
test('取消预览不产生音符，旧草稿与长条草稿可读取',()=>{
 const s=editor();s.click(1,1000);s.cancelHold();assert.equal(s.notes.length,0);assert.equal(s.pendingHold,null);for(const rows of [[[1,1000]],[[1,1000,2000]]])assert.deepEqual(C.parse(JSON.stringify(chart(rows))).notes.map(C.pack),rows);
});
test('50000 枚混合音符可完整导出重读',()=>{
 const notes=Array.from({length:50000},(_,i)=>({id:i,lane:i%4+1,time:i*100,...(i%2?{end:i*100+50}:{})})),data=C.serialize(C.defaults(),notes),parsed=C.parse(data);assert.equal(parsed.notes.length,50000);assert.deepEqual(parsed.notes.map(C.pack),notes.map(C.pack));
});
test('5000% 音量和共用音频时钟保留，键音只按头部调度',()=>{
 assert.match(html,/id="hitVolume"[^>]*max="5000"/);assert.ok(source.includes('musicSource.start(startAudio'));const schedule=source.split('\n').find(l=>l.includes('function scheduleSounds'));assert.ok(schedule.includes('n.time - startTime'));assert.ok(!schedule.includes('n.end'));
});
