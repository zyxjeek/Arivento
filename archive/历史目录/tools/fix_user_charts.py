from 制谱器 import *

def main():
    source=ROOT/'dist/Rail4K_Offline_v9_CodeOnly.aia'
    target=ROOT/'dist/Rail4K_Offline_v10_CodeOnly.aia'
    raw=source.read_bytes()
    backup=ROOT/('original/user_v9_'+hashlib.sha256(raw).hexdigest()[:12]+'.aia')
    if not backup.exists(): backup.write_bytes(raw)
    with zipfile.ZipFile(source) as z: files={n:z.read(n) for n in z.namelist()}
    path=next(n for n in files if n.endswith('/Screen1.bky'))
    xml=ET.fromstring(files[path])
    for e in xml.iter(): e.tag=e.tag.split('}')[-1]
    scm=path[:-4]+'.scm'
    design=json.loads(files[scm].decode().split('$JSON')[1].rsplit('|#',1)[0])
    def register(c):
        TYPES[c['$Name']]=c['$Type']
        for x in c.get('$Components',[]): register(x)
    register(design['Properties'])
    procs={b.findtext("field[@name='NAME']"):b for b in xml if b.get('type','').startswith('procedures_def')}
    for n,b in procs.items(): PROCS[n]=[a.get('name') for a in b.find('mutation').findall('arg')]
    p=procs['还原数字'];v=p.find("value[@name='RETURN']");v.clear();v.set('name','RETURN')
    v.append(选(等(get('原值'),True),1,选(等(get('原值'),False),0,选(数字(get('原值')),mul(1,get('原值')),get('原值')))))
    def bad(message): return [put('有效',False),put('校验问题',message)]
    header=get('数据')
    h=lambda i:item(get('数据'),i)
    notes=h(8)
    n=lambda i:item(get('音符'),i)
    body=[put('有效',False),put('校验问题','谱面必须是包含八项数据的 JSON 列表'),call('修正数值',get('数据')),
        iff(列表(header),[iff(等(长(get('数据')),8),[
            put('校验问题','名称、音乐名、过屏时间、模式、BPM、吸附单位或结束时间不正确'),
            iff(全(文本(h(1)),文本(h(2)),正数(h(3)),包含(make_list(1,2),h(4)),正数(h(5)),正数(h(6)),正数(h(7))),[
                put('校验问题','第八项必须是非空音符列表'),iff(列表(notes),[iff(compare('GT',长(h(8)),0),[
                    put('有效',True),put('校验问题',''),local('前时',-1,[loop('键号',1,长(h(8)),[
                        iff(g('有效'),[local('音符',item(h(8),get('键号')),[
                            iff(列表(get('音符')),[iff(等(长(get('音符')),2),[
                                iff(全(包含(make_list(1,2,3,4),n(1)),数字(n(2))),[
                                    iff(compare('LT',n(2),0),bad(join('第 ',get('键号'),' 个音符时间为负数')),[
                                        iff(compare('LT',n(2),选(等(get('键号'),1),0,item(item(h(8),sub(get('键号'),1)),2))),bad(join('第 ',get('键号'),' 个音符时间早于前一个音符')),[
                                            iff(compare('GT',add(n(2),160),h(7)),bad(join('第 ',get('键号'),' 个音符距离结束不足 160ms')),[局设('前时',n(2))])
                                        ])
                                    ])
                                ],bad(join('第 ',get('键号'),' 个音符的轨道或时间不是有效数字')))
                            ],bad(join('第 ',get('键号'),' 个音符不是二项列表')))],bad(join('第 ',get('键号'),' 个音符不是列表')))
                        ])])
                    ])])
                ])])
            ])
        ])])]
    s=procs['检查谱面'].find('statement');s.clear();s.set('name','STACK');s.append(chain(body))
    xml[:]=[b for b in xml if not(b.get('type')=='component_event' and b.find('mutation').get('instance_name')=='谱面文件' and b.find('mutation').get('event_name')=='GotText')]
    TOP.clear()
    top(block('global_declaration',{'NAME':'校验问题'},{'VALUE':''}),'')
    事件('谱面文件','GotText',[iff(g('读取中'),[
        put('读取中',False),设('选谱',True,'Enabled'),
        iff(等(修剪(get('内容')),''),[put('当前谱',make_list()),设('开始',False,'Enabled'),设('读取状态',join(取('选谱','Selection'),' 是空文件')),警告('谱面文件没有内容。请把制谱器分享的完整文本保存到文件后重新上传。')],[
            local('数据',method('文本转换','JsonTextDecode',修剪(get('内容'))),[
                call('检查谱面',get('数据')),iff(g('有效'),[put('当前谱',get('数据')),设('标题',join('定轨四键\n',h(1))),设('读取状态',取('选谱','Selection')),设('开始',True,'Enabled')],[
                    put('当前谱',make_list()),设('开始',False,'Enabled'),设('读取状态',join(取('选谱','Selection'),'：',g('校验问题'))),警告(join('谱面读取失败：',g('校验问题')))
                ])
            ])
        ])
    ])],['内容'])
    xml.extend(TOP)
    stamp=xml.find('yacodeblocks');xml.remove(stamp);xml.append(stamp)
    for i,b in enumerate(xml.findall('block')):
        b.set('x',str(40+i//13*470));b.set('y',str(40+i%13*115))
        if b.get('type')!='global_declaration': b.set('collapsed','true')
    for i,b in enumerate(xml.iter('block')): b.set('id',f'校验_{i}')
    xml.set('xmlns','http://www.w3.org/1999/xhtml');ET.indent(xml,space='  ')
    files[path]=ET.tostring(xml,encoding='utf-8')
    chart=json.loads(files['assets/测试.txt'])
    def exact(v):
        if isinstance(v,list): return [exact(x) for x in v]
        return int(v) if isinstance(v,float) and v.is_integer() else v
    files['assets/测试.txt']=json.dumps(exact(chart),ensure_ascii=False,separators=(',',':')).encode()
    audio=[]
    for n in list(files):
        if n.startswith('assets/') and Path(n).suffix.lower() in ['.mp3','.ogg','.m4a','.wav','.aac']:
            audio.append(n);del files[n]
        elif n.endswith('.scm'):
            d=json.loads(files[n].decode().split('$JSON')[1].rsplit('|#',1)[0]);d['Properties'].update(VersionCode='14',VersionName='0.7.3')
            files[n]=('#|\n$JSON\n'+json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode()
        elif n.endswith('project.properties'):
            files[n]=files[n].decode().replace('versioncode=13','versioncode=14').replace('versionname=0.7.2','versionname=0.7.3').encode()
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for n,data in files.items():
            z.writestr(n,data)
            f=ROOT/'native/Rail4K_UserChartFix'/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
    print(json.dumps({'output':str(target),'backup':str(backup),'audio_not_packaged':audio,'ark2_bytes':len(files['assets/ark2.txt'])},ensure_ascii=False))

if __name__=='__main__': main()
