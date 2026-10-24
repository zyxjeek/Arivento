from build_ios_fix import music_names
from pathlib import Path
import argparse

p=argparse.ArgumentParser()
p.add_argument('source',type=Path)
p.add_argument('--output',type=Path,default=Path('music_list.txt'))
a=p.parse_args()
names=music_names(a.source)
a.output.write_text('\n'.join(names)+'\n',encoding='utf-8')
print(f'{len(names)} tracks: {a.output.resolve()}')
