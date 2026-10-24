from pathlib import Path
import sys,copy,re

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'archive/历史目录/tools'))
from 制谱器 import *
ROOT=Path(__file__).resolve().parents[1]
NAME='Rail4K_1011_1'

def replace_value(b,name,v):
    e=b.find("value[@name='"+name+"']");e.clear();e.set('name',name);e.append(v)

def prepend(s,body):
    old=s[0];s.remove(old);head=chain(body);last=head
    while last.find('next/block') is not None:last=last.find('next/block')
    ET.SubElement(last,'next').append(old);s.append(head)

def main():
    with zipfile.ZipFile(ROOT/'dist/Rail4K_0924_2.aia') as z:files={n:z.read(n) for n in z.namelist()}
    for path in [n for n in files if n.endswith('.scm')]:
        screen=Path(path).stem;d=json.loads(files[path].decode().split('$JSON')[1].rsplit('|#',1)[0]);p=d['Properties']
        TOP.clear();TYPES.clear();PROCS.clear()
        def register(c):
            TYPES[c['$Name']]=c['$Type']
            for x in c.get('$Components',[]):register(x)
        register(p)
        bk=path[:-4]+'.bky';r=ET.fromstring(files[bk])
        for e in r.iter():e.tag=e.tag.split('}')[-1]
        procs={b.findtext("field[@name='NAME']"):b for b in r if b.get('type','').startswith('procedures_def')}
        for n,b in procs.items():PROCS[n]=[a.get('name') for a in b.find('mutation').findall('arg')]
        if screen=='EditorSettings':
            def defaults(c):
                if c['$Name']=='过屏输入':c['Text']='500'
                for x in c.get('$Components',[]):defaults(x)
            defaults(p)
        if screen=='Screen1':
            home=p['$Components'][0]
            home['$Components'].extend([
                component('延迟标题','Label',5,Text='谱面延迟（毫秒，-200～200）',Width=-2,TextColor=白色,FontSize=14),
                component('延迟输入','TextBox',6,Text='0',Hint='正数延后，负数提前',Width=-2,Height=40,BackgroundColor='&HFF151E32',TextColor=白色,FontSize=16,MultiLine=False),
                component('过屏标题','Label',5,Text='过屏时间（毫秒）',Width=-2,TextColor=白色,FontSize=14),
                component('游玩过屏输入','TextBox',6,Text='500',Hint='数值越小，下落越快',Width=-2,Height=40,BackgroundColor='&HFF151E32',TextColor=白色,FontSize=16,NumbersOnly=True,MultiLine=False)])
            register(p)
            event=next(b for b in r if b.get('type')=='component_event' and b.find('mutation').get('instance_name')=='开始')
            s=event.find('statement');old=s[0];s.remove(old)
            opening=next(b for b in old.iter('block') if b.get('type')=='controls_openAnotherScreenWithStartValue')
            replace_value(opening,'STARTVALUE',make_list(*[item(g('当前谱'),i) for i in range(1,9)],add(取('延迟输入'),0),add(取('游玩过屏输入'),0)))
            s.append(iff(全(数字(取('延迟输入')),数字(取('游玩过屏输入'))),[
                iff(全(compare('GTE',add(取('延迟输入'),0),-200),compare('LTE',add(取('延迟输入'),0),200),compare('GT',add(取('游玩过屏输入'),0),0)),[old],[警告('延迟须在 -200～200ms，过屏时间须大于 0ms')])],[警告('请输入有效的延迟和过屏时间数字')]))
        if screen=='Play':
            initial=next(b for b in r if b.get('type')=='global_declaration' and b.findtext("field[@name='NAME']")=='过屏时间')
            replace_value(initial,'VALUE',expr(500))
            top(block('global_declaration',{'NAME':'谱面延迟'},{'VALUE':0}),'')
            read=procs['读取当前谱']
            prepend(read.find('statement'),[put('谱面延迟',选(compare('GTE',长(g('当前谱')),9),item(g('当前谱'),9),0))])
            for b in read.iter('block'):
                if b.get('type')=='lexical_variable_set':
                    name=b.findtext("field[@name='VAR']")
                    if name=='global 过屏时间':replace_value(b,'VALUE',选(compare('GTE',长(g('当前谱')),10),item(g('当前谱'),10),500))
                    if name=='global 结束时间':replace_value(b,'VALUE',add(item(g('当前谱'),7),选(compare('GT',g('谱面延迟'),0),g('谱面延迟'),0)))
            for b in procs['准备游玩键'].iter('block'):
                if b.get('type')=='lists_create_with' and b.find("value[@name='ADD2']") is not None:
                    replace_value(b,'ADD1',add(item(get('音符'),2),g('谱面延迟')))
            for name in ['按轨','走时']:
                for parent in procs[name].iter():
                    for b in list(parent):
                        if b.tag=='block' and b.get('type')=='lexical_variable_get' and b.findtext("field[@name='VAR']")=='global 已播放':
                            if name=='走时' and parent.get('name')=='IF0':
                                owner=next(x for x in procs[name].iter('block') if parent in list(x))
                                if owner.find("statement[@name='ELSE']") is not None:continue
                            parent.remove(b);parent.append(expr(True))
        r.extend(TOP)
        stamp=r.find('yacodeblocks');r.remove(stamp);r.append(stamp)
        for i,b in enumerate(r.iter('block')):b.set('id',screen+'_'+str(i))
        for i,b in enumerate(r.findall('block')):b.set('x',str(40+i//13*470));b.set('y',str(40+i%13*115))
        r.set('xmlns','http://www.w3.org/1999/xhtml');ET.indent(r,space='  ');files[bk]=ET.tostring(r,encoding='utf-8')
        p.update(VersionCode='23',VersionName='1011.1')
        counter=[0]
        def ids(c):
            c['Uuid']=str(counter[0]);counter[0]+=1
            for x in c.get('$Components',[]):ids(x)
        ids(p)
        files[path]=('#|\n$JSON\n'+json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode()
    for n in files:
        if n.endswith('project.properties'):
            s=files[n].decode()
            for k,v in [('name',NAME),('versioncode','23'),('versionname','1011.1')]:s=re.sub(r'(?m)^'+k+r'=.*',k+'='+v,s)
            files[n]=s.encode()
    with zipfile.ZipFile(ROOT/'dist'/f'{NAME}.aia','w',zipfile.ZIP_DEFLATED) as z:
        for n,data in files.items():
            z.writestr(n,data);f=ROOT/'native'/NAME/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
    print(NAME)

if __name__=='__main__':main()
