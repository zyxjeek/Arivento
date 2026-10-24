from 制谱器 import *

def number(v):
    m=mut(name='还原数字');ET.SubElement(m,'arg',name='原值')
    return block('procedures_callreturn',{'PROCNAME':'还原数字'},{'ARG0':v},mutation=m)

def main():
    source=ROOT/'dist/Rail4K_Offline_v8_CodeOnly.aia'
    target=ROOT/'dist/Rail4K_Offline_v9_CodeOnly.aia'
    with zipfile.ZipFile(source) as z: files={n:z.read(n) for n in z.namelist()}
    path=next(n for n in files if n.endswith('/Screen1.bky'))
    xml=ET.fromstring(files[path])
    for e in xml.iter(): e.tag=e.tag.split('}')[-1]
    p=next(b for b in xml if b.get('type')=='procedures_defnoreturn' and b.findtext("field[@name='NAME']")=='检查谱面')
    PROCS.update(修正数值=['数据'])
    s=p.find('statement');first=s[0];s.remove(first)
    head=call('修正数值',get('数据'));ET.SubElement(head,'next').append(first);s.append(head)
    TOP.clear()
    m=mut();ET.SubElement(m,'arg',name='原值')
    top(block('procedures_defreturn',{'NAME':'还原数字','VAR0':'原值'},{'RETURN':选(等(get('原值'),True),1,选(等(get('原值'),False),0,get('原值')))},mutation=m),'')
    过程('修正数值',[iff(列表(get('数据')),[iff(等(长(get('数据')),8),[
        loop('序号',3,7,[改(get('数据'),get('序号'),number(item(get('数据'),get('序号'))))]),
        iff(列表(item(get('数据'),8)),[遍历('音符',item(get('数据'),8),[iff(列表(get('音符')),[iff(等(长(get('音符')),2),[
            改(get('音符'),1,number(item(get('音符'),1))),改(get('音符'),2,number(item(get('音符'),2)))
        ])])])])
    ])])])
    xml.extend(TOP)
    stamp=xml.find('yacodeblocks');xml.remove(stamp);xml.append(stamp)
    for i,b in enumerate(xml.findall('block')):
        b.set('x',str(40+i//13*470));b.set('y',str(40+i%13*115))
        if b.get('type')!='global_declaration': b.set('collapsed','true')
    for i,b in enumerate(xml.iter('block')): b.set('id',f'读取_{i}')
    xml.set('xmlns','http://www.w3.org/1999/xhtml');ET.indent(xml,space='  ')
    files[path]=ET.tostring(xml,encoding='utf-8')
    names=files['assets/music_list.txt'].decode().splitlines()
    names=[n[:-4]+'.mp3' if n.lower().endswith('.ogg') else n for n in names]
    assert len(names)==322 and all((ROOT/'Phigros_Music_3.20.0_MP3'/n).is_file() for n in names)
    files['assets/music_list.txt']=('\n'.join(names)+'\n').encode()
    (ROOT/'docs/music_list.txt').write_bytes(files['assets/music_list.txt'])
    for n in files:
        if n.endswith('.scm'):
            d=json.loads(files[n].decode().split('$JSON')[1].rsplit('|#',1)[0]);d['Properties'].update(VersionCode='13',VersionName='0.7.2')
            files[n]=('#|\n$JSON\n'+json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode()
        elif n.endswith('project.properties'):
            files[n]=files[n].decode().replace('versioncode=12','versioncode=13').replace('versionname=0.7.1','versionname=0.7.2').encode()
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for n,data in files.items():
            z.writestr(n,data)
            f=ROOT/'native/Rail4K_ChartFix'/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
    print(target)

if __name__=='__main__': main()
