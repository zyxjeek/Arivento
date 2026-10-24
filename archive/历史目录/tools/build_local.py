from 制谱器 import *
from build_multiscreen import opening, field, rewrite
import re

TYPE='LocalFiles'
TARGET=ROOT/'dist/Rail4K_0919_1.aia'

def main():
    source=ROOT/'dist/Rail4K_Offline_v12_CodeOnly.aia'
    raw=source.read_bytes()
    backup=ROOT/('original/v12_'+hashlib.sha256(raw).hexdigest()[:12]+'.aia')
    if not backup.exists(): backup.write_bytes(raw)
    with zipfile.ZipFile(source) as z: files={n:z.read(n) for n in z.namelist()}
    versions=dict(re.findall(r'public static final int (\w+)_COMPONENT_VERSION = (\d+);',(ROOT/'reference/nb190/YaVersion.java').read_text()))
    for path in [n for n in files if n.endswith('.scm')]:
        screen=Path(path).stem
        design=json.loads(files[path].decode().split('$JSON')[1].rsplit('|#',1)[0]);props=design['Properties']
        components={}
        def register(c):
            components[c['$Name']]=c;TYPES[c['$Name']]=c['$Type']
            for x in c.get('$Components',[]): register(x)
        register(props)
        bk=path[:-4]+'.bky';xml=ET.fromstring(files[bk])
        for e in xml.iter(): e.tag=e.tag.split('}')[-1]
        procs={field(b,'NAME'):b for b in xml if b.get('type','').startswith('procedures_def')}
        for n,b in procs.items(): PROCS[n]=[a.get('name') for a in b.find('mutation').findall('arg')]
        TOP.clear()
        def remove_event(c,e=None):
            xml[:]=[b for b in xml if not(b.get('type')=='component_event' and b.find('mutation').get('instance_name')==c and (e is None or b.find('mutation').get('event_name')==e))]
        def convert_button(name,text):
            c=components[name];c.update({'$Type':'Button','Text':text});TYPES[name]='Button'
            for k in ['Selection','ElementsFromString','ShowFilterBar']:c.pop(k,None)
            for b in xml.iter('block'):
                m=b.find('mutation')
                if m is not None and m.get('instance_name')==name:m.set('component_type','Button')
        def body(n,stm):
            s=procs[n].find('statement');s.clear();s.set('name','STACK');s.append(chain(stm))
        if screen!='Play': props['$Components'].append(component('本地文件',TYPE,1))
        if screen=='Screen1':
            props['$Components']=[c for c in props['$Components'] if c['$Name'] not in ['目录文件','谱面文件']]
            convert_button('选谱','导入本地谱面')
            home=components['首页']['$Components']
            home.insert(3,按钮('选音乐','选择本地音乐',Enabled='False'))
            home.insert(4,按钮('不放音乐','无音乐游玩',Enabled='False'))
            components['读取状态']['Text']='请选择手机中的谱面文件'
            xml[:]=[b for b in xml if b.get('type')!='component_event']
            PROCS['读取谱面']=['内容','名称']
            top(block('global_declaration',{'NAME':'音乐就绪'},{'VALUE':False}),'')
            过程('读取谱面',[
                put('读取中',False),设('选谱',True,'Enabled'),
                iff(等(修剪(get('内容')),''),[设('读取状态','谱面文件为空'),警告('谱面文件没有内容')],[
                    local('数据',method('文本转换','JsonTextDecode',修剪(get('内容'))),[
                        call('检查谱面',get('数据')),
                        iff(g('有效'),[put('当前谱',get('数据')),设('标题',item(g('当前谱'),1)),
                            put('音乐就绪',等(item(g('当前谱'),2),'')),设('开始',g('音乐就绪'),'Enabled'),
                            设('选音乐',True,'Enabled'),设('不放音乐',True,'Enabled'),
                            设('读取状态',join(get('名称'),选(g('音乐就绪'),'：可直接开始','：请选择对应的本地音乐')))
                        ],[设('读取状态',g('校验问题')),警告(g('校验问题'))])
                    ])
                ])])
            事件('Screen1','Initialize',[设('读取状态','请选择手机中的谱面文件')])
            事件('选谱','Click',[put('读取中',True),method('本地文件','导入谱面')])
            事件('本地文件','谱面已读',[
                put('当前谱',make_list()),put('音乐就绪',False),设('开始',False,'Enabled'),设('选音乐',False,'Enabled'),设('不放音乐',False,'Enabled'),
                call('读取谱面',get('内容'),get('名称'))],['内容','名称'])
            事件('选音乐','Click',[method('本地文件','选择音乐')])
            事件('本地文件','音乐已选',[改(g('当前谱'),2,get('地址')),put('音乐就绪',True),设('开始',True,'Enabled'),设('读取状态',join('音乐：',get('名称')))],['地址','名称'])
            事件('不放音乐','Click',[改(g('当前谱'),2,''),put('音乐就绪',True),设('开始',True,'Enabled'),设('读取状态','无音乐游玩')])
            事件('开始','Click',[iff(全(非(g('读取中')),g('音乐就绪'),等(长(g('当前谱')),8)),[opening('Play',g('当前谱'))])])
            事件('制谱','Click',[opening('EditorSettings','')])
            事件('本地文件','取消',[put('读取中',False)])
            事件('本地文件','出错',[put('读取中',False),设('读取状态',join('文件操作失败：',get('消息'))),警告(get('消息'))],['消息'])
            事件('Screen1','ErrorOccurred',[put('读取中',False),put('当前谱',make_list()),put('音乐就绪',False),设('开始',False,'Enabled'),设('选音乐',False,'Enabled'),设('不放音乐',False,'Enabled'),设('读取状态','谱面读取失败'),警告(get('消息'))],['组件','函数','编号','消息'])
        elif screen=='EditorSettings':
            props['$Components']=[c for c in props['$Components'] if c['$Name']!='曲目文件']
            convert_button('音乐输入','选择本地音乐（当前无音乐）')
            components['设置']['$Components'].insert(4,按钮('清除音乐','使用无音乐'))
            for c,e in [('曲目文件',None),('音乐输入',None),(screen,'Initialize'),(screen,'ErrorOccurred')]:remove_event(c,e)
            for b in procs['检查设置'].iter('block'):
                if b.get('type')=='lexical_variable_set' and b.findtext("field[@name='VAR']")=='global 音乐名':
                    v=b.find('value');v.clear();v.set('name','VALUE');v.append(g('音乐名'))
            事件('音乐输入','Click',[method('本地文件','选择音乐')])
            事件('本地文件','音乐已选',[put('音乐名',get('地址')),设('音乐输入',get('名称'))],['地址','名称'])
            事件('清除音乐','Click',[put('音乐名',''),设('音乐输入','选择本地音乐（当前无音乐）')])
            事件('本地文件','出错',[警告(get('消息'))],['消息'])
            事件(screen,'ErrorOccurred',[警告(get('消息'))],['组件','函数','编号','消息'])
        elif screen=='Recorder':
            props['$Components']=[c for c in props['$Components'] if c['$Name']!='文本分享']
            components['分享全文']['Text']='保存到手机'
            components['导出说明']['Text']='生成完成后，点击“保存到手机”选择文件夹和文件名。'
            remove_event('分享全文')
            top(block('global_declaration',{'NAME':'正在保存'},{'VALUE':False}),'')
            事件('分享全文','Click',[iff(全(非(g('正在导出')),非(g('正在保存')),非(等(g('导出全文'),''))),[
                put('正在保存',True),设('分享全文',False,'Enabled'),设('导出返回',False,'Enabled'),设('导出进度','请选择保存位置'),method('本地文件','保存谱面',g('谱面名'),g('导出全文'))])])
            for event,text in [('谱面已保存',join('已保存：',get('名称'))),('取消','已取消保存，仍可重新选择位置'),('出错',join('保存失败：',get('消息')))]:
                事件('本地文件',event,[put('正在保存',False),设('分享全文',True,'Enabled'),设('导出返回',True,'Enabled'),设('导出进度',text)],['名称'] if event=='谱面已保存' else ['消息'] if event=='出错' else [])
            for b in xml.iter('block'):
                if b.get('type')=='text':
                    f=b.find('field');f.text=(f.text or '').replace('请使用全文按钮。','请点击“保存到手机”。')
            old=next(b for b in xml if b.get('type')=='component_event' and b.find('mutation').get('event_name')=='BackPressed')
            s=old.find('statement');first=s[0];s.remove(first);s.append(iff(非(g('正在保存')),[first],[警告('正在保存，请稍候')]))
        xml.extend(TOP)
        def messages(b):
            if b.get('type')=='text':
                f=b.find('field')
                if f is not None:
                    f.text=(f.text or '').replace('。请确认已上传同名音频；iPhone 建议使用真正转换后的 MP3/M4A，不能只改后缀。','。请重新选择可播放的本地音频，确认文件未移动或删除。').replace('请确认素材区已上传同名音频','请重新选择手机中的音频').replace('请上传','请选择')
            return b
        rewrite(xml,messages)
        defs={field(b,'NAME'):b for b in xml if b.get('type','').startswith('procedures_def')}
        retained=[b for b in xml if b.get('type')=='component_event'];used=set()
        for b in retained:
            for c in b.iter('block'):
                if c.get('type') in ['procedures_callreturn','procedures_callnoreturn']:
                    n=field(c,'PROCNAME')
                    if n not in used:used.add(n);retained.append(defs[n])
        variables={f.text[7:] for b in retained for f in b.iter('field') if f.get('name')=='VAR' and (f.text or '').startswith('global ')}
        xml[:]=[b for b in xml if b.get('type')=='global_declaration' and field(b,'NAME') in variables]+retained
        for i,b in enumerate(xml.findall('block')):
            b.set('x',str(40+i//13*470));b.set('y',str(40+i%13*115))
            if b.get('type')!='global_declaration':b.set('collapsed','true')
        for i,b in enumerate(xml.iter('block')):b.set('id',f'{screen}_{i}')
        ET.SubElement(xml,'yacodeblocks',{'ya-version':'219','language-version':'34'})
        xml.set('xmlns','http://www.w3.org/1999/xhtml');ET.indent(xml,space='  ')
        files[bk]=ET.tostring(xml,encoding='utf-8')
        design['YaVersion']='219';props.update(VersionCode='18',VersionName='0919.1')
        seq=[0]
        def compat(c):
            c['$Version']='1' if c['$Type']==TYPE else versions[c['$Type'].upper()]
            c.pop('HintColor',None);c['Uuid']=str(seq[0]);seq[0]+=1
            for x in c.get('$Components',[]):compat(x)
        compat(props)
        files[path]=('#|\n$JSON\n'+json.dumps(design,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode()
    for n in files:
        if n.endswith('project.properties'):
            t=files[n].decode();t=re.sub(r'(?m)^versioncode=.*','versioncode=18',t);t=re.sub(r'(?m)^versionname=.*','versionname=0919.1',t)
            t=re.sub(r'(?m)^androidminsdk=.*','androidminsdk=19',t);t=re.sub(r'(?m)^name=.*','name=Rail4K_0919_1',t)
            t=re.sub(r'(?m)^(IosMinSdk|projectcolors)=.*\n?','',t);files[n]=t.encode()
    ext=ROOT/'extensions/localfiles/package'
    for p in ext.rglob('*'):
        if p.is_file():files['assets/external_comps/'+p.relative_to(ext).as_posix()]=p.read_bytes()
    with zipfile.ZipFile(TARGET,'w',zipfile.ZIP_DEFLATED) as z:
        for n,data in files.items():
            z.writestr(n,data);p=ROOT/'native/Rail4K_0919_1'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    print(TARGET)

if __name__=='__main__':main()
