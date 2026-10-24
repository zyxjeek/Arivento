(function(root){
 'use strict';
 const step=m=>60000/m.bpm/m.division,precise=t=>Math.round(t*1e6)/1e6;
 const snap=(t,m)=>precise(m.offset+Math.max(Math.ceil(-m.offset/step(m)),Math.round((t-m.offset)/step(m)))*step(m));
 const defaults=()=>({name:'未命名谱面',music:'',bpm:120,beats:4,division:4,offset:0,approach:500,duration:60000,mode:2});
 const finite=x=>typeof x==='number'&&Number.isFinite(x),end=n=>n.end??n.time;
 const pack=n=>n.end===undefined?[n.lane,n.time]:[n.lane,n.time,n.end];
 const last=notes=>notes.reduce((v,n)=>Math.max(v,end(n)),0);
 function normalize(notes){
  const sorted=[...notes].sort((a,b)=>a.time-b.time||a.lane-b.lane),previous=new Map(),result=[];
  for(const n of sorted){
   const error=message=>{throw Error(`音符 ${n.id??result.length+1}（第 ${n.lane} 轨，${n.time}ms）：${message}`);};
   if(!Number.isInteger(n.lane)||n.lane<1||n.lane>4||!finite(n.time)||n.time<0||end(n)>7199500)error('轨道或时间超出范围');
   if(n.end!==undefined&&(!finite(n.end)||n.end<=n.time))error('Hold 尾部必须晚于头部');
   const p=previous.get(n.lane);
   if(p&&n.time<=end(p)){
    if(p.end===undefined&&n.end===undefined&&p.time===n.time)continue;
    error('与同轨音符重叠，下一枚音符必须晚于 Hold 尾部');
   }
   previous.set(n.lane,n);result.push(n);
  }
  return result;
 }
 function parse(text){
  const a=JSON.parse(text.replace(/^\uFEFF/,'').trim());
  if(Array.isArray(a)&&a[2]>1e9)throw Error('过屏时间超出范围');
  if(!Array.isArray(a)||a.length!==8||typeof a[0]!=='string'||!a[0].trim()||typeof a[1]!=='string'||![a[2],a[4],a[5],a[6]].every(finite)||a[2]<=0||![1,2].includes(a[3])||a[4]<20||a[4]>400||a[5]<1||a[5]>64||a[6]<0||a[6]>7200000||!Array.isArray(a[7])||a[7].length>100000)throw Error('谱面格式不正确，或 BPM / 时长超出范围。');
  const notes=a[7].map((n,i)=>{if(!Array.isArray(n)||![2,3].includes(n.length))throw Error(`第 ${i+1} 个音符必须是 Tap 二项或 Hold 三项列表`);if(i&&n[1]<a[7][i-1][1])throw Error(`第 ${i+1} 个音符未按头部时间排序`);return {id:i+1,lane:n[0],time:n[1],...(n.length===3?{end:n[2]}:{})};});
  const sorted=normalize(notes);
  return {meta:{...defaults(),name:a[0],music:a[1],approach:a[2],mode:a[3],bpm:a[4],division:a[5],offset:a[3]===2&&sorted.length?sorted[0].time:0,duration:Math.max(1000,a[6],last(sorted)+500)},notes:sorted};
 }
 function serialize(meta,notes){
  if(!meta.name.trim())throw Error('请填写谱面名称');
  const sorted=normalize(notes);if(!sorted.length)throw Error('请先放置至少一枚音符');
  return JSON.stringify([meta.name.trim(),meta.music,meta.approach,meta.mode,meta.bpm,meta.division,Math.max(meta.duration,last(sorted)+500),sorted.map(pack)]);
 }
 function move(notes,ids,lanes,time){
  const changed=notes.map(n=>ids.has(n.id)?{...n,lane:n.lane+lanes,time:precise(n.time+time),...(n.end===undefined?{}:{end:precise(n.end+time)})}:n);
  const sorted=normalize(changed);if(sorted.length!==notes.length)throw Error('目标位置已有音符');return sorted;
 }
 function lowerBound(notes,time){let lo=0,hi=notes.length;while(lo<hi){const mid=(lo+hi)>>1;if(notes[mid].time<time)lo=mid+1;else hi=mid;}return lo;}
 const api={step,snap,defaults,precise,normalize,parse,serialize,move,lowerBound,end,last,pack};
 if(typeof module!=='undefined')module.exports=api;else root.ChartCore=api;
})(typeof window==='undefined'?globalThis:window);
