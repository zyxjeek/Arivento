from pathlib import Path
import copy,json,struct,sys,wave

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'archive/历史目录/tools'))
from 制谱器 import *

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'native'/json.loads((ROOT/'tools/current_release.json').read_text(encoding='utf-8'))['name']
original=source/'assets/arivento_hit.wav'
with wave.open(str(original),'rb') as w:
    params=w.getparams();data=struct.unpack('<'+'h'*(w.getnframes()*w.getnchannels()),w.readframes(w.getnframes()))
assert params.sampwidth==2
peak=max(map(abs,data));maximum_gain=32767/peak
for volume in range(101):
    path=source/'assets'/f'arivento_hit_{volume}.wav'
    if volume==20:path.write_bytes(original.read_bytes());continue
    gain=volume/20 if volume<=20 else 1+(volume-20)/80*(maximum_gain-1)
    samples=[round(v*gain) for v in data]
    assert all(-32768<=v<=32767 for v in samples)
    with wave.open(str(path),'wb') as w:
        w.setparams(params);w.writeframes(struct.pack('<'+'h'*len(samples),*samples))

for screen in ['Screen1','Play']:
    TYPES.clear();PROCS.clear();TOP.clear()
    scm=next(source.rglob(screen+'.scm'));bky=scm.with_suffix('.bky')
    design=json.loads(scm.read_text(encoding='utf-8').split('$JSON')[1].rsplit('|#',1)[0]);components={}
    def register(c):
        components[c['$Name']]=c;TYPES[c['$Name']]=c['$Type']
        for x in c.get('$Components',[]):register(x)
    register(design['Properties'])
    root=ET.fromstring(bky.read_bytes())
    for e in root.iter():e.tag=e.tag.split('}')[-1]
    if any(b.findtext("field[@name='NAME']")=='打击音量' for b in root):continue
    procedures={b.findtext("field[@name='NAME']"):b for b in root if b.get('type','').startswith('procedures_def')}
    for name,b in procedures.items():PROCS[name]=[a.get('name') for a in b.find('mutation').findall('arg')]
    def append(b,items):
        s=b.find('statement');last=s.find('block')
        if last is None:s.append(chain(items));return
        while last.find('next/block') is not None:last=last.find('next/block')
        ET.SubElement(last,'next').append(chain(items))
    def normalized(value):return 选(数字(copy.deepcopy(value)),maximum(0,minimum(100,unary('ROUND',add(value,0)))),20)
    def filename():return join('arivento_hit_',g('打击音量'),'.wav')
    root.insert(0,block('global_declaration',{'NAME':'打击音量'},{'VALUE':20}))
    db='本地记录' if screen=='Screen1' else '本地设置'
    init=next(b for b in root if b.get('type')=='component_event' and b.find('mutation').get('instance_name')==screen and b.find('mutation').get('event_name')=='Initialize')
    load=local('原音量',method(db,'GetValue','打击音量',20),[put('打击音量',normalized(get('原音量')))])
    if screen=='Screen1':
        home=components['首页']['$Components'];index=next(i for i,c in enumerate(home) if c['$Name']=='打击音设置')+1
        label=component('打击音量标题','Label',int(components['延迟标题']['$Version']),Text='打击音量：20%（原音量）',TextColor=白色,Width=-2,FontSize=15)
        slider=component('打击音量滑条','Slider',3,MinValue=0,MaxValue=100,NumberOfSteps=100,ThumbPosition=20,ThumbEnabled='True',Width=-2,ColorLeft='&HFF56DEEF',ColorRight='&HFF334155',ThumbColor='&HFF56DEEF')
        uid=max(int(c.get('Uuid','0')) for c in components.values())+1
        label['Uuid']=str(uid);slider['Uuid']=str(uid+1);home[index:index]=[label,slider]
        root.insert(0,block('global_declaration',{'NAME':'音量已就绪'},{'VALUE':False}))
        PROCS['应用打击音量']=[]
        过程('应用打击音量',[
            设('打击音量标题',join('打击音量：',g('打击音量'),'%（20%为原音量）')),
            iff(非(等(取('校准打击','Source'),filename())),[设('校准打击',filename(),'Source')])])
        append(init,[load,设('打击音量滑条',g('打击音量'),'ThumbPosition'),call('应用打击音量'),put('音量已就绪',True)])
        事件('打击音量滑条','PositionChanged',[iff(g('音量已就绪'),[
            put('打击音量',normalized(get('位置'))),method(db,'StoreValue','打击音量',g('打击音量')),call('应用打击音量')])],['位置'])
        sounds=['校准打击']
    else:
        sounds=['打击音'+n for n in ['一','二','三','四']]
        append(init,[load]+[iff(非(等(取(n,'Source'),filename())),[设(n,filename(),'Source')]) for n in sounds])
    for n in sounds:components[n]['Source']='arivento_hit_20.wav'
    parents={c:p for p in root.iter() for c in p}
    for b in list(root.iter('block')):
        m=b.find('mutation')
        if b.get('type')!='component_method' or m.get('method_name')!='Play' or m.get('instance_name') not in sounds:continue
        parent=parents[b];pos=list(parent).index(b);parent.remove(b)
        nxt=b.find('next')
        if nxt is not None:b.remove(nxt)
        guarded=iff(compare('GT',g('打击音量'),0),[b])
        if nxt is not None:guarded.append(nxt)
        parent.insert(pos,guarded)
    root.extend(TOP)
    stamp=root.find('yacodeblocks');root.remove(stamp);root.append(stamp)
    for i,b in enumerate(root.iter('block')):b.set('id',screen+'_hit_volume_'+str(i))
    root.set('xmlns','http://www.w3.org/1999/xhtml');ET.indent(root,space='  ')
    bky.write_bytes(ET.tostring(root,encoding='utf-8'))
    scm.write_bytes(('#|\n$JSON\n'+json.dumps(design,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode())
print(source)
