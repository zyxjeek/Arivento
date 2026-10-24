from 制谱器 import *

OUT = ROOT / 'native/Rail4K_Multi'
PKG = 'src/appinventor/ai_me/Rail4K_0905/'

def opening(screen, value):
    return block('controls_openAnotherScreenWithStartValue', values={'SCREENNAME': screen, 'STARTVALUE': value})

def closing(value=''):
    return block('controls_closeScreenWithValue', values={'SCREEN': value})

def asset_list():
    return method('文件', 'ListDirectory', block('helpers_dropdown', {'OPTION': 'Asset'}, mutation=mut(key='FileScope')), '')

def field(b, name):
    return b.findtext(f"field[@name='{name}']", '')

def rewrite(parent, fn):
    for node in list(parent):
        if node.tag == 'block':
            replacement = fn(node)
            if replacement is not node:
                tail = node.find('next')
                parent.remove(node)
                if replacement is None:
                    if tail is not None: parent.append(tail[0])
                else:
                    if tail is not None: replacement.append(tail)
                    parent.append(replacement)
                rewrite(parent, fn)
                return
        rewrite(node, fn)

def main():
    design = 界面()
    程序()
    base = copy.deepcopy(TOP)
    components = {}
    def collect(c):
        components[c['$Name']] = c
        for child in c.get('$Components', []): collect(child)
    collect(design['Properties'])
    summary = {}
    for screen in ['Screen1', '制谱设置', '录制屏', '游玩屏']:
        TOP.clear()
        TOP.extend(copy.deepcopy(base))
        TYPES[screen] = 'Form'
        def replace_proc(name, body):
            TOP[:] = [b for b in TOP if not (b.get('type') == 'procedures_defnoreturn' and field(b, 'NAME') == name)]
            过程(name, body)
        def replace_event(name, event_name, body, args=()):
            TOP[:] = [b for b in TOP if not (b.get('type') == 'component_event' and b.find('mutation').get('instance_name') == name and b.find('mutation').get('event_name') == event_name)]
            事件(name, event_name, body, args)
        if screen == 'Screen1':
            names = ['首页', '云端', '云时钟', '提示']
            keep = {'开始', '制谱', '刷新', '选谱', '云端', '云时钟', '提示'}
            replace_proc('返回首页', [设('标题', join('定轨四键\n', item(g('当前谱'), 1)))])
            replace_proc('开局', [闲时([opening('游玩屏', g('当前谱'))])])
            replace_proc('打开设置', [闲时([opening('制谱设置', '')])])
            init = [call('创建测试'), call('返回首页'), call('请求', '初始化', '测试')]
        elif screen == '制谱设置':
            names = ['设置', '文件', '提示']
            keep = {'录制', '模式输入', '设置返回'}
            replace_proc('返回首页', [closing()])
            init_event = next(b for b in base if b.get('type') == 'component_event' and b.find('mutation').get('event_name') == 'Initialize')
            init = [copy.deepcopy(init_event.find('statement/block/next/block/next/block'))]
            init[0].remove(init[0].find('next'))
        else:
            names = ['游戏', '时钟', '音乐', '文件', '提示']
            keep = {'重开', '返回', '时钟', '画布'}
            if screen == '录制屏':
                names += ['云端', '云时钟', '云状态']
                keep |= {'结束', '保存', '音乐', '云端', '云时钟', '提示'}
            replace_proc('返回首页', [put('状态', 0), 设('时钟', False, 'TimerEnabled'), method('音乐', 'Stop'), closing(选(等(g('云请求'), '写入'), g('待保存'), ''))])
            init = [put('当前谱', block('controls_getStartValue')), call('读取当前谱')]
            if screen == '录制屏':
                init += [put('间隔时间', div(div(60000, g('速度')), g('单位'))), call('入场', 2)]
                replace_proc('统计', [设('信息', join(g('谱面名'), ' · ', 选(等(g('模式'), 1), '自由模式', '吸附模式'), '\n已录入 ', g('物量'), ' 键'))])
                replace_event('云端', 'GotValue', [iff(全(等(g('云请求'), '检查保存'), 等(get('标签'), g('请求名称'))), [iff(等(get('值'), make_list()), [call('写入')], [put('云请求', '等待覆盖'), 设('云时钟', False, 'TimerEnabled'), method('提示', 'ShowChooseDialog', '同名谱面已存在，是否覆盖？', g('谱面名'), '覆盖', '取消', False)])])], ['标签', '值'])
                replace_event('云端', 'UpdateDone', [iff(全(等(get('标签'), g('请求名称')), 等(get('操作'), 'StoreValue'), 等(g('云请求'), '写入')), [call('请求结束'), 设('时钟', False, 'TimerEnabled'), method('音乐', 'Stop'), closing(g('待保存'))])], ['标签', '操作'])
                TOP[:] = [b for b in TOP if not (b.get('type') == 'component_event' and b.find('mutation').get('event_name') == 'TagList')]
            else:
                init += [call('入场', 1)]
                replace_event('重开', 'Click', [call('读取当前谱'), call('入场', 1)])
            replace_event('画布', 'TouchDown', [iff(compare('GT', 取('画布', 'Width'), 0), [call('录入' if screen == '录制屏' else '按轨', maximum(1, minimum(4, add(unary('FLOOR', div(mul(get('横坐标'), 4), 取('画布', 'Width'))), 1))))])], ['横坐标', '纵坐标'])
        TOP[:] = [b for b in TOP if b.get('type') != 'component_event' or b.find('mutation').get('instance_name') in keep]
        事件(screen, 'Initialize', init)
        if screen != 'Screen1':
            事件(screen, 'BackPressed', [闲时([call('返回首页')])])
        if screen in ['Screen1', '制谱设置']:
            事件(screen, 'OtherScreenClosed', [iff(全(列表(get('返回值')), 等(长(get('返回值')), 8)), [put('当前谱', get('返回值')), call('返回首页'), 设('云状态', '谱面已保存到云端'), method('云端', 'GetTagList')] if screen == 'Screen1' else [closing(get('返回值'))])], ['屏幕名', '返回值'])
        if screen in ['录制屏', '游玩屏']:
            事件(screen, 'ErrorOccurred', ([call('完成录制')] if screen == '录制屏' else [设('时钟', False, 'TimerEnabled'), method('音乐', 'Stop'), put('状态', 3)]) + [警告(join('播放或运行失败：', get('消息')))], ['组件', '函数', '编号', '消息'])
        props = copy.deepcopy(design['Properties'])
        props.update({'$Name': screen, 'Title': '定轨四键' if screen == 'Screen1' else screen, 'VersionCode': '6', 'VersionName': '0.6.0', '$Components': [copy.deepcopy(components[n]) for n in names]})
        for c in props['$Components']:
            if c['$Name'] in ['游戏', '设置']: c['Visible'] = 'True'
        if screen == '游玩屏':
            buttons = props['$Components'][0]['$Components'][-1]['$Components']
            buttons[:] = [c for c in buttons if c['$Name'] in ['重开', '返回']]
            for c in buttons: c['Width'] = '-1050'
        if screen == '录制屏':
            props['$Components'][0]['Height'] = '-1094'
            props['$Components'][0]['$Components'][0]['Height'] = '-1010'
            props['$Components'][0]['$Components'][1]['Height'] = '-1076'
            next(c for c in props['$Components'] if c['$Name'] == '云状态')['Height'] = '-1006'
        present = set()
        def walk(c):
            present.add(c['$Name'])
            for child in c.get('$Components', []): walk(child)
        walk(props)
        def edit(b):
            t, m = b.get('type'), b.find('mutation')
            if screen == '录制屏':
                unused = ['完美', '良好', '漏击', '连击', '最大连击', '判定表']
                if t == 'lexical_variable_set' and field(b, 'VAR') in ['global ' + n for n in unused]: return None
                if t == 'controls_forRange' and b.findtext("statement/block/value[@name='LIST']/block/field[@name='VAR']") == 'global 判定表': return None
            if t == 'math_compare' and field(b, 'OP') == 'EQ' and b.findtext("value[@name='A']/block/field[@name='VAR']") == 'global 状态':
                number = b.findtext("value[@name='B']/block/field[@name='NUM']")
                if (screen == '录制屏' and number == '1') or (screen == '游玩屏' and number in ['2', '4']): return expr(False)
            if screen == '制谱设置' and t == 'procedures_callnoreturn' and field(b, 'PROCNAME') == '入场':
                return opening('录制屏', 封装())
            if screen == '录制屏' and t == 'procedures_callnoreturn' and field(b, 'PROCNAME') == '开局':
                return call('入场', 2)
            if t == 'component_set_get' and m.get('instance_name') == '音乐输入' and m.get('property_name') == 'Elements' and screen != '制谱设置':
                return asset_list()
            if t == 'component_set_get' and m.get('instance_name') == '标题' and screen == '游玩屏':
                m.set('instance_name', '信息')
                b.find("field[@name='COMPONENT_SELECTOR']").text = '信息'
            if t.startswith('component_') and m.get('instance_name') not in present:
                if t == 'component_set_get' and m.get('set_or_get') == 'set': return None
            return b
        xml = ET.Element('xml')
        xml.extend(TOP)
        rewrite(xml, edit)
        def simplify(b):
            t = b.get('type')
            if t in ['controls_if', 'controls_choose']:
                key = 'IF0' if t == 'controls_if' else 'TEST'
                val = b.findtext(f"value[@name='{key}']/block/field[@name='BOOL']")
                if val is not None:
                    chosen = b.find(("statement[@name='%s']/block" % ('DO0' if val == 'TRUE' else 'ELSE')) if t == 'controls_if' else ("value[@name='%s']/block" % ('THENRETURN' if val == 'TRUE' else 'ELSERETURN')))
                    if chosen is not None:
                        chosen = copy.deepcopy(chosen)
                        tail = b.find('next')
                        if tail is not None:
                            last = chosen
                            while last.find('next/block') is not None: last = last.find('next/block')
                            last.append(copy.deepcopy(tail))
                            b.remove(tail)
                    return chosen
            if t == 'logic_negate':
                val = b.findtext("value[@name='BOOL']/block/field[@name='BOOL']")
                if val is not None: return expr(val == 'FALSE')
            if t == 'logic_operation':
                a, c = [b.find(f"value[@name='{n}']/block") for n in ['A', 'B']]
                av, cv = [x.findtext("field[@name='BOOL']") for x in [a, c]]
                op = field(b, 'OP')
                if (op == 'OR' and 'TRUE' in [av, cv]) or (op == 'AND' and 'FALSE' in [av, cv]): return expr(op == 'OR')
                if av is not None: return copy.deepcopy(c)
                if cv is not None: return copy.deepcopy(a)
            return b
        for _ in range(4): rewrite(xml, simplify)
        procs = {field(b, 'NAME'): b for b in xml if b.get('type') == 'procedures_defnoreturn'}
        retained = [b for b in xml if b.get('type') == 'component_event']
        used = set()
        for b in retained:
            for callblock in b.iter('block'):
                if callblock.get('type') == 'procedures_callnoreturn':
                    name = field(callblock, 'PROCNAME')
                    if name not in used:
                        used.add(name)
                        retained.append(procs[name])
        globals_used = {f.text[7:] for b in retained for f in b.iter('field') if f.get('name') == 'VAR' and (f.text or '').startswith('global ')}
        retained = [b for b in xml if b.get('type') == 'global_declaration' and field(b, 'NAME') in globals_used] + retained
        xml[:] = retained
        xml.set('xmlns', 'http://www.w3.org/1999/xhtml')
        for i, b in enumerate(xml.iter('block')): b.set('id', f'{screen}_{i}')
        ET.SubElement(xml, 'yacodeblocks', {'ya-version': '237', 'language-version': '39'})
        ET.indent(xml, space='  ')
        folder = OUT / PKG
        folder.mkdir(parents=True, exist_ok=True)
        d = copy.deepcopy(design)
        d['Properties'] = props
        (folder / (screen + '.scm')).write_text('#|\n$JSON\n' + json.dumps(d, ensure_ascii=False, separators=(',', ':')) + '\n|#\n', encoding='utf-8')
        (folder / (screen + '.bky')).write_bytes(ET.tostring(xml, encoding='utf-8'))
        summary[screen] = dict(components=len(present), globals=len(globals_used), procedures=sorted(used), blocks=len(list(xml.iter('block'))))
    p = OUT / 'youngandroidproject/project.properties'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text((ROOT / 'native/Rail4K_Editor/youngandroidproject/project.properties').read_text(encoding='utf-8').replace('versioncode=5', 'versioncode=6').replace('versionname=0.5.0', 'versionname=0.6.0'), encoding='utf-8')
    music = sorted((ROOT / 'Phigros_Music_3.20.0').rglob('*.ogg'))
    assert len({p.name for p in music}) == len(music)
    manifest = []
    target = ROOT / 'dist/Rail4K_Multi_v2.aia'
    with zipfile.ZipFile(ROOT / 'dist/Rail4K_Multi_v2_CodeOnly.aia', 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(OUT.rglob('*')):
            if f.is_file(): z.write(f, f.relative_to(OUT).as_posix())
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(OUT.rglob('*')):
            if f.is_file(): z.write(f, f.relative_to(OUT).as_posix())
        for f in music:
            z.write(f, 'assets/' + f.name, compress_type=zipfile.ZIP_STORED)
            with f.open('rb') as stream:
                manifest.append(dict(file=f.name, bytes=f.stat().st_size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest()))
    report = dict(version='0.6.0', screens=summary, music_count=len(music), music_bytes=sum(f.stat().st_size for f in music), aia_bytes=target.stat().st_size, music=manifest)
    (ROOT / 'docs/多屏版构建报告.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'music'}, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
