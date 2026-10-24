from 制谱器 import *
import argparse

def fix(source, target):
    assert source.resolve() != target.resolve()
    TYPES.update(音乐输入='TextBox')
    with zipfile.ZipFile(source) as old, zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as new:
        for name in old.namelist():
            data = old.read(name)
            if name.endswith('.scm'):
                design = json.loads(data.decode().split('$JSON')[1].rsplit('|#', 1)[0])
                def update(c):
                    if '$Components' in c:
                        c['$Components'] = [x for x in c['$Components'] if x['$Name'] != '文件']
                        for x in c['$Components']: update(x)
                    if c['$Name'] == '音乐输入':
                        uuid = c['Uuid']
                        c.clear()
                        c.update(输入('音乐输入', '音乐文件名（含后缀，留空无音乐）'))
                        c['Uuid'] = uuid
                update(design['Properties'])
                design['Properties'].update(VersionCode='8', VersionName='0.6.2')
                data = ('#|\n$JSON\n'+json.dumps(design,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode()
            elif name.endswith('.bky'):
                xml = ET.fromstring(data)
                for e in xml.iter(): e.tag = e.tag.split('}')[-1]
                for b in xml.findall('block'):
                    m = b.find('mutation')
                    if b.get('type') == 'component_event' and m.get('instance_name') == 'EditorSettings' and m.get('event_name') == 'Initialize':
                        xml.remove(b)
                for b in xml.iter('block'):
                    if b.get('type') == 'procedures_defnoreturn' and b.findtext("field[@name='NAME']") == '入场':
                        s = b.find('statement')
                        condition = s.find('block')
                        body = condition.find("statement[@name='DO0']/block")
                        s.remove(condition)
                        s.append(body)
                    if name.endswith('/EditorSettings.bky') and b.get('type') == 'lexical_variable_set' and b.findtext("field[@name='VAR']") == 'global 音乐名':
                        v = b.find("value[@name='VALUE']")
                        v.clear()
                        v.set('name', 'VALUE')
                        v.append(修剪(取('音乐输入')))
                for i,b in enumerate(xml.iter('block')): b.set('id', f'修复_{i}')
                xml.set('xmlns','http://www.w3.org/1999/xhtml')
                ET.indent(xml,space='  ')
                data = ET.tostring(xml,encoding='utf-8')
                assert b'ListDirectory' not in data
                assert 'instance_name="文件"'.encode() not in data
            elif name.endswith('project.properties'):
                data = data.decode().replace('versioncode=7','versioncode=8').replace('versionname=0.6.1','versionname=0.6.2').encode()
            new.writestr(name,data)
            if not name.startswith('assets/'):
                out = ROOT/'native/Rail4K_AssetFix'/name
                out.parent.mkdir(parents=True,exist_ok=True)
                out.write_bytes(data)
    print(target)

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--input',type=Path,default=ROOT/'dist/Rail4K_Multi_v3_CodeOnly.aia')
    p.add_argument('--output',type=Path,default=ROOT/'dist/Rail4K_Multi_v4_CodeOnly.aia')
    a = p.parse_args()
    fix(a.input,a.output)
