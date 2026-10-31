const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const C=require('../hold-core.js'),html=fs.readFileSync(__dirname+'/../source.html','utf8');
const base=['标签谱','song.mp3',500,2,120,4,20000,[[1,1000],[2,1500,2500]]];
const chart=tags=>JSON.stringify(base)+'\n//tags:'+JSON.stringify(tags);
test('无标签时导出与旧格式逐字相同',()=>{
 const p=C.parse(JSON.stringify(base));assert.deepEqual(p.tags,[]);assert.equal(C.serialize(p.meta,p.notes),JSON.stringify(base));assert.equal(C.serialize(p.meta,p.notes,[]),JSON.stringify(base));
});
test('标签随 txt 往返，按时间排序，第一行仍是八项谱面',()=>{
 const p=C.parse(JSON.stringify(base)),text=C.serialize(p.meta,p.notes,[['副歌',8000.5],[' 前奏 ',0]]),lines=text.split('\n');
 assert.equal(lines.length,2);assert.equal(JSON.parse(lines[0]).length,8);
 const again=C.parse(text);assert.deepEqual(again.tags,[['前奏',0],['副歌',8000.5]]);assert.deepEqual(again.notes.map(C.pack),base[7]);
});
test('手机端读取方式只取第一个 JSON 值，标签行不影响八项检查',()=>{
 const text=C.serialize(C.parse(JSON.stringify(base)).meta,C.parse(JSON.stringify(base)).notes,[['A]"[',1000]]);
 let depth=0,inText=false,stop=-1;
 for(let i=0;i<text.length&&stop<0;i++){const c=text[i];if(inText){if(c==='\\')i++;else if(c==='"')inText=false;}else if(c==='"')inText=true;else if(c==='[')depth++;else if(c===']'&&--depth===0)stop=i;}
 assert.deepEqual(JSON.parse(text.slice(0,stop+1)),base);
});
test('Windows 换行、BOM、尾部空白与多行谱面都能读取标签',()=>{
 for(const text of ['﻿'+JSON.stringify(base)+'\r\n//tags:[["A",1000]]\r\n',JSON.stringify(base,null,1)+'\n//tags:[["A",1000]]\n'])assert.deepEqual(C.parse(text).tags,[['A',1000]]);
});
test('谱面名称含标记文本不会被当作标签',()=>{
 const named=['a//tags:[["x",1]]',...base.slice(1)];assert.deepEqual(C.parse(JSON.stringify(named)).tags,[]);
});
test('非法标签被拒绝',()=>{
 for(const tags of [[['',1]],[['  ',1]],[['A',-1]],[['A','1']],[['A',7200001]],[['A']],[['A',1,2]],'x',{}])assert.throws(()=>C.parse(chart(tags)),/标签格式不正确/);
 assert.throws(()=>C.parse(JSON.stringify(base)+'\n//tags:[oops'),/标签格式不正确/);
 assert.throws(()=>C.normalizeTags(Array.from({length:1001},(_,i)=>['A',i])),/标签格式不正确/);
});
test('网页副本与内嵌脚本一致',()=>{
 const crlf=s=>s.replace(/\r?\n/g,'\r\n');
 assert.ok(html.includes(crlf(fs.readFileSync(__dirname+'/../hold-core.js','utf8'))));
 assert.ok(html.includes(crlf(fs.readFileSync(__dirname+'/../hold-app.js','utf8'))));
});
