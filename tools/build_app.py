from pathlib import Path
import json,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'native'/json.loads((ROOT/'tools/current_release.json').read_text(encoding='utf-8'))['name']
SRC=next(SOURCE.rglob('Screen1.scm')).parent
TYPES={}

def el(kind,fields=(),values=(),statements=(),mutation=None):
    b=ET.Element('block',type=kind)
    if mutation is not None:b.append(mutation)
    for k,v in fields:ET.SubElement(b,'field',name=k).text=str(v)
    for k,v in values:ET.SubElement(b,'value',name=k).append(x(v))
    for k,v in statements:
        if v:ET.SubElement(b,'statement',name=k).append(chain(v))
    return b
def mut(*children,**attrs):
    m=ET.Element('mutation',{k:str(v) for k,v in attrs.items()})
    for tag,a in children:ET.SubElement(m,tag,a)
    return m
def x(v):
    if isinstance(v,ET.Element):return v
    if isinstance(v,bool):return el('logic_boolean',[('BOOL','TRUE' if v else 'FALSE')])
    if isinstance(v,(int,float)):return el('math_number',[('NUM',v)])
    return el('text',[('TEXT',v)])
def chain(items):
    items=[i for i in items if i is not None]
    for a,b in zip(items,items[1:]):ET.SubElement(a,'next').append(b)
    return items[0]
def many(kind,prefix,args,**f):return el(kind,list(f.items()),[(prefix+str(i),a) for i,a in enumerate(args)],mutation=mut(items=len(args)))

def G(n):return el('lexical_variable_get',[('VAR','global '+n)])
def L(n):return el('lexical_variable_get',[('VAR',n)])
def setg(n,v):return el('lexical_variable_set',[('VAR','global '+n)],[('VALUE',v)])
def setl(n,v):return el('lexical_variable_set',[('VAR',n)],[('VALUE',v)])
def cmp(op,a,b):return el('math_compare',[('OP',op)],[('A',a),('B',b)])
def eq(a,b):return cmp('EQ',a,b)
def logic(op,args):
    b=el('logic_operation',[('OP',op)],[('A',args[0]),('B',args[1])],mutation=mut(items=2))
    return b if len(args)==2 else logic(op,[b,*args[2:]])
def AND(*a):return logic('AND',a)
def OR(*a):return logic('OR',a)
def NOT(a):return el('logic_negate',values=[('BOOL',a)])
def add(*a):return many('math_add','NUM',a)
def mul(*a):return many('math_multiply','NUM',a)
def sub(a,b):return el('math_subtract',values=[('A',a),('B',b)])
def div(a,b):return el('math_division',values=[('A',a),('B',b)])
def mx(*a):return many('math_on_list','NUM',a,OP='MAX')
def mn(*a):return many('math_on_list','NUM',a,OP='MIN')
def single(op,a):return el('math_single',[('OP',op)],[('NUM',a)])
def isnum(a):return el('math_is_a_number',[('OP','NUMBER')],[('NUM',a)])
def item(l,i):return el('lists_select_item',values=[('LIST',l),('NUM',i)])
def length(l):return el('lists_length',values=[('LIST',l)])
def mklist(*a):return many('lists_create_with','ADD',a)
def append(l,*a):return el('lists_add_items',values=[('LIST',l)]+[('ITEM'+str(i),v) for i,v in enumerate(a)],mutation=mut(items=len(a)))
def replace(l,i,v):return el('lists_replace_item',values=[('LIST',l),('NUM',i),('ITEM',v)])
def islist(a):return el('lists_is_list',values=[('ITEM',a)])
def isstr(a):return el('text_is_string',values=[('ITEM',a)])
def inlist(v,l):return el('lists_is_in',values=[('LIST',l),('ITEM',v)])
def copy(l):return el('lists_copy',values=[('LIST',l)])
def join(*a):return many('text_join','ADD',a)
def trim(a):return el('text_trim',values=[('TEXT',a)])
def choose(c,a,b):return el('controls_choose',values=[('TEST',c),('THENRETURN',a),('ELSERETURN',b)])
def decimal(a,p):return el('math_format_as_decimal',values=[('NUM',a),('PLACES',p)])
def IF(*branches,else_=None):
    pairs=[branches[i:i+2] for i in range(0,len(branches),2)]
    attrs={}
    if len(pairs)>1:attrs['elseif']=len(pairs)-1
    if else_:attrs['else']=1
    values=[('IF'+str(i),c) for i,(c,_) in enumerate(pairs)]
    statements=[('DO'+str(i),s) for i,(_,s) in enumerate(pairs)]+([('ELSE',else_)] if else_ else [])
    return el('controls_if',values=values,statements=statements,mutation=mut(**attrs) if attrs else None)
def WHILE(c,body):return el('controls_while',values=[('TEST',c)],statements=[('DO',body)])
def EACH(n,l,body):return el('controls_forEach',[('VAR',n)],[('LIST',l)],[('DO',body)])
def RANGE(n,a,b,body):return el('controls_forRange',[('VAR',n)],[('START',a),('END',b),('STEP',1)],[('DO',body)])
def LET(pairs,body):
    return el('local_declaration_statement',[('VAR'+str(i),n) for i,(n,_) in enumerate(pairs)],[('DECL'+str(i),v) for i,(_,v) in enumerate(pairs)],[('STACK',body)],mut(*[('localname',{'name':n}) for n,_ in pairs]))
