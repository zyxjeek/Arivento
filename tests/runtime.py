from pathlib import Path
import copy,json,math,os,xml.etree.ElementTree as ET,zipfile

ROOT=Path(__file__).resolve().parents[1]
AIA=Path(os.environ.get('ARIVENTO_AIA') or ROOT/'dist'/(json.loads((ROOT/'tools/current_release.json').read_text(encoding='utf-8'))['name']+'.aia'))

class Comp:
    def __init__(self,name):self.name=name
    def __eq__(self,other):return isinstance(other,Comp) and other.name==self.name
    def __hash__(self):return hash(self.name)
    def __repr__(self):return '<'+self.name+'>'

class Stop(Exception):pass

def number(v):
    if isinstance(v,bool):raise TypeError(v)
    if isinstance(v,(int,float)):return v
    f=float(v);return int(f) if f.is_integer() else f
def isnumber(v):
    try:return not isinstance(v,(bool,list,Comp)) and math.isfinite(float(v))
    except (TypeError,ValueError):return False
def same(a,b):
    if isnumber(a) and isnumber(b):return float(a)==float(b)
    return a==b

class Runtime:
    def __init__(self,screen='Screen1',start='',storage=None,aia=None):
        with zipfile.ZipFile(aia or AIA) as z:
            name=lambda suffix:next(n for n in z.namelist() if n.endswith('/'+screen+suffix))
            design=json.loads(z.read(name('.scm')).decode().split('$JSON')[1].rsplit('|#',1)[0])
            self.root=ET.fromstring(z.read(name('.bky')))
        for e in self.root.iter():e.tag=e.tag.split('}')[-1]
        self.screen=screen;self.start=start;self.storage={} if storage is None else storage
        self.now=1_000_000;self.alerts=[];self.reads=[];self.opened=None;self.closed=False
        self.plays=[];self.draws={};self.texts={};self.needs_permission=False;self.pending=None
        self.missing=set();self.music_delay=0;self.music_fail=False;self.music_started=None
        self.components={};self.types={}
        def visit(c):
            self.components[c['$Name']]=dict(c);self.types[c['$Name']]=c['$Type']
            for k in c.get('$Components',[]):visit(k)
        visit(design['Properties'])
        for n,t in self.types.items():
            c=self.components[n]
            for k,v in list(c.items()):
                if v in('True','False'):c[k]=v=='True'
            if t=='Canvas':c.update(Width=90,Height=430,PaintColor=0,LineWidth=1)
            if t=='ListPicker':c.update(Elements=[],SelectionIndex=0)
            if t=='Player':c.setdefault('Source','');c['IsPlaying']=False
            if t=='TextBox':c.setdefault('Text','')
            if t=='Clock':c.setdefault('TimerEnabled',True)
            c.setdefault('Visible',True);c.setdefault('Enabled',True)
        self.globals={};self.procs={};self.events={}
        for b in self.root.findall('block'):
            t=b.get('type')
            if t=='global_declaration':self.globals[self.f(b,'NAME')]=self.value(b,'VALUE',{})
            elif t.startswith('procedures_def'):self.procs[self.f(b,'NAME')]=b
            elif t=='component_event':
                m=b.find('mutation');self.events[m.get('instance_name'),m.get('event_name')]=b

    def f(self,b,n):return b.find(f"field[@name='{n}']").text or ''
    def slot(self,b,tag,n):return b.find(f"{tag}[@name='{n}']/block")
    def value(self,b,n,env):return self.eval(self.slot(b,'value',n),env)
    def args(self,b,env,prefix='ARG'):
        out=[];i=0
        while self.slot(b,'value',prefix+str(i)) is not None:out.append(self.value(b,prefix+str(i),env));i+=1
        return out
    def initialize(self):self.event(self.screen,'Initialize');return self

    def event(self,name,ev,*params):
        b=self.events.get((name,ev))
        if b is None:return
        m=b.find('mutation');env={m.get('param_name'+str(i)):p for i,p in enumerate(params)}
        try:self.run(self.slot(b,'statement','DO'),env)
        except Stop:pass
    def error(self,comp,fn,msg):self.event(self.screen,'ErrorOccurred',Comp(comp),fn,0,msg)

    def call(self,name,args):
        p=self.procs[name];m=p.find('mutation');env={a.get('name'):v for a,v in zip(m.findall('arg'),args)}
        if p.get('type')=='procedures_defreturn':return self.value(p,'RETURN',env)
        self.run(self.slot(p,'statement','STACK'),env)

    def run(self,b,env):
        while b is not None:
            self.statement(b,env);b=b.find('next/block')
    def statement(self,b,env):
        t=b.get('type');v=lambda n:self.value(b,n,env)
        if t=='controls_if':
            i=0
            while self.slot(b,'value','IF'+str(i)) is not None:
                if v('IF'+str(i)):self.run(self.slot(b,'statement','DO'+str(i)),env);return
                i+=1
            self.run(self.slot(b,'statement','ELSE'),env)
        elif t=='lexical_variable_set':
            n=self.f(b,'VAR');val=v('VALUE')
            if n.startswith('global '):self.globals[n[7:]]=val
            else:env[n]=val
        elif t=='local_declaration_statement':
            scope=dict(env);i=0
            while b.find(f"field[@name='VAR{i}']") is not None:scope[self.f(b,'VAR'+str(i))]=self.value(b,'DECL'+str(i),env);i+=1
            self.run(self.slot(b,'statement','STACK'),scope)
            for k in env:env[k]=scope[k]
        elif t=='controls_forEach':
            for item in list(v('LIST')):
                env[self.f(b,'VAR')]=item;self.run(self.slot(b,'statement','DO'),env)
        elif t=='controls_forRange':
            i=number(v('START'))
            while i<=number(v('END')):
                env[self.f(b,'VAR')]=i;self.run(self.slot(b,'statement','DO'),env);i+=number(v('STEP'))
        elif t=='controls_while':
            n=0
            while v('TEST'):
                self.run(self.slot(b,'statement','DO'),env);n+=1;assert n<1_000_000
        elif t=='lists_add_items':v('LIST').extend(self.args(b,env,'ITEM'))
        elif t=='lists_replace_item':v('LIST')[int(number(v('NUM')))-1]=v('ITEM')
        elif t=='procedures_callnoreturn':self.call(self.f(b,'PROCNAME'),self.args(b,env))
        elif t=='component_set_get':self.set(self.target(b,env),self.f(b,'PROP'),v('VALUE'))
        elif t=='component_method':self.method(self.target(b,env),b.find('mutation').get('method_name'),self.args(b,env))
        elif t=='controls_openAnotherScreenWithStartValue':self.opened=(v('SCREENNAME'),json.loads(json.dumps(v('STARTVALUE'))));raise Stop
        elif t=='controls_closeScreenWithValue':self.closed=True;raise Stop
        elif t=='controls_closeApplication':self.closed=True;raise Stop
        else:raise ValueError(t)
    def target(self,b,env):
        m=b.find('mutation')
        return m.get('instance_name') if m.get('is_generic')=='false' else self.value(b,'COMPONENT',env).name

    def eval(self,b,env):
        t=b.get('type');v=lambda n:self.value(b,n,env);m=b.find('mutation')
        if t=='math_number':return number(self.f(b,'NUM'))
        if t=='text':return self.f(b,'TEXT')
        if t=='logic_boolean':return self.f(b,'BOOL')=='TRUE'
        if t=='lexical_variable_get':
            n=self.f(b,'VAR');return self.globals[n[7:]] if n.startswith('global ') else env[n]
        if t=='math_compare':
            op=self.f(b,'OP');a,c=v('A'),v('B')
            if op=='EQ':return same(a,c)
            if op=='NEQ':return not same(a,c)
            a,c=number(a),number(c)
            return {'LT':a<c,'LTE':a<=c,'GT':a>c,'GTE':a>=c}[op]
        if t=='logic_operation':
            if self.f(b,'OP')=='AND':return bool(v('A')) and bool(v('B'))
            return bool(v('A')) or bool(v('B'))
        if t=='logic_negate':return not v('BOOL')
        if t=='math_add':return sum(number(x) for x in self.args(b,env,'NUM'))
        if t=='math_multiply':return math.prod(number(x) for x in self.args(b,env,'NUM'))
        if t=='math_subtract':return number(v('A'))-number(v('B'))
        if t=='math_division':return number(v('A'))/number(v('B'))
        if t=='math_on_list':return (max if self.f(b,'OP')=='MAX' else min)(number(x) for x in self.args(b,env,'NUM'))
        if t=='math_single':
            a=number(v('NUM'));return {'FLOOR':math.floor,'CEILING':math.ceil,'ABS':abs,'ROUND':round}[self.f(b,'OP')](a)
        if t=='math_is_a_number':return isnumber(v('NUM'))
        if t=='math_format_as_decimal':return f"{number(v('NUM')):.{int(v('PLACES'))}f}"
        if t=='lists_select_item':return v('LIST')[int(number(v('NUM')))-1]
        if t=='lists_length':return len(v('LIST'))
        if t=='lists_create_with':return self.args(b,env,'ADD')
        if t=='lists_is_list':return isinstance(v('ITEM'),list)
        if t=='lists_is_in':
            item=v('ITEM');return any(same(item,x) for x in v('LIST'))
        if t=='lists_copy':return copy.deepcopy(v('LIST'))
        if t=='text_is_string':return isinstance(v('ITEM'),str)
        if t=='text_join':return ''.join(self.text(x) for x in self.args(b,env,'ADD'))
        if t=='text_trim':return v('TEXT').strip()
        if t=='text_replace_all':return v('TEXT').replace(v('SEGMENT'),v('REPLACEMENT'))
        if t=='controls_choose':return v('THENRETURN') if v('TEST') else v('ELSERETURN')
        if t=='local_declaration_expression':
            scope=dict(env);i=0
            while b.find(f"field[@name='VAR{i}']") is not None:scope[self.f(b,'VAR'+str(i))]=self.value(b,'DECL'+str(i),env);i+=1
            return self.value(b,'RETURN',scope)
        if t=='controls_do_then_return':self.run(self.slot(b,'statement','STM'),env);return v('VALUE')
        if t=='procedures_callreturn':return self.call(self.f(b,'PROCNAME'),self.args(b,env))
        if t=='component_component_block':return Comp(self.f(b,'COMPONENT_SELECTOR'))
        if t=='component_set_get':return self.get(self.target(b,env),self.f(b,'PROP'))
        if t=='component_method':return self.method(self.target(b,env),m.get('method_name'),self.args(b,env))
        if t=='controls_getStartValue':return json.loads(json.dumps(self.start))
        raise ValueError(t)
    def text(self,x):
        if isinstance(x,bool):return 'true' if x else 'false'
        if isinstance(x,float) and x.is_integer():return str(int(x))
        return str(x)

    def get(self,n,p):
        c=self.components[n]
        if self.types[n]=='Player' and p=='IsPlaying':
            if n=='音乐':return self.music_started is not None and not self.music_fail and self.now>=self.music_started+self.music_delay
            return c['IsPlaying']
        return c[p]
    def set(self,n,p,v):
        c=self.components[n]
        if self.types[n]=='Player' and p=='Source':
            c['IsPlaying']=False
            if v and self.needs_permission and n!='音乐':self.pending=v;return
        if self.types[n]=='ListPicker' and p=='Elements':v=list(v)
        c[p]=v
    def method(self,n,name,a):
        t=self.types[n];c=self.components[n]
        if t=='TinyDB':
            if name=='GetValue':return copy.deepcopy(self.storage.get(a[0],a[1]))
            self.storage[a[0]]=copy.deepcopy(a[1]);return
        if t=='Notifier':self.alerts.append(a[0]);return
        if t=='Web':
            try:return json.JSONDecoder().raw_decode(a[0])[0]
            except ValueError:self.error(n,'JsonTextDecode','JSON 格式错误');return ''
        if t=='File':self.reads.append(a[0]);return
        if t=='Clock':return self.now
        if t=='Sound':self.plays.append((n,self.now));return
        if t=='Player':
            if name=='Start':
                if n=='音乐':self.music_started=self.now
                elif c['Source'] in self.missing:self.error(n,'Start','missing')
                else:c['IsPlaying']=True
            else:c['IsPlaying']=False
            return
        if t=='Canvas':
            if name=='Clear':self.draws[n]=[];self.texts[n]=[]
            elif name=='DrawLine':
                assert all(math.isfinite(number(x)) for x in a);self.draws.setdefault(n,[]).append(dict(args=[number(x) for x in a],color=c['PaintColor'],width=c['LineWidth']))
            elif name=='DrawText':self.texts.setdefault(n,[]).append(a)
            return
        raise ValueError(t+'.'+name)

    def tick(self,ms=16):
        self.now+=ms
        for n,t in self.types.items():
            if t=='Clock' and self.components[n]['TimerEnabled']:self.event(n,'Timer')
    def advance(self,ms,step=16):
        end=self.now+ms
        while self.now<end:self.tick(min(step,end-self.now))
    def click(self,n):self.event(n,'Click')
    def pick(self,n,uri):self.components[n]['Selection']=uri;self.event(n,'AfterPicking')
    def grant(self):
        path,self.pending=self.pending,None;self.needs_permission=False
        self.components['音乐检查']['Source']=path
        if path in self.missing:self.error('音乐检查','Source','missing')
    def deny(self):self.pending=None;self.event(self.screen,'PermissionDenied',Comp('音乐检查'),'Source','READ_MEDIA_AUDIO')
