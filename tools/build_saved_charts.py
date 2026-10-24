from pathlib import Path
import sys,copy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'archive/历史目录/tools'))
from 制谱器 import *
from build_native_tracks import ref,prepend
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'native/Arivento_1017_1'
OUT=ROOT/'native/Arivento_saved_source'
files={p.relative_to(SOURCE).as_posix():p.read_bytes() for p in SOURCE.rglob('*') if p.is_file()}
path=next(n for n in files if n.endswith('/Screen1.scm'))
d=json.loads(files[path].decode().split('$JSON')[1].rsplit('|#',1)[0]);p=d['Properties']
p.update(Title='Arivento',VersionCode='26',VersionName='1017.3',Scrollable='True')
TOP.clear();TYPES.clear();PROCS.clear()
def register(c):
    TYPES[c['$Name']]=c['$Type']
    for x in c.get('$Components',[]):register(x)
register(p)
home=p['$Components'][0];home.update(Height='-1',AlignVertical='1')
children=home['$Components'];title=next(x for x in children if x['$Name']=='标题');title['Text']='Arivento'
legacy=next(x for x in children if x['$Name']=='制谱');children.remove(legacy)
legacy.update(Text='Legacy 制谱器',FontSize='12',Height='32',Width='-1',BackgroundColor=背景,TextColor='&HFF8994A8',ShowFeedback='False')
children.insert(1,component('当前谱名','Label',5,Text='尚未选择谱面',TextColor=白色,Width=-2,TextAlignment=1,FontSize=14))
children.insert(4,component('保存谱面','ListPicker',10,Text='保存的谱面（0）',Title='保存的谱面',ElementsFromString='',ShowFilterBar='True',Width=-2,Height=44,BackgroundColor='&HFF151E32',TextColor=白色,FontSize=16,ItemBackgroundColor=背景,ItemTextColor=白色))
children.extend([component('底部留白','Label',5,Text='',Height=24),component('底部入口','HorizontalArrangement',4,[legacy],Width=-2,AlignHorizontal=2)])
p['$Components'].extend([component('本地记录','TinyDB',3,Namespace='Arivento'),component('音乐检查','Player',6,Volume=0,PlayOnlyInForeground='True')])
bk=path[:-4]+'.bky';r=ET.fromstring(files[bk])
for e in r.iter():e.tag=e.tag.split('}')[-1]
procs={b.findtext("field[@name='NAME']"):b for b in r if b.get('type','').startswith('procedures_def')}
for n,b in procs.items():PROCS[n]=[a.get('name') for a in b.find('mutation').findall('arg')]
def ev(name,event):return next(b for b in r if b.get('type')=='component_event' and b.find('mutation').get('instance_name')==name and b.find('mutation').get('event_name')==event)
def body(b,items):
    s=b.find('statement');s.clear();s.set('name','DO' if b.get('type')=='component_event' else 'STACK');s.append(chain(items))
def append(b,items):
    last=b.find('statement/block')
    while last.find('next/block') is not None:last=last.find('next/block')
    ET.SubElement(last,'next').append(chain(items))
for name,value in [('保存列表',make_list()),('谱面地址',''),('待用音乐',''),('检查失败',False),('正在检查',False)]:top(block('global_declaration',{'NAME':name},{'VALUE':value}),'')
PROCS.update({'刷新保存列表':[],'保存当前谱':[],'连接音乐':['地址'],'读取本地谱':['地址'],'恢复入口':[]})
for b in procs['读取谱面'].iter('block'):
    m=b.find('mutation')
    if m is not None and m.get('instance_name')=='标题':
        m.set('instance_name','当前谱名');b.find("field[@name='COMPONENT_SELECTOR']").text='当前谱名'
过程('恢复入口',[put('读取中',False),设('选谱',True,'Enabled'),设('保存谱面',True,'Enabled'),设('制谱',True,'Enabled'),设('选音乐',等(长(g('当前谱')),8),'Enabled'),设('开始',全(等(长(g('当前谱')),8),g('音乐就绪')),'Enabled')])
过程('刷新保存列表',[local('名称表',make_list(),[loop('序号',1,长(g('保存列表')),[添(get('名称表'),join(get('序号'),' · ',item(item(g('保存列表'),get('序号')),1)))]),设('保存谱面',get('名称表'),'Elements')]),设('保存谱面',join('保存的谱面（',长(g('保存列表')),'）'))])
过程('保存当前谱',[iff(全(等(长(g('当前谱')),8),g('音乐就绪'),非(等(g('谱面地址'),''))),[
    local('位置',0,[loop('序号',1,长(g('保存列表')),[iff(等(item(item(g('保存列表'),get('序号')),2),g('谱面地址')),[局设('位置',get('序号'))])]),
        local('记录',make_list(item(g('当前谱'),1),g('谱面地址'),item(g('当前谱'),2)),[iff(等(get('位置'),0),[添(g('保存列表'),get('记录'))],[改(g('保存列表'),get('位置'),get('记录'))])])]),
    method('本地记录','StoreValue','保存的谱面',g('保存列表')),call('刷新保存列表')])])
