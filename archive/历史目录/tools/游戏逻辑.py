"""定轨四键：原生积木源程序。固定 60 键，1 秒间隔，判定 80/160ms。"""
from 积木工具 import *

背景, 白色, 青色 = '&HFF0B1020', '&HFFEAF2FF', '&HFF56DEEF'
def 色值(颜色): return int(颜色[2:], 16) - 2**32
def 选择(条件, 是, 否):
    return block('controls_choose', values={'TEST': 条件, 'THENRETURN': 是, 'ELSERETURN': 否})
def 目标(序号): return sub(mul(序号, 1000), 500)
def 时间(): return method('时钟', 'SystemTime')
def 文字(名称, 内容): return prop(名称, 'Text', 内容)
def 画线(*坐标): return method('画布', 'DrawLine', *坐标)
def 画字(内容, 纵坐标): return method('画布', 'DrawText', 内容, mul(g('轨宽'), 2), 纵坐标)
def 画笔(颜色): return prop('画布', 'PaintColor', 色值(颜色))
def 线宽(宽度): return prop('画布', 'LineWidth', 宽度)
def 标签(名称, 内容, 字号=16):
    return component(名称, 'Label', 5, Text=内容, Width=-2, FontSize=字号, TextColor=白色, TextAlignment=1)
def 按钮(名称, 内容, 宽度=-2):
    return component(名称, 'Button', 7, Text=内容, Width=宽度, Height=48,
                     BackgroundColor='&HFF151E32', TextColor=白色, FontSize=16, ShowFeedback='False')
def 布局(名称, 子项, 横排=False, **属性):
    return component(名称, 'HorizontalArrangement' if 横排 else 'VerticalArrangement', 4,
                     子项, Width=-2, **属性)


def 界面():
    首页 = 布局('首页', [标签('标题', '定轨四键', 24), 按钮('开始', '开始')], Height=-2, AlignVertical=2)
    信息 = 标签('信息', '准确率 100.00%\n连击 0   最高 0')
    信息['Height'] = '-1012'
    重开 = 按钮('重开', '重开')
    重开['Height'] = '-1008'
    游戏 = 布局('游戏', [信息,
        component('画布', 'Canvas', 15,
            Width=-2, Height=-1080, BackgroundColor=背景, TextAlignment=1, FontSize=22), 重开,
    ], Height=-2, Visible='False')
    主屏 = component('Screen1', 'Form', 30, [首页, 游戏,
        component('时钟', 'Clock', 4, TimerInterval=16, TimerEnabled='False', TimerAlwaysFires='True')],
        AppName='定轨四键', Title='定轨四键', BackgroundColor=背景, ScreenOrientation='portrait',
        Sizing='Responsive', Scrollable='False', TitleVisible='False', ShowStatusBar='False',
        ActionBar='False', Theme='AppTheme.Light', VersionCode=4, VersionName='0.4.0')
    主屏['Uuid'] = '0'
    return {'authURL': ['ai2.appinventor.mit.edu'], 'YaVersion': '219', 'Source': 'Form', 'Properties': 主屏}


