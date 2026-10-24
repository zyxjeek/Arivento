from pathlib import Path
import sys,copy,io,wave,math,random,struct
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'archive/历史目录/tools'))
from 制谱器 import *
from build_native_tracks import ref,prepend
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'native/Arivento_1017_3'
OUT=ROOT/'native/Arivento_calibration_source'
files={p.relative_to(SOURCE).as_posix():p.read_bytes() for p in SOURCE.rglob('*') if p.is_file()}
def wav(samples):
    stream=io.BytesIO()
    with wave.open(stream,'wb') as w:w.setparams((1,2,22050,0,'NONE','not compressed'));w.writeframes(struct.pack('<'+'h'*len(samples),*[round(max(-1,min(1,v))*32767) for v in samples]))
    return stream.getvalue()
rng=random.Random(4)
hit=[.25*(.65*math.sin(2*math.pi*1550*i/22050)+.35*rng.uniform(-1,1))*math.exp(-i/22050*95)*min(1,i/12) for i in range(1103)]
files['assets/arivento_hit.wav']=wav(hit)
track=[0.0]*int(36*22050)
for beat in range(14):
    start=round((2+2.5*beat)*22050)
    for i in range(2205):track[start+i]=.65*math.sin(2*math.pi*1000*i/22050)*math.exp(-i/22050*50)*min(1,i/15)
files['assets/arivento_calibration.wav']=wav(track)

def body(b,items):
    s=b.find('statement');s.clear();s.set('name','DO' if b.get('type')=='component_event' else 'STACK');s.append(chain(items))
def append(b,items):
    last=b.find('statement/block')
    while last.find('next/block') is not None:last=last.find('next/block')
    ET.SubElement(last,'next').append(chain(items))
