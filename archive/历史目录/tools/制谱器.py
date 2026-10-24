from 积木工具 import *
import copy

背景, 白色, 青色 = '&HFF0B1020', '&HFFEAF2FF', '&HFF56DEEF'

def 取(名, 属性='Text'): return prop(名, 属性, read=True)
def 设(名, 值, 属性='Text'): return prop(名, 属性, 值)
def 等(甲, 乙): return compare('EQ', 甲, 乙)
def 非(条件): return block('logic_negate', values={'BOOL': 条件})
def 全(*条件):
    return 条件[0] if len(条件) == 1 else both(条件[0], 全(*条件[1:]))
def 选(条件, 是, 否): return block('controls_choose', values={'TEST': 条件, 'THENRETURN': 是, 'ELSERETURN': 否})
def 长(表): return block('lists_length', values={'LIST': 表})
def 列表(值): return block('lists_is_list', values={'ITEM': 值})
def 数字(值): return block('math_is_a_number', {'OP': 'NUMBER'}, {'NUM': 值})
def 文本(值): return block('text_is_string', values={'ITEM': 值})
def 正数(值): return 全(数字(copy.deepcopy(值)), compare('GT', 值, 0))
def 修剪(值): return block('text_trim', values={'TEXT': 值})
def 包含(表, 值): return block('lists_is_in', values={'LIST': 表, 'ITEM': 值})
def 添(表, 值): return block('lists_add_items', values={'LIST': 表, 'ITEM0': 值}, mutation=mut(items=1))
def 改(表, 序号, 值): return block('lists_replace_item', values={'LIST': 表, 'NUM': 序号, 'ITEM': 值})
def 复本(表): return block('lists_copy', values={'LIST': 表})
def 遍历(名, 表, 内容): return block('controls_forEach', {'VAR': 名}, {'LIST': 表}, {'DO': 内容})
def 循环(条件, 内容): return block('controls_while', values={'TEST': 条件}, statements={'DO': 内容})
def 局设(名, 值): return block('lexical_variable_set', {'VAR': 名}, {'VALUE': 值})
def 时间(): return method('时钟', 'SystemTime')
def 时刻(序号): return item(item(g('谱面'), 序号), 2)
def 所在轨(序号): return item(item(g('谱面'), 序号), 1)
def 警告(内容): return method('提示', 'ShowAlert', 内容)
def 画线(*坐标): return method('画布', 'DrawLine', *坐标)
def 画笔(颜色): return 设('画布', int(颜色[2:], 16) - 2**32, 'PaintColor')
def 过程(名, 内容): procedure(名, 内容, '')
def 事件(名, 类, 内容, 参数=()):
    event(名, 类, 内容, '')
    TOP[-1].find('mutation').attrib.update({f'param_name{i}': v for i, v in enumerate(参数)})
def 闲时(内容): return iff(等(g('云请求'), ''), 内容, [警告('正在访问云端，请稍候')])
def 截面(名): return [设(n, n == 名, 'Visible') for n in ['首页', '设置', '游戏']]
def 封装(): return make_list(g('谱面名'), g('音乐名'), g('过屏时间'), g('模式'), g('速度'), g('单位'), g('结束时间'), 复本(g('谱面')))

def 按钮(名, 字, 类='Button', **属性):
    return component(名, 类, 10 if 类 == 'ListPicker' else 8, Text=字, Width=-2, Height=44,
        BackgroundColor='&HFF151E32', TextColor=白色, FontSize=16, **属性)
def 输入(名, 提示, 字='', 数=False):
    return component(名, 'TextBox', 15, Text=字, Hint=提示, NumbersOnly=str(数), MultiLine='False',
        Width=-2, Height=44, FontSize=16, BackgroundColor='&HFF151E32', TextColor=白色, HintColor='&HFF99AABB')
def 排列(名, 内容, 横=False, **属性):
    return component(名, 'HorizontalArrangement' if 横 else 'VerticalArrangement', 4, 内容, Width=-2, **属性)

