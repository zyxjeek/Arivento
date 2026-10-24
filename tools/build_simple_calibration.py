from pathlib import Path
import sys,copy,io,wave,math,struct
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'archive/历史目录/tools'))
from 制谱器 import *
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'native/Arivento_1024_1'
OUT=ROOT/'native/Arivento_simple_calibration_source'
files={p.relative_to(SOURCE).as_posix():p.read_bytes() for p in SOURCE.rglob('*') if p.is_file()}
samples=[0]* (8*22050)
for beat in range(8):
    for i in range(2205):samples[11025+beat*22050+i]=round(20000*math.sin(2*math.pi*1000*i/22050)*math.exp(-i/22050*50)*min(1,i/15))
stream=io.BytesIO()
with wave.open(stream,'wb') as w:w.setparams((1,2,22050,0,'NONE','not compressed'));w.writeframes(struct.pack('<'+'h'*len(samples),*samples))
files['assets/arivento_calibration.wav']=stream.getvalue()
def body(b,items):
    s=b.find('statement');s.clear();s.set('name','DO' if b.get('type')=='component_event' else 'STACK');s.append(chain(items))
def glob(n,v):top(block('global_declaration',{'NAME':n},{'VALUE':v}),'')
def valid(v):return 全(数字(copy.deepcopy(v)),compare('GTE',copy.deepcopy(v),-400),compare('LTE',v,400))
def clamp(v):return maximum(-400,minimum(400,v))
for path in [n for n in files if n.endswith(('/Screen1.scm','/Play.scm'))]:
    screen=Path(path).stem;d=json.loads(files[path].decode().split('$JSON')[1].rsplit('|#',1)[0]);p=d['Properties']
    TYPES.clear();PROCS.clear();TOP.clear()
    def register(c):
        TYPES[c['$Name']]=c['$Type']
        for x in c.get('$Components',[]):register(x)
    register(p)
    bk=path[:-4]+'.bky';r=ET.fromstring(files[bk])
    for e in r.iter():e.tag=e.tag.split('}')[-1]
    parents={c:parent for parent in r.iter() for c in parent}
    for b in r.iter('block'):
        if b.get('type')=='math_number':
            f=b.find("field[@name='NUM']")
            if f.text in ['1000','-1000'] and parents[parents[b]].get('type') in ['math_compare','math_on_list']:f.text=str(int(f.text)*2//5)
        if b.get('type')=='text':
            f=b.find("field[@name='TEXT']")
            if f.text:f.text=f.text.replace('1000','400')
    procs={b.findtext("field[@name='NAME']"):b for b in r if b.get('type','').startswith('procedures_def')}
    for n,b in procs.items():PROCS[n]=[a.get('name') for a in b.find('mutation').findall('arg')]
    if screen=='Play':
        body(procs['轨道按下'],[iff(全(等(g('状态'),1),等(item(g('按住轨道'),get('轨道')),0)),[call('走时'),iff(等(g('状态'),1),[改(g('按住轨道'),get('轨道'),1),call('按轨',get('轨道'))])])])
        target=next(b for b in procs['按轨'].iter('block') if b.get('type')=='local_declaration_statement' and b.findtext("field[@name='VAR0']")=='头部判定')
        s=target.find('statement');old=s.find('block');s.remove(old)
        sound=iff(g('打击音开启'),[iff(等(get('轨道'),i),[method('打击音'+n,'Play')]) for i,n in enumerate(['一','二','三','四'],1)])
        s.append(chain([sound,old]))
    else:
        p.update(VersionCode='28',VersionName='1024.2')
        remove={'停止校准','启动校准','更新校准','绘制校准','完成测量','校准微调'}
        r[:]=[b for b in r if not (b.findtext("field[@name='NAME']") in remove or b.get('type')=='global_declaration' and b.findtext("field[@name='NAME']",'').startswith(('校准','试听')) or b.get('type')=='component_event' and b.find('mutation').get('instance_name','').startswith('校准'))]
        for n in remove:PROCS.pop(n,None)
        def revise(c):
            if c['$Name']=='延迟标题':c['Text']='谱面延迟（毫秒，-400～400）'
            if c['$Name']=='打击音设置':c['Text']='打击音效（有效按下时播放）'
            if c['$Name']=='校准页':
                c['$Components']=[x for x in c['$Components'] if x['$Name'] not in ['校准开始','校准试听']]
            if c['$Name']=='校准说明':c['Text']='调整延迟，让循环节拍器与音符落到白线时的打击音重合。无需点击音符。'
            if c['$Name']=='校准数值标题':c['Text']='延迟（-400～400ms，正数让音符与打击音更晚）'
            if c['$Name']=='校准提示':c['Text']='两种声音重合后，点击应用。'
            if c['$Name']=='校准音乐':c['Loop']='True'
            for x in c.get('$Components',[]):revise(x)
        revise(p)
        p['$Components'].append(component('校准打击','Sound',4,Source='arivento_hit.wav',MinimumInterval=0))
        for n,v in [('校准状态',0),('校准起点',0),('校准用时',0),('校准上次',0),('校准下一拍',0),('试听延迟',0)]:glob(n,v)
        PROCS.update({'停止校准':[],'启动校准':[],'更新校准':[],'绘制校准':[],'校准微调':['变化'],'调整校准':[]})
        now=lambda:method('校准时钟','SystemTime')
        target=lambda:add(500,mul(g('校准下一拍'),1000),g('试听延迟'))
        nextbeat=lambda:maximum(0,add(unary('FLOOR',div(sub(sub(g('校准用时'),500),g('试听延迟')),1000)),1))
        过程('停止校准',[设('校准时钟',False,'TimerEnabled'),put('校准状态',0),method('校准音乐','Stop'),method('校准打击','Stop')])
        过程('启动校准',[call('停止校准'),put('校准下一拍',0),put('校准用时',0),put('校准状态',1),put('校准起点',now()),设('校准提示','调节数值，让节拍器与打击音重合。'),method('校准音乐','Start'),iff(等(g('校准状态'),1),[设('校准时钟',True,'TimerEnabled'),call('更新校准')])])
        过程('调整校准',[iff(valid(取('校准数值')),[put('试听延迟',add(取('校准数值'),0)),put('校准用时',sub(now(),g('校准起点'))),put('校准下一拍',maximum(g('校准下一拍'),nextbeat())),设('校准提示','调节数值，让节拍器与打击音重合。')],[设('校准提示','请输入 -400～400 的数值')])])
        过程('校准微调',[iff(数字(取('校准数值')),[设('校准数值',clamp(add(取('校准数值'),get('变化')))),call('调整校准')],[设('校准提示','请输入 -400～400 的数值')])])
        过程('绘制校准',[method('校准画布','Clear'),设('校准画布',-1,'PaintColor'),设('校准画布',2,'LineWidth'),method('校准画布','DrawLine',15,140,sub(取('校准画布','Width'),15),140),
            设('校准画布',-11084049,'PaintColor'),设('校准画布',12,'LineWidth'),method('校准画布','DrawLine',sub(div(取('校准画布','Width'),2),35),sub(140,mul(sub(target(),g('校准用时')),.14)),add(div(取('校准画布','Width'),2),35),sub(140,mul(sub(target(),g('校准用时')),.14)))])
        过程('更新校准',[
            iff(等(g('校准状态'),1),[iff(取('校准音乐','IsPlaying'),[put('校准起点',now()),put('校准上次',now()),put('校准状态',2)],[iff(compare('GT',sub(now(),g('校准起点')),1500),[call('停止校准'),设('校准提示','音频无法播放，请返回后重新打开助手。')])])]),
            iff(等(g('校准状态'),2),[put('校准用时',sub(now(),g('校准起点'))),iff(either(compare('GT',sub(now(),g('校准上次')),500),非(取('校准音乐','IsPlaying'))),[call('启动校准')],[
                put('校准上次',now()),call('绘制校准'),iff(compare('GTE',g('校准用时'),target()),[iff(compare('LTE',sub(g('校准用时'),target()),120),[method('校准打击','Play')]),put('校准下一拍',nextbeat())])])])])
        事件('校准入口','Click',[iff(非(g('读取中')),[设('校准数值',选(数字(取('延迟输入')),clamp(add(取('延迟输入'),0)),0)),put('试听延迟',add(取('校准数值'),0)),设('首页',False,'Visible'),设('校准页',True,'Visible'),call('启动校准')])])
        事件('校准减少','Click',[call('校准微调',-10)]);事件('校准增加','Click',[call('校准微调',10)])
        事件('校准数值','LostFocus',[call('调整校准')])
        事件('校准应用','Click',[iff(valid(取('校准数值')),[call('停止校准'),设('延迟输入',add(取('校准数值'),0)),call('保存延迟'),设('校准页',False,'Visible'),设('首页',True,'Visible')],[设('校准提示','请输入 -400～400 的数值')])])
        事件('校准返回','Click',[call('停止校准'),设('校准页',False,'Visible'),设('首页',True,'Visible')])
        事件('校准时钟','Timer',[call('更新校准')])
        事件('校准音乐','OtherPlayerStarted',[call('停止校准'),设('校准提示','音频被打断，请返回后重新打开助手。')])
        err=next(b for b in r if b.get('type')=='component_event' and b.find('mutation').get('event_name')=='ErrorOccurred')
        old=copy.deepcopy(err.find('statement/block'))
        component_ref=block('component_component_block',{'COMPONENT_SELECTOR':'校准打击'},mutation=mut(component_type='Sound',instance_name='校准打击'))
        body(err,[iff(等(get('组件'),component_ref),[call('停止校准'),设('校准提示','打击音无法播放，请返回后重试。')],[old])])
    r.extend(TOP);stamp=r.find('yacodeblocks');r.remove(stamp);r.append(stamp)
    for i,b in enumerate(r.iter('block')):b.set('id',screen+'_simple_'+str(i))
    r.set('xmlns','http://www.w3.org/1999/xhtml');ET.indent(r,space='  ')
    files[bk]=ET.tostring(r,encoding='utf-8');files[path]=('#|\n$JSON\n'+json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode()
prop='youngandroidproject/project.properties';values={'versioncode':'28','versionname':'1024.2'}
files[prop]=('\n'.join(k+'='+values[k] if (k:=line.split('=',1)[0]) in values else line for line in files[prop].decode().splitlines())+'\n').encode()
for n,data in files.items():
    dest=OUT/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
with zipfile.ZipFile(ROOT/'archive/hold_base_1016/Simple_candidate.aia','w',zipfile.ZIP_DEFLATED) as z:
    for n,data in files.items():z.writestr(n,data)
print(OUT)
