from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'archive/历史目录/tools'))
from 制谱器 import *
ROOT=Path(__file__).resolve().parents[1]
NAME='Rail4K_0924_1'

def prepend(s,items):
    old=s[0];s.remove(old);head=chain(items);last=head
    while last.find('next/block') is not None:last=last.find('next/block')
    ET.SubElement(last,'next').append(old);s.append(head)

def main():
    with zipfile.ZipFile(ROOT/'archive/历史目录/dist/Rail4K_0919_2.aia') as z:files={n:z.read(n) for n in z.namelist()}
    for path in [n for n in files if n.endswith('.scm')]:
        screen=Path(path).stem;d=json.loads(files[path].decode().split('$JSON')[1].rsplit('|#',1)[0]);p=d['Properties']
        if screen=='Play':p['$Components'].append(component('本地文件','LocalFiles',2))
        if screen=='EditorSettings':
            p['$Components'][0]['$Components'].insert(3,component('多押设置','CheckBox',2,Text='多押合并（40ms）',Checked='True',TextColor='&HFFEAF2FF',FontSize=16,Width=-2))
        def register(c):
            TYPES[c['$Name']]=c['$Type']
            if c['$Type']=='LocalFiles':c['$Version']='2'
            for x in c.get('$Components',[]):register(x)
        register(p)
        bk=path[:-4]+'.bky';r=ET.fromstring(files[bk])
        for e in r.iter():e.tag=e.tag.split('}')[-1]
        procs={b.findtext("field[@name='NAME']"):b for b in r if b.get('type','').startswith('procedures_def')}
        for n,b in procs.items():PROCS[n]=[a.get('name') for a in b.find('mutation').findall('arg')]
        TOP.clear()
        if screen=='EditorSettings':
            b=next(b for b in r.iter('block') if b.get('type')=='controls_openAnotherScreenWithStartValue')
            value=b.find("value[@name='STARTVALUE']/block");value.find('mutation').set('items','9')
            ET.SubElement(value,'value',name='ADD8').append(prop('多押设置','Checked',read=True))
        if screen in ['Play','Recorder']:
            r[:]=[b for b in r if not(b.get('type')=='component_event' and b.find('mutation').get('instance_name')=='画布' and b.find('mutation').get('event_name')=='TouchDown')]
            init=next(b for b in r if b.get('type')=='component_event' and b.find('mutation').get('event_name')=='Initialize')
            bind=method('本地文件','启用多点',block('component_component_block',{'COMPONENT_SELECTOR':'画布'},mutation=mut(component_type='Canvas',instance_name='画布')))
            if screen=='Play':
                prepend(init.find('statement'),[bind])
                事件('本地文件','轨道按下',[call('按轨',get('轨道'))],['轨道','触点数'])
            else:
                for n,v in [('合并多押',True),('触点数',1),('多押时间',-1)]:top(block('global_declaration',{'NAME':n},{'VALUE':v}),'')
                start=block('controls_getStartValue')
                setting=选(compare('GTE',长(start),9),item(block('controls_getStartValue'),9),True)
                prepend(init.find('statement'),[put('合并多押',setting),bind])
                prepend(procs['入场'].find('statement'),[put('多押时间',-1),put('触点数',1)])
                事件('本地文件','轨道按下',[put('触点数',get('触点数')),call('录入',get('轨道'))],['轨道','触点数'])
                ready=procs['录入'].find("statement/block/next/block/statement[@name='DO0']")
                reset=iff(either(非(g('合并多押')),either(等(g('触点数'),1),either(compare('LT',g('多押时间'),0),compare('GT',sub(g('用时'),g('多押时间')),40)))),[put('多押时间',g('用时'))])
                prepend(ready,[reset])
                decl=next(b for b in procs['录入'].iter('block') if b.get('type')=='local_declaration_statement' and b.findtext("field[@name='VAR0']")=='目标时间')
                for f in decl.find("value[@name='DECL0']").iter('field'):
                    if f.get('name')=='VAR' and f.text=='global 用时':f.text='global 多押时间'
        r.extend(TOP)
        stamp=r.find('yacodeblocks');r.remove(stamp);r.append(stamp)
        for i,b in enumerate(r.findall('block')):
            b.set('x',str(40+i//13*470));b.set('y',str(40+i%13*115))
            if b.get('type')!='global_declaration':b.set('collapsed','true')
        for i,b in enumerate(r.iter('block')):b.set('id',screen+'_'+str(i))
        r.set('xmlns','http://www.w3.org/1999/xhtml');ET.indent(r,space='  ');files[bk]=ET.tostring(r,encoding='utf-8')
        p.update(VersionCode='20',VersionName='0924.1')
        count=[0]
        def uuid(c):
            c['Uuid']=str(count[0]);count[0]+=1
            for x in c.get('$Components',[]):uuid(x)
        uuid(p)
        files[path]=('#|\n$JSON\n'+json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode()
    import re
    for n in files:
        if n.endswith('project.properties'):
            s=files[n].decode()
            for k,v in [('name',NAME),('versioncode','20'),('versionname','0924.1')]:s=re.sub(r'(?m)^'+k+r'=.*',k+'='+v,s)
            files[n]=s.encode()
    ext=ROOT/'extensions/localfiles/package'
    for f in ext.rglob('*'):
        if f.is_file():files['assets/external_comps/'+f.relative_to(ext).as_posix()]=f.read_bytes()
    with zipfile.ZipFile(ROOT/'dist'/f'{NAME}.aia','w',zipfile.ZIP_DEFLATED) as z:
        for n,data in files.items():
            z.writestr(n,data);f=ROOT/'native'/NAME/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
    print(NAME)

if __name__=='__main__':main()