def 界面():
    with zipfile.ZipFile(ROOT / 'Rail4K_0910.aia') as 包:
        字串 = 包.read(next(n for n in 包.namelist() if n.endswith('.scm'))).decode('utf-8')
    设计 = json.loads(字串.split('$JSON')[1].rsplit('|#', 1)[0])
    主屏 = 设计['Properties']
    def 注册(组件):
        TYPES[组件['$Name']] = 组件['$Type']
        for 子 in 组件.get('$Components', []): 注册(子)
    注册(主屏)
    首页, 游戏, 时钟 = 主屏['$Components']
    首页['$Components'] += [按钮('选谱', '选择谱面', 'ListPicker', ElementsFromString='测试', Selection='测试'),
        按钮('刷新', '刷新云端谱面'), 按钮('制谱', '制谱器'),
        component('云状态', 'Label', 6, Text='正在连接云端', Width=-2, TextColor=白色, TextAlignment=1)]
    设置 = 排列('设置', [
        component('设置标题', 'Label', 6, Text='制谱器', Width=-2, FontSize=24, TextColor=白色, TextAlignment=1),
        输入('名称输入', '谱面名称'),
        component('模式输入', 'Spinner', 2, ElementsFromString='自由模式,吸附模式', Width=-2, Height=44),
        component('音乐输入', 'Spinner', 2, ElementsFromString='无音乐', Width=-2, Height=44, Prompt='选择音乐'),
        输入('过屏输入', '过屏时间（毫秒）', '1000', True),
        排列('吸附设置', [输入('速度输入', 'BPM', '120', True), 输入('单位输入', '吸附单位', '4', True)], Visible='False'),
        按钮('录制', '开始录制'), 按钮('设置返回', '返回')], Height=-2, Visible='False')
    重开 = 游戏['$Components'].pop()
    重开.update(Width='-1025', Height='-2')
    操作 = 排列('操作', [重开,
        按钮('结束', '结束'),
        按钮('保存', '保存'), 按钮('返回', '返回')], 横=True, Height=-1008)
    for 子 in 操作['$Components']: 子.update(Width='-1025', Height='-2')
    游戏['$Components'].append(操作)
    主屏['$Components'] = [首页, 设置, 游戏, 时钟,
        component('音乐', 'Player', 8, Loop='False', PlayOnlyInForeground='False', Volume=100),
        component('文件', 'File', 4, DefaultScope='App'),
        component('云端', 'CloudDB', 2, ProjectID='Rail4K_Editor_0910', RedisServer='DEFAULT', RedisPort=6381, UseSSL='True'),
        component('提示', 'Notifier', 7),
        component('云时钟', 'Clock', 4, TimerInterval=20000, TimerEnabled='False', TimerAlwaysFires='True')]
    主屏.update(VersionCode='5', VersionName='0.5.0')
    return 设计

