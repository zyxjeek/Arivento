from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse,json,re,shutil,zipfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'native/Rail4K_1011_1'
if (ROOT/'tools/current_release.json').exists():
    SOURCE=ROOT/'native'/json.loads((ROOT/'tools/current_release.json').read_text(encoding='utf-8'))['name']

def release(version=None,date=None):
    date=date or datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%m%d')
    dist=ROOT/'dist';archive=ROOT/'archive/releases'
    dist.mkdir(exist_ok=True);archive.mkdir(parents=True,exist_ok=True)
    used=[int(m[1]) for d in (dist,archive) for p in d.rglob('*.aia') if (m:=re.fullmatch('Arivento_'+date+r'_(\d+)\.aia',p.name))]
    version=version or max(used,default=0)+1
    name=f'Arivento_{date}_{version}'
    creator=f'AriventoCreator_{date}_{version}'
    assert not (dist/(name+'.aia')).exists() and not (archive/(name+'.aia')).exists(),'版本已存在'
    html=(ROOT/'web-editor/source.html').read_text(encoding='utf-8')
    assert 'max="5000"' in html and 'musicSource.start(startAudio' in html
    files={p.relative_to(SOURCE).as_posix():p.read_bytes() for p in SOURCE.rglob('*') if p.is_file()}
    for n,data in list(files.items()):
        if n.endswith('.scm'):
            d=json.loads(data.decode().split('$JSON')[1].rsplit('|#',1)[0])
            d['Properties']['AppName']='Arivento'
            def brand(c):
                for k in ('Text','Title','Hint'):
                    if isinstance(c.get(k),str):c[k]=c[k].replace('Rail4K','Arivento')
                for child in c.get('$Components',[]):brand(child)
            brand(d['Properties'])
            files[n]=('#|\n$JSON\n'+json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode()
        elif n.endswith('project.properties'):
            files[n]=re.sub(r'(?m)^name=.*','name='+name,data.decode()).encode()
    stage=ROOT/'native'/name
    stage.mkdir(exist_ok=False)
    for n,data in files.items():
        p=stage/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    aia=stage/(name+'.aia')
    with zipfile.ZipFile(aia,'x',zipfile.ZIP_DEFLATED) as z:
        for n,data in files.items():z.writestr(n,data)
    with zipfile.ZipFile(aia) as z:assert z.testzip() is None and sum(n.endswith('.scm') for n in z.namelist())==4
    for p in list(dist.iterdir()):
        if p.is_file() and p.suffix.lower() in ('.aia','.html','.zip'):
            dest=archive/p.name
            if dest.exists():dest=archive/(datetime.now().strftime('%Y%m%d%H%M%S')+'_'+p.name)
            shutil.move(str(p),str(dest))
    shutil.move(str(aia),str(dist/aia.name))
    (dist/(creator+'.html')).write_text(html,encoding='utf-8')
    (ROOT/'tools/current_release.json').write_text(json.dumps({'name':name},indent=2),encoding='utf-8')
    print(dist/(name+'.aia'));print(dist/(creator+'.html'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--version',type=int);p.add_argument('--date');a=p.parse_args();release(a.version,a.date)
