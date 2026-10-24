from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys,urllib.error,urllib.parse,urllib.request,zipfile

ROOT=Path(__file__).resolve().parents[1]

def run(*args,capture=False):
    return subprocess.run(args,cwd=ROOT,check=True,text=True,encoding='utf-8',stdout=subprocess.PIPE if capture else None).stdout

def credentials():
    p=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',capture_output=True,text=True,check=True)
    values=dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
    return values['password']

def api(token,path,method='GET',data=None,content_type='application/json'):
    url=path if path.startswith('https://') else 'https://api.github.com'+path
    body=json.dumps(data).encode() if isinstance(data,dict) else data
    req=urllib.request.Request(url,data=body,method=method,headers={'Authorization':'Bearer '+token,'User-Agent':'Arivento-publisher','Accept':'application/vnd.github+json','Content-Type':content_type})
    with urllib.request.urlopen(req,timeout=120) as response:
        return json.load(response)

def current():
    return json.loads((ROOT/'tools/current_release.json').read_text(encoding='utf-8'))['name']

def sync_sources(name):
    p=ROOT/'.gitignore';s=p.read_text(encoding='utf-8')
    s=re.sub(r'(?s)# current-native-start\n.*?# current-native-end','# current-native-start\n!/native/'+name+'/\n# current-native-end',s)
    p.write_text(s,encoding='utf-8')
    tracked=run('git','ls-files','-z','--','native',capture=True).split('\0')
    stale=[p for p in tracked if p and not p.startswith('native/'+name+'/')]
    if stale:run('git','rm','--cached','--',*stale)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--repository',default='zyxjeek/Arivento')
    p.add_argument('--message',required=True)
    p.add_argument('--existing',action='store_true',help='发布当前版本，不生成新版本')
    args=p.parse_args()
    token=credentials()
    repo=api(token,'/repos/'+args.repository)
    origin=run('git','remote','get-url','origin',capture=True).strip()
    if origin not in [repo['clone_url'],repo['ssh_url']]:raise RuntimeError('origin 与目标仓库不一致')
    if not args.existing:run(sys.executable,'-B','-X','utf8','tools/release.py')
    name=current();aia=ROOT/'dist'/(name+'.aia');html=ROOT/'dist'/('AriventoCreator_'+name.removeprefix('Arivento_')+'.html')
    if args.existing:
        aia.parent.mkdir(exist_ok=True)
        if not aia.exists():
            source=ROOT/'native'/name
            with zipfile.ZipFile(aia,'x',zipfile.ZIP_DEFLATED) as z:
                for f in sorted(source.rglob('*')):
                    if f.is_file():z.writestr(f.relative_to(source).as_posix(),f.read_bytes())
        if not html.exists():html.write_bytes((ROOT/'web-editor/source.html').read_bytes())
    run(sys.executable,'-B','-X','utf8','tools/project.py','check')
    if html.read_bytes()!=(ROOT/'web-editor/source.html').read_bytes():raise RuntimeError('Creator 交付与源码不一致')
    run('node','--test','web-editor/tests/core.test.cjs','web-editor/tests/hold.test.cjs','web-editor/tests/pitch.test.cjs','web-editor/fix_1016/sync.test.cjs')
    run(sys.executable,'-B','-X','utf8','tests/run_current.py')
    sync_sources(name)
    run('git','add','-A')
    if run('git','diff','--cached','--name-only',capture=True).strip():run('git','commit','-m',args.message)
    sha=run('git','rev-parse','HEAD',capture=True).strip()
    run('git','push','-u','origin','main')
    tag='v'+name.removeprefix('Arivento_')
    try:target=api(token,'/repos/'+args.repository+'/git/ref/tags/'+urllib.parse.quote(tag,safe=''))['object']['sha']
    except urllib.error.HTTPError as e:
        if e.code!=404:raise
        target=api(token,'/repos/'+args.repository+'/git/refs','POST',{'ref':'refs/tags/'+tag,'sha':sha})['object']['sha']
    if target!=sha:raise RuntimeError('Release 标签已指向其他提交；请生成新版本')
    try:release=api(token,'/repos/'+args.repository+'/releases/tags/'+tag)
    except urllib.error.HTTPError as e:
        if e.code!=404:raise
        body='AIA 与离线单文件制谱器。\n\n验证：四屏静态检查、38 项网页回归、33 项当前 AIA 积木模拟通过。\n尚未完成本版本 APK 编译及真机验收。\n\n'+ '\n'.join(f'{f.name}: SHA-256 `{hashlib.sha256(f.read_bytes()).hexdigest()}`' for f in [aia,html])
        release=api(token,'/repos/'+args.repository+'/releases','POST',{'tag_name':tag,'target_commitish':sha,'name':name,'body':body,'draft':True})
    assets={a['name']:a for a in api(token,'/repos/'+args.repository+'/releases/'+str(release['id'])+'/assets')}
    for f in [aia,html]:
        digest='sha256:'+hashlib.sha256(f.read_bytes()).hexdigest()
        if f.name in assets:
            if assets[f.name].get('digest')!=digest:raise RuntimeError('已有附件哈希无法确认一致：'+f.name)
            continue
        api(token,release['upload_url'].split('{')[0]+'?name='+urllib.parse.quote(f.name),'POST',f.read_bytes(),'application/octet-stream')
    assets=api(token,'/repos/'+args.repository+'/releases/'+str(release['id'])+'/assets')
    for f in [aia,html]:
        a=next(a for a in assets if a['name']==f.name)
        if a['size']!=f.stat().st_size or a.get('digest')!='sha256:'+hashlib.sha256(f.read_bytes()).hexdigest():raise RuntimeError('附件校验失败：'+f.name)
    release=api(token,'/repos/'+args.repository+'/releases/'+str(release['id']),'PATCH',{'draft':False})
    print('COMMIT',sha);print('RELEASE',release['html_url'])

if __name__=='__main__':main()
