"""按最终AIA绘图命令生成布局核对图，非Android真机截图。"""
from pathlib import Path
import sys, zipfile, io
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
from bky_runtime import Runtime, ROOT, AIA
from PIL import Image, ImageDraw, ImageFont

运行 = Runtime(width=360, height=576)
运行.start()
运行.hit(1)
图 = Image.new('RGB', (360, 720), '#0B1020')
画布 = Image.new('RGB', (360, 576), '#0B1020')
画 = ImageDraw.Draw(画布)
字体 = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 22)
颜色 = lambda 值: f'#{值 & 0xffffff:06x}'
for 线 in 运行.draws:
    画.line(tuple(线['args']), fill=颜色(线['color']), width=round(线['width']))
for 字 in 运行.text_draws:
    if 字['text']: 画.text((字['x'], 字['y']), str(字['text']), fill=颜色(字['color']), font=字体, anchor='ms')
图.paste(画布, (0, 86))
画 = ImageDraw.Draw(图)
小字 = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 16)
画.multiline_text((180, 38), 运行.components['信息']['Text'], fill='#EAF2FF', font=小字, anchor='mm', align='center', spacing=8)
画.rounded_rectangle((4, 666, 356, 716), radius=6, fill='#151E32')
画.text((180, 691), '重开', fill='#EAF2FF', font=小字, anchor='mm')
图.save(ROOT / 'docs/判定位置预览.png')
图.save(ROOT / 'docs/v0.4_界面预览.png')
