import io,json,unittest,zipfile,xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def missing(path):
    failures=[]
    with zipfile.ZipFile(path) as z:
        definitions={}
        for n in z.namelist():
            if n.startswith('assets/external_comps/') and n.endswith('/components.json'):
                for d in json.loads(z.read(n)):definitions[d['name']]=d
        for n in z.namelist():
            if n.endswith('.scm'):
                d=json.loads(z.read(n).decode().split('$JSON')[1].rsplit('|#',1)[0])
                def visit(c):
                    if c['$Name']=='本地文件' and c['$Type'] not in definitions:failures.append((n,c['$Type']))
                    for x in c.get('$Components',[]):visit(x)
                visit(d['Properties'])
            elif n.endswith('.bky'):
                r=ET.fromstring(z.read(n))
                for m in r.iter():
                    if m.tag.endswith('mutation') and m.get('instance_name')=='本地文件' and m.get('component_type') not in definitions:failures.append((n,m.get('component_type')))
    return failures

class Tests(unittest.TestCase):
    def test_old_archive_reproduces_missing_component(self):
        errors=missing(ROOT/'dist/Rail4K_0918_1.aia')
        self.assertTrue(errors)
        self.assertEqual({t for _,t in errors},{'rail4k.local.LocalFiles'})
    def test_fixed_archive_resolves_components_and_blocks(self):
        self.assertEqual(missing(ROOT/'dist/Rail4K_0919_1.aia'),[])
        with zipfile.ZipFile(ROOT/'dist/Rail4K_0919_1.aia') as z:
            d=json.loads(z.read('assets/external_comps/rail4k.local.LocalFiles/components.json'))[0]
            self.assertEqual(d['name'],'LocalFiles');self.assertEqual(d['type'],'rail4k.local.LocalFiles')
            with zipfile.ZipFile(io.BytesIO(z.read('assets/external_comps/rail4k.local.LocalFiles/files/AndroidRuntime.jar'))) as jar:
                self.assertIn(d['type'].replace('.','/')+'.class',jar.namelist())
            for n in z.namelist():
                if not n.endswith('.bky'):continue
                r=ET.fromstring(z.read(n))
                for e in r.iter():e.tag=e.tag.split('}')[-1]
                for b in r.iter('block'):
                    m=b.find('mutation')
                    if m is None or m.get('instance_name')!='本地文件':continue
                    name=m.get('method_name') or m.get('event_name')
                    members=d['methods'] if b.get('type')=='component_method' else d['events']
                    entry=next(x for x in members if x['name']==name)
                    count=len(b.findall('value')) if b.get('type')=='component_method' else len([k for k in m.attrib if k.startswith('param_name')])
                    self.assertEqual(count,len(entry['params']))
    def test_payload_and_logic_preserved(self):
        with zipfile.ZipFile(ROOT/'dist/Rail4K_0918_1.aia') as old,zipfile.ZipFile(ROOT/'dist/Rail4K_0919_1.aia') as new:
            self.assertEqual(old.namelist(),new.namelist())
            for n in old.namelist():
                if n.startswith('assets/'):self.assertEqual(old.read(n),new.read(n))
                if n.endswith('.bky'):self.assertEqual(old.read(n).replace(b'component_type="rail4k.local.LocalFiles"',b'component_type="LocalFiles"'),new.read(n))

if __name__=='__main__':unittest.main(verbosity=2)
