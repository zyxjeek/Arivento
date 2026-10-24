from pathlib import Path
from collections import Counter
import json,re,hashlib,zipfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('D:/下载/TypingPractice/s')
OUT=ROOT/'charts/TypingPractice_Rail4K'
OUT.mkdir(parents=True,exist_ok=True)
rows=[]
for i in range(5):
    source=SOURCE/f'{i}.txt'
    raw=source.read_bytes()
    tokens=raw.decode('utf-8-sig').strip().split(',')
    assert all(re.fullmatch(r'\s*[1-4]:\d+\s*',x) for x in tokens),source
    notes=[list(map(int,x.strip().split(':'))) for x in tokens]
    assert len(notes)==len(set(map(tuple,notes))),source
    ordered=sorted(notes,key=lambda x:(x[1],x[0]))
    chart=[f'TypingPractice {i}','music.mp3',500,1,120,4,ordered[-1][1]+1000,ordered]
    target=OUT/f'{i}.txt'
    target.write_text(json.dumps(chart,ensure_ascii=False,separators=(',',':')),encoding='utf8')
    decoded=json.loads(target.read_text(encoding='utf8'))
    assert Counter(map(tuple,decoded[7]))==Counter(map(tuple,notes))
    chords=Counter(t for lane,t in notes)
    rows.append(dict(file=target.name,notes=len(notes),first_ms=ordered[0][1],last_ms=ordered[-1][1],end_ms=chart[6],max_chord=max(chords.values()),source_sha256=hashlib.sha256(raw).hexdigest()))
text='''# TypingPractice → Rail4K

五张谱面从 `轨道:毫秒时间` 转成 Rail4K 八项 JSON 数组，按时间及轨道排序，保留所有音符、原始时间和多押。原文件未修改。

在 Rail4K 中选择对应的 TXT，再选择原目录 `D:/下载/TypingPractice/s/music.mp3`。传到手机时需要把音乐另行传入；压缩包仅包含谱面和本说明。

源文件未提供谱面名称、BPM 和吸附单位，名称使用 TypingPractice 0～4，模式为自由模式（1），BPM 120 和单位 4 仅为兼容占位值，不表示测得的歌曲 BPM，不会参与游玩时的音符时间计算。

兼容字段过屏时间填 500ms，实际游玩速度由 Rail4K_1011_1 首页设置决定。结束时间设为末键之后 1000ms，保证判定和结算余量，不代表音频文件的总时长。没有添加或应用额外延迟。

| 文件 | 音符数 | 首键 / ms | 末键 / ms | 结束 / ms | 最大同时音符数 |
| --- | ---: | ---: | ---: | ---: | ---: |
'''
for r in rows:text+=f"| {r['file']} | {r['notes']} | {r['first_ms']} | {r['last_ms']} | {r['end_ms']} | {r['max_chord']} |\n"
(OUT/'说明.md').write_text(text,encoding='utf8')
(OUT/'转换记录.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
with zipfile.ZipFile(OUT.parent/'TypingPractice_Rail4K.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(OUT.iterdir()):
        if p.is_file():z.write(p,'TypingPractice_Rail4K/'+p.name)
print(json.dumps(rows,ensure_ascii=False,indent=2))
