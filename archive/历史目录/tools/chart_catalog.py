from pathlib import Path
import argparse
import json
import zipfile

def valid(v):
    number=lambda x:type(x) in (int,float)
    if not isinstance(v,list) or len(v)!=8: return False
    if not all(isinstance(x,str) for x in v[:2]): return False
    if not all(number(v[i]) and v[i]>0 for i in [2,4,5,6]) or v[3] not in [1,2]: return False
    if not isinstance(v[7],list) or not v[7]: return False
    prev=0
    for n in v[7]:
        if not isinstance(n,list) or len(n)!=2 or n[0] not in [1,2,3,4] or not number(n[1]) or not prev<=n[1]<=v[6]-160: return False
        prev=n[1]
    return True

def main():
    p=argparse.ArgumentParser()
    p.add_argument('source',type=Path)
    p.add_argument('--output',type=Path,default=Path('chart_list.txt'))
    a=p.parse_args()
    if a.source.suffix.lower()=='.aia':
        with zipfile.ZipFile(a.source) as z: files={n[7:]:z.read(n) for n in z.namelist() if n.startswith('assets/') and n.lower().endswith(('.txt','.json'))}
    else: files={f.name:f.read_bytes() for f in a.source.iterdir() if f.is_file() and f.suffix.lower() in ['.txt','.json']}
    names=[]
    for n,data in sorted(files.items()):
        if n in ['chart_list.txt','music_list.txt']: continue
        try:
            if valid(json.loads(data.decode('utf-8'))): names.append(n)
            else: print('跳过无效谱面：'+n)
        except (ValueError,UnicodeError): print('跳过非 JSON 文本：'+n)
    a.output.write_text('\n'.join(names)+'\n',encoding='utf-8')
    print(f'{a.output}: {len(names)} 个谱面')

if __name__=='__main__': main()
