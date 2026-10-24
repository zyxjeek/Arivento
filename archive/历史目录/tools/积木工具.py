"""App Inventor XML积木构造工具。平台字段保持标准英文。"""
from pathlib import Path
import hashlib
import json
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'native' / 'Rail4K'
SOURCE = PROJECT / 'src' / 'appinventor' / 'ai_me' / 'Rail4K'
COUNTER = 0
TYPES = {}
PROCS = {}
TOP = []


def block(kind, fields=None, values=None, statements=None, mutation=None):
    global COUNTER
    COUNTER += 1
    b = ET.Element('block', type=kind, id=f'r4k_{COUNTER:05d}')
    if mutation is not None:
        b.append(mutation)
    for name, value in (fields or {}).items():
        ET.SubElement(b, 'field', name=name).text = str(value)
    for name, value in (values or {}).items():
        ET.SubElement(b, 'value', name=name).append(expr(value))
    for name, body in (statements or {}).items():
        if body:
            ET.SubElement(b, 'statement', name=name).append(chain(body))
    return b


def mut(**attrs):
    return ET.Element('mutation', {k: str(v) for k, v in attrs.items()})


def expr(value):
    if isinstance(value, ET.Element):
        return value
    if isinstance(value, bool):
        return block('logic_boolean', {'BOOL': 'TRUE' if value else 'FALSE'})
    if isinstance(value, (int, float)):
        return block('math_number', {'NUM': value})
    return block('text', {'TEXT': value})


def chain(items):
    for a, b in zip(items, items[1:]):
        ET.SubElement(a, 'next').append(b)
    return items[0]


def get(name):
    return block('lexical_variable_get', {'VAR': name})


def g(name):
    return get('global ' + name)


def put(name, value):
    return block('lexical_variable_set', {'VAR': 'global ' + name}, {'VALUE': value})


def change(name, value=1):
    return put(name, add(g(name), value))


def variadic(kind, prefix, args):
    return block(kind, values={f'{prefix}{i}': a for i, a in enumerate(args)}, mutation=mut(items=len(args)))


def add(*a): return variadic('math_add', 'NUM', a)
def mul(*a): return variadic('math_multiply', 'NUM', a)
def sub(a, b): return block('math_subtract', values={'A': a, 'B': b})
def div(a, b): return block('math_division', values={'A': a, 'B': b})
def compare(op, a, b): return block('math_compare', {'OP': op}, {'A': a, 'B': b})
def both(a, b): return block('logic_operation', {'OP': 'AND'}, {'A': a, 'B': b}, mutation=mut(items=2))
def either(a, b): return block('logic_operation', {'OP': 'OR'}, {'A': a, 'B': b}, mutation=mut(items=2))
def unary(op, a): return block('math_single', {'OP': op}, {'NUM': a})
def minimum(a, b): return block('math_on_list', {'OP': 'MIN'}, {'NUM0': a, 'NUM1': b}, mutation=mut(items=2))
def maximum(a, b): return block('math_on_list', {'OP': 'MAX'}, {'NUM0': a, 'NUM1': b}, mutation=mut(items=2))
def join(*a): return variadic('text_join', 'ADD', a)
def make_list(*a): return variadic('lists_create_with', 'ADD', a)
def item(a, i): return block('lists_select_item', values={'LIST': a, 'NUM': i})
def decimal(a, places=2): return block('math_format_as_decimal', values={'NUM': a, 'PLACES': places})


def iff(condition, yes, no=None):
    statements = {'DO0': yes}
    if no:
        statements['ELSE'] = no
    return block('controls_if', values={'IF0': condition}, statements=statements,
                 mutation=mut(**{'else': 1}) if no else None)


def loop(name, start, end, body):
    return block('controls_forRange', {'VAR': name}, {'START': start, 'END': end, 'STEP': 1}, {'DO': body})


def local(name, value, body):
    m = mut()
    ET.SubElement(m, 'localname', name=name)
    return block('local_declaration_statement', {'VAR0': name}, {'DECL0': value}, {'STACK': body}, m)


def prop(name, attribute, value=None, *, read=False):
    m = mut(component_type=TYPES[name], set_or_get='get' if read else 'set',
            property_name=attribute, is_generic='false', instance_name=name)
    return block('component_set_get', {'COMPONENT_SELECTOR': name, 'PROP': attribute},
                 None if read else {'VALUE': value}, mutation=m)


def method(name, operation, *args):
    return block('component_method', {'COMPONENT_SELECTOR': name},
                 {f'ARG{i}': a for i, a in enumerate(args)},
                 mutation=mut(component_type=TYPES[name], method_name=operation,
                              is_generic='false', instance_name=name))


def call(name, *args):
    m = mut(name=name)
    for arg in PROCS[name]:
        ET.SubElement(m, 'arg', name=arg)
    return block('procedures_callnoreturn', {'PROCNAME': name},
                 {f'ARG{i}': a for i, a in enumerate(args)}, mutation=m)


def top(b, comment):
    # Compact columns of collapsed stacks remain easy to find in the Blocks editor.
    b.set('x', str(40 + (len(TOP) // 13) * 470))
    b.set('y', str(40 + (len(TOP) % 13) * 115))
    if b.get('type') != 'global_declaration':
        b.set('collapsed', 'true')
    if comment: ET.SubElement(b, 'comment', pinned='false', h='100', w='380').text = comment
    TOP.append(b)


def procedure(name, body, comment):
    m = mut()
    for arg in PROCS[name]:
        ET.SubElement(m, 'arg', name=arg)
    fields = {'NAME': name, **{f'VAR{i}': v for i, v in enumerate(PROCS[name])}}
    top(block('procedures_defnoreturn', fields, statements={'STACK': body}, mutation=m), comment)


def event(name, event_name, body, comment):
    top(block('component_event', {'COMPONENT_SELECTOR': name}, statements={'DO': body},
              mutation=mut(component_type=TYPES[name], is_generic='false', instance_name=name,
                           event_name=event_name)), comment)


def component(name, kind, version, children=None, **properties):
    TYPES[name] = kind
    c = {'$Name': name, '$Type': kind, '$Version': str(version),
         'Uuid': str(10000 + len(TYPES)), **{k: str(v) for k, v in properties.items()}}
    if children:
        c['$Components'] = children
    return c


