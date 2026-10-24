from pathlib import Path
import argparse,datetime,json,zipfile,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
NAME=json.loads((ROOT/'tools/current_release.json').read_text(encoding='utf-8'))['name']
SOURCE=ROOT/'native'/NAME
LATEST=ROOT/'dist'/(NAME+'.aia')

def check_block_structure(r):
    ids=[]
    for b in r.iter('block'):
        ident=b.get('id');ids.append(ident)
        for tag in ('next','mutation'):
            assert len(b.findall(tag))<=1,f'{ident} 有重复 {tag} 连接'
        for tag in ('value','statement','field'):
            names=[e.get('name') for e in b.findall(tag)]
            assert len(names)==len(set(names)),f'{ident} 有重复 {tag} 名称'
        for e in b.findall('next')+b.findall('value')+b.findall('statement'):
            assert len(e.findall('block'))<=1,f'{ident} 单个输入连接多块积木'
    assert len(ids)==len(set(ids)),'积木 ID 重复'

def check():
    with zipfile.ZipFile(LATEST) as z:
        assert z.testzip() is None
        files={n:z.read(n) for n in z.namelist()}
    local={p.relative_to(SOURCE).as_posix():p.read_bytes() for p in SOURCE.rglob('*') if p.is_file()}
    assert files==local,'AIA 与展开源码不一致'
    props=dict(line.split('=',1) for line in files['youngandroidproject/project.properties'].decode().splitlines() if '=' in line)
    folder='src/'+props['main'].rsplit('.',1)[0].replace('.','/')+'/'
    screens={Path(n).stem for n in files if n.startswith(folder) and n.endswith('.scm')}
    assert screens=={'Screen1','Play','EditorSettings','Recorder'},f'屏幕缺失或路径不一致：{screens}'
    assert {n[:-4] for n in files if n.endswith('.scm')}=={n[:-4] for n in files if n.endswith('.bky')},'屏幕与积木文件不配对'
    ext={}
    for n,data in files.items():
        if n.startswith('assets/external_comps/') and n.endswith('/components.json'):
            ext.update({d['name']:d for d in json.loads(data)})
    count=0
    refs=0
    assert not ext,'当前版不应包含扩展'
    for n,data in files.items():
        if not n.endswith('.scm'):continue
        d=json.loads(data.decode().split('$JSON')[1].rsplit('|#',1)[0]);components={}
        assert d['Properties']['$Name']==Path(n).stem,f'屏幕内部名称与文件名不一致：{n}'
        versions={}
        def visit(c):
            kind=c['$Type'];version=int(c['$Version'])
            assert kind not in versions or versions[kind]==version,f'{n} 同类组件版本不一致：{kind}'
            versions[kind]=version
            components[c['$Name']]=c['$Type']
            if c['$Name']=='本地文件':assert c['$Type'] in ext
            for x in c.get('$Components',[]):visit(x)
        visit(d['Properties'])
        r=ET.fromstring(files[n[:-4]+'.bky'])
        for e in r.iter():e.tag=e.tag.split('}')[-1]
        check_block_structure(r)
        for b in r.iter('block'):
            if b.get('type') in ('controls_openAnotherScreen','controls_openAnotherScreenWithStartValue'):
                target=b.find("value[@name='SCREENNAME']/block/field[@name='TEXT']")
                assert target is not None and target.text in screens,f'跳转目标不存在：{n}'
            m=b.find('mutation')
            if b.get('type') in ('procedures_callnoreturn','procedures_callreturn'):
                proc=next(p for p in r if p.get('type','').startswith('procedures_def') and p.findtext("field[@name='NAME']")==m.get('name'))
                assert len(b.findall('value'))==len(proc.find('mutation').findall('arg'))
            if m is not None and m.get('is_generic')=='true':
                assert b.find("value[@name='COMPONENT']/block") is not None
                assert m.get('component_type')=='Canvas'
                refs+=1
            if m is None or not m.get('instance_name'):continue
            kind=components[m.get('instance_name')];assert kind==m.get('component_type')
            refs+=1
            if kind not in ext:continue
            key='methods' if b.get('type')=='component_method' else 'events'
            name=m.get('method_name') or m.get('event_name')
            entry=next(x for x in ext[kind][key] if x['name']==name)
            args=len(b.findall('value')) if key=='methods' else len([k for k in m.attrib if k.startswith('param_name')])
            assert args==len(entry['params'])
            count+=1
    print(f'通过：源码与 AIA 一致，4 个屏幕，{refs} 个组件引用有效，无自定义扩展，过程参数数量一致')

def build(version):
    import release
    release.SOURCE=SOURCE
    release.release(version)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['check','build']);parser.add_argument('--version',type=int)
    args=parser.parse_args()
    if args.action=='check':check()
    else:build(args.version)
