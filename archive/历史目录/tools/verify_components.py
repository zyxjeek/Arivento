"""Validate Designer and component blocks against MIT's live component metadata.

Snapshot: public MIT ode build dated 2026-08-28, retrieved 2026-09-05.
This is an interface check, not an online import/build or an Android test.
"""
from pathlib import Path
import hashlib
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
from bky_runtime import Runtime, ROOT, AIA

r = Runtime()
metadata_path = ROOT / 'reference' / 'component-types.json'
metadata = {x['name']: x for x in json.loads(metadata_path.read_text(encoding='utf-8'))}
issues = []
for c in r.components.values():
    md = metadata[c['$Type']]
    properties = {p['name'] for p in md['properties']}
    # App Inventor Designer supplies these inherited sizing properties for
    # visible components. They occur in the original AIA and blockProperties,
    # but are not emitted in the per-component Designer property array.
    if md['nonVisible'] == 'false':
        properties.update(p['name'] for p in md['blockProperties'] if p['name'] in ('Width', 'Height'))
    if int(c['$Version']) > int(md['version']):
        issues.append(f"Unsupported component version: {c['$Name']}")
    for name in c:
        if not name.startswith('$') and name != 'Uuid' and name not in properties:
            issues.append(f"Unknown Designer property: {c['$Name']}.{name}")

counts = {'methods': 0, 'events': 0, 'property_accesses': 0}
for b in r.root.iter('block'):
    kind = b.get('type')
    m = b.find('mutation')
    if kind == 'component_method':
        counts['methods'] += 1
        method = next((x for x in metadata[m.get('component_type')]['methods']
                       if x['name'] == m.get('method_name')), None)
        if method is None or len(method['params']) != len(b.findall('value')):
            issues.append(f"Invalid method or arity: {m.attrib}")
    elif kind == 'component_event':
        counts['events'] += 1
        if not any(x['name'] == m.get('event_name') for x in metadata[m.get('component_type')]['events']):
            issues.append(f"Invalid event: {m.attrib}")
    elif kind == 'component_set_get':
        counts['property_accesses'] += 1
        prop = next((x for x in metadata[m.get('component_type')]['blockProperties']
                     if x['name'] == m.get('property_name')), None)
        if prop is None:
            issues.append(f"Invalid property: {m.attrib}")
        elif m.get('set_or_get') == 'set' and prop.get('rw') == 'read-only':
            issues.append(f"Read-only property written: {m.attrib}")

report = {'success': not issues, 'components': len(r.components), **counts, 'issues': issues,
          'metadata_build_date': metadata['Canvas']['dateBuilt'],
          'metadata_sha256': hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
          'aia_sha256': hashlib.sha256(AIA.read_bytes()).hexdigest(),
          'scope': 'Designer properties, component versions, method arities, events and property access; not Blockly import or Android execution.'}
(ROOT / 'docs' / 'component-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(bool(issues))
