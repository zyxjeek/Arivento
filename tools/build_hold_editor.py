from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'archive/hold_base_1016/Creator.html').read_text(encoding='utf-8')
a=s.index('        (function (root)');b=s.index('        (() => {',a)
s=s[:a]+(ROOT/'web-editor/hold-core.js').read_text(encoding='utf-8')+'\n'+s[b:]
def replace(a,b):
    global s
    assert a in s,a[:100]
    s=s.replace(a,b)
def function(name,body):
    global s
    s,n=re.subn(r'(?m)^            function '+name+r'\([^\n]*\n',lambda m:'            '+body+'\n',s)
    assert n==1,name
replace('dirty = true, gesture = null;', 'dirty = true, gesture = null, pendingHold = null, laneNotes = [[],[],[],[]];')
replace('notes.map(n => [n.lane, n.time])','notes.map(C.pack)')
replace('notes[notes.length - 1].time + 500','C.last(notes) + 500')
replace("function refresh() {", "function refresh() { laneNotes = [1,2,3,4].map(lane=>notes.filter(n=>n.lane===lane));")
replace("draw: '点击网格放置音符，再点一次删除',", "draw: '点击网格放置音符，再点一次删除', hold: pendingHold ? '已设置头部，请点击同轨更晚的尾部；Esc 取消' : '依次点击同轨的头部、尾部放置 Hold',")
replace("field('selectedTime', chosen.length ? C.precise(chosen[0].time) : '');", "field('selectedTime', chosen.length ? C.precise(chosen[0].time) : ''); $('holdEnd').disabled=playing||chosen.length!==1||chosen[0].end===undefined; field('holdEnd',chosen.length===1&&chosen[0].end!==undefined?chosen[0].end:'');")
function('action',"function action(fn) { if (playing) { toast('请先暂停预览，再编辑音符。'); return; } const before=cloneNotes(),selection=new Set(selected); try { if(fn()===false)return; notes=C.normalize(notes); if(JSON.stringify(before)===JSON.stringify(notes))return; history.push(before); if(history.length>100)history.shift(); future=[]; edited(); } catch(e) { notes=before; selected=selection; refresh(); fail(e); } }")
function('nearest',"function nearest(p) { const range=Math.min(C.step(meta)*.45,12/pxMs); return visibleNotes(p.time-range,p.time+range).filter(n=>n.lane===p.lane).sort((a,b)=>Math.abs(a.time-p.time)-Math.abs(b.time-p.time))[0]||null; }\n            function visibleNotes(from,to) { const result=[]; for(const lane of laneNotes){let i=C.lowerBound(lane,from); if(i&&C.end(lane[i-1])>=from)i--; while(i<lane.length&&lane[i].time<=to)result.push(lane[i++]);} return result; }")
function('place',"function place(p,erase=false,stroke=false) { if(p.x<gutter)return false; const time=C.snap(p.time,meta); if(time>meta.duration||time>7199500)return false; const near=nearest(p); let result; if(erase){if(!near)return false;result=notes.filter(n=>n.id!==near.id);}else if(near){if(near.end!==undefined)throw Error('该位置被 Hold 占用');if(stroke)return false;result=notes.filter(n=>n.id!==near.id);}else{if(notes.length>=100000)throw Error('音符数量已达 100000 枚');result=C.normalize([...notes,{id:nextId++,lane:p.lane,time}]);} notes=result;selected.clear();return true; }\n            function safePlace(...args) { if(gesture?.invalid)return false; try{return place(...args);}catch(e){if(gesture){notes=gesture.before;gesture.changed=false;gesture.invalid=true;refresh();}fail(e);return false;} }\n            function holdClick(p) { if(playing||p.x<gutter)return; const time=C.snap(p.time,meta); if(!pendingHold){pendingHold={lane:p.lane,time};selectionUI();dirty=true;return;} if(p.lane!==pendingHold.lane||time<=pendingHold.time){toast('尾部必须在同轨且晚于头部');return;} action(()=>{if(notes.length>=100000)throw Error('音符数量已达 100000 枚'); const note={id:nextId++,...pendingHold,end:time}; notes=C.normalize([...notes,note]);selected=new Set([note.id]);pendingHold=null;}); }\n            function cancelHold(){pendingHold=null;dirty=true;}")
replace('function setTool(value) { tool = value;', 'function setTool(value) { cancelHold(); tool = value;')
replace('gesture.changed = place(', 'gesture.changed = safePlace(')
replace('g.changed = place(', 'g.changed = safePlace(')
replace('if (g.ruler) return; if (tool', "if (g.ruler) return; if(tool==='hold'){if(!g.moved)holdClick(p);return;} if (tool")
replace('if (n.time >= lo && n.time <= hi && x >= x1 && x <= x2)', 'if (C.end(n) >= lo && n.time <= hi && x >= x1 && x <= x2)')
replace('time: C.precise(target + n.time - first) }', 'time: C.precise(target + n.time - first), ...(n.end===undefined?{}:{end:C.precise(target+n.end-first)}) }')
replace('time: C.snap(n.time, meta) }', 'time: C.snap(n.time, meta), ...(n.end===undefined?{}:{end:C.snap(n.end,meta)}) }')
replace('async function togglePlay() {', 'async function togglePlay() { cancelHold();')
replace("$('importButton').onclick = () => $('chartFile').click();", "$('importButton').onclick = () => {cancelHold();$('chartFile').click();};")
replace("$('newButton').onclick = () => {", "$('newButton').onclick = () => { cancelHold();")
replace("if (k === 'escape') {", "if (k === 'escape') { cancelHold();")
replace("$('selectedTime').onchange =", "$('holdEnd').onchange=()=>action(()=>{const n=notes.find(n=>selected.has(n.id));if(n&&selected.size===1&&n.end!==undefined)notes=notes.map(x=>x.id===n.id?{...x,end:Number($('holdEnd').value)}:x);});\n            $('selectedTime').onchange =")
a=s.index('                const from = (top - pad - 12)');b=s.index('                const cy =',a)
s=s[:a]+'''                const from=(top-pad-12)/pxMs,to=(bottom-pad+12)/pxMs;
                for(const n of visibleNotes(from,to)){const x=gutter+(n.lane-1)*laneW+9,y=pad+n.time*pxMs-top,tail=pad+C.end(n)*pxMs-top;
                    ctx.fillStyle=selected.has(n.id)?'#efd199':'#81cab4';
                    if(n.end!==undefined){ctx.globalAlpha=.55;ctx.fillRect(x+5,Math.max(-8,y),laneW-28,Math.min(height+8,tail)-Math.max(-8,y));ctx.globalAlpha=1;ctx.fillRect(x,tail-4,laneW-18,8);}
                    ctx.fillRect(x,y-5,laneW-18,10);if(selected.has(n.id)){ctx.strokeStyle='#fff0cf';ctx.strokeRect(x-2,Math.max(-8,y-7),laneW-14,Math.min(height+8,tail+7)-Math.max(-8,y-7));}
                }
                if(pendingHold){const x=gutter+(pendingHold.lane-1)*laneW+9,y=pad+pendingHold.time*pxMs-top;ctx.strokeStyle='#edcc8d';ctx.strokeRect(x,y-7,laneW-18,14);}
''' +s[b:]
replace('<div class="tool-group history"', '<button data-tool="hold" aria-pressed="false" title="先点头部，再点尾部">Hold 长条</button><div class="tool-group history"')
replace('<footer class="transport">','<label class="hold-end-field">Hold 尾部 <input id="holdEnd" type="number" min="0" step="any" aria-label="选中 Hold 尾部时间，毫秒"> ms</label>\n        <footer class="transport">')
replace('</style>', '.hold-end-field{font-size:13px;padding:4px 16px}.hold-end-field input{width:130px;height:32px}\n</style>')
replace('点网格交叉位置放置 Tap。同一横线上不同轨道即为多押。','点网格放置 Tap；Hold 工具依次点击同轨头尾。禁止同轨重叠，包括尾部同一时刻的新音符。点击条身可选择或擦除整根长条。')
(ROOT/'web-editor/source.html').write_text(s,encoding='utf-8')
(ROOT/'web-editor/hold-app.js').write_text(s[s.index('        (() => {'):s.rindex('</script>')],encoding='utf-8')
print('Creator Hold ready')
