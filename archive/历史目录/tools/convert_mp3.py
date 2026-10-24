from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/_deps'))
import imageio_ffmpeg

def digest(p):
    with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    source=ROOT/'Phigros_Music_3.20.0'
    target=ROOT/'Phigros_Music_3.20.0_MP3'
    files=sorted(source.rglob('*.ogg'))
    target.mkdir(exist_ok=True)
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    def run(args):
        p=subprocess.run([ffmpeg,'-hide_banner','-nostdin','-v','error',*args],capture_output=True,text=True,encoding='utf-8',errors='replace')
        if p.returncode: raise RuntimeError(p.stderr.strip())
    def convert(src):
        dst=target/src.relative_to(source).with_suffix('.mp3')
        dst.parent.mkdir(parents=True,exist_ok=True)
        before=digest(src)
        run(['-n','-i',str(src),'-map','0:a:0','-vn','-c:a','libmp3lame','-q:a','2',str(dst)])
        run(['-xerror','-i',str(dst),'-map','0:a:0','-f','null','-'])
        after=digest(src)
        if before!=after: raise RuntimeError('Source changed: '+str(src))
        return {'source':src.relative_to(source).as_posix(),'output':dst.relative_to(target).as_posix(),'source_bytes':src.stat().st_size,'output_bytes':dst.stat().st_size,'source_sha256':before,'output_sha256':digest(dst),'decoded':True,'source_unchanged':True}
    start=time.time()
    results=[]
    errors=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(convert,f):f for f in files}
        for i,f in enumerate(as_completed(futures),1):
            try: results.append(f.result())
            except Exception as e: errors.append({'source':str(futures[f]),'error':str(e)})
            if i%20==0 or i==len(files): print(f'{i}/{len(files)} processed; {len(errors)} failed',flush=True)
    results.sort(key=lambda r:r['output'])
    if not errors:
        (target/'music_list.txt').write_text('\n'.join(r['output'] for r in results)+'\n',encoding='utf-8')
    report={'source':str(source),'target':str(target),'codec':'libmp3lame','quality':'VBR q=2','total':len(files),'converted':len(results),'seconds':round(time.time()-start,1),'output_bytes':sum(r['output_bytes'] for r in results),'errors':errors,'files':results}
    (ROOT/'docs/MP3转换报告.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='files'},ensure_ascii=False),flush=True)
    raise SystemExit(bool(errors))

if __name__=='__main__': main()
