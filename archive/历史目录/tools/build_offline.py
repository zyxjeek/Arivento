from build_multiscreen import opening, closing, field, rewrite
from build_ios_fix import invoke
from 制谱器 import *

def main():
    source=ROOT/'dist/Rail4K_Multi_v6_CodeOnly.aia'
    target=ROOT/'dist/Rail4K_Offline_v7_CodeOnly.aia'
    out=ROOT/'native/Rail4K_Offline'
    with zipfile.ZipFile(source) as z:
        files={n:z.read(n) for n in z.namelist()}
    for path in [n for n in files if n.endswith('.scm')]:
        screen=Path(path).stem
        d=json.loads(files[path].decode().split('$JSON')[1].rsplit('|#',1)[0])
        props=d['Properties']
        def clean(c):
            TYPES[c['$Name']]=c['$Type']
            c['$Components']=[x for x in c.get('$Components',[]) if x['$Name'] not in ['云端','云时钟','云状态']]
            for x in c['$Components']: clean(x)
        clean(props)
        bk=path[:-4]+'.bky'
        xml=ET.fromstring(files[bk])
        for e in xml.iter(): e.tag=e.tag.split('}')[-1]
        procs={field(b,'NAME'):b for b in xml if b.get('type','').startswith('procedures_def')}
        for n,b in procs.items(): PROCS[n]=[a.get('name') for a in b.find('mutation').findall('arg')]
        def remove_event(c,e=None):
            xml[:]=[b for b in xml if not(b.get('type')=='component_event' and b.find('mutation').get('instance_name')==c and (e is None or b.find('mutation').get('event_name')==e))]
        def body(n,stm):
            s=procs[n].find('statement');s.clear();s.set('name','STACK');s.append(chain(stm))
        for c in ['云端','云时钟','提示']: remove_event(c)
        def unwrap(b):
            if b.get('type')=='controls_if' and b.findtext("value[@name='IF0']/block/value[@name='A']/block/field[@name='VAR']")=='global 云请求':
                return copy.deepcopy(b.find("statement[@name='DO0']/block"))
            return b
        rewrite(xml,unwrap)
        TOP.clear()
        if screen=='Screen1':
            valid=procs['检查谱面']
            xml[:]=[valid]
            home=props['$Components'][0]
            home['$Components']=[c for c in home['$Components'] if c['$Name']!='刷新']
            for c in home['$Components']:
                if c['$Name']=='选谱': c.update(ElementsFromString='',Selection='',ShowFilterBar='True')
                if c['$Name']=='开始': c['Enabled']='False'
            home['$Components'].append(component('读取状态','Label',6,Text='正在读取谱面列表',Width=-2,TextColor=白色))
            props['$Components'] += [component('目录文件','File',4),component('谱面文件','File',4),component('文本转换','Web',9)]
            for n,v in [('当前谱',make_list()),('有效',False),('读取中',False)]: top(block('global_declaration',{'NAME':n},{'VALUE':v}),'')
            事件('Screen1','Initialize',[method('目录文件','ReadFrom','//chart_list.txt')])
            lines=block('text_split',{'OP':'SPLIT'},{'TEXT':get('内容'),'AT':'\n'})
            事件('目录文件','GotText',[local('目录',make_list(),[遍历('行',lines,[local('文件名',修剪(get('行')),[iff(全(非(等(get('文件名'),'')),非(包含(get('目录'),get('文件名')))),[添(get('目录'),get('文件名'))])])]),设('选谱',get('目录'),'Elements'),设('读取状态','请选择素材中的谱面')])],['内容'])
            事件('选谱','AfterPicking',[put('读取中',True),put('当前谱',make_list()),设('开始',False,'Enabled'),设('选谱',False,'Enabled'),设('读取状态',join('正在读取：',取('选谱','Selection'))),method('谱面文件','ReadFrom',join('//',取('选谱','Selection')))])
            事件('谱面文件','GotText',[iff(g('读取中'),[put('读取中',False),设('选谱',True,'Enabled'),local('数据',method('文本转换','JsonTextDecode',修剪(get('内容'))),[call('检查谱面',get('数据')),iff(g('有效'),[put('当前谱',get('数据')),设('标题',join('定轨四键\n',item(get('数据'),1))),设('读取状态',取('选谱','Selection')),设('开始',True,'Enabled')],[设('读取状态','谱面格式不正确'),警告('谱面格式不正确，请检查 JSON 和音符时间')])])])],['内容'])
            事件('开始','Click',[iff(全(非(g('读取中')),compare('GT',长(g('当前谱')),0)),[opening('Play',g('当前谱'))])])
            事件('制谱','Click',[opening('EditorSettings','')])
            事件('Screen1','ErrorOccurred',[put('读取中',False),put('当前谱',make_list()),设('开始',False,'Enabled'),设('选谱',True,'Enabled'),设('读取状态','素材读取失败'),警告(join('请检查 chart_list.txt、谱面文件及其格式。',get('消息')))],['组件','函数','编号','消息'])
        elif screen=='EditorSettings':
            remove_event(screen,'OtherScreenClosed')
        elif screen=='Recorder':
            body('返回首页',[put('状态',0),设('时钟',False,'TimerEnabled'),method('音乐','Stop'),closing()])
            remove_event('保存')
            game=props['$Components'][0];game['Height']='-2'
            def rename(c):
                if c['$Name']=='保存': c.update(Text='导出',**{'$Name':'导出'})
                for x in c.get('$Components',[]): rename(x)
            rename(game)
            TYPES['导出']='Button'
            text=输入('谱面文本','长按文本，全选并复制')
            text.update(MultiLine='True',Height='-1070',FontSize='13')
            props['$Components'] += [排列('导出页',[component('导出说明','Label',6,Text='长按下方文本，全选并复制。保存为 UTF-8 文本文件后上传到素材，并加入 chart_list.txt。',Width=-2,TextColor=白色),text,按钮('导出返回','返回录制结果')],Height=-2,Visible='False'),component('文本转换','Web',9)]
            chart=make_list(*[g(n) for n in ['谱面名','音乐名','过屏时间','模式','速度','单位','结束时间']],invoke(g('谱面')))
            事件('导出','Click',[iff(compare('GT',g('物量'),0),[设('谱面文本',method('文本转换','JsonObjectEncode',chart)),设('游戏',False,'Visible'),设('导出页',True,'Visible')],[警告('至少录入一个音符后才能导出')])])
            事件('导出返回','Click',[method('谱面文本','HideKeyboard'),设('导出页',False,'Visible'),设('游戏',True,'Visible')])
            remove_event(screen,'BackPressed')
            事件(screen,'BackPressed',[iff(取('导出页','Visible'),[method('谱面文本','HideKeyboard'),设('导出页',False,'Visible'),设('游戏',True,'Visible')],[call('返回首页')])])
            for b in xml.iter('block'):
                m=b.find('mutation')
                if m is not None and m.get('instance_name')=='保存': m.set('instance_name','导出')
                for f in b.findall('field'):
                    if f.get('name')=='COMPONENT_SELECTOR' and f.text=='保存': f.text='导出'
        elif screen=='Play':
            body('返回首页',[put('状态',0),设('时钟',False,'TimerEnabled'),method('音乐','Stop'),closing()])
        xml.extend(TOP)
        defs={field(b,'NAME'):b for b in xml if b.get('type','').startswith('procedures_def')}
        retained=[b for b in xml if b.get('type')=='component_event']
        used=set()
        for b in retained:
            for c in b.iter('block'):
                if c.get('type') in ['procedures_callreturn','procedures_callnoreturn']:
                    n=field(c,'PROCNAME')
                    if n not in used: used.add(n);retained.append(defs[n])
        variables={f.text[7:] for b in retained for f in b.iter('field') if f.get('name')=='VAR' and (f.text or '').startswith('global ')}
        xml[:]=[b for b in xml if b.get('type')=='global_declaration' and field(b,'NAME') in variables]+retained
        for i,b in enumerate(xml.findall('block')):
            b.set('x',str(40+i//13*470));b.set('y',str(40+i%13*115))
            if b.get('type')!='global_declaration': b.set('collapsed','true')
        for i,b in enumerate(xml.iter('block')): b.set('id',f'{screen}_{i}')
        ET.SubElement(xml,'yacodeblocks',{'ya-version':'237','language-version':'39'})
        xml.set('xmlns','http://www.w3.org/1999/xhtml');ET.indent(xml,space='  ')
        files[bk]=ET.tostring(xml,encoding='utf-8')
        assert '云' not in files[bk].decode() and 'CloudDB' not in files[bk].decode()
        props.update(VersionCode='11',VersionName='0.7.0')
        seq=[0]
        def uuid(c):
            c['Uuid']=str(seq[0]);seq[0]+=1
            for x in c.get('$Components',[]): uuid(x)
            if not c.get('$Components'): c.pop('$Components',None)
        uuid(props)
        files[path]=('#|\n$JSON\n'+json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode()
    import sys
    sys.path.insert(0,str(ROOT/'tests'))
    from playback_runtime import Runtime
    r=Runtime();r.call('创建测试')
    files['assets/测试.txt']=json.dumps(r.globals['当前谱'],ensure_ascii=False,separators=(',',':')).encode()
    files['assets/chart_list.txt']='测试.txt\n'.encode()
    for n in files:
        if n.endswith('project.properties'): files[n]=files[n].decode().replace('versioncode=10','versioncode=11').replace('versionname=0.6.4','versionname=0.7.0').encode()
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for n,data in files.items():
            z.writestr(n,data)
            f=out/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
    print(target)

if __name__=='__main__': main()
