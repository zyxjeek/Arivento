from pathlib import Path
import sys,re,copy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'archive/历史目录/tools'))
from 制谱器 import *
ROOT=Path(__file__).resolve().parents[1]
NAME='Rail4K_0924_2'
LANES=['轨道一','轨道二','轨道三','轨道四']

def ref(n):
    return block('component_component_block',{'COMPONENT_SELECTOR':n},mutation=mut(component_type=TYPES[n],instance_name=n))

def cm(c,n,*args):
    return block('component_method',values={'COMPONENT':c,**{f'ARG{i}':a for i,a in enumerate(args)}},mutation=mut(component_type='Canvas',method_name=n,is_generic='true'))

def cp(c,n,v=None,read=False):
    return block('component_set_get',{'PROP':n},{'COMPONENT':c,**({} if read else {'VALUE':v})},mutation=mut(component_type='Canvas',property_name=n,set_or_get='get' if read else 'set',is_generic='true'))

def scope(n):return block('helpers_dropdown',{'OPTION':n},mutation=mut(key='FileScope'))

def prepend(s,items):
    old=s[0];s.remove(old);head=chain(items);last=head
    while last.find('next/block') is not None:last=last.find('next/block')
    ET.SubElement(last,'next').append(old);s.append(head)

def strip_calls(r,name):
    for p in list(r.iter()):
        for b in list(p):
            m=b.find('mutation')
            if b.tag=='block' and m is not None and m.get('method_name')==name:
                p.remove(b)
                if b.find('next/block') is not None:p.append(b.find('next/block'))