def glob(n,v):top(block('global_declaration',{'NAME':n},{'VALUE':v}),'')
def limited(v):return maximum(-1000,minimum(1000,v))
def valid(v):return 全(数字(copy.deepcopy(v)),compare('GTE',copy.deepcopy(v),-1000),compare('LTE',v,1000))
def label(n,t,**kw):return component(n,'Label',5,Text=t,TextColor=白色,Width=-2,FontSize=15,**kw)
def button(n,t):return component(n,'Button',7,Text=t,Width=-2,Height=42,BackgroundColor='&HFF151E32',TextColor=白色,FontSize=15)
for path in [n for n in files if n.endswith(('/Screen1.scm','/Play.scm'))]:
    screen=Path(path).stem;d=json.loads(files[path].decode().split('$JSON')[1].rsplit('|#',1)[0]);p=d['Properties']
    TYPES.clear();PROCS.clear();TOP.clear()
    def register(c):
        TYPES[c['$Name']]=c['$Type']
        for x in c.get('$Components',[]):register(x)
    register(p)
    bk=path[:-4]+'.bky';r=ET.fromstring(files[bk])
    for e in r.iter():e.tag=e.tag.split('}')[-1]
    procs={b.findtext("field[@name='NAME']"):b for b in r if b.get('type','').startswith('procedures_def')}
    for n,b in procs.items():PROCS[n]=[a.get('name') for a in b.find('mutation').findall('arg')]
    def ev(n,event):return next(b for b in r if b.get('type')=='component_event' and b.find('mutation').get('instance_name')==n and b.find('mutation').get('event_name')==event)
    for b in r.iter('block'):
        if b.get('type')=='math_number':
            f=b.find("field[@name='NUM']")
            if f.text in ['200','-200']:f.text=str(int(f.text)*5)
        if b.get('type')=='text':
            f=b.find("field[@name='TEXT']")
            if f.text:f.text=f.text.replace('-200','-1000').replace('～200','～1000').replace('到200','到1000')
    if screen=='Play':
        p['$Components'].append(component('本地设置','TinyDB',3,Namespace='Arivento'))
        for n in ['一','二','三','四']:p['$Components'].append(component('打击音'+n,'Sound',4,Source='arivento_hit.wav',MinimumInterval=0))
        glob('打击音开启',True)
        prepend(ev('Play','Initialize').find('statement'),[put('打击音开启',method('本地设置','GetValue','打击音效',True))])
        old=procs['按轨'].find('statement/block');assert old.find('mutation').get('name')=='走时'
        rest=old.find('next/block');s=procs['按轨'].find('statement');s.remove(old);s.append(rest)
        body(procs['轨道按下'],[iff(全(等(g('状态'),1),等(item(g('按住轨道'),get('轨道')),0)),[
            iff(g('打击音开启'),[iff(等(get('轨道'),i),[method('打击音'+n,'Play')]) for i,n in enumerate(['一','二','三','四'],1)]),
            call('走时'),iff(等(g('状态'),1),[改(g('按住轨道'),get('轨道'),1),call('按轨',get('轨道'))])])])
        err=ev('Play','ErrorOccurred');old=copy.deepcopy(err.find('statement/block'))
        sound_error=包含(make_list(*[ref('打击音'+n) for n in ['一','二','三','四']]),get('组件'))
        body(err,[iff(sound_error,[put('打击音开启',False)],[old])])
    else:
        p.update(VersionCode='27',VersionName='1024.1')
        for c in p['$Components']:
            if c['$Type']=='Player':c['$Version']='8'
        home=p['$Components'][0];children=home['$Components']
        for c in children:
            if c['$Name']=='延迟标题':c['Text']='谱面延迟（毫秒，-1000～1000）'
        idx=next(i for i,c in enumerate(children) if c['$Name']=='延迟输入')+1
        children[idx:idx]=[button('校准入口','延迟设置助手'),component('打击音设置','CheckBox',3,Text='打击音效（按下时播放）',Checked='True',TextColor=白色,Width=-2,FontSize=15)]
        panel=component('校准页','VerticalArrangement',4,[label('校准标题','延迟设置助手',FontBold='True'),
            label('校准说明','佩戴游玩时使用的耳机。先听两拍，再在听到提示音的瞬间点击圆点区域。不要等看到圆点才按。每拍间隔 2.5 秒。'),
            component('校准画布','Canvas',15,Width=-2,Height=170,BackgroundColor=背景),
            label('校准提示','建议先跟拍测量，再试听微调；更换设备或耳机后可重测。'),button('校准开始','开始跟拍测量'),
            label('校准数值标题','延迟值（-1000～1000ms，正数延后谱面）'),component('校准数值','TextBox',6,Text='0',Width=-2,Height=40,TextColor=白色,BackgroundColor='&HFF151E32'),
            component('校准调整','HorizontalArrangement',4,[button('校准减少','−10ms'),button('校准增加','+10ms')],Width=-2),
            button('校准试听','试听当前设置'),button('校准应用','应用并返回'),button('校准返回','取消并返回')],Width=-2,Height=-1,Visible='False')
        panel['$Components'][7]['$Components'][0]['Width']='-1050';panel['$Components'][7]['$Components'][1]['Width']='-1050'
        p['$Components'].extend([panel,component('校准音乐','Player',8,Source='arivento_calibration.wav',Volume=80,PlayOnlyInForeground='True'),component('校准时钟','Clock',4,TimerInterval=16,TimerEnabled='False',TimerAlwaysFires='False')])
        for n,v in [('校准状态',0),('校准模式',0),('校准起点',0),('校准用时',0),('校准上次',0),('校准上拍',-1),('校准数量',0),('校准总差',0),('校准最小',1001),('校准最大',-1001),('试听延迟',0)]:glob(n,v)
        PROCS.update({'停止校准':[],'启动校准':['模式'],'更新校准':[],'绘制校准':[],'完成测量':[],'保存延迟':[],'校准微调':['变化']})
        now=lambda:method('校准时钟','SystemTime')
        过程('停止校准',[设('校准时钟',False,'TimerEnabled'),put('校准状态',0),method('校准音乐','Stop'),设('校准开始',True,'Enabled'),设('校准试听',True,'Enabled'),设('校准应用',True,'Enabled')])
        过程('保存延迟',[iff(valid(取('延迟输入')),[method('本地记录','StoreValue','谱面延迟',add(取('延迟输入'),0))])])
        过程('启动校准',[call('停止校准'),put('校准模式',get('模式')),put('校准数量',0),put('校准总差',0),put('校准最小',1001),put('校准最大',-1001),put('校准上拍',-1),put('校准用时',0),put('校准状态',1),put('校准起点',now()),
            设('校准开始',False,'Enabled'),设('校准试听',False,'Enabled'),设('校准应用',False,'Enabled'),设('校准提示','先听两拍熟悉节奏，再开始点击。'),method('校准音乐','Start'),iff(等(g('校准状态'),1),[设('校准时钟',True,'TimerEnabled'),call('更新校准')])])
        过程('完成测量',[call('停止校准'),iff(compare('GTE',g('校准数量'),8),[
            iff(compare('LTE',sub(g('校准最大'),g('校准最小')),250),[设('校准数值',limited(unary('ROUND',div(sub(sub(g('校准总差'),g('校准最小')),g('校准最大')),sub(g('校准数量'),2))))),设('校准提示',join('建议延迟 ',取('校准数值'),'ms。可试听微调，满意后应用。'))],[设('校准提示','点击波动较大，本次不更新建议值。请跟随声音重测。')])],[设('校准提示','有效点击不足 8 次，本次不更新建议值。请重新测量。')])])
        过程('更新校准',[
            iff(等(g('校准状态'),1),[iff(取('校准音乐','IsPlaying'),[put('校准起点',now()),put('校准上次',now()),put('校准状态',2)],[iff(compare('GT',sub(now(),g('校准起点')),1500),[call('停止校准'),设('校准提示','提示音无法播放，请检查音量并重新开始。')])])]),
            iff(等(g('校准状态'),2),[put('校准用时',sub(now(),g('校准起点'))),
                iff(compare('GT',sub(now(),g('校准上次')),500),[call('停止校准'),设('校准提示','检测到中断或明显卡顿，请重新测量。')],[
                    put('校准上次',now()),call('绘制校准'),iff(compare('GTE',g('校准用时'),36000),[iff(等(g('校准模式'),1),[call('完成测量')],[call('停止校准'),设('校准提示','试听结束，可继续微调或应用。')])],[iff(非(取('校准音乐','IsPlaying')),[call('停止校准'),设('校准提示','提示音被中断，请重新测量。')])])])])])
        offset=lambda:选(等(g('校准模式'),2),g('试听延迟'),0)
        过程('绘制校准',[method('校准画布','Clear'),设('校准画布',-1,'PaintColor'),设('校准画布',2,'LineWidth'),method('校准画布','DrawLine',div(取('校准画布','Width'),2),15,div(取('校准画布','Width'),2),150),
            local('拍号',unary('ROUND',div(sub(sub(g('校准用时'),2000),offset()),2500)),[
                local('距离',sub(g('校准用时'),add(2000,mul(get('拍号'),2500),offset())),[
                    设('校准画布',-11084049,'PaintColor'),method('校准画布','DrawCircle',mul(add(.5,div(get('距离'),2500)),取('校准画布','Width')),80,18,True)])])])
        过程('校准微调',[iff(valid(取('校准数值')),[call('停止校准'),设('校准数值',limited(add(取('校准数值'),get('变化'))))],[警告('请输入 -1000～1000 的延迟值')])])
        事件('校准入口','Click',[iff(非(g('读取中')),[call('停止校准'),设('校准数值',选(valid(取('延迟输入')),add(取('延迟输入'),0),0)),设('首页',False,'Visible'),设('校准页',True,'Visible'),设('校准提示','先跟拍测量，再试听微调。点击只按声音判断。')])])
        事件('校准开始','Click',[call('启动校准',1)])
        事件('校准试听','Click',[iff(valid(取('校准数值')),[put('试听延迟',add(取('校准数值'),0)),call('启动校准',2),设('校准提示','圆点经过白线时应与提示音同步；可点击查看误差。')],[警告('请输入 -1000～1000 的延迟值')])])
        事件('校准减少','Click',[call('校准微调',-10)]);事件('校准增加','Click',[call('校准微调',10)])
        事件('校准应用','Click',[iff(valid(取('校准数值')),[call('停止校准'),设('延迟输入',add(取('校准数值'),0)),call('保存延迟'),设('校准页',False,'Visible'),设('首页',True,'Visible')],[警告('请输入 -1000～1000 的延迟值')])])
        事件('校准返回','Click',[call('停止校准'),设('校准页',False,'Visible'),设('首页',True,'Visible')])
        事件('校准时钟','Timer',[call('更新校准')])
        事件('校准音乐','OtherPlayerStarted',[call('停止校准'),设('校准提示','音频被其他应用打断，请重新测量。')])
        事件('校准画布','TouchDown',[iff(等(g('校准状态'),2),[
            local('点击时间',sub(now(),g('校准起点')),[local('拍号',unary('ROUND',div(sub(get('点击时间'),2000),2500)),[
                local('偏差',sub(get('点击时间'),add(2000,mul(get('拍号'),2500))),[
                    iff(等(g('校准模式'),2),[设('校准提示',join('本次点击相对当前设置：',unary('ROUND',sub(get('偏差'),g('试听延迟'))),'ms（正数为晚按）'))],[
                        iff(全(compare('GTE',get('拍号'),2),compare('LTE',get('拍号'),13),compare('GT',get('拍号'),g('校准上拍')),compare('LTE',unary('ABS',get('偏差')),1000)),[
                            put('校准上拍',get('拍号')),change('校准数量'),put('校准总差',add(g('校准总差'),get('偏差'))),put('校准最小',minimum(g('校准最小'),get('偏差'))),put('校准最大',maximum(g('校准最大'),get('偏差'))),
                            设('校准提示',join('已记录 ',g('校准数量'),'/12；本次偏差 ',unary('ROUND',get('偏差')),'ms')),iff(compare('GTE',g('校准数量'),12),[call('完成测量')])])])])])])])],['横坐标','纵坐标'])
        事件('打击音设置','Changed',[method('本地记录','StoreValue','打击音效',取('打击音设置','Checked'))])
        事件('延迟输入','LostFocus',[call('保存延迟')])
        append(ev('Screen1','Initialize'),[local('原延迟',method('本地记录','GetValue','谱面延迟',0),[设('延迟输入',选(valid(get('原延迟')),get('原延迟'),0))]),设('打击音设置',method('本地记录','GetValue','打击音效',True),'Checked')])
        for parent in list(ev('开始','Click').iter()):
            for b in list(parent):
                if b.get('type')=='controls_openAnotherScreenWithStartValue':parent.remove(b);parent.append(chain([call('保存延迟'),b]))
        error=ev('Screen1','ErrorOccurred');old=copy.deepcopy(error.find('statement/block'))
        body(error,[iff(等(get('组件'),ref('校准音乐')),[call('停止校准'),设('校准提示','提示音无法播放，请重新进入校准助手。')],[old])])
        backs=[b for b in r if b.get('type')=='component_event' and b.find('mutation').get('event_name')=='BackPressed']
        if backs:
            old=copy.deepcopy(backs[0].find('statement/block'));body(backs[0],[iff(取('校准页','Visible'),[call('停止校准'),设('校准页',False,'Visible'),设('首页',True,'Visible')],[old])])
        else:事件('Screen1','BackPressed',[iff(取('校准页','Visible'),[call('停止校准'),设('校准页',False,'Visible'),设('首页',True,'Visible')],[block('controls_closeApplication')])])
    r.extend(TOP);stamp=r.find('yacodeblocks');r.remove(stamp);r.append(stamp)
    for i,b in enumerate(r.iter('block')):b.set('id',screen+'_cal_'+str(i))
    r.set('xmlns','http://www.w3.org/1999/xhtml');ET.indent(r,space='  ')
    files[bk]=ET.tostring(r,encoding='utf-8');files[path]=('#|\n$JSON\n'+json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode()
prop='youngandroidproject/project.properties';values={'versioncode':'27','versionname':'1024.1'}
files[prop]=('\n'.join(k+'='+values[k] if (k:=line.split('=',1)[0]) in values else line for line in files[prop].decode().splitlines())+'\n').encode()
for n,data in files.items():
    dest=OUT/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
with zipfile.ZipFile(ROOT/'archive/hold_base_1016/Calibration_candidate.aia','w',zipfile.ZIP_DEFLATED) as z:
    for n,data in files.items():z.writestr(n,data)
print(OUT)

