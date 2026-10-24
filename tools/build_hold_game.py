from pathlib import Path
import sys,copy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'archive/历史目录/tools'))
from 制谱器 import *
from build_native_tracks import cm,cp,prepend
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'native/Arivento_Hold_source'
LANES=['轨道一','轨道二','轨道三','轨道四']
def ret(n,*a):
    b=call(n,*a);b.set('type','procedures_callreturn');return b
def note(i):return ret('取游玩键',i)
def v(i,k):return item(note(i),k)
def setbody(b,body):
    s=b.find('statement');s.clear();s.set('name','STACK');s.append(chain(body))
def replace_value(b,n,value):
    e=b.find("value[@name='"+n+"']");e.clear();e.set('name',n);e.append(expr(value))
def glob(n,value):top(block('global_declaration',{'NAME':n},{'VALUE':value}),'')
def fail(message):return [put('有效',False),put('校验问题',message)]
def invalid():return fail(join('第 ',get('键号'),' 个音符格式、时间或同轨占用不正确'))
def bounded(x,lo,hi):return 全(非(文本(copy.deepcopy(x))),数字(copy.deepcopy(x)),compare('GTE',copy.deepcopy(x),lo),compare('LTE',x,hi))

with zipfile.ZipFile(ROOT/'archive/hold_base_1016/Arivento.aia') as z:files={n:z.read(n) for n in z.namelist()}
for path in [n for n in files if n.endswith('.scm')]:
    screen=Path(path).stem
    if screen not in ['Screen1','Play']:continue
    d=json.loads(files[path].decode().split('$JSON')[1].rsplit('|#',1)[0]);p=d['Properties']
    if screen=='Screen1':p.update(VersionCode='24',VersionName='1017.1',AppName='Arivento')
    TOP.clear();TYPES.clear();PROCS.clear()
    def register(c):
        TYPES[c['$Name']]=c['$Type']
        if screen=='Play' and c['$Type']=='Canvas':c['ExtendMovesOutsideCanvas']='True'
        if c.get('$Name')=='制谱':c['Text']='内置制谱器（Legacy · Tap）'
        for child in c.get('$Components',[]):register(child)
    register(p)
    bk=path[:-4]+'.bky';r=ET.fromstring(files[bk])
    for e in r.iter():e.tag=e.tag.split('}')[-1]
    procs={b.findtext("field[@name='NAME']"):b for b in r if b.get('type','').startswith('procedures_def')}
    for n,b in procs.items():PROCS[n]=[a.get('name') for a in b.find('mutation').findall('arg')]
    if screen=='Screen1':
        for b in procs['修正数值'].iter('block'):
            if b.get('type')=='math_compare' and b.find("value[@name='A']/block[@type='lists_length']") is not None:
                length=b.find("value[@name='A']/block/value/block")
                if length is not None and length.findtext("field[@name='VAR']")=='音符':
                    b.find("field[@name='OP']").text='GTE'
        s=procs['修正数值'].find('statement')
        fix_tail=iff(列表(get('音符')),[iff(等(长(get('音符')),3),[改(get('音符'),3,ret('还原数字',item(get('音符'),3)))])])
        fix_notes=iff(列表(item(get('数据'),8)),[遍历('音符',item(get('数据'),8),[fix_tail])])
        prepend(s,[iff(列表(get('数据')),[iff(等(长(get('数据')),8),[fix_notes])])])
        valid_header=全(文本(item(get('数据'),1)),非(等(修剪(item(get('数据'),1)),'')),文本(item(get('数据'),2)),bounded(item(get('数据'),3),0,1e9),compare('GT',item(get('数据'),3),0),bounded(item(get('数据'),4),1,2),包含(make_list(1,2),item(get('数据'),4)),bounded(item(get('数据'),5),20,400),bounded(item(get('数据'),6),1,64),bounded(item(get('数据'),7),0,7200000))
        n=lambda k:item(get('音符'),k)
        lane=lambda:item(get('上条'),n(1))
        validate_note=[iff(列表(get('音符')),[iff(包含(make_list(2,3),长(get('音符'))),[
            iff(全(bounded(n(1),1,4),包含(make_list(1,2,3,4),n(1)),bounded(n(2),0,7199500)),[
                local('尾时',选(等(长(get('音符')),3),n(3),n(2)),[
                    iff(全(bounded(get('尾时'),0,7199500),either(等(长(get('音符')),2),compare('GT',get('尾时'),n(2))),compare('GTE',n(2),get('前时'))),[
                        iff(compare('GT',n(2),item(get('上尾'),n(1))),[
                            添(get('整理'),get('音符')),改(get('上尾'),n(1),get('尾时')),改(get('上条'),n(1),长(get('音符'))),改(get('数据'),7,maximum(item(get('数据'),7),add(get('尾时'),500)))
                        ],[iff(非(全(等(lane(),2),等(长(get('音符')),2),等(n(2),item(get('上尾'),n(1))))),invalid())]),局设('前时',n(2))
                    ],invalid())
                ])
            ],invalid())
        ],invalid())],invalid())]
        setbody(procs['检查谱面'],[*fail('谱面必须为合法八项列表'),iff(列表(get('数据')),[iff(等(长(get('数据')),8),[iff(valid_header,[iff(列表(item(get('数据'),8)),[iff(全(compare('GT',长(item(get('数据'),8)),0),compare('LTE',长(item(get('数据'),8)),100000)),[
            put('有效',True),put('校验问题',''),local('上尾',make_list(-1,-1,-1,-1),[local('上条',make_list(0,0,0,0),[local('前时',-1,[local('整理',make_list(),[
                loop('键号',1,长(item(get('数据'),8)),[iff(g('有效'),[local('音符',item(item(get('数据'),8),get('键号')),validate_note)])]),iff(g('有效'),[改(get('数据'),8,get('整理'))])
            ])])])])
        ])])])])])])
    else:
        PROCS.update(清空按压=[],轨道按下=['轨道'],轨道松开=['轨道'],长条到期=[],绘制音符=['键号'])
        for name in ['按住轨道','持续长条','显示长条']:glob(name,make_list(0,0,0,0))
        过程('清空按压',[put(n,make_list(0,0,0,0)) for n in ['按住轨道','持续长条','显示长条']])
        for name in ['入场','返回首页','播放失败','完成游玩']:prepend(procs[name].find('statement'),[call('清空按压')])
        for b in procs['准备游玩键'].iter('block'):
            if b.get('type')=='lists_create_with' and b.find("value[@name='ADD2']") is not None:
                b.find('mutation').set('items','4');ET.SubElement(b,'value',name='ADD3').append(expr(选(等(长(get('音符')),3),add(item(get('音符'),3),g('谱面延迟')),add(item(get('音符'),2),g('谱面延迟')))))
        prepare_loop=next(b for b in procs['准备游玩键'].iter('block') if b.get('type')=='controls_forEach')
        prepend(prepare_loop.find('statement'),[put('结束时间',maximum(g('结束时间'),add(选(等(长(get('音符')),3),item(get('音符'),3),item(get('音符'),2)),g('谱面延迟'),500)))])
        r[:]=[b for b in r if not(b.get('type')=='component_event' and b.find('mutation').get('instance_name') in LANES)]
        for i,n in enumerate(LANES,1):
            事件(n,'TouchDown',[call('轨道按下',i)],['横坐标','纵坐标'])
            事件(n,'TouchUp',[call('轨道松开',i)],['横坐标','纵坐标'])
            事件(n,'Dragged',[iff(either(either(compare('LTE',get('横坐标'),0),compare('GTE',get('横坐标'),取(n,'Width'))),either(compare('LTE',get('纵坐标'),0),compare('GTE',get('纵坐标'),取(n,'Height')))),[call('轨道松开',i)])],['起横','起纵','前横','前纵','横坐标','纵坐标','精灵'])
        过程('轨道按下',[call('走时'),iff(全(等(g('状态'),1),等(item(g('按住轨道'),get('轨道')),0)),[改(g('按住轨道'),get('轨道'),1),call('按轨',get('轨道'))])])
        过程('轨道松开',[call('走时'),改(g('按住轨道'),get('轨道'),0),local('键号',item(g('持续长条'),get('轨道')),[iff(compare('GT',get('键号'),0),[call('记录判定',get('键号'),1),改(g('持续长条'),get('轨道'),0)])])])
        过程('长条到期',[loop('轮次',1,4,[local('最早',0,[loop('轨号',1,4,[local('键号',item(g('持续长条'),get('轨号')),[iff(compare('GT',get('键号'),0),[iff(compare('LTE',v(get('键号'),4),g('用时')),[iff(either(等(get('最早'),0),compare('LT',v(get('键号'),4),v(get('最早'),4))),[局设('最早',get('键号'))])])])])]),iff(compare('GT',get('最早'),0),[改(g('持续长条'),v(get('最早'),1),0),call('记录判定',get('最早'),sub(v(get('最早'),3),2))])])])])
        clock=copy.deepcopy(procs['走时'].find("statement/block/statement[@name='DO0']/block"))
        nxt=clock.find('next');clock.remove(nxt)
        setbody(procs['走时'],[iff(等(g('状态'),1),[clock,call('长条到期'),local('序号',g('下一键'),[循环(全(compare('LTE',get('序号'),g('物量')),compare('LTE',v(get('序号'),2),g('用时'))),[
            iff(全(等(v(get('序号'),3),0),either(compare('GT',g('用时'),add(v(get('序号'),2),160)),全(compare('GT',v(get('序号'),4),v(get('序号'),2)),compare('GTE',g('用时'),v(get('序号'),4))))),[call('记录判定',get('序号'),1)]),局设('序号',add(get('序号'),1))
        ])]),iff(compare('GTE',g('用时'),g('结束时间')),[call('完成游玩')])])])
        old=procs['记录判定'].find('statement/block');procs['记录判定'].find('statement').remove(old)
        setbody(procs['记录判定'],[iff(either(等(v(get('键号'),3),0),compare('GTE',v(get('键号'),3),4)),[
            iff(compare('GT',v(get('键号'),4),v(get('键号'),2)),[改(g('显示长条'),v(get('键号'),1),get('键号'))]),old
        ])])
        for parent in list(procs['按轨'].iter()):
            for b in list(parent):
                if b.get('type')=='procedures_callnoreturn' and b.find('mutation').get('name')=='记录判定':
                    result=copy.deepcopy(b.find("value[@name='ARG1']/block"));nxt=b.find('next');parent.remove(b)
                    new=local('头部判定',result,[iff(compare('GT',v(get('命中号'),4),v(get('命中号'),2)),[
                        改(note(get('命中号')),3,add(get('头部判定'),2)),改(g('持续长条'),get('轨道'),get('命中号')),改(g('显示长条'),get('轨道'),get('命中号')),
                        put('判定',get('头部判定')),put('提示截止',add(g('用时'),550)),循环(全(compare('LTE',g('下一键'),g('物量')),非(等(v(g('下一键'),3),0))),[change('下一键')])
                    ],[call('记录判定',get('命中号'),get('头部判定'))])])
                    if nxt is not None:new.append(nxt)
                    parent.append(new)
        draw=procs['绘图'];sdraw=draw.find('statement')
        target=next(b for b in draw.iter('block') if b.get('type')=='local_declaration_statement' and b.findtext("field[@name='VAR0']")=='键号')
        stack=target.find('statement/block/statement');stack.clear();stack.set('name','DO');stack.append(chain([iff(等(v(get('键号'),3),0),[call('绘制音符',get('键号'))]),局设('键号',add(get('键号'),1))]))
        nxt=target.find('next');saved=nxt.find('block');nxt.remove(saved);nxt.append(loop('轨号',1,4,[local('键号',item(g('显示长条'),get('轨号')),[iff(compare('GT',get('键号'),0),[iff(全(compare('GTE',v(get('键号'),4),g('用时')),either(等(v(get('键号'),3),1),compare('GTE',v(get('键号'),3),4))),[call('绘制音符',get('键号'))],[改(g('显示长条'),get('轨号'),0)])])])]))
        ET.SubElement(nxt[0],'next').append(saved)
        cv=lambda:item(g('轨道画布'),v(get('键号'),1))
        y=lambda t:sub(g('判定线'),div(mul(sub(t,g('用时')),g('判定线')),g('过屏时间')))
        clip=lambda t:maximum(0,minimum(g('画高'),t))
        过程('绘制音符',[local('头纵',选(compare('GTE',v(get('键号'),3),4),g('判定线'),y(v(get('键号'),2))),[
            cp(cv(),'PaintColor',选(等(v(get('键号'),3),1),-10066330,选(compare('GTE',v(get('键号'),3),4),-1379585,-11084049))),
            iff(compare('GT',v(get('键号'),4),v(get('键号'),2)),[local('尾纵',y(v(get('键号'),4)),[
                cp(cv(),'LineWidth',maximum(6,sub(g('轨宽'),32))),cm(cv(),'DrawLine',div(g('轨宽'),2),clip(get('头纵')),div(g('轨宽'),2),clip(get('尾纵'))),
                cp(cv(),'LineWidth',8),iff(全(compare('GTE',get('尾纵'),0),compare('LTE',get('尾纵'),g('画高'))),[cm(cv(),'DrawLine',9,get('尾纵'),sub(g('轨宽'),9),get('尾纵'))])
            ])]),cp(cv(),'LineWidth',16),iff(全(compare('GTE',get('头纵'),0),compare('LTE',get('头纵'),g('画高'))),[cm(cv(),'DrawLine',9,get('头纵'),sub(g('轨宽'),9),get('头纵'))])
        ])])
    r.extend(TOP)
    stamp=r.find('yacodeblocks');r.remove(stamp);r.append(stamp)
    for i,b in enumerate(r.iter('block')):b.set('id',screen+'_hold_'+str(i))
    r.set('xmlns','http://www.w3.org/1999/xhtml');ET.indent(r,space='  ')
    files[bk]=ET.tostring(r,encoding='utf-8');files[path]=('#|\n$JSON\n'+json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode()
prop='youngandroidproject/project.properties'
lines=files[prop].decode().splitlines()
values={'aname':'Arivento','versioncode':'24','versionname':'1017.1'}
files[prop]=('\n'.join(k+'='+values[k] if (k:=line.split('=',1)[0]) in values else line for line in lines)+'\n').encode()
for n,data in files.items():
    p=OUT/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
with zipfile.ZipFile(ROOT/'archive/hold_base_1016/Hold_candidate.aia','w',zipfile.ZIP_DEFLATED) as z:
    for n,data in files.items():z.writestr(n,data)
print(OUT)

