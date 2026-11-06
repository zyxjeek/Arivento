from pathlib import Path
import json,zipfile,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
NAME=json.loads((ROOT/'tools/current_release.json').read_text(encoding='utf-8'))['name']
SOURCE=ROOT/'native'/NAME
LATEST=ROOT/'dist'/(NAME+'.aia')
SCREENS={'Screen1','Play'}

def check_block_structure(r):
    ids=[]
    for b in r.iter('block'):
        ident=b.get('id');ids.append(ident)
        for tag in ('next','mutation'):assert len(b.findall(tag))<=1,f'{ident} 有重复 {tag} 连接'
        for tag in ('value','statement','field'):
            names=[e.get('name') for e in b.findall(tag)]
            assert len(names)==len(set(names)),f'{ident} 有重复 {tag} 名称'
        for e in b.findall('next')+b.findall('value')+b.findall('statement'):assert len(e.findall('block'))<=1,f'{ident} 单个输入连接多块积木'
    assert len(ids)==len(set(ids)),'积木 ID 重复'

def check():
    with zipfile.ZipFile(LATEST) as z:
        assert z.testzip() is None
        files={n:z.read(n) for n in z.namelist()}
    local={p.relative_to(SOURCE).as_posix():p.read_bytes() for p in SOURCE.rglob('*') if p.is_file()}
    assert files==local,'AIA 与展开源码不一致'
    props=dict(line.split('=',1) for line in files['youngandroidproject/project.properties'].decode().splitlines() if '=' in line)
    folder='src/'+props['main'].rsplit('.',1)[0].replace('.','/')+'/'
    assert {Path(n).stem for n in files if n.startswith(folder) and n.endswith('.scm')}==SCREENS,'屏幕缺失或路径不一致'
    assert {n[:-4] for n in files if n.endswith('.scm')}=={n[:-4] for n in files if n.endswith('.bky')},'屏幕与积木文件不配对'
    assets={Path(n).name for n in files if n.startswith('assets/')}
    refs=blocks=0
    for n,data in files.items():
        if not n.endswith('.scm'):continue
        d=json.loads(data.decode().split('$JSON')[1].rsplit('|#',1)[0]);components={};versions={}
        assert d['Properties']['$Name']==Path(n).stem,f'屏幕内部名称与文件名不一致：{n}'
        def visit(c):
            kind=c['$Type'];version=int(c['$Version'])
            assert versions.setdefault(kind,version)==version,f'{n} 同类组件版本不一致：{kind}'
            components[c['$Name']]=kind
            if c.get('Source'):assert c['Source'] in assets,f'素材不存在：{c["Source"]}'
            for x in c.get('$Components',[]):visit(x)
        visit(d['Properties'])
        r=ET.fromstring(files[n[:-4]+'.bky'])
        for e in r.iter():e.tag=e.tag.split('}')[-1]
        check_block_structure(r);blocks+=sum(1 for _ in r.iter('block'))
        procs={p.findtext("field[@name='NAME']"):p for p in r if p.get('type','').startswith('procedures_def')}
        for b in r.iter('block'):
            if b.get('type')=='controls_openAnotherScreenWithStartValue':
                assert b.find("value[@name='SCREENNAME']/block/field[@name='TEXT']").text in SCREENS,f'跳转目标不存在：{n}'
            m=b.find('mutation')
            if b.get('type') in ('procedures_callnoreturn','procedures_callreturn'):
                assert len(b.findall('value'))==len(procs[m.get('name')].find('mutation').findall('arg')),f'过程参数数量不一致：{m.get("name")}'
            if m is None or m.get('is_generic') is None:continue
            if m.get('is_generic')=='true':assert b.find("value[@name='COMPONENT']/block") is not None and m.get('component_type') in components.values()
            else:assert components[m.get('instance_name')]==m.get('component_type'),f'组件引用无效：{m.get("instance_name")}'
            refs+=1
    print(f'通过：源码与 AIA 一致，2 个屏幕，{blocks} 块积木，{refs} 个组件引用有效')

if __name__=='__main__':check()