def 程序():
    初值 = dict(状态=0, 起点=0, 用时=-3000, 下一键=1, 完美=0, 良好=0, 漏击=0,
                连击=0, 最大连击=0, 准确率=100, 判定=1, 提示截止=-3000, 轨宽=0, 判定线=0)
    for 名称, 数值 in {**初值, '谱面': make_list()}.items():
        top(block('global_declaration', {'NAME': 名称}, {'VALUE': 数值}), '')
    PROCS.update(开局=[], 统计=[], 记录判定=['结果'], 走时=[], 按轨=['轨道'], 绘图=[], 返回首页=[])

    procedure('返回首页', [put('状态', 0), prop('时钟', 'TimerEnabled', False),
        prop('首页', 'Visible', True), prop('游戏', 'Visible', False), 文字('标题', '定轨四键')], '首页只保留标题与开始。')
    procedure('开局', [prop('首页', 'Visible', False), prop('游戏', 'Visible', True),
        *[put(名称, 初值[名称]) for 名称 in ['用时', '下一键', '完美', '良好', '漏击', '连击', '最大连击', '提示截止']],
        put('谱面', make_list()), loop('序号', 1, 60, [block('lists_add_items',
            values={'LIST': g('谱面'), 'ITEM0': block('math_random_int', values={'FROM': 1, 'TO': 4})}, mutation=mut(items=1))]),
        put('起点', add(时间(), 3000)), put('状态', 1),
        prop('时钟', 'TimerEnabled', True), call('统计'), call('绘图'),
    ], '准备3秒；随机60键，目标时间0.5、1.5…59.5秒。')

    procedure('统计', [put('准确率', 选择(compare('GT', g('下一键'), 1),
        div(add(mul(g('完美'), 100), mul(g('良好'), 65)), sub(g('下一键'), 1)), 100)),
        文字('信息', join('准确率 ', decimal(g('准确率')),
            '%\n连击 ', g('连击'), '   最高 ', g('最大连击'))),
    ], '只统计准确率和连击。Perfect权重100、Good权重65、Miss权重0；分母为已判定数。')

    procedure('记录判定', [
        iff(compare('EQ', get('结果'), 0), [change('漏击'), put('连击', 0)], [
            change('连击'), iff(compare('EQ', get('结果'), 2), [change('完美')], [change('良好')])]),
        put('最大连击', maximum(g('最大连击'), g('连击'))), put('判定', add(get('结果'), 1)),
        put('提示截止', add(g('用时'), 550)), change('下一键'), call('统计'),
    ], '结果0=Miss，1=Good，2=Perfect。命中续连；Miss断连；每键仅记一次。')

    procedure('走时', [iff(compare('EQ', g('状态'), 1), [
            put('用时', maximum(g('用时'), sub(时间(), g('起点')))),
            block('controls_while', values={'TEST': both(compare('LTE', g('下一键'), 60),
                compare('GT', g('用时'), add(目标(g('下一键')), 160)))}, statements={'DO': [call('记录判定', 0)]}),
            iff(compare('GTE', g('用时'), 60000), [put('状态', 3), prop('时钟', 'TimerEnabled', False),
                prop('首页', 'Visible', True), prop('游戏', 'Visible', False),
                文字('标题', join('准确率 ', decimal(g('准确率')),
                    '%\nPerfect ', g('完美'), '   Good ', g('良好'), '\nMiss ', g('漏击'), '   最高连击 ', g('最大连击'))),
            ]),
    ])], '真实时间推进，不暂停；切后台仍计入一分钟，返回后补齐超时Miss。时钟回拨时不倒退。')

    procedure('按轨', [call('走时'), iff(both(compare('EQ', g('状态'), 1), compare('LTE', g('下一键'), 60)), [
        local('误差', unary('ABS', sub(g('用时'), 目标(g('下一键')))), [
            iff(both(compare('EQ', get('轨道'), item(g('谱面'), g('下一键'))), compare('LTE', get('误差'), 160)),
                [call('记录判定', 选择(compare('LTE', get('误差'), 80), 2, 1))])]), call('绘图')
    ])], '垂直判定：同一竖直轨道内点击高度不限，只看横向轨道与时间误差。')

    procedure('绘图', [iff(both(compare('GT', prop('画布', 'Width', read=True), 32),
                                  compare('GT', prop('画布', 'Height', read=True), 32)), [
        put('轨宽', div(prop('画布', 'Width', read=True), 4)),
        put('判定线', mul(prop('画布', 'Height', read=True), 0.85)), method('画布', 'Clear'),
        画笔('&HFF29334A'), 线宽(1), loop('轨号', 1, 3, [
            画线(mul(get('轨号'), g('轨宽')), 0, mul(get('轨号'), g('轨宽')), prop('画布', 'Height', read=True))]),
        画笔(白色), 线宽(3), 画线(0, g('判定线'), mul(g('轨宽'), 4), g('判定线')),
        画笔(青色), 线宽(16),
        loop('键号', g('下一键'), minimum(60, add(g('下一键'), 1)), [
            local('纵位', sub(g('判定线'), div(mul(sub(目标(get('键号')), g('用时')), g('判定线')), 1500)), [
                iff(both(compare('GTE', get('纵位'), 0), compare('LTE', get('纵位'), prop('画布', 'Height', read=True))), [
                    local('横位', mul(sub(item(g('谱面'), get('键号')), 1), g('轨宽')), [
                        画线(add(get('横位'), 9), get('纵位'), sub(add(get('横位'), g('轨宽')), 9), get('纵位')),
                    ])
                ])
            ])
        ]),
        画笔(白色),
        画字(选择(compare('LT', g('用时'), 0), join('准备 ', unary('CEILING', div(sub(0, g('用时')), 1000))),
            选择(compare('LT', g('用时'), g('提示截止')), item(make_list('MISS', 'GOOD', 'PERFECT'), g('判定')), '')),
            mul(prop('画布', 'Height', read=True), 0.475)),
    ])], '顶部12%信息、中央80%画布、底部8%重开；判定位于整屏中央。画布未布局时等待下一帧。')

    for 名称 in ['开始', '重开']:
        event(名称, 'Click', [call('开局')], '')
    event('Screen1', 'BackPressed', [iff(compare('EQ', g('状态'), 0),
        [block('controls_closeApplication')], [call('返回首页')])], '返回直接结束本局回到首页，不提供暂停。')
    event('画布', 'TouchDown', [iff(compare('GT', prop('画布', 'Width', read=True), 0), [
        call('按轨', maximum(1, minimum(4, add(unary('FLOOR', div(mul(get('横坐标'), 4),
            prop('画布', 'Width', read=True))), 1))))])], '')
    TOP[-1].find('mutation').attrib.update(param_name0='横坐标', param_name1='纵坐标')
    event('时钟', 'Timer', [call('走时'), iff(compare('EQ', g('状态'), 1), [call('绘图')])], '')
