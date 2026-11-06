from pathlib import Path
import copy,json,sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'archive/历史目录/tools'))
from 积木工具 import *
ROOT=Path(__file__).resolve().parents[1]

source=ROOT/'native'/json.loads((ROOT/'tools/current_release.json').read_text(encoding='utf-8'))['name']
bky=next(source.rglob('Play.bky'))
root=ET.fromstring(bky.read_bytes())
for e in root.iter():e.tag=e.tag.split('}')[-1]
globals_={b.findtext("field[@name='NAME']") for b in root if b.get('type')=='global_declaration'}
if '上一头时' in globals_:print('skip',bky);raise SystemExit
procedures={b.findtext("field[@name='NAME']"):b for b in root if b.get('type','').startswith('procedures_def')}
def steps(first):
    out=[first]
    while out[-1].find('next/block') is not None:out.append(out[-1].find('next/block'))
    return out
def insert_after(b,items):
    old=b.find('next');rest=old.find('block') if old is not None else None
    if old is not None:b.remove(old)
    if rest is not None:items=items+[rest]
    ET.SubElement(b,'next').append(chain(items))
def fresh(b):
    b=copy.deepcopy(b)
    for n in b.findall('next'):b.remove(n)
    for x in b.iter('block'):x.set('id','new')
    return b
def boolean(v):return block('logic_boolean',{'BOOL':'TRUE' if v else 'FALSE'})
new=[block('global_declaration',{'NAME':'上一头时'},{'VALUE':-10**12}),block('global_declaration',{'NAME':'上一游玩键'},{'VALUE':make_list()})]
for b in reversed(new):root.insert(0,b)

prepare=procedures['准备游玩键'];stack=steps(prepare.find("statement[@name='STACK']/block"))
loop_=next(b for b in stack if b.get('type')=='local_declaration_statement').find("statement[@name='STACK']/block")
body=steps(loop_.find("statement[@name='DO']/block"))
append=next(b for b in body if b.get('type')=='lists_add_items' and b.find("value[@name='LIST']/block/field").text=='分段')
entry=append.find("value[@name='ITEM0']/block");entry.find('mutation').set('items','5')
ET.SubElement(entry,'value',name='ADD4').append(boolean(False))
head=lambda:item(get('音符'),2)
last=lambda:item(get('分段'),长度(get('分段')))
def 长度(x):return block('lists_length',values={'LIST':x})
def 改(表,序号,值):return block('lists_replace_item',values={'LIST':表,'NUM':序号,'ITEM':值})
insert_after(append,[
    iff(compare('EQ',g('上一头时'),head()),[改(g('上一游玩键'),5,True),改(last(),5,True)]),
    put('上一头时',head()),put('上一游玩键',last())])
insert_after(stack[2],[put('上一头时',-10**12),put('上一游玩键',make_list())])

draw=procedures['绘制音符'];lines=steps(draw.find("statement[@name='STACK']/block/statement[@name='STACK']/block"))
paint,hold,width,visible=lines[:4]
gold=fresh(paint);color=gold.find("value[@name='VALUE']");color.remove(color.find('block'))
color.append(block('math_number',{'NUM':0xFFFFD54F-2**32}))
wide=fresh(width);wide.find("value[@name='VALUE']/block/field").text='24'
line=fresh(visible.find("statement[@name='DO0']/block"))
line.find("value[@name='ARG0']/block/field").text='5';line.find("value[@name='ARG2']/block/value[@name='B']/block/field").text='5'
key=fresh(paint.find("value[@name='COMPONENT']/block/value[@name='NUM']/block/value[@name='LIST']/block"))
insert_after(hold,[iff(both(item(key,5),fresh(visible.find("value[@name='IF0']/block"))),[gold,wide,line,fresh(paint)])])

used={b.get('id') for b in root.iter('block')};n=0
for b in root.iter('block'):
    if b.get('id')=='new' or b.get('id','').startswith('r4k_'):
        while 'Play_chord_'+str(n) in used:n+=1
        b.set('id','Play_chord_'+str(n));used.add(b.get('id'))
stamp=root.find('yacodeblocks')
if stamp is not None:root.remove(stamp);root.append(stamp)
root.set('xmlns','http://www.w3.org/1999/xhtml');ET.indent(root,space='  ')
bky.write_bytes(ET.tostring(root,encoding='utf-8'))
print(bky)
