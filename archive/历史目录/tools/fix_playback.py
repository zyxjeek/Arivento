from 制谱器 import *

def main():
    source=ROOT/'dist/Rail4K_Multi_v5_CodeOnly.aia'
    target=ROOT/'dist/Rail4K_Multi_v6_CodeOnly.aia'
    TYPES.update(音乐='Player',时钟='Clock',信息='Label',提示='Notifier')
    with zipfile.ZipFile(source) as old, zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as new:
        for name in old.namelist():
            data=old.read(name)
            if name.endswith('.scm'):
                d=json.loads(data.decode().split('$JSON')[1].rsplit('|#',1)[0])
                d['Properties'].update(VersionCode='10',VersionName='0.6.4')
                data=('#|\n$JSON\n'+json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode()
            elif name.endswith(('/Recorder.bky','/Play.bky')):
                xml=ET.fromstring(data)
                for e in xml.iter(): e.tag=e.tag.split('}')[-1]
                procs={b.findtext("field[@name='NAME']"):b for b in xml.findall('block') if b.get('type').startswith('procedures_def')}
                for n,b in procs.items(): PROCS[n]=[x.get('name') for x in b.find('mutation').findall('arg')]
                PROCS.update(启动音乐=[],播放失败=[])
                def body(n,stm):
                    b=procs[n]
                    s=b.find('statement'); s.clear(); s.set('name','STACK'); s.append(chain(stm))
                logic=copy.deepcopy(procs['走时'].find("statement/block/statement[@name='DO0']/block/next/block/next/block"))
                body('走时',[iff(either(等(g('状态'),1),等(g('状态'),2)),[
                    iff(g('已播放'),[put('用时',maximum(g('用时'),sub(时间(),g('起点'))))],[put('用时',minimum(0,sub(时间(),g('起点')))),iff(compare('GTE',g('用时'),0),[call('启动音乐')])]),
                    iff(g('已播放'),[logic])])])
                first=procs['入场'].find('statement/block')
                procs['入场'].find('statement').remove(first)
                head=chain([put('播放请求',False),put('播放起始',0),method('音乐','Stop'),设('音乐','','Source'),设('音乐',100,'Volume')])
                tail=head
                while tail.find('next/block') is not None: tail=tail.find('next/block')
                ET.SubElement(tail,'next').append(first)
                procs['入场'].find('statement').append(head)
                for n in ['录入','按轨']:
                    if n in procs:
                        v=procs[n].find("statement/block/next/block/value[@name='IF0']")
                        oldtest=v[0];v.remove(oldtest);v.append(全(g('已播放'),oldtest))
                TOP.clear()
                for n,v in [('播放请求',False),('播放起始',0)]: top(block('global_declaration',{'NAME':n},{'VALUE':v}),'')
                confirm=[put('已播放',True),put('起点',时间()),put('用时',0)]
                过程('启动音乐',[iff(等(g('音乐名'),''),copy.deepcopy(confirm),[
                    iff(非(g('播放请求')),[put('播放请求',True),put('播放起始',时间()),method('音乐','Start')]),
                    iff(either(等(g('状态'),1),等(g('状态'),2)),[iff(取('音乐','IsPlaying'),copy.deepcopy(confirm),[iff(compare('GTE',sub(时间(),g('播放起始')),1500),[call('播放失败')])])])])])
                过程('播放失败',([call('完成录制')] if '/Recorder.' in name else [put('状态',3)])+[
                    设('时钟',False,'TimerEnabled'),method('音乐','Stop'),put('已播放',False),
                    设('信息',join('音乐未能播放：',g('音乐名'))),警告(join('无法播放 ',g('音乐名'),'。请确认已上传同名音频；iPhone 建议使用真正转换后的 MP3/M4A，不能只改后缀。'))])
                xml.extend(TOP)
                for b in xml.iter('block'):
                    m=b.find('mutation')
                    if m is not None and m.get('method_name')=='DrawText':
                        v=b.find("value[@name='ARG0']"); original=v[0]; v.remove(original)
                        v.append(选(全(g('播放请求'),非(g('已播放')),either(等(g('状态'),1),等(g('状态'),2))),'正在启动音乐',original))
                stamp=xml.find('yacodeblocks');xml.remove(stamp);xml.append(stamp)
                for i,b in enumerate(xml.iter('block')):b.set('id',f'播放_{i}')
                xml.set('xmlns','http://www.w3.org/1999/xhtml');ET.indent(xml,space='  ')
                data=ET.tostring(xml,encoding='utf-8')
            elif name.endswith('project.properties'):
                data=data.decode().replace('versioncode=9','versioncode=10').replace('versionname=0.6.3','versionname=0.6.4').encode()
            new.writestr(name,data)
            out=ROOT/'native/Rail4K_PlaybackFix'/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
    print(target)

if __name__=='__main__': main()
