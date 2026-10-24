from 制谱器 import *

def main():
    设计 = 界面()
    程序()
    with zipfile.ZipFile(ROOT / 'Rail4K_0910.aia') as 原包:
        原文件 = {n: 原包.read(n) for n in 原包.namelist()}
    源名 = next(n for n in 原文件 if n.endswith('.scm'))
    积木 = ET.Element('xml', xmlns='http://www.w3.org/1999/xhtml')
    积木.extend(TOP)
    for 序号, 节点 in enumerate(积木.iter('block'), 1): 节点.set('id', f'制谱_{序号}')
    ET.SubElement(积木, 'yacodeblocks', {'ya-version': '237', 'language-version': '39'})
    ET.indent(积木, space='  ')
    原文件[源名] = ('#|\n$JSON\n' + json.dumps(设计, ensure_ascii=False, separators=(',', ':')) + '\n|#\n').encode()
    原文件[源名[:-4] + '.bky'] = ET.tostring(积木, encoding='utf-8')
    原文件['youngandroidproject/project.properties'] = ('source=../src\nname=Rail4K_0905\nmain=appinventor.ai_me.Rail4K_0905.Screen1\nassets=../assets\nbuild=../build\nsizing=Responsive\ntheme=AppTheme.Light\nshowlistsasjson=True\nuseslocation=False\naname=定轨四键\nactionbar=False\nversioncode=5\nversionname=0.5.0\n').encode()
    素材 = ROOT / 'music'
    素材.mkdir(exist_ok=True)
    for 文件 in 素材.iterdir():
        if 文件.is_file() and 文件.suffix.lower() in ['.mp3', '.wav', '.ogg', '.m4a', '.aac']:
            原文件['assets/' + 文件.name] = 文件.read_bytes()
    目录 = ROOT / 'native/Rail4K_Editor'
    导出 = ROOT / 'dist/Rail4K_Editor_v1.aia'
    with zipfile.ZipFile(导出, 'w', zipfile.ZIP_DEFLATED) as 包:
        for 名, 内容 in sorted(原文件.items()):
            文件 = 目录 / 名
            文件.parent.mkdir(parents=True, exist_ok=True)
            文件.write_bytes(内容)
            条目 = zipfile.ZipInfo(名, (2026, 9, 11, 0, 0, 0))
            条目.compress_type = zipfile.ZIP_DEFLATED
            包.writestr(条目, 内容)
    报告 = dict(version='0.5.0', input='Rail4K_0910.aia', output=str(导出), components=len(TYPES),
        globals=sum(b.get('type') == 'global_declaration' for b in TOP), procedures=list(PROCS),
        blocks=len(list(积木.iter('block'))), events=sum(b.get('type') == 'component_event' for b in TOP),
        comments=len(list(积木.iter('comment'))), sha256=hashlib.sha256(导出.read_bytes()).hexdigest())
    (ROOT / 'docs/制谱版构建报告.json').write_text(json.dumps(报告, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(报告, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
