from 制谱器 import *

def note(index):
    m=mut(name='取游玩键');ET.SubElement(m,'arg',name='键号')
    return block('procedures_callreturn',{'PROCNAME':'取游玩键'},{'ARG0':index},mutation=m)

def main():
    source=ROOT/'dist/Rail4K_Offline_v10_CodeOnly.aia'
    target=ROOT/'dist/Rail4K_Offline_v11_CodeOnly.aia'
    with zipfile.ZipFile(source) as z: files={n:z.read(n) for n in z.namelist()}
    path=next(n for n in files if n.endswith('/Play.bky'))
    scm=path[:-4]+'.scm'
    d=json.loads(files[scm].decode().split('$JSON')[1].rsplit('|#',1)[0])
    components={}
    def register(c):
        TYPES[c['$Name']]=c['$Type'];components[c['$Name']]=c
        for x in c.get('$Components',[]): register(x)
    register(d['Properties'])
    xml=ET.fromstring(files[path])
    for e in xml.iter(): e.tag=e.tag.split('}')[-1]
    procs={b.findtext("field[@name='NAME']"):b for b in xml if b.get('type','').startswith('procedures_def')}
    for n,b in procs.items(): PROCS[n]=[a.get('name') for a in b.find('mutation').findall('arg')]
    PROCS.update(准备游玩键=[],完成游玩=[],更新信息=[])
    def prepend(p,body):
        s=p.find('statement');first=s[0];s.remove(first)
        head=chain(body);last=head
        while last.find('next/block') is not None: last=last.find('next/block')
        ET.SubElement(last,'next').append(first);s.append(head)
    def append(p,body):
        last=p.find('statement/block')
        while last.find('next/block') is not None: last=last.find('next/block')
        ET.SubElement(last,'next').append(chain(body))
    def replace(parent):
        for c in list(parent):
            if c.tag=='block':
                t=c.get('type');m=c.find('mutation');f=c.findtext("field[@name='VAR']")
                replacement=None
                if t=='lexical_variable_set' and f=='global 判定表':
                    tail=c.find('next/block/next')
                    parent.remove(c)
                    if tail is not None: parent.append(copy.deepcopy(tail[0]))
                    continue
                if t=='lists_select_item' and c.findtext("value[@name='LIST']/block/field[@name='VAR']") in ['global 谱面','global 判定表']:
                    index=copy.deepcopy(c.find("value[@name='NUM']/block"))
                    replacement=note(index)
                    if c.findtext("value[@name='LIST']/block/field[@name='VAR']")=='global 判定表': replacement=item(replacement,3)
                if t=='lists_replace_item' and c.findtext("value[@name='LIST']/block/field[@name='VAR']")=='global 判定表':
                    replacement=改(note(copy.deepcopy(c.find("value[@name='NUM']/block"))),3,copy.deepcopy(c.find("value[@name='ITEM']/block")))
                if t=='lexical_variable_set' and f=='global 谱面':
                    v=c.find("value[@name='VALUE']");v.clear();v.set('name','VALUE');v.append(item(g('当前谱'),8))
                if replacement is not None:
                    tail=c.find('next')
                    if tail is not None: replacement.append(copy.deepcopy(tail))
                    parent.remove(c);parent.append(replacement);replace(replacement)
                else: replace(c)
            else: replace(c)
    replace(xml)
    append(procs['读取当前谱'],[call('准备游玩键')])
    prepend(procs['入场'],[设('画布',True,'Visible'),设('信息',int(components['信息']['Height']),'Height'),put('信息待更新',False)])
    end=next(b for b in procs['走时'].iter('block') if b.get('type')=='controls_if' and b.findtext("value[@name='IF0']/block/value[@name='B']/block/field[@name='VAR']")=='global 结束时间')
    s=end.find("statement[@name='DO0']");s.clear();s.set('name','DO0');s.append(call('完成游玩'))
    for b in procs['记录判定'].iter('block'):
        if b.get('type')=='procedures_callnoreturn' and b.findtext("field[@name='PROCNAME']")=='统计':
            b.clear();b.set('type','lexical_variable_set');ET.SubElement(b,'field',name='VAR').text='global 信息待更新';ET.SubElement(b,'value',name='VALUE').append(expr(True))
    for b in procs['按轨'].iter('block'):
        if b.get('type')=='procedures_callnoreturn' and b.findtext("field[@name='PROCNAME']")=='绘图':
            b.find('mutation').set('name','更新信息');b.find("field[@name='PROCNAME']").text='更新信息'
    for b in xml:
        if b.get('type')=='component_event' and b.find('mutation').get('instance_name')=='时钟': append(b,[call('更新信息')])
    TOP.clear()
    for n,v in [('游玩分段',make_list()),('信息待更新',False),('画宽',0),('画高',0)]: top(block('global_declaration',{'NAME':n},{'VALUE':v}),'')
    过程('准备游玩键',[put('游玩分段',make_list()),local('分段',make_list(),[
        遍历('音符',g('谱面'),[
            iff(等(长(get('分段')),0),[添(g('游玩分段'),get('分段'))]),
            添(get('分段'),make_list(item(get('音符'),1),item(get('音符'),2),0)),
            iff(等(长(get('分段')),64),[局设('分段',make_list())])
        ])
    ])])
    m=mut();ET.SubElement(m,'arg',name='键号')
    group=unary('FLOOR',div(sub(get('键号'),1),64))
    value=item(item(g('游玩分段'),add(copy.deepcopy(group),1)),sub(get('键号'),mul(group,64)))
    top(block('procedures_defreturn',{'NAME':'取游玩键','VAR0':'键号'},{'RETURN':value},mutation=m),'')
    过程('更新信息',[iff(g('信息待更新'),[put('信息待更新',False),call('统计')])])
    过程('完成游玩',[iff(等(g('状态'),1),[
        put('状态',3),设('时钟',False,'TimerEnabled'),method('音乐','Stop'),put('信息待更新',False),call('统计'),
        设('游戏',True,'Visible'),设('画布',False,'Visible'),设('信息',-1092,'Height'),设('重开',True,'Visible'),
        设('信息',join(g('谱面名'),'\n游玩完成\n\n准确率 ',decimal(g('准确率')),'%\n\nPerfect ',g('完美'),'   Good ',g('良好'),'\nMiss ',g('漏击'),'\n最高连击 ',g('最大连击')))
    ])])
    for b in procs['绘图'].iter('block'):
        m=b.find('mutation')
        if b.get('type')=='component_set_get' and m.get('instance_name')=='画布' and m.get('set_or_get')=='get' and m.get('property_name') in ['Width','Height']:
            name='画宽' if m.get('property_name')=='Width' else '画高'
            b.clear();b.set('type','lexical_variable_get');ET.SubElement(b,'field',name='VAR').text='global '+name
    prepend(procs['绘图'],[put('画宽',取('画布','Width')),put('画高',取('画布','Height'))])
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
    for i,b in enumerate(xml.iter('block')): b.set('id',f'游玩_{i}')
    ET.SubElement(xml,'yacodeblocks',{'ya-version':'237','language-version':'39'})
    xml.set('xmlns','http://www.w3.org/1999/xhtml');ET.indent(xml,space='  ')
    files[path]=ET.tostring(xml,encoding='utf-8')
    for n in files:
        if n.endswith('.scm'):
            d=json.loads(files[n].decode().split('$JSON')[1].rsplit('|#',1)[0]);d['Properties'].update(VersionCode='15',VersionName='0.7.4')
            files[n]=('#|\n$JSON\n'+json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode()
        elif n.endswith('project.properties'):
            files[n]=files[n].decode().replace('versioncode=14','versioncode=15').replace('versionname=0.7.3','versionname=0.7.4').encode()
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for n,data in files.items():
            z.writestr(n,data)
            f=ROOT/'native/Rail4K_PlayFinish'/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
    print(target)

if __name__=='__main__': main()