def 程序():
    初值 = dict(状态=0, 起点=0, 用时=-3000, 下一键=1, 完美=0, 良好=0, 漏击=0, 连击=0,
        最大连击=0, 准确率=100, 判定=1, 提示截止=-3000, 轨宽=0, 判定线=0, 物量=0,
        间隔时间=200, 过屏时间=1000, 谱面名='测试', 音乐名='', 模式=1, 速度=120, 单位=4,
        基准=-1, 结束时间=61000, 已播放=False, 云请求='', 请求名称='', 有效=True)
    for 名, 值 in {**初值, '谱面': make_list(), '判定表': make_list(), '当前谱': make_list(), '测试谱': make_list(), '待保存': make_list()}.items():
        top(block('global_declaration', {'NAME': 名}, {'VALUE': 值}), '')
    PROCS.update(返回首页=[], 创建测试=[], 读取当前谱=[], 开局=[], 入场=['用途'], 统计=[], 记录判定=['键号', '结果'],
        走时=[], 按轨=['轨道'], 录入=['轨道'], 绘图=[], 完成录制=[], 打开设置=[], 检查设置=[], 请求=['操作名', '名称'],
        请求结束=[], 请求失败=['消息'], 检查谱面=['数据'], 写入=[])

    过程('返回首页', [put('状态', 0), 设('时钟', False, 'TimerEnabled'), method('音乐', 'Stop'),
        *截面('首页'), 设('标题', join('定轨四键\n', item(g('当前谱'), 1)))])
    过程('创建测试', [put('谱面', make_list()), put('物量', 300), put('间隔时间', 200), put('过屏时间', 1000),
        loop('序号', 1, g('物量'), [添(g('谱面'), make_list(block('math_random_int', values={'FROM': 1, 'TO': 4}), add(500, mul(get('序号'), g('间隔时间')))))]),
        put('测试谱', make_list('测试', '', 1000, 1, 120, 4, 61000, 复本(g('谱面')))), put('当前谱', 复本(g('测试谱')))])
    过程('读取当前谱', [*[put(名, item(g('当前谱'), i)) for i, 名 in enumerate(['谱面名', '音乐名', '过屏时间', '模式', '速度', '单位', '结束时间'], 1)],
        put('谱面', 复本(item(g('当前谱'), 8))), put('物量', 长(g('谱面')))])
    过程('开局', [闲时([call('读取当前谱'), call('入场', 1)])])
    过程('入场', [iff(either(等(g('音乐名'), ''), 包含(取('音乐输入', 'Elements'), g('音乐名'))), [
        method('音乐', 'Stop'), put('状态', get('用途')), 设('音乐', g('音乐名'), 'Source'), iff(等(g('状态'), get('用途')), [
        *[put(n, v) for n, v in dict(用时=-3000, 下一键=1, 完美=0, 良好=0, 漏击=0, 连击=0, 最大连击=0, 提示截止=-3000, 已播放=False).items()],
        put('判定表', make_list()), loop('序号', 1, g('物量'), [添(g('判定表'), 0)]),
        put('状态', get('用途')), put('起点', add(时间(), 3000)), *截面('游戏'),
        设('结束', 等(g('状态'), 2), 'Visible'), 设('保存', False, 'Visible'), 设('重开', True, 'Visible'),
        设('时钟', True, 'TimerEnabled'), call('统计'), call('绘图')])], [警告('此版本应用没有谱面所用音乐，请开发者上传同名素材并重新打包')])])
    过程('统计', [put('准确率', 选(compare('GT', add(g('完美'), g('良好'), g('漏击')), 0),
        div(add(mul(100, g('完美')), mul(65, g('良好'))), add(g('完美'), g('良好'), g('漏击'))), 100)),
        设('信息', 选(either(等(g('状态'), 2), 等(g('状态'), 4)),
            join(g('谱面名'), ' · ', 选(等(g('模式'), 1), '自由模式', '吸附模式'), '\n已录入 ', g('物量'), ' 键'),
            join('准确率 ', decimal(g('准确率')), '%\n连击 ', g('连击'), '   最高 ', g('最大连击'))))])
    过程('记录判定', [改(g('判定表'), get('键号'), get('结果')),
        iff(等(get('结果'), 1), [change('漏击'), put('连击', 0)], [change('连击'), iff(等(get('结果'), 3), [change('完美')], [change('良好')])]),
        put('最大连击', maximum(g('最大连击'), g('连击'))), put('判定', get('结果')), put('提示截止', add(g('用时'), 550)),
        循环(全(compare('LTE', g('下一键'), g('物量')), 非(等(item(g('判定表'), g('下一键')), 0))), [change('下一键')]), call('统计')])
    过程('走时', [iff(either(等(g('状态'), 1), 等(g('状态'), 2)), [
        put('用时', maximum(g('用时'), sub(时间(), g('起点')))),
        iff(全(compare('GTE', g('用时'), 0), 非(g('已播放'))), [
            iff(非(等(g('音乐名'), '')), [method('音乐', 'Start')]), put('起点', 时间()), put('用时', 0), put('已播放', True)]),
        iff(等(g('状态'), 1), [
            循环(全(compare('LTE', g('下一键'), g('物量')), compare('GT', g('用时'), add(时刻(g('下一键')), 160))), [call('记录判定', g('下一键'), 1)]),
            iff(compare('GTE', g('用时'), g('结束时间')), [put('状态', 3), 设('时钟', False, 'TimerEnabled'), method('音乐', 'Stop'), *截面('首页'),
                设('标题', join(g('谱面名'), '\n准确率 ', decimal(g('准确率')), '%\nPerfect ', g('完美'), '   Good ', g('良好'), '\nMiss ', g('漏击'), '   最高连击 ', g('最大连击')))])
        ], [循环(全(compare('LTE', g('下一键'), g('物量')), compare('LT', 时刻(g('下一键')), sub(g('用时'), g('过屏时间')))), [change('下一键')])])
    ])])
    过程('按轨', [call('走时'), iff(等(g('状态'), 1), [local('序号', g('下一键'), [local('命中号', 0, [
        循环(全(compare('LTE', get('序号'), g('物量')), 等(get('命中号'), 0), compare('LTE', 时刻(get('序号')), add(g('用时'), 160))), [
            iff(全(等(item(g('判定表'), get('序号')), 0), 等(所在轨(get('序号')), get('轨道'))), [局设('命中号', get('序号'))]),
            局设('序号', add(get('序号'), 1))]),
        iff(compare('GT', get('命中号'), 0), [call('记录判定', get('命中号'), 选(compare('LTE', unary('ABS', sub(g('用时'), 时刻(get('命中号')))), 80), 3, 2))])
    ])]), call('绘图')])])
    过程('录入', [call('走时'), iff(全(等(g('状态'), 2), compare('GTE', g('用时'), 0)), [
        iff(等(g('基准'), -1), [put('基准', g('用时'))]),
        local('目标时间', 选(等(g('模式'), 1), g('用时'), add(g('基准'), mul(unary('FLOOR', add(div(sub(g('用时'), g('基准')), g('间隔时间')), 0.5)), g('间隔时间')))), [
            local('新键', make_list(get('轨道'), get('目标时间')), [iff(非(包含(g('谱面'), get('新键'))), [添(g('谱面'), get('新键')), change('物量')])])]),
        call('统计'), call('绘图')])])
    过程('绘图', [iff(全(compare('GT', 取('画布', 'Width'), 32), compare('GT', 取('画布', 'Height'), 32)), [
        put('轨宽', div(取('画布', 'Width'), 4)), put('判定线', mul(取('画布', 'Height'), 0.85)), method('画布', 'Clear'),
        画笔('&HFF29334A'), 设('画布', 1, 'LineWidth'), loop('轨号', 1, 3, [画线(mul(get('轨号'), g('轨宽')), 0, mul(get('轨号'), g('轨宽')), 取('画布', 'Height'))]),
        画笔(白色), 设('画布', 3, 'LineWidth'), 画线(0, g('判定线'), 取('画布', 'Width'), g('判定线')),
        画笔(青色), 设('画布', 16, 'LineWidth'), local('键号', g('下一键'), [
            循环(全(compare('LTE', get('键号'), g('物量')), compare('LTE', 时刻(get('键号')), add(g('用时'), g('过屏时间')))), [
                iff(either(非(等(g('状态'), 1)), 等(item(g('判定表'), get('键号')), 0)), [
                    local('纵位', sub(g('判定线'), div(mul(sub(时刻(get('键号')), g('用时')), g('判定线')), g('过屏时间'))), [
                        iff(全(compare('GTE', get('纵位'), 0), compare('LTE', get('纵位'), 取('画布', 'Height'))), [
                            local('横位', mul(sub(所在轨(get('键号')), 1), g('轨宽')), [画线(add(get('横位'), 9), get('纵位'), sub(add(get('横位'), g('轨宽')), 9), get('纵位'))])])])]),
                局设('键号', add(get('键号'), 1))])]),
        画笔(白色), method('画布', 'DrawText',
            选(compare('LT', g('用时'), 0), join('准备 ', unary('CEILING', div(sub(0, g('用时')), 1000))),
                选(等(g('状态'), 2), '录制中', 选(等(g('状态'), 4), '录制完成',
                    选(compare('LT', g('用时'), g('提示截止')), item(make_list('MISS', 'GOOD', 'PERFECT'), g('判定')), '')))),
            mul(g('轨宽'), 2), mul(取('画布', 'Height'), 0.475))
    ])])
    过程('完成录制', [iff(等(g('状态'), 2), [
        put('用时', maximum(g('用时'), sub(时间(), g('起点')))),
        put('结束时间', maximum(maximum(0, g('用时')), 选(compare('GT', g('物量'), 0), add(时刻(g('物量')), 500), 0))),
        put('状态', 4), 设('时钟', False, 'TimerEnabled'), method('音乐', 'Stop'),
        设('结束', False, 'Visible'), 设('保存', True, 'Visible'), call('统计'), call('绘图')])])
    过程('打开设置', [闲时([call('返回首页'), *截面('设置')])])
    过程('检查设置', [闲时([
        iff(全(非(等(修剪(取('名称输入')), '')), 正数(取('过屏输入')),
            either(等(取('模式输入', 'SelectionIndex'), 1), 全(正数(取('速度输入')), 正数(取('单位输入'))))), [
            put('谱面名', 修剪(取('名称输入'))), put('音乐名', 选(等(取('音乐输入', 'Selection'), '无音乐'), '', 取('音乐输入', 'Selection'))),
            put('过屏时间', mul(取('过屏输入'), 1)), put('模式', 取('模式输入', 'SelectionIndex')),
            put('速度', 选(等(g('模式'), 1), 120, mul(取('速度输入'), 1))), put('单位', 选(等(g('模式'), 1), 4, mul(取('单位输入'), 1))),
            put('间隔时间', div(div(60000, g('速度')), g('单位'))), put('基准', -1), put('谱面', make_list()), put('物量', 0),
            method('名称输入', 'HideKeyboard'), call('入场', 2)
        ], [警告('请填写谱面名称、正数过屏时间；吸附模式还需要正数BPM和吸附单位')])
    ])])

    过程('请求', [put('云请求', get('操作名')), put('请求名称', get('名称')), 设('云时钟', False, 'TimerEnabled'), 设('云时钟', True, 'TimerEnabled'),
        设('云状态', '正在访问云端'), method('云端', 'GetValue', get('名称'), make_list())])
    过程('请求结束', [put('云请求', ''), 设('云时钟', False, 'TimerEnabled')])
    过程('请求失败', [call('请求结束'), 设('云状态', join('云端失败：', get('消息'))), 警告(join('云端失败：', get('消息'), '；录制内容仍保留，可重试保存'))])
    过程('写入', [put('云请求', '写入'), 设('云时钟', False, 'TimerEnabled'), 设('云时钟', True, 'TimerEnabled'), method('云端', 'StoreValue', g('请求名称'), g('待保存'))])
    过程('检查谱面', [put('有效', False), iff(全(列表(get('数据')), 等(长(get('数据')), 8)), [
        iff(全(文本(item(get('数据'), 1)), 文本(item(get('数据'), 2)), 正数(item(get('数据'), 3)),
            包含(make_list(1, 2), item(get('数据'), 4)), 正数(item(get('数据'), 5)), 正数(item(get('数据'), 6)),
            正数(item(get('数据'), 7)), 列表(item(get('数据'), 8)), compare('GT', 长(item(get('数据'), 8)), 0)), [
            put('有效', True), local('前时', -1, [遍历('音符', item(get('数据'), 8), [
                iff(全(列表(get('音符')), 等(长(get('音符')), 2)), [
                    iff(全(包含(make_list(1, 2, 3, 4), item(get('音符'), 1)), 数字(item(get('音符'), 2)),
                        compare('GTE', item(get('音符'), 2), maximum(0, get('前时'))),
                        compare('LTE', add(item(get('音符'), 2), 160), item(get('数据'), 7))),
                        [局设('前时', item(get('音符'), 2))], [put('有效', False)])
                ], [put('有效', False)])])])
        ])
    ])])

    事件('Screen1', 'Initialize', [call('创建测试'), call('返回首页'),
        local('文件列表', method('文件', 'ListDirectory', block('helpers_dropdown', {'OPTION': 'Asset'}, mutation=mut(key='FileScope')), ''), [
            设('音乐输入', make_list('无音乐'), 'Elements'), 遍历('文件名', get('文件列表'), [
                local('小写名', block('text_changeCase', {'OP': 'DOWNCASE'}, {'TEXT': get('文件名')}), [
                    iff(compare('GTE', block('text_length', values={'VALUE': get('小写名')}), 4), [
                        iff(包含(make_list('.mp3', '.wav', '.ogg', '.m4a', '.aac'), block('text_segment', values={'TEXT': get('小写名'), 'START': sub(block('text_length', values={'VALUE': get('小写名')}), 3), 'LENGTH': 4})), [
                            local('音乐列表', 复本(取('音乐输入', 'Elements')), [添(get('音乐列表'), get('文件名')), 设('音乐输入', get('音乐列表'), 'Elements')])])])])])]),
        call('请求', '初始化', '测试')])
    事件('开始', 'Click', [call('开局')])
    事件('制谱', 'Click', [call('打开设置')])
    事件('录制', 'Click', [call('检查设置')])
    事件('模式输入', 'AfterSelecting', [设('吸附设置', 等(取('模式输入', 'SelectionIndex'), 2), 'Visible')], ['选择'])
    事件('设置返回', 'Click', [call('返回首页')])
    事件('重开', 'Click', [闲时([iff(等(g('状态'), 1), [call('开局')], [put('基准', -1), put('物量', 0), put('谱面', make_list()), call('入场', 2)])])])
    事件('结束', 'Click', [call('完成录制')])
    事件('保存', 'Click', [闲时([iff(compare('GT', g('物量'), 0), [put('待保存', 封装()), call('请求', '检查保存', g('谱面名'))], [警告('至少录入一个音符后才能保存')])])])
    事件('返回', 'Click', [闲时([call('返回首页')])])
    事件('Screen1', 'BackPressed', [闲时([call('返回首页')])])
    事件('时钟', 'Timer', [call('走时'), iff(either(等(g('状态'), 1), 等(g('状态'), 2)), [call('绘图')])])
    事件('画布', 'TouchDown', [iff(compare('GT', 取('画布', 'Width'), 0), [
        local('轨道', maximum(1, minimum(4, add(unary('FLOOR', div(mul(get('横坐标'), 4), 取('画布', 'Width'))), 1))), [
            iff(等(g('状态'), 2), [call('录入', get('轨道'))], [call('按轨', get('轨道'))])])])], ['横坐标', '纵坐标'])
    事件('音乐', 'Completed', [call('完成录制')])
    事件('Screen1', 'ErrorOccurred', [iff(等(get('组件'), block('component_component_block', {'COMPONENT_SELECTOR': '音乐'}, mutation=mut(component_type='Player', instance_name='音乐'))), [
        iff(等(g('状态'), 2), [call('完成录制')], [call('返回首页')]), 警告(join('音乐无法播放：', get('消息')))
    ], [警告(get('消息'))])], ['组件', '函数', '编号', '消息'])
    事件('刷新', 'Click', [闲时([call('请求', '刷新', '测试')])])
    事件('选谱', 'AfterPicking', [闲时([call('请求', '选谱', 取('选谱', 'Selection'))])])
    事件('云时钟', 'Timer', [call('请求失败', '连接超时')])
    事件('云端', 'CloudDBError', [call('请求失败', get('消息'))], ['消息'])
    事件('云端', 'TagList', [local('名称表', get('值'), [iff(非(包含(get('名称表'), '测试')), [添(get('名称表'), '测试')]), 设('选谱', get('名称表'), 'Elements')])], ['值'])
    事件('云端', 'GotValue', [iff(全(非(等(g('云请求'), '')), 等(get('标签'), g('请求名称'))), [
        iff(either(等(g('云请求'), '初始化'), 等(g('云请求'), '刷新')), [
            iff(等(get('值'), make_list()), [put('待保存', 复本(g('测试谱'))), put('请求名称', '测试'), put('云请求', '初始化写入'),
                method('云端', 'StoreValue', '测试', g('待保存'))], [
                iff(等(g('云请求'), '初始化'), [call('检查谱面', get('值')), iff(g('有效'), [put('当前谱', get('值')), call('返回首页')])]),
                call('请求结束'), 设('云状态', '云端已连接'), method('云端', 'GetTagList')])
        ], [iff(等(g('云请求'), '选谱'), [
            call('检查谱面', get('值')), iff(g('有效'), [put('当前谱', get('值')), call('返回首页'), 设('云状态', '已加载云端谱面')], [警告('谱面不存在或数据格式不正确')]), call('请求结束')
        ], [iff(等(g('云请求'), '检查保存'), [
            iff(等(get('值'), make_list()), [call('写入')], [put('云请求', '等待覆盖'), 设('云时钟', False, 'TimerEnabled'),
                method('提示', 'ShowChooseDialog', '同名谱面已存在，是否覆盖？', g('谱面名'), '覆盖', '取消', False)])
        ])])])
    ])], ['标签', '值'])
    事件('提示', 'AfterChoosing', [iff(等(g('云请求'), '等待覆盖'), [iff(等(get('选择'), '覆盖'), [call('写入')], [call('请求结束')])])], ['选择'])
    事件('云端', 'UpdateDone', [iff(全(等(get('标签'), g('请求名称')), 等(get('操作'), 'StoreValue'),
        either(等(g('云请求'), '写入'), 等(g('云请求'), '初始化写入'))), [
        iff(等(g('云请求'), '写入'), [put('当前谱', 复本(g('待保存'))), call('返回首页'), 警告('谱面已保存到云端')]),
        call('请求结束'), 设('云状态', '已保存到云端'), method('云端', 'GetTagList')
    ])], ['标签', '操作'])
