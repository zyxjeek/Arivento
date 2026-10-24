(function(root){
 'use strict';
 function* stretch(channels,sampleRate,rate){
  if(!channels.length||!Number.isFinite(rate)||rate<.5||rate>2)throw Error('不支持的试听速度');
  const length=channels[0].length;
  if(!channels.every(c=>c.length===length))throw Error('音频通道长度不一致');
  if(rate===1)return channels.map(c=>c.slice());
  const size=Math.max(64,Math.round(sampleRate*.04/2)*2),hop=size/2,seek=Math.round(sampleRate*.006),outLength=Math.max(1,Math.round(length/rate));
  const out=channels.map(()=>new Float32Array(outLength)),stride=8,coarse=16;
  let guide=0,energy=-1;
  for(let c=0;c<channels.length;c++){let e=0;for(let i=0;i<length;i+=101)e+=channels[c][i]*channels[c][i];if(e>energy){energy=e;guide=c;}}
  for(let c=0;c<channels.length;c++)for(let i=0;i<Math.min(size,outLength);i++)out[c][i]=channels[c][i]||0;
  for(let pos=hop,frame=0;pos<outLength;pos+=hop,frame++){
   const expected=Math.round(pos*rate),low=Math.max(0,expected-seek),high=Math.min(Math.max(0,length-hop),expected+seek),ref=out[guide],src=channels[guide];
   let refEnergy=1e-12;
   for(let i=0;i<hop&&pos+i<outLength;i+=stride)refEnergy+=ref[pos+i]*ref[pos+i];
   const score=at=>{let dot=0,e=1e-12;for(let i=0;i<hop&&pos+i<outLength;i+=stride){const v=src[at+i]||0;dot+=ref[pos+i]*v;e+=v*v;}return dot/Math.sqrt(e*refEnergy)-.002*Math.abs(at-expected)/Math.max(1,seek);};
   let best=Math.min(Math.max(expected,low),Math.max(low,high)),quality=score(best);
   if(refEnergy>1e-8&&high>=low){
    for(let at=low;at<=high;at+=coarse){const s=score(at);if(s>quality){quality=s;best=at;}}
    const center=best;
    for(let at=Math.max(low,center-coarse);at<=Math.min(high,center+coarse);at++){const s=score(at);if(s>quality){quality=s;best=at;}}
   }
   for(let c=0;c<channels.length;c++)for(let i=0;i<size&&pos+i<outLength;i++){
    const v=channels[c][best+i]||0,w=i<hop?i/hop:1;
    out[c][pos+i]=out[c][pos+i]*(1-w)+v*w;
   }
   if(frame%64===0)yield pos/outLength;
  }
  return out;
 }
 let cache=null,job=null;
 function cancel(){if(job){const active=job;job=null;active.abort();}}
 function clear(){cancel();cache=null;}
 async function prepare(context,input,rate,progress=()=>{}){
  cancel();
  if(rate===1)return input;
  if(cache&&cache.input===input&&cache.rate===rate)return cache.output;
  cache=null;
  const outputLength=Math.max(1,Math.round(input.length/rate));
  if((input.length+outputLength)*input.numberOfChannels*8>640*1024*1024)throw Error('音频过长，保调处理可能超出设备内存；请使用原速或较短的音乐。');
  let active;
  const arrays=await new Promise((resolve,reject)=>{
   let worker=null,url=null,stopped=false;
   const clean=()=>{if(worker)worker.terminate();if(url)URL.revokeObjectURL(url);};
   active={abort(){stopped=true;clean();reject(Object.assign(Error('已取消音频处理'),{name:'AbortError'}));}};job=active;
   const finish=(error,result)=>{if(stopped)return;clean();if(error)reject(error);else resolve(result);};
   if(typeof Worker!=='undefined'){
    try{
     url=URL.createObjectURL(new Blob(['const stretch='+stretch.toString()+';onmessage=e=>{try{const g=stretch(e.data.channels,e.data.sampleRate,e.data.rate);let r;do{r=g.next();if(!r.done)postMessage({progress:r.value});}while(!r.done);postMessage({channels:r.value},r.value.map(c=>c.buffer));}catch(e){postMessage({error:e.message});}}'],{type:'text/javascript'}));
     worker=new Worker(url);
     worker.onmessage=e=>{if(stopped)return;if(e.data.error)finish(Error(e.data.error));else if(e.data.channels)finish(null,e.data.channels);else progress(Math.round(e.data.progress*100));};
     worker.onerror=()=>finish(Error('后台音频处理失败，请尝试原速或重新打开制谱器。'));
     const channels=Array.from({length:input.numberOfChannels},(_,i)=>input.getChannelData(i).slice());
     worker.postMessage({channels,sampleRate:input.sampleRate,rate},channels.map(c=>c.buffer));return;
    }catch{clean();worker=null;url=null;}
   }
   const g=stretch(Array.from({length:input.numberOfChannels},(_,i)=>input.getChannelData(i)),input.sampleRate,rate);
   const run=()=>{if(stopped)return;try{const r=g.next();if(r.done)finish(null,r.value);else{progress(Math.round(r.value*100));setTimeout(run,0);}}catch(e){finish(e);}};
   setTimeout(run,0);
  }).finally(()=>{if(job===active)job=null;});
  const output=context.createBuffer(input.numberOfChannels,outputLength,input.sampleRate);
  arrays.forEach((a,i)=>output.copyToChannel(a,i));cache={input,rate,output};progress(100);return output;
 }
 const api={stretch,prepare,cancel,clear};
 if(typeof module!=='undefined')module.exports=api;else root.PitchAudio=api;
})(typeof window==='undefined'?globalThis:window);
