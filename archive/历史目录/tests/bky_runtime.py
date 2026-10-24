"""Small deterministic interpreter for the exported BKY subset.

This executes the real XML program with a fake Clock and Canvas. It tests game
logic, not Android input latency or MIT's build service. Unsupported blocks fail.
"""
from pathlib import Path
import json
import math
import random
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
AIA = ROOT / 'dist' / 'Rail4K_MVP.aia'


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
    def __init__(self, seed=7, width=360, height=430):
        with zipfile.ZipFile(AIA) as z:
            self.archive_names = z.namelist()
            scm = z.read(next(n for n in z.namelist() if n.endswith('.scm'))).decode('utf-8')
            self.design = json.loads(scm.split('$JSON', 1)[1].rsplit('|#', 1)[0])
            xml = z.read(next(n for n in z.namelist() if n.endswith('.bky')))
        self.root = ET.fromstring(xml)
        for e in self.root.iter():
            e.tag = e.tag.split('}')[-1]
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
            for child in c.get('$Components', []): register(child)
        register(self.design['Properties'])
        self.components['画布'].update(Width=width, Height=height)
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
        if t == 'math_number':
            f = float(field(b, 'NUM'))
            return int(f) if f.is_integer() else f
        if t == 'text': return field(b, 'TEXT')
        if t == 'logic_boolean': return field(b, 'BOOL') == 'TRUE'
        if t == 'lexical_variable_get':
            name = field(b, 'VAR')
            return self.globals[name[7:]] if name.startswith('global ') else env[name]
        if t in ('math_add', 'math_multiply', 'math_on_list', 'lists_create_with', 'text_join'):
            vals = [self.evaluate(e.find('block'), env) for e in b.findall('value')]
            if t == 'math_add': return sum(vals)
            if t == 'math_multiply': return math.prod(vals)
            if t == 'math_on_list': return (min if field(b, 'OP') == 'MIN' else max)(vals)
            if t == 'lists_create_with': return vals
            return ''.join(str(x) for x in vals)
        if t == 'math_subtract': return v('A') - v('B')
        if t == 'math_division': return v('A') / v('B')
        if t == 'math_single':
            return {'ABS': abs, 'ROUND': round, 'CEILING': math.ceil, 'FLOOR': math.floor}[field(b, 'OP')](v('NUM'))
        if t == 'math_compare':
            a, c = v('A'), v('B')
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
        if t == 'math_format_as_decimal': return f"{v('NUM'):.{v('PLACES')}f}"
        if t == 'component_set_get':
            m = b.find('mutation').attrib
            if m['set_or_get'] != 'get': raise ValueError('Setter in expression')
            return self.components[m['instance_name']][m['property_name']]
        if t == 'component_component_block': return b.find('mutation').get('instance_name')
        if t == 'component_method':
            m = b.find('mutation').attrib
            if m['component_type'] == 'Clock' and m['method_name'] == 'SystemTime': return self.now
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
            elif t == 'procedures_callnoreturn':
                args = [self.evaluate(e.find('block'), env) for e in b.findall('value')]
                self.call(field(b, 'PROCNAME'), *args)
            elif t == 'controls_if':
                branch = 'DO0' if v('IF0') else 'ELSE'
                entry = b.find(f"statement[@name='{branch}']/block")
                if entry is not None: self.execute(entry, env)
            elif t == 'controls_forRange':
                start, end, step = v('START'), v('END'), v('STEP')
                for i in range(int(start), int(end)+1, int(step)):
                    self.execute(slot(b, 'statement', 'DO'), {**env, field(b, 'VAR'): i})
            elif t == 'controls_while':
                count = 0
                while v('TEST'):
                    self.execute(slot(b, 'statement', 'DO'), env)
                    count += 1
                    if count > 1000: raise ValueError('Loop runaway')
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
                if m['component_type'] != 'Canvas': raise ValueError(m)
                args = [self.evaluate(e.find('block'), env) for e in b.findall('value')]
                if m['method_name'] == 'Clear':
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
            elif t == 'controls_closeApplication': self.closed = True
            else: raise ValueError(f'Unsupported statement: {t}')
            b = b.find('next/block')

    def call(self, name, *args):
        p = self.procedures[name]
        argnames = [a.get('name') for a in p.find('mutation').findall('arg')]
        assert len(argnames) == len(args), (name, argnames, args)
        if name == '记录判定': self.judgements.append((self.globals['下一键'], args[0], self.globals['用时']))
        self.execute(slot(p, 'statement', 'STACK'), dict(zip(argnames, args)))

    def event(self, component, name, **params):
        b = self.events[component, name]
        if component == '画布' and name == 'TouchDown':
            m = b.find('mutation')
            params = {m.get('param_name0', 'x'): params['x'], m.get('param_name1', 'y'): params['y']}
        self.execute(slot(b, 'statement', 'DO'), params)

    def start(self):
        self.event('开始', 'Click')

    def advance(self, elapsed, step=100):
        """Drive native Timer callbacks, preserving the same clock/time basis."""
        target = self.globals['起点'] + elapsed
        assert target >= self.now
        while self.now < target:
            self.now = min(self.now + step, target)
            if self.components['时钟']['TimerEnabled'] is True and (
                    str(self.components['时钟']['TimerAlwaysFires']).lower() == 'true' or self.on_screen):
                self.event('时钟', 'Timer')

    def tap(self, lane, y=10):
        self.event('画布', 'TouchDown', x=(lane-0.5)*self.components['画布']['Width']/4, y=y)

    def hit(self, index, offset=0):
        self.advance(index * 1000 - 500 + offset)
        self.tap(self.globals['谱面'][index-1])
