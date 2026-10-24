from pathlib import Path
import copy,json,re,zipfile,xml.etree.ElementTree as E

ROOT=Path(__file__).resolve().parents[1]
NAME='Rail4K_0919_2'

def block(t,fields={},values={},mutation=None):
    b=E.Element('block',type=t)
    if mutation:E.SubElement(b,'mutation',mutation)
    for k,v in fields.items():E.SubElement(b,'field',name=k).text=v
    for k,v in values.items():E.SubElement(b,'value',name=k).append(v)
    return b
def text(s):return block('text',{'TEXT':s})
def boolean(v):return block('logic_boolean',{'BOOL':'TRUE' if v else 'FALSE'})
def prop(c,p,v=None):
    return block('component_set_get',{'COMPONENT_SELECTOR':c,'PROP':p},{} if v is None else {'VALUE':v},dict(component_type='ListPicker' if c=='模式输入' else 'Button',instance_name=c,is_generic='false',set_or_get='get' if v is None else 'set',property_name=p))
def append(s,b):
    if not len(s):s.append(b);return
    last=s[0]
    while last.find('next/block') is not None:last=last.find('next/block')
    E.SubElement(last,'next').append(b)

def main():
    with zipfile.ZipFile(ROOT/'archive/历史目录/dist/Rail4K_0919_1.aia') as z:files={n:z.read(n) for n in z.namelist()}
    removed={'不放音乐','清除音乐'}
    for path in [n for n in files if n.endswith('.scm')]:
        screen=Path(path).stem;d=json.loads(files[path].decode().split('$JSON')[1].rsplit('|#',1)[0])
        def design(c):
            c['$Components']=[x for x in c.get('$Components',[]) if x['$Name'] not in removed]
            if not c['$Components']:c.pop('$Components')
            if c['$Name']=='音乐输入':c['Text']='选择本地音乐'
            if c['$Name']=='录制':c['Enabled']='False'
            if c['$Name']=='模式输入':c.update({'$Type':'ListPicker','$Version':'9','Text':'模式：自由模式','Selection':'自由模式','SelectionIndex':'1','BackgroundColor':'&HFFEAF2FF','TextColor':'&HFF0B1020','ItemBackgroundColor':'&HFFEAF2FF','ItemTextColor':'&HFF0B1020','FontSize':'16'})
            for x in c.get('$Components',[]):design(x)
        design(d['Properties']);d['Properties'].update(VersionCode='19',VersionName='0919.2')
        files[path]=('#|\n$JSON\n'+json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode()
        bk=path[:-4]+'.bky';r=E.fromstring(files[bk])
        for e in r.iter():e.tag=e.tag.split('}')[-1]
        def prune(parent):
            for b in list(parent):
                m=b.find('mutation')
                if b.tag=='block' and m is not None and m.get('instance_name') in removed:
                    i=list(parent).index(b);tail=b.find('next/block');parent.remove(b)
                    if tail is not None:parent.insert(i,tail);prune(parent)
                else:prune(b)
        prune(r)
        for b in r.iter('block'):
            m=b.find('mutation')
            if m is not None and m.get('instance_name')=='模式输入':
                m.set('component_type','ListPicker')
                if m.get('event_name')=='AfterSelecting':
                    m.set('event_name','AfterPicking');m.attrib.pop('param_name0',None)
                    append(b.find('statement'),prop('模式输入','Text',block('text_join',values={'ADD0':text('模式：'),'ADD1':prop('模式输入','Selection')},mutation={'items':'2'})))
            if screen=='EditorSettings' and m is not None and m.get('event_name')=='音乐已选':append(b.find('statement'),prop('录制','Enabled',boolean(True)))
            if screen=='Screen1' and b.get('type')=='procedures_defnoreturn' and b.findtext("field[@name='NAME']")=='读取谱面':
                for q in b.iter('block'):
                    if q.get('type')=='lexical_variable_set' and q.findtext("field[@name='VAR']")=='global 音乐就绪':
                        v=q.find('value');v[:]=[boolean(False)]
            if screen=='EditorSettings' and b.get('type')=='procedures_defnoreturn' and b.findtext("field[@name='NAME']")=='检查设置':
                v=b.find("statement/block/value[@name='IF0']");old=v[0];v.remove(old)
                has=block('logic_negate',values={'BOOL':block('math_compare',{'OP':'EQ'},{'A':block('lexical_variable_get',{'VAR':'global 音乐名'}),'B':text('')})})
                v.append(block('logic_operation',{'OP':'AND'},{'A':has,'B':old},mutation={'items':'2'}))
            if b.get('type')=='text':
                f=b.find('field')
                if f is not None and f.text:f.text=f.text.replace('：可直接开始','：请选择对应的本地音乐')
        for i,b in enumerate(r.iter('block')):b.set('id',screen+'_'+str(i))
        r.set('xmlns','http://www.w3.org/1999/xhtml');E.indent(r,space='  ');files[bk]=E.tostring(r,encoding='utf-8')
    for n in files:
        if n.endswith('project.properties'):
            s=files[n].decode()
            for k,v in [('name',NAME),('versioncode','19'),('versionname','0919.2')]:s=re.sub(r'(?m)^'+k+r'=.*',k+'='+v,s)
            files[n]=s.encode()
    with zipfile.ZipFile(ROOT/'dist'/f'{NAME}.aia','x',zipfile.ZIP_DEFLATED) as z:
        for n,data in files.items():
            z.writestr(n,data);p=ROOT/'native'/NAME/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    print(NAME)

if __name__=='__main__':main()
