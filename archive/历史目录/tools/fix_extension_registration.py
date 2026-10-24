from pathlib import Path
import hashlib,json,re,zipfile,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'dist/Rail4K_0919_1.aia'

def main():
    source=ROOT/'dist/Rail4K_0918_1.aia'
    raw=source.read_bytes()
    backup=ROOT/('original/0918_1_'+hashlib.sha256(raw).hexdigest()[:12]+'.aia')
    if not backup.exists():backup.write_bytes(raw)
    with zipfile.ZipFile(source) as z:files={n:z.read(n) for n in z.namelist()}
    for n,data in list(files.items()):
        if n.endswith('.scm'):
            d=json.loads(data.decode().split('$JSON')[1].rsplit('|#',1)[0])
            def fix(c):
                if c['$Type']=='rail4k.local.LocalFiles':c['$Type']='LocalFiles'
                for x in c.get('$Components',[]):fix(x)
            fix(d['Properties']);d['Properties'].update(VersionCode='18',VersionName='0919.1')
            files[n]=('#|\n$JSON\n'+json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode()
        elif n.endswith('.bky'):
            files[n]=data.replace(b'component_type="rail4k.local.LocalFiles"',b'component_type="LocalFiles"')
        elif n.endswith('project.properties'):
            s=data.decode()
            for k,v in [('name','Rail4K_0919_1'),('versioncode','18'),('versionname','0919.1')]:s=re.sub(r'(?m)^'+k+r'=.*',k+'='+v,s)
            files[n]=s.encode()
    with zipfile.ZipFile(TARGET,'w',zipfile.ZIP_DEFLATED) as z:
        for n,data in files.items():
            z.writestr(n,data)
            p=ROOT/'native/Rail4K_0919_1'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    print(TARGET)

if __name__=='__main__':main()
