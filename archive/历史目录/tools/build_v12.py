from 制谱器 import *

def main():
    source=ROOT/'dist/Rail4K_Offline_v11_CodeOnly.aia'
    target=ROOT/'dist/Rail4K_Offline_v12_CodeOnly.aia'
    raw=source.read_bytes()
    backup=ROOT/('original/v11_'+hashlib.sha256(raw).hexdigest()[:12]+'.aia')
    if not backup.exists(): backup.write_bytes(raw)
    with zipfile.ZipFile(source) as z: files={n:z.read(n) for n in z.namelist()}
    path=next(n for n in files if n.endswith('/Play.bky'))
    xml=ET.fromstring(files[path])
    for e in xml.iter():e.tag=e.tag.split('}')[-1]
    procs={b.findtext("field[@name='NAME']"):b for b in xml if b.get('type','').startswith('procedures_def')}
    assert all(n in procs for n in ['准备游玩键','取游玩键','完成游玩'])
    p=procs['取游玩键'];value=p.find("value[@name='RETURN']");value.clear();value.set('name','RETURN')
    m=mut();ET.SubElement(m,'localname',name='段号')
    body=block('controls_do_then_return',values={'VALUE':item(g('缓存分段'),sub(get('键号'),mul(sub(get('段号'),1),64)))},statements={'STM':[
        iff(非(等(g('缓存段号'),get('段号'))),[put('缓存段号',get('段号')),put('缓存分段',item(g('游玩分段'),get('段号')))])
    ]})
    value.append(block('local_declaration_expression',{'VAR0':'段号'},{'DECL0':add(unary('FLOOR',div(sub(get('键号'),1),64)),1),'RETURN':body},mutation=m))
    s=procs['准备游玩键'].find('statement');first=s[0];s.remove(first)
    head=chain([put('缓存段号',0),put('缓存分段',make_list())]);ET.SubElement(head.find('next/block'),'next').append(first);s.append(head)
    TOP.clear()
    for n,v in [('缓存段号',0),('缓存分段',make_list())]:top(block('global_declaration',{'NAME':n},{'VALUE':v}),'')
    xml.extend(TOP)
    stamp=xml.find('yacodeblocks');xml.remove(stamp);xml.append(stamp)
    for i,b in enumerate(xml.findall('block')):
        b.set('x',str(40+i//13*470));b.set('y',str(40+i%13*115))
        if b.get('type')!='global_declaration':b.set('collapsed','true')
    for i,b in enumerate(xml.iter('block')):b.set('id',f'分段_{i}')
    xml.set('xmlns','http://www.w3.org/1999/xhtml');ET.indent(xml,space='  ')
    files[path]=ET.tostring(xml,encoding='utf-8')
    for n in files:
        if n.endswith('.scm'):
            d=json.loads(files[n].decode().split('$JSON')[1].rsplit('|#',1)[0]);d['Properties'].update(VersionCode='16',VersionName='0.7.5')
            files[n]=('#|\n$JSON\n'+json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode()
        elif n.endswith('project.properties'):
            files[n]=files[n].decode().replace('versioncode=15','versioncode=16').replace('versionname=0.7.4','versionname=0.7.5').encode()
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for n,data in files.items():
            z.writestr(n,data)
            p=ROOT/'native/Rail4K_V12'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    print(target)

if __name__=='__main__':main()