过程('连接音乐',[
    put('音乐就绪',False),put('检查失败',False),put('正在检查',True),设('开始',False,'Enabled'),设('读取状态','正在检查音乐'),
    设('音乐检查',get('地址'),'Source'),iff(非(g('检查失败')),[method('音乐检查','Start'),iff(非(取('音乐检查','IsPlaying')),[put('检查失败',True)])]),
    method('音乐检查','Stop'),设('音乐检查','','Source'),put('正在检查',False),
    iff(非(g('检查失败')),[改(g('当前谱'),2,get('地址')),put('音乐就绪',True),call('保存当前谱'),设('读取状态','已保存谱面与音乐，可以开始游玩')],
        [设('读取状态','音乐源文件找不到、无访问权限或无法播放，请重新选择本地音乐'),警告('音乐源文件找不到、无访问权限或无法播放，请重新选择本地音乐')]),call('恢复入口')])
过程('读取本地谱',[
    put('谱面地址',get('地址')),put('读取中',True),put('音乐就绪',False),put('有效',False),put('当前谱',make_list()),设('当前谱名','正在读取谱面'),
    *[设(n,False,'Enabled') for n in ['选谱','选音乐','开始','保存谱面','制谱']],设('读取状态','正在读取谱面源文件'),method('谱面文件','ReadFrom',get('地址'))])
body(ev('选谱','AfterPicking'),[put('待用音乐',''),call('读取本地谱',取('选谱','Selection'))])
append(ev('谱面文件','GotText'),[iff(全(g('有效'),等(长(g('当前谱')),8),非(等(g('待用音乐'),''))),[call('连接音乐',g('待用音乐'))]),put('待用音乐',''),call('恢复入口')])
body(ev('选音乐','AfterPicking'),[iff(全(等(长(g('当前谱')),8),非(g('读取中'))),[call('连接音乐',取('选音乐','Selection'))])])
valid=全(*[全(文本(item(get('记录'),i)),非(等(item(get('记录'),i),''))) for i in range(1,4)])
keep=iff(列表(get('记录')),[iff(等(长(get('记录')),3),[iff(valid,[添(g('保存列表'),get('记录'))])])])
append(ev('Screen1','Initialize'),[
    put('保存列表',make_list()),local('记录表',method('本地记录','GetValue','保存的谱面',make_list()),[
        iff(列表(get('记录表')),[遍历('记录',get('记录表'),[keep])])]),call('刷新保存列表')])
事件('保存谱面','BeforePicking',[call('刷新保存列表')])
事件('保存谱面','AfterPicking',[iff(全(非(g('读取中')),compare('GTE',取('保存谱面','SelectionIndex'),1),compare('LTE',取('保存谱面','SelectionIndex'),长(g('保存列表')))),[
    local('记录',item(g('保存列表'),取('保存谱面','SelectionIndex')),[put('待用音乐',item(get('记录'),3)),call('读取本地谱',item(get('记录'),2))])])])
error=ev('Screen1','ErrorOccurred');old=copy.deepcopy(error.find('statement/block'))
tail=old
while tail.find('next/block') is not None:tail=tail.find('next/block')
ET.SubElement(tail,'next').append(chain([设('保存谱面',True,'Enabled'),设('制谱',True,'Enabled')]))
body(error,[iff(等(get('组件'),ref('音乐检查')),[put('检查失败',True),put('音乐就绪',False),设('开始',False,'Enabled')],[
    iff(等(get('组件'),ref('谱面文件')),[put('当前谱',make_list()),put('有效',False),put('音乐就绪',False),put('待用音乐',''),设('当前谱名','源谱面不可用'),call('恢复入口'),设('读取状态','谱面源文件找不到或无访问权限，请重新导入本地谱面'),警告('谱面源文件找不到或无访问权限，请重新导入本地谱面')],[old])])])
事件('Screen1','PermissionDenied',[
    iff(等(get('组件'),ref('音乐检查')),[put('检查失败',True)]),put('音乐就绪',False),put('待用音乐',''),call('恢复入口'),设('读取状态','无法访问源文件，请重新选择谱面或音乐以授予访问权限'),警告('无法访问源文件，请重新选择谱面或音乐以授予访问权限')],['组件','函数','权限'])
r.extend(TOP);stamp=r.find('yacodeblocks');r.remove(stamp);r.append(stamp)
for i,b in enumerate(r.iter('block')):b.set('id','首页保存_'+str(i))
r.set('xmlns','http://www.w3.org/1999/xhtml');ET.indent(r,space='  ')
files[bk]=ET.tostring(r,encoding='utf-8');files[path]=('#|\n$JSON\n'+json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode()
prop='youngandroidproject/project.properties';values={'versioncode':'26','versionname':'1017.3'}
files[prop]=('\n'.join(k+'='+values[k] if (k:=line.split('=',1)[0]) in values else line for line in files[prop].decode().splitlines())+'\n').encode()
for n,data in files.items():
    dest=OUT/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
with zipfile.ZipFile(ROOT/'archive/hold_base_1016/Saved_candidate.aia','w',zipfile.ZIP_DEFLATED) as z:
    for n,data in files.items():z.writestr(n,data)
print(OUT)

