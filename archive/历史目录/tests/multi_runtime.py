from pathlib import Path
import json
import math
import random
import xml.etree.ElementTree as ET
import zipfile
import copy

ROOT = Path(__file__).resolve().parents[1]
AIA = ROOT / 'dist' / 'Rail4K_Multi_v2.aia'


def field(b, name):
    e = b.find(f"field[@name='{name}']")
    if e is None:
        raise ValueError(f'Missing field {name} in {b.attrib}')
    return e.text or ''


def slot(b, tag, name):
    e = b.find(f"{tag}[@name='{name}']/block")
    if e is None:
        raise ValueError(f'Missing {tag} {name} in {b.attrib}')
    return e


class Runtime:
    def __init__(self, seed=7, width=360, height=430, cloud=None, assets=(), screen='Screen1', start=''):
        with zipfile.ZipFile(AIA) as z:
            self.archive_names = z.namelist()
            scm = z.read(next(n for n in z.namelist() if n.endswith('/'+screen+'.scm'))).decode('utf-8')
            self.design = json.loads(scm.split('$JSON', 1)[1].rsplit('|#', 1)[0])
            xml = z.read(next(n for n in z.namelist() if n.endswith('/'+screen+'.bky')))
        self.root = ET.fromstring(xml)
        for e in self.root.iter():
            e.tag = e.tag.split('}')[-1]
        self.screen = screen
        self.start_value = start
        self.opened = None
        self.result = None
        self.cloud = {} if cloud is None else cloud
        self.pending = []
        self.alerts = []
        self.assets = list(assets)
        self.music_starts = []
        self.fail_music = False
        self.globals = {}
        self.components = {}
        self.procedures = {}
        self.events = {}
        self.on_screen = True
        self.now = 1_000_000
        self.rng = random.Random(seed)
        self.draws = []
        self.text_draws = []
        self.executed = set()
        self.judgements = []
        self.closed = False

        def register(c):
            self.components[c['$Name']] = dict(c)
            if c['$Type'] in ('Spinner', 'ListPicker'):
                self.components[c['$Name']].update(Elements=c.get('ElementsFromString','').split(','), Selection=c.get('ElementsFromString','').split(',')[0], SelectionIndex=1)
            for child in c.get('$Components', []): register(child)
        register(self.design['Properties'])
        if '画布' in self.components: self.components['画布'].update(Width=width, Height=height)
        for b in self.root.findall('block'):
            if b.get('type') == 'procedures_defnoreturn':
                self.procedures[field(b, 'NAME')] = b
            elif b.get('type') == 'component_event':
                m = b.find('mutation').attrib
                self.events[m['instance_name'], m['event_name']] = b
            elif b.get('type') == 'global_declaration':
                self.globals[field(b, 'NAME')] = self.value(b, 'VALUE', {})
            else: raise ValueError('Unexpected top-level block')

    def value(self, b, name, env): return self.evaluate(slot(b, 'value', name), env)

    def evaluate(self, b, env):
        self.executed.add(b.get('id'))
        t = b.get('type')
        v = lambda n: self.value(b, n, env)
        if t == 'controls_getStartValue': return copy.deepcopy(self.start_value)
        if t == 'math_number':
            f = float(field(b, 'NUM'))
            return int(f) if f.is_integer() else f
        if t == 'text': return field(b, 'TEXT')
        if t == 'helpers_dropdown': return field(b, 'OPTION')
        if t == 'logic_negate': return not v('BOOL')
        if t == 'lists_length': return len(v('LIST'))
        if t == 'lists_is_list': return isinstance(v('ITEM'), list)
        if t == 'lists_copy': return copy.deepcopy(v('LIST'))
        if t == 'lists_is_in': return v('ITEM') in v('LIST')
        if t == 'text_trim': return v('TEXT').strip()
        if t == 'text_length': return len(v('VALUE'))
        if t == 'text_changeCase': return v('TEXT').lower()
        if t == 'text_segment': return v('TEXT')[int(v('START'))-1:int(v('START'))-1+int(v('LENGTH'))]
        if t == 'text_is_string': return isinstance(v('ITEM'), str)
        if t == 'math_is_a_number':
            try: return not isinstance(v('NUM'), (bool,list)) and math.isfinite(float(v('NUM')))
            except (ValueError,TypeError): return False
        if t == 'logic_boolean': return field(b, 'BOOL') == 'TRUE'
        if t == 'lexical_variable_get':
            name = field(b, 'VAR')
            return self.globals[name[7:]] if name.startswith('global ') else env[name]
        if t in ('math_add', 'math_multiply', 'math_on_list', 'lists_create_with', 'text_join'):
            vals = [self.evaluate(e.find('block'), env) for e in b.findall('value')]
            if t == 'math_add': return sum(float(x) for x in vals)
            if t == 'math_multiply': return math.prod(float(x) for x in vals)
            if t == 'math_on_list': return (min if field(b, 'OP') == 'MIN' else max)(vals)
            if t == 'lists_create_with': return vals
            return ''.join(str(x) for x in vals)
        if t == 'math_subtract': return float(v('A')) - float(v('B'))
        if t == 'math_division': return float(v('A')) / float(v('B'))
        if t == 'math_single':
            return {'ABS': abs, 'ROUND': round, 'CEILING': math.ceil, 'FLOOR': math.floor}[field(b, 'OP')](float(v('NUM')))
        if t == 'math_compare':
            a, c = v('A'), v('B')
            if field(b, 'OP') not in ('EQ','NEQ'): a, c = float(a), float(c)
            elif isinstance(a,(int,float)) and isinstance(c,str):
                try: c=float(c)
                except ValueError: pass
            return {'EQ': lambda: a == c, 'NEQ': lambda: a != c, 'LT': lambda: a < c,
                    'LTE': lambda: a <= c, 'GT': lambda: a > c, 'GTE': lambda: a >= c}[field(b, 'OP')]()
        if t == 'logic_operation':
            return (v('A') and v('B')) if field(b, 'OP') == 'AND' else (v('A') or v('B'))
        if t == 'controls_choose': return v('THENRETURN') if v('TEST') else v('ELSERETURN')
        if t == 'math_random_int': return self.rng.randint(v('FROM'), v('TO'))
        if t == 'lists_select_item':
            items, index = v('LIST'), v('NUM')
            if not isinstance(index, (int, float)) or int(index) != index or not 1 <= index <= len(items):
                raise IndexError(f'App Inventor list index {index}; length {len(items)}')
            return items[int(index)-1]
        if t == 'math_format_as_decimal': return f"{v('NUM'):.{int(v('PLACES'))}f}"
        if t == 'component_set_get':
            m = b.find('mutation').attrib
            if m['set_or_get'] != 'get': raise ValueError('Setter in expression')
            return self.components[m['instance_name']][m['property_name']]
        if t == 'component_component_block': return b.find('mutation').get('instance_name')
        if t == 'component_method':
            m = b.find('mutation').attrib
            if m['component_type'] == 'Clock' and m['method_name'] == 'SystemTime': return self.now
            if m['component_type'] == 'File': return self.assets[:]
        raise ValueError(f'Unsupported expression: {t}')

    def execute(self, b, env=None):
        env = {} if env is None else env
        while b is not None:
            self.executed.add(b.get('id'))
            t = b.get('type')
            v = lambda n: self.value(b, n, env)
            if t == 'lexical_variable_set':
                name = field(b, 'VAR')
                if name.startswith('global '): self.globals[name[7:]] = v('VALUE')
                else: env[name] = v('VALUE')
            elif t == 'component_set_get':
                m = b.find('mutation').attrib
                if m['set_or_get'] != 'set': raise ValueError('Getter in statement')
                name = v('COMPONENT') if m.get('is_generic') == 'true' else m['instance_name']
                self.components[name][m['property_name']] = v('VALUE')
                if m['property_name'] == 'Elements':
                    self.components[name]['SelectionIndex'] = 1
                    self.components[name]['Selection'] = v('VALUE')[0] if v('VALUE') else ''
                if name=='音乐' and m['property_name']=='Source' and self.fail_music and v('VALUE'):
                    self.event(self.screen,'ErrorOccurred',组件='音乐',函数='Source',编号=701,消息='bad audio')
            elif t == 'procedures_callnoreturn':
                args = [self.evaluate(e.find('block'), env) for e in b.findall('value')]
                self.call(field(b, 'PROCNAME'), *args)
            elif t == 'controls_if':
                branch = 'DO0' if v('IF0') else 'ELSE'
                entry = b.find(f"statement[@name='{branch}']/block")
                if entry is not None: self.execute(entry, env)
            elif t == 'controls_forEach':
                var = field(b,'VAR')
                before = env.get(var)
                for x in list(v('LIST')):
                    env[var] = x
                    self.execute(slot(b,'statement','DO'),env)
                env[var] = before
            elif t == 'lists_replace_item':
                v('LIST')[int(v('NUM'))-1] = v('ITEM')
            elif t == 'controls_forRange':
                start, end, step = v('START'), v('END'), v('STEP')
                for i in range(int(start), int(end)+1, int(step)):
                    self.execute(slot(b, 'statement', 'DO'), {**env, field(b, 'VAR'): i})
            elif t == 'controls_while':
                count = 0
                while v('TEST'):
                    self.execute(slot(b, 'statement', 'DO'), env)
                    count += 1
                    if count > 20000: raise ValueError('Loop runaway')
            elif t == 'local_declaration_statement':
                scoped = dict(env)
                for i, name in enumerate(b.find('mutation').findall('localname')):
                    scoped[name.get('name')] = v(f'DECL{i}')
                self.execute(slot(b, 'statement', 'STACK'), scoped)
            elif t == 'lists_add_items':
                lst = v('LIST')
                for e in b.findall('value'):
                    if e.get('name').startswith('ITEM'): lst.append(self.evaluate(e.find('block'), env))
            elif t == 'component_method':
                m = b.find('mutation').attrib
                args = [self.evaluate(e.find('block'), env) for e in b.findall('value')]
                kind, method = m['component_type'], m['method_name']
                if kind == 'CloudDB':
                    if method=='GetValue': self.pending.append(('GetValue',args))
                    elif method=='StoreValue': self.pending.append(('StoreValue',copy.deepcopy(args)))
                    elif method=='GetTagList': self.pending.append(('GetTagList',args))
                    else: raise ValueError(method)
                elif kind == 'Player':
                    if method=='Start': self.music_starts.append(self.now)
                elif kind == 'Notifier': self.alerts.append(args)
                elif kind == 'TextBox': pass
                elif m['method_name'] == 'Clear':
                    self.draws = []
                    self.text_draws = []
                elif m['method_name'] == 'DrawLine':
                    assert all(math.isfinite(x) for x in args)
                    self.draws.append({'args': args, 'color': self.components['画布']['PaintColor'],
                                       'width': self.components['画布']['LineWidth']})
                elif m['method_name'] == 'DrawText':
                    assert len(args) == 3 and all(math.isfinite(x) for x in args[1:])
                    self.text_draws.append({'text': args[0], 'x': args[1], 'y': args[2],
                        'color': self.components['画布']['PaintColor']})
                else: raise ValueError(m)
            elif t == 'controls_openAnotherScreenWithStartValue': self.opened = (self.value(b, 'SCREENNAME', env), copy.deepcopy(self.value(b, 'STARTVALUE', env)))
            elif t == 'controls_closeScreenWithValue':
                self.closed = True
                self.result = copy.deepcopy(self.value(b, 'SCREEN', env))
                return
            elif t == 'controls_closeApplication': self.closed = True
            else: raise ValueError(f'Unsupported statement: {t}')
            b = b.find('next/block')

    def call(self, name, *args):
        p = self.procedures[name]
        argnames = [a.get('name') for a in p.find('mutation').findall('arg')]
        assert len(argnames) == len(args), (name, argnames, args)
        if name == '记录判定': self.judgements.append((args[0],args[1],self.globals['用时']))
        self.execute(slot(p, 'statement', 'STACK'), dict(zip(argnames, args)))

    def event(self, component, name, **params):
        b = self.events[component, name]
        if component == '画布' and name == 'TouchDown':
            m = b.find('mutation')
            params = {m.get('param_name0', 'x'): params['x'], m.get('param_name1', 'y'): params['y']}
        self.execute(slot(b, 'statement', 'DO'), params)

    def initialize(self):
        self.event(self.screen,'Initialize')

    def cloud_step(self, fail=False):
        method,args = self.pending.pop(0)
        if fail:
            self.event('云端','CloudDBError',消息='network failed')
        elif method=='GetValue':
            self.event('云端','GotValue',标签=args[0],值=copy.deepcopy(self.cloud.get(args[0],args[1])))
        elif method=='StoreValue':
            self.cloud[args[0]]=copy.deepcopy(args[1])
            self.event('云端','UpdateDone',标签=args[0],操作='StoreValue')
        else: self.event('云端','TagList',值=list(self.cloud))

    def cloud_flush(self):
        for _ in range(30):
            if not self.pending: return
            self.cloud_step()
        raise ValueError('cloud loop')

    def start(self): self.event('开始','Click')

    def advance(self, elapsed, step=100):
        target = self.globals['起点'] + elapsed
        assert target >= self.now,(target,self.now)
        while self.now < target:
            self.now = min(self.now+step,target)
            if self.components['时钟']['TimerEnabled'] is True:
                self.event('时钟','Timer')

    def tap(self, lane, y=10):
        self.event('画布','TouchDown',x=(lane-0.5)*self.components['画布']['Width']/4,y=y)

    def record(self,name='新谱面',mode=1,bpm='120',unit='4',approach='1000',music='无音乐'):
        self.event('制谱','Click')
        self.components['名称输入']['Text']=name
        self.components['模式输入']['SelectionIndex']=mode
        self.components['速度输入']['Text']=bpm
        self.components['单位输入']['Text']=unit
        self.components['过屏输入']['Text']=approach
        self.components['音乐输入']['Selection']=music
        self.event('录制','Click')

    def note(self,lane,time):
        self.advance(time)
        self.tap(lane)

    def notes(self): return [d for d in self.draws if d['color'] & 0xffffffff == 0xff56deef]