def LETX(pairs,ret):
    return el('local_declaration_expression',[('VAR'+str(i),n) for i,(n,_) in enumerate(pairs)],[('DECL'+str(i),v) for i,(_,v) in enumerate(pairs)]+[('RETURN',ret)],mutation=mut(*[('localname',{'name':n}) for n,_ in pairs]))
def DO(body,value):return el('controls_do_then_return',values=[('VALUE',value)],statements=[('STM',body)])
def comp(n):return el('component_component_block',[('COMPONENT_SELECTOR',n)],mutation=mut(component_type=TYPES[n],instance_name=n))
def get(n,p):return el('component_set_get',[('COMPONENT_SELECTOR',n),('PROP',p)],mutation=mut(component_type=TYPES[n],set_or_get='get',property_name=p,is_generic='false',instance_name=n))
def put(n,p,v):return el('component_set_get',[('COMPONENT_SELECTOR',n),('PROP',p)],[('VALUE',v)],mutation=mut(component_type=TYPES[n],set_or_get='set',property_name=p,is_generic='false',instance_name=n))
def meth(n,m,*a):return el('component_method',[('COMPONENT_SELECTOR',n)],[('ARG'+str(i),v) for i,v in enumerate(a)],mutation=mut(component_type=TYPES[n],method_name=m,is_generic='false',instance_name=n))
def gput(c,kind,p,v):return el('component_set_get',[('PROP',p)],[('COMPONENT',c),('VALUE',v)],mutation=mut(component_type=kind,property_name=p,set_or_get='set',is_generic='true'))
def gmeth(c,kind,m,*a):return el('component_method',values=[('COMPONENT',c)]+[('ARG'+str(i),v) for i,v in enumerate(a)],mutation=mut(component_type=kind,method_name=m,is_generic='true'))
PROCS={}
def call(n,*a):return el('procedures_callnoreturn',[('PROCNAME',n)],[('ARG'+str(i),v) for i,v in enumerate(a)],mutation=mut(*[('arg',{'name':p}) for p in PROCS[n]],name=n))
def callr(n,*a):
    b=call(n,*a);b.set('type','procedures_callreturn');return b
def glob(n,v):return el('global_declaration',[('NAME',n)],[('VALUE',v)])
def proc(n,args,body=None):
    if body is None:args,body=[],args
    return el('procedures_defnoreturn',[('NAME',n)]+[('VAR'+str(i),a) for i,a in enumerate(args)],statements=[('STACK',body)],mutation=mut(*[('arg',{'name':a}) for a in args]))
def procr(n,args,value):return el('procedures_defreturn',[('NAME',n)]+[('VAR'+str(i),a) for i,a in enumerate(args)],[('RETURN',value)],mutation=mut(*[('arg',{'name':a}) for a in args]))
def on(n,e,body,params=()):
    return el('component_event',[('COMPONENT_SELECTOR',n)],statements=[('DO',body)],mutation=mut(component_type=TYPES[n],is_generic='false',instance_name=n,event_name=e,**{'param_name'+str(i):p for i,p in enumerate(params)}))
def alert(t):return meth('提示','ShowAlert',t)

def load(screen):
    path=SRC/(screen+'.scm');design=json.loads(path.read_text(encoding='utf-8').split('$JSON')[1].rsplit('|#',1)[0])
    return path,design
def components(design):
    out={}
    def visit(c):
        out[c['$Name']]=c
        for k in c.get('$Components',[]):visit(k)
    visit(design['Properties']);return out
def remove(design,names):
    def visit(c):
        c['$Components']=[k for k in c.get('$Components',[]) if k['$Name'] not in names]
        for k in c['$Components']:visit(k)
        if not c['$Components']:del c['$Components']
    visit(design['Properties'])
def insert(design,anchor,comps):
    every=components(design)
    if comps[0]['$Name'] in every:return
    ids=[int(c['Uuid']) for c in every.values() if str(c.get('Uuid','')).lstrip('-').isdigit()]
    def number(c,n):
        c['Uuid']=str(n)
        for k in c.get('$Components',[]):n=number(k,n+1)
        return n
    n=max(ids,default=0)
    for c in comps:n=number(c,n+1)
    def visit(c):
        kids=c.get('$Components',[])
        for i,k in enumerate(kids):
            if k['$Name']==anchor:kids[i+1:i+1]=comps;return True
            if visit(k):return True
    visit(design['Properties'])
def ui(name,kind,version,**props):
    kids=props.pop('kids',None);c={'$Name':name,'$Type':kind,'$Version':str(version),**{k:str(v) for k,v in props.items()}}
    if kids:c['$Components']=kids
    return c
