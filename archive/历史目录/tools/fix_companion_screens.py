from pathlib import Path
import argparse
import json
import shutil
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NAMES = {'制谱设置': 'EditorSettings', '录制屏': 'Recorder', '游玩屏': 'Play'}

def fix(source, target):
    assert source.resolve() != target.resolve()
    with zipfile.ZipFile(source) as old, zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as new:
        for info in old.infolist():
            name = info.filename
            if name.endswith(('.scm', '.bky')):
                data = old.read(name)
                path = Path(name)
                name = str(path.with_name(NAMES.get(path.stem, path.stem) + path.suffix)).replace('\\', '/')
                if path.suffix == '.scm':
                    form = json.loads(data.decode('utf-8').split('$JSON', 1)[1].rsplit('|#', 1)[0])
                    props = form['Properties']
                    props['$Name'] = NAMES.get(props['$Name'], props['$Name'])
                    props.update(VersionCode='7', VersionName='0.6.1')
                    data = ('#|\n$JSON\n' + json.dumps(form, ensure_ascii=False, separators=(',', ':')) + '\n|#\n').encode()
                else:
                    xml = ET.fromstring(data)
                    for e in xml.iter(): e.tag = e.tag.split('}')[-1]
                    for b in xml.iter('block'):
                        m = b.find('mutation')
                        if m is not None and m.get('component_type') == 'Form':
                            m.set('instance_name', NAMES.get(m.get('instance_name'), m.get('instance_name')))
                            f = b.find("field[@name='COMPONENT_SELECTOR']")
                            if f is not None: f.text = NAMES.get(f.text, f.text)
                        if b.get('type') in ['controls_openAnotherScreen', 'controls_openAnotherScreenWithStartValue']:
                            f = b.find("value[@name='SCREENNAME']/block/field[@name='TEXT']")
                            if f is not None: f.text = NAMES.get(f.text, f.text)
                    xml.set('xmlns', 'http://www.w3.org/1999/xhtml')
                    ET.indent(xml, space='  ')
                    data = ET.tostring(xml, encoding='utf-8')
                new.writestr(name, data)
                out = ROOT / 'native/Rail4K_CompanionFix' / name
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
            elif name.endswith('project.properties'):
                data = old.read(name).decode('utf-8').replace('versioncode=6', 'versioncode=7').replace('versionname=0.6.0', 'versionname=0.6.1').encode()
                new.writestr(name, data)
                out = ROOT / 'native/Rail4K_CompanionFix' / name
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
            else:
                entry = zipfile.ZipInfo(name, info.date_time)
                entry.compress_type = info.compress_type
                with old.open(info) as a, new.open(entry, 'w') as b: shutil.copyfileobj(a, b)
    print(str(target))

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--input', type=Path)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    if bool(a.input) != bool(a.output): p.error('--input and --output must be used together')
    if a.input:
        fix(a.input, a.output)
    else:
        for suffix in ['_CodeOnly', '']:
            fix(ROOT / f'dist/Rail4K_Multi_v2{suffix}.aia', ROOT / f'dist/Rail4K_Multi_v3{suffix}.aia')
