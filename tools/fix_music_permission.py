from pathlib import Path
import copy,json,sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'archive/历史目录/tools'))
from 制谱器 import *

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'native'/json.loads((ROOT/'tools/current_release.json').read_text(encoding='utf-8'))['name']
scm=next(source.rglob('Screen1.scm'));bky=scm.with_suffix('.bky')
design=json.loads(scm.read_text(encoding='utf-8').split('$JSON')[1].rsplit('|#',1)[0]);components={}
def register(c):
    components[c['$Name']]=c;TYPES[c['$Name']]=c['$Type']
    for x in c.get('$Components',[]):register(x)
register(design['Properties'])
components['音乐检查']['Source']=''
components['打击音量标题']['Text']='打击音量：20%'
root=ET.fromstring(bky.read_bytes())
for e in root.iter():e.tag=e.tag.split('}')[-1]
for b in root.iter('block'):
    if b.get('type')=='text':
        f=b.find("field[@name='TEXT']")
        if f.text:f.text=f.text.replace('（20%为原音量）','').replace('（原音量）','')
procedures={b.findtext("field[@name='NAME']"):b for b in root if b.get('type','').startswith('procedures_def')}
for name,b in procedures.items():PROCS[name]=[a.get('name') for a in b.find('mutation').findall('arg')]
def body(b,items):
    s=b.find('statement');s.clear();s.set('name','DO' if b.get('type')=='component_event' else 'STACK');s.append(chain(items))
def ref(name):return block('component_component_block',{'COMPONENT_SELECTOR':name},mutation=mut(component_type=TYPES[name],instance_name=name))
if '完成音乐检查' not in procedures:
    c=component('音乐检查时钟','Clock',int(components['校准时钟']['$Version']),TimerInterval=100,TimerEnabled='False',TimerAlwaysFires='False')
    c['Uuid']=str(max(int(c.get('Uuid','0')) for c in components.values())+1)
    design['Properties']['$Components'].append(c)
    for name,value in [('检查音乐地址',''),('音乐权限拒绝',False)]:root.insert(0,block('global_declaration',{'NAME':name},{'VALUE':value}))
    PROCS.update({'完成音乐检查':['成功'],'继续音乐检查':[]})
    failure=选(g('音乐权限拒绝'),'未获得音乐访问权限，请重新选择音乐并允许读取音频','音乐源文件找不到、无访问权限或无法播放，请重新选择本地音乐')
    过程('完成音乐检查',[
        设('音乐检查时钟',False,'TimerEnabled'),put('正在检查',False),method('音乐检查','Stop'),设('音乐检查','','Source'),
        iff(get('成功'),[改(g('当前谱'),2,g('检查音乐地址')),put('音乐就绪',True),call('保存当前谱'),设('读取状态','已保存谱面与音乐，可以开始游玩')],
            [put('音乐就绪',False),设('读取状态',copy.deepcopy(failure)),警告(failure)]),
        put('检查音乐地址',''),call('恢复入口')])
    过程('继续音乐检查',[iff(g('正在检查'),[
        iff(g('检查失败'),[call('完成音乐检查',False)],[
            iff(等(取('音乐检查','Source'),g('检查音乐地址')),[method('音乐检查','Start'),call('完成音乐检查',全(非(g('检查失败')),取('音乐检查','IsPlaying')))])])])])
    body(procedures['连接音乐'],[iff(全(非(g('正在检查')),等(长(g('当前谱')),8),非(等(get('地址'),''))),[
        put('检查音乐地址',get('地址')),put('音乐权限拒绝',False),put('音乐就绪',False),put('检查失败',False),put('正在检查',True),
        call('恢复入口'),设('读取状态','正在检查音乐；如有权限弹窗，请允许读取音频'),
        设('音乐检查时钟',True,'TimerEnabled'),设('音乐检查',g('检查音乐地址'),'Source'),call('继续音乐检查')])])
    body(procedures['恢复入口'],[
        put('读取中',g('正在检查')),*[设(n,非(g('正在检查')),'Enabled') for n in ['选谱','保存谱面','制谱']],
        设('选音乐',全(等(长(g('当前谱')),8),非(g('正在检查'))),'Enabled'),
        设('开始',全(等(长(g('当前谱')),8),g('音乐就绪'),非(g('正在检查'))),'Enabled')])
    事件('音乐检查时钟','Timer',[call('继续音乐检查')])
    error=next(b for b in root if b.get('type')=='component_event' and b.find('mutation').get('event_name')=='ErrorOccurred')
    original=copy.deepcopy(error.find('statement/block'))
    body(error,[iff(等(get('组件'),ref('音乐检查')),[put('检查失败',True),put('音乐就绪',False),设('开始',False,'Enabled')],[original])])
    denied=next(b for b in root if b.get('type')=='component_event' and b.find('mutation').get('event_name')=='PermissionDenied')
    original=copy.deepcopy(denied.find('statement/block'))
    body(denied,[iff(全(g('正在检查'),等(get('组件'),ref('音乐检查'))),[
        put('检查失败',True),put('音乐权限拒绝',True),设('开始',False,'Enabled')],[original])])
    root.extend(TOP)
stamp=root.find('yacodeblocks');root.remove(stamp);root.append(stamp)
for i,b in enumerate(root.iter('block')):b.set('id','Screen1_music_permission_'+str(i))
root.set('xmlns','http://www.w3.org/1999/xhtml');ET.indent(root,space='  ')
bky.write_bytes(ET.tostring(root,encoding='utf-8'))
scm.write_bytes(('#|\n$JSON\n'+json.dumps(design,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode())
print(source)