def write(screen,path,design,tops,procs):
    root=ET.Element('xml',xmlns='http://www.w3.org/1999/xhtml')
    for i,b in enumerate(tops):
        b.set('x',str(40+(i//14)*480));b.set('y',str(40+(i%14)*60))
        if b.get('type')!='global_declaration':b.set('collapsed','true')
        root.append(b)
    ET.SubElement(root,'yacodeblocks',{'ya-version':'224','language-version':'34'})
    for i,b in enumerate(root.iter('block')):b.set('id',f'{screen}_{i}')
    ET.indent(root,space='  ')
    (SRC/(screen+'.bky')).write_bytes(ET.tostring(root,encoding='utf-8'))
    path.write_bytes(('#|\n$JSON\n'+json.dumps(design,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode())

def declare(names):
    for n,a in names.items():PROCS[n]=a

def screen1():
    path,design=load('Screen1')
    remove(design,{'打击音量标题','打击音量滑条','底部入口','校准音乐'})
    look=dict(BackgroundColor='&HFF151E32',TextColor='&HFFEAF2FF',FontSize=16,Height=40,MultiLine='False',NumbersOnly='True',Width=-1050)
    insert(design,'开始',[ui('练习设置','CheckBox',3,Text='练习模式',TextColor='&HFFEAF2FF',Width=-2,FontSize=15),
        ui('练习区','VerticalArrangement',4,Width=-2,Visible='False',kids=[
            ui('练习标题','Label',5,Text='练习时间段（秒，结束留空则到谱面结尾）',Width=-2,TextColor='&HFFEAF2FF',FontSize=14),
            ui('练习范围','HorizontalArrangement',4,Width=-2,kids=[ui('练习开始','TextBox',6,Text='0',Hint='开始',**look),ui('练习结束','TextBox',6,Text='',Hint='结束',**look)]),
            ui('自动播放','CheckBox',3,Text='AutoPlay',TextColor='&HFFEAF2FF',Width=-2,FontSize=15)])])
    c=components(design);TYPES.clear();TYPES.update({k:v['$Type'] for k,v in c.items()})
    c['校准打击']['Source']='arivento_hit.wav';c['打击音设置']['Text']='打击音效'
    PROCS.clear();declare({'合法延迟':['值'],'练习范围':[],'刷新入口':[],'提示问题':['文本'],'保存延迟':[],'读取本地谱':['地址'],'检查谱面':['数据'],'连接音乐':['地址'],
        '继续音乐检查':[],'完成音乐检查':['成功'],'保存当前谱':[],'刷新保存列表':[],'启动校准':[],'调整校准':[],'校准微调':['变化'],'更新校准':[],'校准发声':['声音','序号','偏移','用时'],'关闭校准':[]})
    bad=join('第 ',L('序号'),' 个音符格式、时间或同轨占用不正确')
    tops=[*[glob(n,v) for n,v in [('当前谱',mklist()),('读取中',False),('音乐就绪',False),('保存列表',mklist()),('谱面地址',''),('待用音乐',''),('检查音乐地址',''),
        ('正在检查',False),('检查失败',False),('音乐权限拒绝',False),('校验问题',''),('校准起点',0),('校准上次',0),('校准节拍号',0),('校准打击号',0),('试听延迟',0)]],
    on('Screen1','Initialize',[
        setg('保存列表',meth('本地记录','GetValue','保存的谱面',mklist())),call('刷新保存列表'),
        LET([('原延迟',meth('本地记录','GetValue','谱面延迟',0))],[put('延迟输入','Text',choose(callr('合法延迟',L('原延迟')),L('原延迟'),0))]),
        put('打击音设置','Checked',meth('本地记录','GetValue','打击音效',True))]),
    procr('合法延迟',['值'],AND(isnum(L('值')),cmp('GTE',L('值'),-400),cmp('LTE',L('值'),400))),
    on('开始','Click',[LET([('范围',callr('练习范围'))],[IF(AND(callr('合法延迟',get('延迟输入','Text')),isnum(get('游玩过屏输入','Text')),cmp('GT',get('游玩过屏输入','Text'),0),islist(L('范围'))),[
        call('保存延迟'),LET([('值',copy(G('当前谱')))],[append(L('值'),get('延迟输入','Text'),get('游玩过屏输入','Text'),get('打击音设置','Checked'),item(L('范围'),1),item(L('范围'),2),item(L('范围'),3)),
        el('controls_openAnotherScreenWithStartValue',values=[('SCREENNAME','Play'),('STARTVALUE',L('值'))])])],
        else_=[alert('延迟须在 -400～400ms，过屏时间须大于 0ms，练习结束时间须晚于开始时间')])])]),
    procr('练习范围',[],LETX([('始',choose(eq(trim(get('练习开始','Text')),''),0,get('练习开始','Text'))),('终',choose(eq(trim(get('练习结束','Text')),''),div(item(G('当前谱'),7),1000),get('练习结束','Text')))],
        choose(get('练习设置','Checked'),choose(AND(isnum(L('始')),isnum(L('终')),cmp('GTE',L('始'),0),cmp('GT',L('终'),L('始'))),mklist(mul(1000,L('始')),mul(1000,L('终')),get('自动播放','Checked')),''),
            mklist(0,item(G('当前谱'),7),False)))),
    on('练习设置','Changed',[put('练习区','Visible',get('练习设置','Checked'))]),
    proc('保存延迟',[IF(callr('合法延迟',get('延迟输入','Text')),[meth('本地记录','StoreValue','谱面延迟',get('延迟输入','Text'))])]),
    on('延迟输入','LostFocus',[call('保存延迟')]),
    on('打击音设置','Changed',[meth('本地记录','StoreValue','打击音效',get('打击音设置','Checked'))]),
    proc('刷新入口',[LET([('忙',OR(G('读取中'),G('正在检查')))],[put('选谱','Enabled',NOT(L('忙'))),put('保存谱面','Enabled',NOT(L('忙'))),
        put('选音乐','Enabled',AND(eq(length(G('当前谱')),8),NOT(L('忙')))),put('开始','Enabled',AND(G('音乐就绪'),NOT(L('忙'))))])]),
    proc('提示问题',['文本'],[put('读取状态','Text',L('文本')),alert(L('文本')),call('刷新入口')]),
    on('选谱','AfterPicking',[setg('待用音乐',''),call('读取本地谱',get('选谱','Selection'))]),
    on('保存谱面','AfterPicking',[LET([('记录',item(G('保存列表'),get('保存谱面','SelectionIndex')))],[setg('待用音乐',item(L('记录'),3)),call('读取本地谱',item(L('记录'),2))])]),
    proc('读取本地谱',['地址'],[setg('谱面地址',L('地址')),setg('读取中',True),setg('音乐就绪',False),setg('当前谱',mklist()),
        put('当前谱名','Text','正在读取谱面'),put('读取状态','Text','正在读取谱面源文件'),call('刷新入口'),meth('谱面文件','ReadFrom',L('地址'))]),
    on('谱面文件','GotText',[setg('读取中',False),
        LET([('数据',meth('文本转换','JsonTextDecode',trim(el('text_replace_all',values=[('TEXT',L('内容')),('SEGMENT','﻿'),('REPLACEMENT','')]))))],[
            IF(eq(callr('检查谱面',L('数据')),''),[setg('当前谱',L('数据')),put('当前谱名','Text',item(L('数据'),1)),put('读取状态','Text','已读取谱面：请选择对应的本地音乐'),
                IF(NOT(eq(G('待用音乐'),'')),[call('连接音乐',G('待用音乐'))])],
            else_=[put('当前谱名','Text','尚未选择谱面'),call('提示问题',G('校验问题'))])]),
        setg('待用音乐',''),call('刷新入口')],['内容']),
    procr('检查谱面',['数据'],DO([setg('校验问题','谱面必须为合法八项列表'),
        IF(AND(islist(L('数据')),eq(length(L('数据')),8),isstr(item(L('数据'),1)),isnum(item(L('数据'),7)),islist(item(L('数据'),8)),cmp('GT',length(item(L('数据'),8)),0)),[
            setg('校验问题',''),
            LET([('上尾',mklist(-1,-1,-1,-1)),('前时',-1)],[RANGE('序号',1,length(item(L('数据'),8)),[
                IF(eq(G('校验问题'),''),[LET([('音符',item(item(L('数据'),8),L('序号')))],[
                    IF(AND(islist(L('音符')),inlist(length(L('音符')),mklist(2,3)),inlist(item(L('音符'),1),mklist(1,2,3,4)),isnum(item(L('音符'),2)),isnum(item(L('音符'),length(L('音符')))),
                        cmp('GTE',item(L('音符'),2),L('前时')),cmp('GT',item(L('音符'),2),item(L('上尾'),item(L('音符'),1))),OR(eq(length(L('音符')),2),cmp('GT',item(L('音符'),3),item(L('音符'),2)))),
                        [replace(L('上尾'),item(L('音符'),1),item(L('音符'),length(L('音符')))),setl('前时',item(L('音符'),2))],else_=[setg('校验问题',bad)])])])])])])],
        G('校验问题'))),
    on('选音乐','AfterPicking',[call('连接音乐',get('选音乐','Selection'))]),
    proc('连接音乐',['地址'],[setg('检查音乐地址',L('地址')),setg('音乐权限拒绝',False),setg('音乐就绪',False),setg('检查失败',False),setg('正在检查',True),
        call('刷新入口'),put('读取状态','Text','正在检查音乐；如有权限弹窗，请允许读取音频'),put('音乐检查时钟','TimerEnabled',True),put('音乐检查','Source',L('地址')),call('继续音乐检查')]),
    proc('继续音乐检查',[IF(G('正在检查'),[IF(G('检查失败'),[call('完成音乐检查',False)],eq(get('音乐检查','Source'),G('检查音乐地址')),[
        meth('音乐检查','Start'),call('完成音乐检查',AND(NOT(G('检查失败')),get('音乐检查','IsPlaying')))])])]),
    on('音乐检查时钟','Timer',[call('继续音乐检查')]),
    proc('完成音乐检查',['成功'],[put('音乐检查时钟','TimerEnabled',False),setg('正在检查',False),meth('音乐检查','Stop'),put('音乐检查','Source',''),
        IF(L('成功'),[replace(G('当前谱'),2,G('检查音乐地址')),setg('音乐就绪',True),call('保存当前谱'),put('读取状态','Text','已保存谱面与音乐，可以开始游玩'),call('刷新入口')],
        else_=[call('提示问题',choose(G('音乐权限拒绝'),'未获得音乐访问权限，请重新选择音乐并允许读取音频','音乐源文件找不到、无访问权限或无法播放，请重新选择本地音乐'))])]),
    proc('保存当前谱',[LET([('位置',0),('记录',mklist(item(G('当前谱'),1),G('谱面地址'),item(G('当前谱'),2)))],[
        RANGE('序号',1,length(G('保存列表')),[IF(eq(item(item(G('保存列表'),L('序号')),2),G('谱面地址')),[setl('位置',L('序号'))])]),
        IF(eq(L('位置'),0),[append(G('保存列表'),L('记录'))],else_=[replace(G('保存列表'),L('位置'),L('记录'))])]),
        meth('本地记录','StoreValue','保存的谱面',G('保存列表')),call('刷新保存列表')]),
    proc('刷新保存列表',[LET([('名称表',mklist())],[EACH('记录',G('保存列表'),[append(L('名称表'),item(L('记录'),1))]),put('保存谱面','Elements',L('名称表'))]),
        put('保存谱面','Text',join('保存的谱面（',length(G('保存列表')),'）'))]),
    on('Screen1','ErrorOccurred',[IF(eq(L('组件'),comp('音乐检查')),[setg('检查失败',True)],
        OR(eq(L('组件'),comp('校准节拍')),eq(L('组件'),comp('校准打击'))),[put('校准时钟','TimerEnabled',False),put('校准提示','Text','校准声音无法播放，请返回后重试。')],
        eq(L('组件'),comp('谱面文件')),[setg('读取中',False),setg('待用音乐',''),put('当前谱名','Text','源谱面不可用'),call('提示问题','谱面源文件找不到或无访问权限，请重新导入本地谱面')],
        else_=[put('读取状态','Text',L('消息'))])],['组件','函数','编号','消息']),
    on('Screen1','PermissionDenied',[IF(eq(L('组件'),comp('音乐检查')),[setg('检查失败',True),setg('音乐权限拒绝',True)],
        else_=[setg('读取中',False),setg('待用音乐',''),call('提示问题','无法访问源文件，请重新选择谱面或音乐以授予访问权限')])],['组件','函数','权限']),
    on('Screen1','BackPressed',[IF(get('校准页','Visible'),[call('关闭校准')],else_=[el('controls_closeApplication')])]),
    on('校准入口','Click',[put('校准数值','Text',choose(callr('合法延迟',get('延迟输入','Text')),get('延迟输入','Text'),0)),call('调整校准'),
        put('首页','Visible',False),put('校准页','Visible',True),call('启动校准')]),
    proc('启动校准',[setg('校准节拍号',0),setg('校准打击号',0),setg('校准上次',0),setg('校准起点',meth('校准时钟','SystemTime')),put('校准时钟','TimerEnabled',True)]),
    proc('调整校准',[IF(callr('合法延迟',get('校准数值','Text')),[setg('试听延迟',get('校准数值','Text')),put('校准提示','Text','调节数值，让节拍器与打击音重合。')],
        else_=[put('校准提示','Text','请输入 -400～400 的数值')])]),
    proc('校准微调',['变化'],[IF(isnum(get('校准数值','Text')),[put('校准数值','Text',mx(-400,mn(400,add(get('校准数值','Text'),L('变化')))))]),call('调整校准')]),
    on('校准减少','Click',[call('校准微调',-10)]),on('校准增加','Click',[call('校准微调',10)]),on('校准数值','LostFocus',[call('调整校准')]),
    on('校准时钟','Timer',[call('更新校准')]),
    proc('更新校准',[LET([('用时',sub(meth('校准时钟','SystemTime'),G('校准起点')))],[IF(cmp('LT',L('用时'),G('校准上次')),[call('启动校准')],else_=[
        setg('校准上次',L('用时')),
        setg('校准节拍号',callr('校准发声',comp('校准节拍'),G('校准节拍号'),0,L('用时'))),
        setg('校准打击号',callr('校准发声',comp('校准打击'),G('校准打击号'),G('试听延迟'),L('用时'))),
        meth('校准画布','Clear'),put('校准画布','PaintColor',-1),put('校准画布','LineWidth',2),meth('校准画布','DrawLine',15,140,sub(get('校准画布','Width'),15),140),
        put('校准画布','PaintColor',-11084049),put('校准画布','LineWidth',12),
        LET([('纵',sub(140,mul(sub(add(500,mul(G('校准打击号'),1000),G('试听延迟')),L('用时')),0.14)))],[
            meth('校准画布','DrawLine',sub(div(get('校准画布','Width'),2),35),L('纵'),add(div(get('校准画布','Width'),2),35),L('纵'))])])])]),
    procr('校准发声',['声音','序号','偏移','用时'],LETX([('迟到',sub(L('用时'),add(500,mul(L('序号'),1000),L('偏移'))))],DO(
        [IF(AND(cmp('GTE',L('迟到'),0),cmp('LTE',L('迟到'),120)),[gmeth(L('声音'),'Sound','Play')])],
        choose(cmp('GTE',L('迟到'),0),add(single('FLOOR',div(sub(sub(L('用时'),L('偏移')),500),1000)),1),L('序号'))))),
    proc('关闭校准',[put('校准时钟','TimerEnabled',False),put('校准页','Visible',False),put('首页','Visible',True)]),
    on('校准应用','Click',[IF(callr('合法延迟',get('校准数值','Text')),[put('延迟输入','Text',get('校准数值','Text')),call('保存延迟'),call('关闭校准')],
        else_=[put('校准提示','Text','请输入 -400～400 的数值')])]),
    on('校准返回','Click',[call('关闭校准')])]
    write('Screen1',path,design,tops,PROCS)

def play():
    path,design=load('Play')
    remove(design,{'打击音二','打击音三','打击音四','本地设置'})
    insert(design,'返回',[ui('练习音乐','VideoPlayer',6,Width=1,Height=1,Volume=100)])
    c=components(design)
    hit=c.get('打击音一') or c['打击音'];hit['$Name']='打击音';hit['Source']='arivento_hit.wav'
    TYPES.clear();TYPES.update({k:v['$Type'] for k,v in components(design).items()})
    PROCS.clear();declare({'开局':[],'清空按压':[],'准备游玩键':[],'取游玩键':['键号'],'纵坐标':['时刻'],'走时':[],'推进下一键':[],'绘图':[],'绘制音符':['键号'],'记录判定':['键号','结果'],
        '长条到期':[],'击中':['键号','等级'],'轨道按下':['轨道'],'轨道松开':['轨道'],'拖动':['轨道','横','纵'],'启动音乐':[],'停止游玩':[],'统计':[],'完成游玩':[],'返回首页':[]})
    K=lambda n,i:item(callr('取游玩键',n),i)
    key=lambda i:item(L('键'),i)
    lanes=['轨道一','轨道二','轨道三','轨道四']
    zeros=lambda:mklist(0,0,0,0)
    tops=[*[glob(n,v) for n,v in [('当前谱',mklist()),('状态',0),('起点',0),('用时',-3000),('下一键',1),('完美',0),('良好',0),('漏击',0),('连击',0),('最大连击',0),('准确率',100),
        ('判定',1),('提示截止',-3000),('轨宽',0),('画高',0),('判定线',0),('物量',0),('过屏时间',500),('音乐名',''),('结束时间',0),('谱面延迟',0),('打击音开启',True),
        ('已播放',False),('播放请求',False),('播放起始',0),('游玩分段',mklist()),('缓存段号',0),('缓存分段',mklist()),('轨道画布',mklist()),
        ('按住轨道',zeros()),('持续长条',zeros()),('显示长条',zeros()),('上一头时',0),('上一游玩键',mklist()),('起始',0),('跳转',False),('自动',False)]],
    on('Play','Initialize',[setg('轨道画布',mklist(*[comp(n) for n in lanes])),setg('当前谱',el('controls_getStartValue')),call('开局')]),
    on('重开','Click',[call('开局')]),
    proc('开局',[call('清空按压'),setg('音乐名',item(G('当前谱'),2)),setg('谱面延迟',item(G('当前谱'),9)),
        setg('过屏时间',item(G('当前谱'),10)),setg('自动',item(G('当前谱'),14)),setg('打击音开启',OR(item(G('当前谱'),11),G('自动'))),
        setg('起始',single('ROUND',mx(0,add(item(G('当前谱'),12),mn(0,G('谱面延迟')))))),setg('跳转',cmp('GT',G('起始'),0)),
        setg('结束时间',add(mn(item(G('当前谱'),7),item(G('当前谱'),13)),mx(0,G('谱面延迟')))),call('准备游玩键'),
        put('轨道区','Visible',True),put('信息','Height',-1012),setg('播放请求',False),meth('音乐','Stop'),meth('练习音乐','Pause'),
        IF(G('跳转'),[put('练习音乐','Source',G('音乐名')),meth('练习音乐','SeekTo',G('起始'))],else_=[put('音乐','Source',G('音乐名'))]),
        *[setg(n,v) for n,v in [('用时',sub(G('起始'),3000)),('下一键',1),('完美',0),('良好',0),('漏击',0),('连击',0),('最大连击',0),('提示截止',sub(G('起始'),3000)),('已播放',False),('状态',1)]],
        setg('起点',add(meth('时钟','SystemTime'),sub(3000,G('起始')))),put('时钟','TimerEnabled',True),call('统计'),call('绘图')]),
    proc('清空按压',[setg('按住轨道',zeros()),setg('持续长条',zeros()),setg('显示长条',zeros())]),
    proc('准备游玩键',[setg('缓存段号',0),setg('游玩分段',mklist()),setg('上一头时',-10**12),setg('物量',0),
        LET([('分段',mklist())],[EACH('音符',item(G('当前谱'),8),[IF(AND(cmp('GTE',item(L('音符'),2),item(G('当前谱'),12)),cmp('LTE',item(L('音符'),2),item(G('当前谱'),13))),[
            setg('物量',add(G('物量'),1)),LET([('头',add(item(L('音符'),2),G('谱面延迟'))),('尾',add(item(L('音符'),length(L('音符'))),G('谱面延迟')))],[
                setg('结束时间',mx(G('结束时间'),add(L('尾'),500))),
                IF(eq(length(L('分段')),0),[append(G('游玩分段'),L('分段'))]),
                append(L('分段'),mklist(item(L('音符'),1),L('头'),0,L('尾'),eq(L('头'),G('上一头时')))),
                IF(eq(L('头'),G('上一头时')),[replace(G('上一游玩键'),5,True)]),
                setg('上一头时',L('头')),setg('上一游玩键',item(L('分段'),length(L('分段')))),
                IF(eq(length(L('分段')),64),[setl('分段',mklist())])])])])])]),
    procr('取游玩键',['键号'],LETX([('段号',add(single('FLOOR',div(sub(L('键号'),1),64)),1))],DO(
        [IF(NOT(eq(G('缓存段号'),L('段号'))),[setg('缓存段号',L('段号')),setg('缓存分段',item(G('游玩分段'),L('段号')))])],
        item(G('缓存分段'),sub(L('键号'),mul(sub(L('段号'),1),64)))))),
    procr('纵坐标',['时刻'],sub(G('判定线'),div(mul(sub(L('时刻'),G('用时')),G('判定线')),G('过屏时间')))),
    on('时钟','Timer',[call('走时'),IF(eq(G('状态'),1),[call('绘图')])]),
    proc('走时',[IF(eq(G('状态'),1),[
        IF(G('已播放'),[setg('用时',mx(G('用时'),sub(meth('时钟','SystemTime'),G('起点'))))],
            else_=[setg('用时',mn(G('起始'),sub(meth('时钟','SystemTime'),G('起点')))),IF(cmp('GTE',G('用时'),G('起始')),[call('启动音乐')])]),
        call('长条到期'),
        LET([('序号',G('下一键'))],[WHILE(AND(cmp('LTE',L('序号'),G('物量')),cmp('LTE',K(L('序号'),2),G('用时'))),[
            LET([('键',callr('取游玩键',L('序号')))],[IF(AND(eq(key(3),0),G('自动')),[call('击中',L('序号'),3)],AND(eq(key(3),0),OR(cmp('GT',G('用时'),add(key(2),160)),AND(cmp('GT',key(4),key(2)),cmp('GTE',G('用时'),key(4))))),[call('记录判定',L('序号'),1)])]),
            setl('序号',add(L('序号'),1))])]),
        IF(cmp('GTE',G('用时'),G('结束时间')),[call('完成游玩')])])]),
    proc('推进下一键',[WHILE(AND(cmp('LTE',G('下一键'),G('物量')),NOT(eq(K(G('下一键'),3),0))),[setg('下一键',add(G('下一键'),1))])]),
    proc('绘图',[setg('画高',get('轨道一','Height')),setg('轨宽',get('轨道一','Width')),IF(AND(cmp('GT',G('轨宽'),18),cmp('GT',G('画高'),32)),[
        setg('判定线',mul(G('画高'),0.85)),
        LET([('文字',choose(AND(G('播放请求'),NOT(G('已播放'))),'正在启动音乐',choose(cmp('LT',G('用时'),G('起始')),join('准备 ',single('CEILING',div(sub(G('用时'),G('起始')),-1000))),
            choose(cmp('LT',G('用时'),G('提示截止')),item(mklist('MISS','GOOD','PERFECT'),G('判定')),''))))],[
            RANGE('轨号',1,4,[LET([('画布',item(G('轨道画布'),L('轨号')))],[gmeth(L('画布'),'Canvas','Clear'),
                gput(L('画布'),'Canvas','PaintColor',-14077110),gput(L('画布'),'Canvas','LineWidth',1),gmeth(L('画布'),'Canvas','DrawLine',0,0,0,G('画高')),
                gput(L('画布'),'Canvas','PaintColor',-1379585),gput(L('画布'),'Canvas','LineWidth',3),gmeth(L('画布'),'Canvas','DrawLine',0,G('判定线'),G('轨宽'),G('判定线')),
                gmeth(L('画布'),'Canvas','DrawText',L('文字'),mul(sub(3,L('轨号')),G('轨宽')),mul(G('画高'),0.475))])])]),
        LET([('键号',G('下一键'))],[WHILE(AND(cmp('LTE',L('键号'),G('物量')),cmp('LTE',K(L('键号'),2),add(G('用时'),G('过屏时间')))),[
            IF(eq(K(L('键号'),3),0),[call('绘制音符',L('键号'))]),setl('键号',add(L('键号'),1))])]),
        RANGE('轨号',1,4,[LET([('键号',item(G('显示长条'),L('轨号')))],[IF(cmp('GT',L('键号'),0),[
            IF(AND(cmp('GTE',K(L('键号'),4),G('用时')),OR(eq(K(L('键号'),3),1),cmp('GTE',K(L('键号'),3),4))),[call('绘制音符',L('键号'))],
                else_=[replace(G('显示长条'),L('轨号'),0)])])])])])]),
    proc('绘制音符',['键号'],[LET([('键',callr('取游玩键',L('键号')))],[LET([('画布',item(G('轨道画布'),key(1))),
        ('头纵',choose(cmp('GTE',key(3),4),G('判定线'),callr('纵坐标',key(2)))),('颜色',choose(eq(key(3),1),-10066330,choose(cmp('GTE',key(3),4),-1379585,-11084049)))],[
        gput(L('画布'),'Canvas','PaintColor',L('颜色')),
        IF(cmp('GT',key(4),key(2)),[LET([('尾纵',callr('纵坐标',key(4)))],[gput(L('画布'),'Canvas','LineWidth',mx(6,sub(G('轨宽'),32))),
            gmeth(L('画布'),'Canvas','DrawLine',div(G('轨宽'),2),L('头纵'),div(G('轨宽'),2),L('尾纵')),gput(L('画布'),'Canvas','LineWidth',8),
            gmeth(L('画布'),'Canvas','DrawLine',9,L('尾纵'),sub(G('轨宽'),9),L('尾纵'))])]),
        IF(key(5),[gput(L('画布'),'Canvas','PaintColor',-10929),gput(L('画布'),'Canvas','LineWidth',24),gmeth(L('画布'),'Canvas','DrawLine',5,L('头纵'),sub(G('轨宽'),5),L('头纵')),
            gput(L('画布'),'Canvas','PaintColor',L('颜色'))]),
        gput(L('画布'),'Canvas','LineWidth',16),gmeth(L('画布'),'Canvas','DrawLine',9,L('头纵'),sub(G('轨宽'),9),L('头纵'))])])]),
    proc('记录判定',['键号','结果'],[LET([('键',callr('取游玩键',L('键号')))],[IF(OR(eq(key(3),0),cmp('GTE',key(3),4)),[
        IF(cmp('GT',key(4),key(2)),[replace(G('显示长条'),key(1),L('键号'))]),replace(L('键'),3,L('结果')),
        IF(eq(L('结果'),1),[setg('漏击',add(G('漏击'),1)),setg('连击',0)],else_=[setg('连击',add(G('连击'),1)),
            IF(eq(L('结果'),3),[setg('完美',add(G('完美'),1))],else_=[setg('良好',add(G('良好'),1))])]),
        setg('最大连击',mx(G('最大连击'),G('连击'))),setg('判定',L('结果')),setg('提示截止',add(G('用时'),550)),call('推进下一键'),call('统计')])])]),
    proc('长条到期',[RANGE('轨号',1,4,[LET([('键号',item(G('持续长条'),L('轨号')))],[IF(AND(cmp('GT',L('键号'),0),cmp('LTE',K(L('键号'),4),G('用时'))),[
        replace(G('持续长条'),L('轨号'),0),call('记录判定',L('键号'),sub(K(L('键号'),3),2))])])])]),
    proc('击中',['键号','等级'],[LET([('键',callr('取游玩键',L('键号')))],[IF(G('打击音开启'),[meth('打击音','Play')]),
        IF(cmp('GT',key(4),key(2)),[replace(L('键'),3,add(L('等级'),2)),replace(G('持续长条'),key(1),L('键号')),replace(G('显示长条'),key(1),L('键号')),
            setg('判定',L('等级')),setg('提示截止',add(G('用时'),550)),call('推进下一键')],else_=[call('记录判定',L('键号'),L('等级'))])])]),
    proc('轨道按下',['轨道'],[IF(AND(eq(G('状态'),1),NOT(G('自动')),eq(item(G('按住轨道'),L('轨道')),0)),[call('走时'),IF(eq(G('状态'),1),[replace(G('按住轨道'),L('轨道'),1),
        LET([('序号',G('下一键')),('命中号',0)],[
            WHILE(AND(cmp('LTE',L('序号'),G('物量')),eq(L('命中号'),0),cmp('LTE',K(L('序号'),2),add(G('用时'),160))),[
                IF(AND(eq(K(L('序号'),3),0),eq(K(L('序号'),1),L('轨道'))),[setl('命中号',L('序号'))]),setl('序号',add(L('序号'),1))]),
            IF(cmp('GT',L('命中号'),0),[call('击中',L('命中号'),choose(cmp('LTE',single('ABS',sub(G('用时'),K(L('命中号'),2))),80),3,2))])])])])]),
    proc('轨道松开',['轨道'],[call('走时'),replace(G('按住轨道'),L('轨道'),0),LET([('键号',item(G('持续长条'),L('轨道')))],[
        IF(AND(cmp('GT',L('键号'),0),NOT(G('自动'))),[replace(G('持续长条'),L('轨道'),0),call('记录判定',L('键号'),1)])])]),
    proc('拖动',['轨道','横','纵'],[IF(OR(cmp('LTE',L('横'),0),cmp('GTE',L('横'),G('轨宽')),cmp('LTE',L('纵'),0),cmp('GTE',L('纵'),G('画高'))),[call('轨道松开',L('轨道'))])]),
    *[e for i,n in enumerate(lanes,1) for e in (on(n,'TouchDown',[call('轨道按下',i)],['横坐标','纵坐标']),on(n,'TouchUp',[call('轨道松开',i)],['横坐标','纵坐标']),
        on(n,'Dragged',[call('拖动',i,L('横坐标'),L('纵坐标'))],['起横','起纵','前横','前纵','横坐标','纵坐标','精灵']))],
    proc('启动音乐',[IF(NOT(G('播放请求')),[setg('播放请求',True),setg('播放起始',meth('时钟','SystemTime')),IF(G('跳转'),[meth('练习音乐','Start')],else_=[meth('音乐','Start')])]),
        IF(OR(G('跳转'),get('音乐','IsPlaying')),[setg('已播放',True),setg('起点',sub(meth('时钟','SystemTime'),G('起始'))),setg('用时',G('起始'))],
            cmp('GTE',sub(meth('时钟','SystemTime'),G('播放起始')),1500),[call('停止游玩'),put('信息','Text',join('音乐未能播放：',G('音乐名'))),
                alert(join('无法播放 ',G('音乐名'),'。请重新选择可播放的本地音频，确认文件未移动或删除。'))])]),
    proc('停止游玩',[call('清空按压'),setg('状态',3),put('时钟','TimerEnabled',False),meth('音乐','Stop'),meth('练习音乐','Pause')]),
    proc('统计',[LET([('总',add(G('完美'),G('良好'),G('漏击')))],[setg('准确率',choose(cmp('GT',L('总'),0),div(add(mul(100,G('完美')),mul(65,G('良好'))),L('总')),100))]),
        put('信息','Text',join('准确率 ',decimal(G('准确率'),2),'%\n连击 ',G('连击'),'   最高 ',G('最大连击')))]),
    proc('完成游玩',[IF(eq(G('状态'),1),[call('停止游玩'),call('统计'),put('轨道区','Visible',False),put('信息','Height',-1092),
        put('信息','Text',join(item(G('当前谱'),1),choose(G('自动'),'\nAutoPlay 完成','\n游玩完成'),'\n\n准确率 ',decimal(G('准确率'),2),'%\n\nPerfect ',G('完美'),'   Good ',G('良好'),'\nMiss ',G('漏击'),'\n最高连击 ',G('最大连击')))])]),
    proc('返回首页',[call('停止游玩'),el('controls_closeScreenWithValue',values=[('SCREEN','')])]),
    on('返回','Click',[call('返回首页')]),on('Play','BackPressed',[call('返回首页')]),
    on('Play','ErrorOccurred',[IF(eq(L('组件'),comp('打击音')),[setg('打击音开启',False)],else_=[call('停止游玩'),alert(join('播放或运行失败：',L('消息')))])],['组件','函数','编号','消息'])]
    write('Play',path,design,tops,PROCS)

def assets():
    folder=SOURCE/'assets'
    loud=folder/'arivento_hit_100.wav'
    if loud.exists():(folder/'arivento_hit.wav').write_bytes(loud.read_bytes())
    for p in folder.iterdir():
        if p.name not in ('arivento_hit.wav','arivento_metronome.wav'):p.unlink()
    for screen in ('EditorSettings','Recorder'):
        for suffix in ('.scm','.bky'):(SRC/(screen+suffix)).unlink(missing_ok=True)

if __name__=='__main__':
    assets();screen1();play()
    for screen in ('Screen1','Play'):print(screen,sum(e.tag.endswith('block') for e in ET.parse(SRC/(screen+'.bky')).getroot().iter()))
