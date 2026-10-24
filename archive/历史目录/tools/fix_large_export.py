from 制谱器 import *

def length(v): return block('text_length',values={'VALUE':v})
def segment(v,start,count): return block('text_segment',values={'TEXT':v,'START':start,'LENGTH':count})

def main():
    source=ROOT/'dist/Rail4K_Offline_v7_CodeOnly.aia'
    target=ROOT/'dist/Rail4K_Offline_v8_CodeOnly.aia'
    with zipfile.ZipFile(source) as z: files={n:z.read(n) for n in z.namelist()}
    scm=next(n for n in files if n.endswith('/Recorder.scm'))
    d=json.loads(files[scm].decode().split('$JSON')[1].rsplit('|#',1)[0])
    def register(c):
        TYPES[c['$Name']]=c['$Type']
        for x in c.get('$Components',[]): register(x)
    register(d['Properties'])
    panel=next(c for c in d['Properties']['$Components'] if c['$Name']=='导出页')
    panel['$Components'][0]['Text']='正在生成谱面。完成后点“复制或分享全文”，在系统菜单中选择拷贝或发送。下方只显示预览。'
    panel['$Components'][1].update(Height='-1045',ReadOnly='True',Hint='仅预览，不要复制预览作为谱面')
    panel['$Components'].insert(2,component('导出进度','Label',6,Text='',Width=-2,TextColor=白色))
    panel['$Components'].insert(3,按钮('分享全文','复制或分享全文',Enabled='False'))
    d['Properties']['$Components'] += [component('导出时钟','Clock',4,TimerEnabled='False',TimerInterval=30,TimerAlwaysFires='False'),component('文本分享','Sharing',1)]
    files[scm]=('#|\n$JSON\n'+json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode()
    bky=scm[:-4]+'.bky'
    xml=ET.fromstring(files[bky])
    for e in xml.iter(): e.tag=e.tag.split('}')[-1]
    procs={b.findtext("field[@name='NAME']"):b for b in xml if b.get('type','').startswith('procedures_def')}
    for n,b in procs.items(): PROCS[n]=[a.get('name') for a in b.find('mutation').findall('arg')]
    PROCS.update(结束导出=[],生成一批=[])
    def remove_event(c,e=None):
        xml[:]=[b for b in xml if not(b.get('type')=='component_event' and b.find('mutation').get('instance_name')==c and (e is None or b.find('mutation').get('event_name')==e))]
    for c in ['导出','导出返回']: remove_event(c)
    remove_event('Recorder','BackPressed')
    for n in ['返回首页','入场']:
        s=procs[n].find('statement');first=s[0];s.remove(first)
        head=call('结束导出');ET.SubElement(head,'next').append(first);s.append(head)
    error=next(b for b in xml if b.get('type')=='component_event' and b.find('mutation').get('event_name')=='ErrorOccurred')
    s=error.find('statement');first=s[0];s.remove(first)
    s.append(iff(取('导出页','Visible'),[call('结束导出'),设('导出进度','导出失败，录制内容仍保留。返回后可重新导出。'),警告(join('导出失败：',get('消息')))],[first]))
    TOP.clear()
    for n,v in [('导出全文',''),('导出序号',1),('正在导出',False)]: top(block('global_declaration',{'NAME':n},{'VALUE':v}),'')
    过程('结束导出',[设('导出时钟',False,'TimerEnabled'),put('正在导出',False),put('导出全文',''),设('谱面文本',''),设('分享全文',False,'Enabled')])
    header=make_list(*[g(n) for n in ['谱面名','音乐名','过屏时间','模式','速度','单位','结束时间']])
    事件('导出','Click',[iff(全(等(g('状态'),4),compare('GT',g('物量'),0)),[
        call('结束导出'),设('游戏',False,'Visible'),设('导出页',True,'Visible'),设('导出进度',join('正在生成：0 / ',g('物量'))),
        put('正在导出',True),
        local('表头',method('文本转换','JsonObjectEncode',header),[iff(g('正在导出'),[put('导出全文',join(segment(get('表头'),1,sub(length(get('表头')),1)),',['))])]),
        put('导出序号',1),设('导出时钟',g('正在导出'),'TimerEnabled')],[警告('请先结束录制，并至少录入一个音符')])])
    过程('生成一批',[iff(g('正在导出'),[
        local('本批','',[loop('键号',g('导出序号'),minimum(add(g('导出序号'),31),g('物量')),[
            iff(g('正在导出'),[局设('本批',join(get('本批'),选(等(get('键号'),1),'',','),method('文本转换','JsonObjectEncode',item(g('谱面'),get('键号')))))])
        ]),iff(g('正在导出'),[put('导出全文',join(g('导出全文'),get('本批')))])]),
        iff(g('正在导出'),[
        put('导出序号',minimum(add(g('导出序号'),32),add(g('物量'),1))),
        设('导出进度',join('正在生成：',sub(g('导出序号'),1),' / ',g('物量'))),
        iff(compare('GT',g('导出序号'),g('物量')),[
            设('导出时钟',False,'TimerEnabled'),put('正在导出',False),put('导出全文',join(g('导出全文'),']]')),
            设('谱面文本',segment(g('导出全文'),1,minimum(2000,length(g('导出全文'))))),设('分享全文',True,'Enabled'),
            设('导出进度',join('已完成：',g('物量'),' 键。全文 ',length(g('导出全文')),' 字符；预览最多 2000 字符。请使用全文按钮。'))
        ])])])])
    事件('导出时钟','Timer',[call('生成一批')])
    事件('分享全文','Click',[iff(全(非(g('正在导出')),compare('GT',length(g('导出全文')),0)),[method('文本分享','ShareMessage',g('导出全文'))])])
    back=[call('结束导出'),method('谱面文本','HideKeyboard'),设('导出页',False,'Visible'),设('游戏',True,'Visible')]
    事件('导出返回','Click',copy.deepcopy(back))
    事件('Recorder','BackPressed',[iff(取('导出页','Visible'),back,[call('返回首页')])])
    xml.extend(TOP)
    defs={b.findtext("field[@name='NAME']"):b for b in xml if b.get('type','').startswith('procedures_def')}
    retained=[b for b in xml if b.get('type')=='component_event'];used=set()
    for b in retained:
        for c in b.iter('block'):
            if c.get('type') in ['procedures_callreturn','procedures_callnoreturn']:
                n=c.findtext("field[@name='PROCNAME']")
                if n not in used: used.add(n);retained.append(defs[n])
    variables={f.text[7:] for b in retained for f in b.iter('field') if f.get('name')=='VAR' and (f.text or '').startswith('global ')}
    xml[:]=[b for b in xml if b.get('type')=='global_declaration' and b.findtext("field[@name='NAME']") in variables]+retained
    for i,b in enumerate(xml.findall('block')):
        b.set('x',str(40+i//13*470));b.set('y',str(40+i%13*115))
        if b.get('type')!='global_declaration': b.set('collapsed','true')
    for i,b in enumerate(xml.iter('block')): b.set('id',f'导出_{i}')
    ET.SubElement(xml,'yacodeblocks',{'ya-version':'237','language-version':'39'})
    xml.set('xmlns','http://www.w3.org/1999/xhtml');ET.indent(xml,space='  ')
    files[bky]=ET.tostring(xml,encoding='utf-8')
    for n in files:
        if n.endswith('.scm'):
            d=json.loads(files[n].decode().split('$JSON')[1].rsplit('|#',1)[0]);d['Properties'].update(VersionCode='12',VersionName='0.7.1')
            seq=[0]
            def uuid(c):
                c['Uuid']=str(seq[0]);seq[0]+=1
                for x in c.get('$Components',[]): uuid(x)
            uuid(d['Properties'])
            files[n]=('#|\n$JSON\n'+json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode()
        elif n.endswith('project.properties'):
            files[n]=files[n].decode().replace('versioncode=11','versioncode=12').replace('versionname=0.7.0','versionname=0.7.1').encode()
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for n,data in files.items():
            z.writestr(n,data)
            f=ROOT/'native/Rail4K_LargeExport'/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
    print(target)

if __name__=='__main__': main()
