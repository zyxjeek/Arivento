from pathlib import Path
import hashlib, json, subprocess, urllib.request, zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'extensions/localfiles'
TYPE = 'rail4k.local.LocalFiles'

def main():
    deps = ROOT/'tools/_deps/localfiles'
    deps.mkdir(parents=True,exist_ok=True)
    for entry in json.loads((OUT/'dependencies.json').read_text(encoding='utf8')):
        path=deps/entry['name']
        if not path.exists():
            data=urllib.request.urlopen(entry['url']).read()
            if hashlib.sha256(data).hexdigest()!=entry['sha256']:raise ValueError(entry['name'])
            path.write_bytes(data)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError(entry['name'])
    subprocess.run(['javac','-encoding','UTF-8','-source','7','-target','7','-Xlint:-options','-proc:none','-cp',str(deps/'*'),'-d',str(OUT/'classes'),str(OUT/'src/rail4k/local/LocalFiles.java')],check=True)
    dest = OUT/'package'/TYPE
    (dest/'files').mkdir(parents=True,exist_ok=True)
    jar = dest/'files/AndroidRuntime.jar'
    with zipfile.ZipFile(jar,'w',zipfile.ZIP_DEFLATED) as z:
        for p in (OUT/'classes').rglob('*.class'): z.write(p,p.relative_to(OUT/'classes').as_posix())
    subprocess.run(['java','-jar',str(deps/'dx.jar'),'--dex','--min-sdk-version=19','--output='+str(dest/'classes.jar'),str(jar)],check=True)
    def member(name,args): return dict(name=name,description='',deprecated='false',params=[dict(name=n,type='text') for n in args])
    meta=dict(categoryString='EXTENSION',dateBuilt='2026-09-24',nonVisible='true',iconName='',helpUrl='',type=TYPE,androidMinSdk=19,version='2',external='true',showOnPalette='true',name='LocalFiles',helpString='本地文件与四轨多点触摸',properties=[],blockProperties=[],methods=[member('选择音乐',[]),member('导入谱面',[]),member('保存谱面',['名称','内容']),member('启用多点',['画布'])],events=[member('音乐已选',['地址','名称']),member('谱面已读',['内容','名称']),member('谱面已保存',['名称']),member('取消',[]),member('出错',['消息']),member('轨道按下',['轨道','触点数'])])
    meta['methods'][-1]['params'][0]['type']='component'
    for p in meta['events'][-1]['params']:p['type']='number'
    build=dict(type=TYPE,assets=[],native=[],permissions=[],activities=[],broadcastReceivers=[],broadcastReceiver=[],libraries=[],androidMinSdk=['19'])
    for n,data in [('components.json',[meta]),('component.json',meta),('files/component_build_infos.json',[build]),('files/component_build_info.json',build)]:
        (dest/n).write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf8')
    (dest/'extension.properties').write_text('type=external\n',encoding='utf8')
    with zipfile.ZipFile(OUT/'本地文件.aix','w',zipfile.ZIP_DEFLATED) as z:
        for p in dest.rglob('*'):
            if p.is_file(): z.write(p,p.relative_to(dest.parent).as_posix())
    print(OUT/'本地文件.aix')

if __name__=='__main__': main()