def main():
    source=ROOT/'dist/Rail4K_0924_1.aia'
    if not source.exists():source=ROOT/'archive/历史目录/dist/Rail4K_0924_1.aia'
    with zipfile.ZipFile(source) as z:files={n:z.read(n) for n in z.namelist() if not n.startswith('assets/external_comps/')}
    for path in [n for n in files if n.endswith('.scm')]:
        screen=Path(path).stem;d=json.loads(files[path].decode().split('$JSON')[1].rsplit('|#',1)[0]);p=d['Properties'];TOP.clear();TYPES.clear();PROCS.clear()
        def register(c):
            TYPES[c['$Name']]=c['$Type']
            for x in c.get('$Components',[]):register(x)
        register(p)
        bk=path[:-4]+'.bky';r=ET.fromstring(files[bk])
        for e in r.iter():e.tag=e.tag.split('}')[-1]
        procs={b.findtext("field[@name='NAME']"):b for b in r if b.get('type','').startswith('procedures_def')}
        for n,b in procs.items():PROCS[n]=[a.get('name') for a in b.find('mutation').findall('arg')]
        p['$Components']=[c for c in p['$Components'] if c['$Type']!='LocalFiles']
        pickers={'Screen1':{'选谱':('*/*','Pick Existing File'),'选音乐':('audio/*','Pick Existing File')},'EditorSettings':{'音乐输入':('audio/*','Pick Existing File')},'Recorder':{'分享全文':('text/plain','Pick New File')}}.get(screen,{})
        def update(c):
            if c['$Name'] in pickers:
                mime,action=pickers[c['$Name']];c.update({'$Type':'FilePicker','$Version':'1','MimeType':mime,'Action':action});TYPES[c['$Name']]='FilePicker'
            for x in c.get('$Components',[]):update(x)
        update(p)
        r[:]=[b for b in r if not(b.get('type')=='component_event' and (b.find('mutation').get('instance_name')=='本地文件' or (b.find('mutation').get('instance_name') in pickers and b.find('mutation').get('event_name')=='Click')))]
        strip_calls(r,'启用多点')
        if screen=='EditorSettings':
            事件('音乐输入','AfterPicking',[put('音乐名',取('音乐输入','Selection')),设('音乐输入','已选择音乐（点击更换）'),设('录制',True,'Enabled')])
        if screen=='Screen1':
            p['$Components'].append(component('谱面文件','File',4,DefaultScope='App'))
            事件('选谱','AfterPicking',[put('读取中',True),设('选谱',False,'Enabled'),设('开始',False,'Enabled'),设('选音乐',False,'Enabled'),设('读取状态','正在读取谱面'),method('谱面文件','ReadFrom',取('选谱','Selection'))])
            事件('谱面文件','GotText',[put('当前谱',make_list()),put('有效',False),put('音乐就绪',False),设('选谱',True,'Enabled'),call('读取谱面',block('text_replace_all',values={'TEXT':get('内容'),'SEGMENT':'\ufeff','REPLACEMENT':''}),'本地谱面')],['内容'])
            事件('选音乐','AfterPicking',[改(g('当前谱'),2,取('选音乐','Selection')),put('音乐就绪',True),设('开始',True,'Enabled'),设('读取状态','音乐已选择，可以开始游玩')])
            err=next(b for b in r if b.get('type')=='component_event' and b.find('mutation').get('event_name')=='ErrorOccurred')
            s=err.find('statement');s.clear();s.set('name','DO');s.append(chain([iff(g('读取中'),[put('当前谱',make_list()),put('有效',False),put('音乐就绪',False)]),put('读取中',False),设('选谱',True,'Enabled'),设('开始',全(等(长(g('当前谱')),8),g('音乐就绪')),'Enabled'),设('选音乐',等(长(g('当前谱')),8),'Enabled'),设('读取状态',get('消息'))]))
        if screen=='Recorder':
            p['$Components'].append(component('谱面文件','File',4,DefaultScope='App'))
            PROCS['保存结束']=['消息']
            过程('保存结束',[put('正在保存',False),设('分享全文',True,'Enabled'),设('导出返回',True,'Enabled'),设('导出进度',get('消息'))])
            事件('分享全文','AfterPicking',[iff(全(非(g('正在导出')),非(g('正在保存')),非(等(g('导出全文'),''))),[put('正在保存',True),设('分享全文',False,'Enabled'),设('导出返回',False,'Enabled'),设('导出进度','正在保存谱面'),method('谱面文件','SaveFile',g('导出全文'),'导出缓存.txt')])])
            事件('谱面文件','AfterFileSaved',[iff(g('正在保存'),[iff(method('谱面文件','CopyFile',scope('App'),'导出缓存.txt',scope('Shared'),取('分享全文','Selection')),[call('保存结束','已保存到所选文件')],[call('保存结束','保存失败，内容仍保留，可以重试')])])],['文件名'])
            err=next(b for b in r if b.get('type')=='component_event' and b.find('mutation').get('event_name')=='ErrorOccurred')
            s=err.find('statement');old=s[0];s.remove(old);s.append(iff(全(取('导出页','Visible'),非(g('正在导出'))),[call('保存结束',join('文件选择或保存失败：',get('消息')))],[old]))
            def labels(c):
                if c['$Name']=='导出说明':c['Text']='生成完成后点击“保存到手机”，选择位置并输入文件名（如 测试.txt）。'
                for x in c.get('$Components',[]):labels(x)
            labels(p)
        if screen in ['Play','Recorder']:
            game=p['$Components'][0];i=next(i for i,c in enumerate(game['$Components']) if c['$Name']=='画布');old=game['$Components'][i]
            game['$Components'][i]=component('轨道区','HorizontalArrangement',4,[component(n,'Canvas',15,BackgroundColor=背景,FontSize=22,TextAlignment=1,Width=-1025,Height=-2) for n in LANES],Width=-2,Height=old['Height'])
            init=next(b for b in r if b.get('type')=='component_event' and b.find('mutation').get('event_name')=='Initialize')
            top(block('global_declaration',{'NAME':'轨道画布'},{'VALUE':make_list()}),'')
            prepend(init.find('statement'),[put('轨道画布',make_list(*[ref(n) for n in LANES]))])
            if screen=='Play':
                for j,n in enumerate(LANES,1):事件(n,'TouchDown',[call('按轨',j)],['横坐标','纵坐标'])
            if screen=='Recorder':
                PROCS['轨道按下']=['轨道']
                top(block('global_declaration',{'NAME':'按住轨道'},{'VALUE':make_list(0,0,0,0)}),'')
                过程('轨道按下',[iff(等(item(g('按住轨道'),get('轨道')),0),[改(g('按住轨道'),get('轨道'),1),put('触点数',add(*[item(g('按住轨道'),j) for j in range(1,5)])),call('录入',get('轨道'))])])
                prepend(procs['入场'].find('statement'),[put('按住轨道',make_list(0,0,0,0))])
                for j,n in enumerate(LANES,1):
                    事件(n,'TouchDown',[call('轨道按下',j)],['横坐标','纵坐标'])
                    事件(n,'TouchUp',[改(g('按住轨道'),j,0)],['横坐标','纵坐标'])
            draw=procs['绘图'];text=copy.deepcopy(next(b for b in draw.iter('block') if b.get('type')=='component_method' and b.find('mutation').get('method_name')=='DrawText').find("value[@name='ARG0']/block"))
            for b in text.iter('block'):
                if b.get('type')=='component_set_get' and b.find('mutation').get('instance_name')=='画布':
                    b.find('mutation').set('instance_name','轨道区');b.find('mutation').set('component_type','HorizontalArrangement');b.find("field[@name='COMPONENT_SELECTOR']").text='轨道区'
            if screen=='Recorder':
                for n in ['画宽','画高']:top(block('global_declaration',{'NAME':n},{'VALUE':0}),'')
            def cv():return item(g('轨道画布'),get('轨号'))
            def note():
                if screen=='Recorder':return item(g('谱面'),get('键号'))
                b=call('取游玩键',get('键号'));b.set('type','procedures_callreturn');return b
            body=[put('画宽',取('轨道区','Width')),put('画高',取('轨道一','Height')),put('轨宽',取('轨道一','Width')),
                iff(全(compare('GT',g('轨宽'),18),compare('GT',g('画高'),32)),[
                    put('判定线',mul(g('画高'),0.85)),
                    loop('轨号',1,4,[cm(cv(),'Clear'),cp(cv(),'PaintColor',-14077110),cp(cv(),'LineWidth',1),cm(cv(),'DrawLine',0,0,0,g('画高')),cp(cv(),'PaintColor',-1379585),cp(cv(),'LineWidth',3),cm(cv(),'DrawLine',0,g('判定线'),g('轨宽'),g('判定线')),cp(cv(),'PaintColor',-11084049),cp(cv(),'LineWidth',16)]),
                    local('键号',g('下一键'),[循环(全(compare('LTE',get('键号'),g('物量')),compare('LTE',item(note(),2),add(g('用时'),g('过屏时间')))),[
                        iff(True if screen=='Recorder' else 等(item(note(),3),0),[local('纵位',sub(g('判定线'),div(mul(sub(item(note(),2),g('用时')),g('判定线')),g('过屏时间'))),[iff(全(compare('GTE',get('纵位'),0),compare('LTE',get('纵位'),g('画高'))),[cm(item(g('轨道画布'),item(note(),1)),'DrawLine',9,get('纵位'),sub(g('轨宽'),9),get('纵位'))])])]),局设('键号',add(get('键号'),1))])]),
                    local('判定文字',text,[loop('轨号',1,4,[cp(cv(),'PaintColor',-1379585),cm(cv(),'DrawText',get('判定文字'),sub(div(g('画宽'),2),mul(sub(get('轨号'),1),g('轨宽'))),mul(g('画高'),0.475))])])])]
            s=draw.find('statement');s.clear();s.set('name','STACK');s.append(chain(body))
            for b in r.iter('block'):
                m=b.find('mutation')
                if m is not None and m.get('instance_name')=='画布':
                    assert b.get('type')=='component_set_get'
                    m.set('instance_name','轨道区');m.set('component_type','HorizontalArrangement');b.find("field[@name='COMPONENT_SELECTOR']").text='轨道区'
        r.extend(TOP)
        register(p)
        for b in r.iter('block'):
            m=b.find('mutation')
            if m is not None and m.get('instance_name'):m.set('component_type',TYPES[m.get('instance_name')])
        stamp=r.find('yacodeblocks');r.remove(stamp);r.append(stamp);stamp.set('ya-version','224')
        for i,b in enumerate(r.findall('block')):
            b.set('x',str(40+i//13*470));b.set('y',str(40+i%13*115))
            if b.get('type')!='global_declaration':b.set('collapsed','true')
        for i,b in enumerate(r.iter('block')):b.set('id',screen+'_'+str(i))
        for parent in r.iter():
            for c in list(parent):
                if c.tag=='comment':parent.remove(c)
        r.set('xmlns','http://www.w3.org/1999/xhtml');ET.indent(r,space='  ');files[bk]=ET.tostring(r,encoding='utf-8')
        p.update(VersionCode='21',VersionName='0924.2',Sizing='Responsive',Scrollable='False');d['YaVersion']='224'
        count=[0]
        def ids(c):
            c['Uuid']=str(count[0]);count[0]+=1
            for x in c.get('$Components',[]):ids(x)
        ids(p)
        files[path]=('#|\n$JSON\n'+json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode()
    for n in files:
        if n.endswith('project.properties'):
            s=files[n].decode()
            for k,v in [('name',NAME),('versioncode','21'),('versionname','0924.2')]:s=re.sub(r'(?m)^'+k+r'=.*',k+'='+v,s)
            files[n]=s.encode()
    with zipfile.ZipFile(ROOT/'dist'/f'{NAME}.aia','w',zipfile.ZIP_DEFLATED) as z:
        for n,data in files.items():
            z.writestr(n,data);f=ROOT/'native'/NAME/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
    print(NAME)

if __name__=='__main__':main()
