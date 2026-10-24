"""生成原生中文积木项目与AIA；仅依赖Python标准库。"""
from 游戏逻辑 import *


def main():
    SOURCE.mkdir(parents=True, exist_ok=True)
    设计 = 界面()
    程序()
    (SOURCE / 'Screen1.scm').write_text('#|\n$JSON\n' + json.dumps(设计, ensure_ascii=False, separators=(',', ':')) + '\n|#\n', encoding='utf-8', newline='\n')
    文档 = ET.Element('xml', xmlns='http://www.w3.org/1999/xhtml')
    文档.extend(TOP)
    ET.SubElement(文档, 'yacodeblocks', {'ya-version': '219', 'language-version': '34'})
    ET.indent(文档, space='  ')
    ET.ElementTree(文档).write(SOURCE / 'Screen1.bky', encoding='utf-8')
    属性目录 = PROJECT / 'youngandroidproject'
    属性目录.mkdir(exist_ok=True)
    属性 = dict(source='../src', name='Rail4K', main='appinventor.ai_me.Rail4K.Screen1',
        assets='../assets', build='../build', defaultfilescope='App', sizing='Responsive',
        theme='AppTheme.Light', showlistsasjson='True', useslocation='False', aname='定轨四键',
        actionbar='False', versioncode='4', versionname='0.4.0')
    (属性目录 / 'project.properties').write_text(''.join(f'{键}={值}\n' for 键, 值 in 属性.items()), encoding='utf-8', newline='\n')
    导出 = ROOT / 'dist/Rail4K_MVP.aia'
    with zipfile.ZipFile(导出, 'w', zipfile.ZIP_DEFLATED) as 包:
        for 文件 in sorted([*SOURCE.glob('Screen1.*'), 属性目录 / 'project.properties']):
            if 文件.is_file():
                条目 = zipfile.ZipInfo(文件.relative_to(PROJECT).as_posix(), (2026, 9, 5, 0, 0, 0))
                条目.compress_type = zipfile.ZIP_DEFLATED
                包.writestr(条目, 文件.read_bytes())
    (导出.parent / '定轨四键_精简中文版.aia').write_bytes(导出.read_bytes())
    (导出.parent / 'Rail4K_v0_4.aia').write_bytes(导出.read_bytes())
    报告 = dict(project='Rail4K', version='0.4.0', components=len(TYPES), blocks=len(list(文档.iter('block'))),
        globals=sum(节点.get('type') == 'global_declaration' for 节点 in TOP),
        top_level_stacks=len(TOP), procedures=list(PROCS), aia_bytes=导出.stat().st_size,
        sha256=hashlib.sha256(导出.read_bytes()).hexdigest())
    (ROOT / 'docs/build-manifest.json').write_text(json.dumps(报告, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(报告, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
