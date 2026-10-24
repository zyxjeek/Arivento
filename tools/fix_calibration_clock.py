from pathlib import Path
import copy,io,json,sys,wave

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'archive/历史目录/tools'))
from 制谱器 import *

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'native'/json.loads((ROOT/'tools/current_release.json').read_text(encoding='utf-8'))['name']
scm=next(source.rglob('Screen1.scm'));bky=scm.with_suffix('.bky')
design=json.loads(scm.read_text(encoding='utf-8').split('$JSON')[1].rsplit('|#',1)[0])
components={}
def register(c):
    components[c['$Name']]=c;TYPES[c['$Name']]=c['$Type']
    for x in c.get('$Components',[]):register(x)
register(design['Properties'])
if '校准节拍' not in components:
    c=component('校准节拍','Sound',int(components['校准打击']['$Version']),Source='arivento_metronome.wav',MinimumInterval=0)
    c['Uuid']=str(max(int(c.get('Uuid','0')) for c in components.values())+1)
    design['Properties']['$Components'].append(c)
components['校准时钟']['TimerInterval']='10'
components['校准音乐']['Loop']='False'
root=ET.fromstring(bky.read_bytes())
for e in root.iter():e.tag=e.tag.split('}')[-1]
procedures={b.findtext("field[@name='NAME']"):b for b in root if b.get('type','').startswith('procedures_def')}
for name,b in procedures.items():PROCS[name]=[a.get('name') for a in b.find('mutation').findall('arg')]
def body(b,items):
    s=b.find('statement');s.clear();s.set('name','DO' if b.get('type')=='component_event' else 'STACK');s.append(chain(items))
def now():return method('校准时钟','SystemTime')
def target(counter,delay):return add(500,mul(g(counter),1000),delay)
def nextbeat(delay):return maximum(0,add(unary('FLOOR',div(sub(sub(g('校准用时'),500),delay),1000)),1))
def sound(counter,delay,name):
    return iff(全(等(g('校准状态'),2),compare('GTE',g('校准用时'),target(counter,copy.deepcopy(delay)))),[
        iff(compare('LTE',sub(g('校准用时'),target(counter,copy.deepcopy(delay))),120),[method(name,'Play')]),
        put(counter,nextbeat(delay))])
if not any(b.get('type')=='global_declaration' and b.findtext("field[@name='NAME']")=='校准节拍号' for b in root):
    root.insert(0,block('global_declaration',{'NAME':'校准节拍号'},{'VALUE':0}))
body(procedures['停止校准'],[设('校准时钟',False,'TimerEnabled'),put('校准状态',0),method('校准音乐','Stop'),method('校准节拍','Stop'),method('校准打击','Stop')])
body(procedures['启动校准'],[call('停止校准'),put('校准下一拍',0),put('校准节拍号',0),put('校准用时',0),put('校准起点',now()),put('校准上次',g('校准起点')),put('校准状态',2),设('校准提示','调节数值，让节拍器与打击音重合。'),设('校准时钟',True,'TimerEnabled'),call('更新校准')])
body(procedures['更新校准'],[iff(等(g('校准状态'),2),[
    local('校准当前',now(),[
        put('校准用时',sub(get('校准当前'),g('校准起点'))),
        iff(compare('LT',get('校准当前'),g('校准上次')),[call('启动校准')],[
            iff(compare('GT',sub(get('校准当前'),g('校准上次')),120),[
                local('恢复拍号',nextbeat(minimum(0,g('试听延迟'))),[
                    put('校准节拍号',maximum(g('校准节拍号'),get('恢复拍号'))),
                    put('校准下一拍',maximum(g('校准下一拍'),get('恢复拍号')))])]),
            put('校准上次',get('校准当前')),
            sound('校准节拍号',0,'校准节拍'),sound('校准下一拍',g('试听延迟'),'校准打击'),iff(等(g('校准状态'),2),[call('绘制校准')])])])])])
error=next(b for b in root if b.get('type')=='component_event' and b.find('mutation').get('event_name')=='ErrorOccurred')
if not any(b.get('type')=='component_component_block' and b.find('mutation').get('instance_name')=='校准节拍' for b in error.iter('block')):
    original=copy.deepcopy(error.find('statement/block'))
    ref=block('component_component_block',{'COMPONENT_SELECTOR':'校准节拍'},mutation=mut(component_type='Sound',instance_name='校准节拍'))
    body(error,[iff(等(get('组件'),ref),[call('停止校准'),设('校准提示','节拍音无法播放，请返回后重试。')],[original])])
for i,b in enumerate(root.iter('block')):b.set('id','Screen1_shared_clock_'+str(i))
root.set('xmlns','http://www.w3.org/1999/xhtml');ET.indent(root,space='  ')
bky.write_bytes(ET.tostring(root,encoding='utf-8'))
scm.write_bytes(('#|\n$JSON\n'+json.dumps(design,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode())
with wave.open(str(source/'assets/arivento_calibration.wav'),'rb') as w:
    params=w.getparams();w.setpos(w.getframerate()//2);samples=w.readframes(w.getframerate()//10)
with wave.open(str(source/'assets/arivento_metronome.wav'),'wb') as w:
    w.setparams(params);w.writeframes(samples)
print(source)
