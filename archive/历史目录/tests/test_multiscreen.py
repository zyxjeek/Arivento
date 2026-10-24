from multi_runtime import *
import unittest
import hashlib
import re

class Tests(unittest.TestCase):
    def runtime(self, screen='Screen1', start='', **kw):
        r = Runtime(screen=screen, start=start, **kw)
        r.initialize()
        return r

    def chart(self, notes=None, mode=1, music=''):
        return ['新谱面', music, 1000, mode, 120, 4, 4000, notes or [[1, 1000], [2, 2000]]]

    def recorder(self, mode=1):
        return self.runtime('录制屏', ['新谱面', '', 1000, mode, 120, 4, 61000, []])

    def test_structure(self):
        md = {c['name']:c for c in json.loads((ROOT/'reference/component-types.json').read_text(encoding='utf-8'))}
        for s in ['Screen1', '制谱设置', '录制屏', '游玩屏']:
            r = Runtime(screen=s)
            blocks = list(r.root.iter('block'))
            self.assertEqual(len(blocks), len({b.get('id') for b in blocks}))
            self.assertFalse(list(r.root.iter('comment')))
            for n in [*r.globals, *r.procedures]: self.assertRegex(n, r'^[\u4e00-\u9fff]+$')
            for b in blocks:
                t, m = b.get('type'), b.find('mutation')
                for f in b.findall('field'):
                    if f.get('name') in ['VAR', 'VAR0']:
                        self.assertRegex((f.text or '').removeprefix('global '), r'^[\u4e00-\u9fff]+$')
                        if (f.text or '').startswith('global '): self.assertIn(f.text[7:], r.globals)
                if t.startswith('component_'):
                    c = r.components[m.get('instance_name')]
                    self.assertEqual(c['$Type'], m.get('component_type'))
                    if t == 'component_method':
                        method = next(x for x in md[c['$Type']]['methods'] if x['name'] == m.get('method_name'))
                        self.assertEqual(len(method['params']), len(b.findall('value')))
                    if t == 'component_event':
                        event = next(x for x in md[c['$Type']]['events'] if x['name'] == m.get('event_name'))
                        params = [v for k,v in m.attrib.items() if k.startswith('param_name')]
                        self.assertEqual(len(params), len(event['params']))
                        for p in params: self.assertRegex(p, r'^[\u4e00-\u9fff]+$')
                if t == 'procedures_callnoreturn': self.assertIn(field(b, 'PROCNAME'), r.procedures)
        self.assertNotIn('记录判定', Runtime(screen='录制屏').procedures)
        self.assertNotIn('录入', Runtime(screen='游玩屏').procedures)

    def test_all_music_bytes(self):
        files = list((ROOT/'Phigros_Music_3.20.0').rglob('*.ogg'))
        with zipfile.ZipFile(AIA) as z:
            self.assertEqual(len(files), 322)
            self.assertEqual({n for n in z.namelist() if n.startswith('assets/')}, {'assets/'+p.name for p in files})
            for p in files:
                with p.open('rb') as f, z.open('assets/'+p.name) as a:
                    self.assertEqual(hashlib.file_digest(f, 'sha256').digest(), hashlib.file_digest(a, 'sha256').digest())

    def test_navigation(self):
        r = self.runtime()
        r.cloud_flush()
        r.event('开始', 'Click')
        self.assertEqual(r.opened, ('游玩屏', r.globals['当前谱']))
        r.event('制谱', 'Click')
        s = self.runtime(*r.opened, assets=['one.ogg', 'two.mp3', 'ignore.txt'])
        self.assertEqual(s.components['音乐输入']['Elements'], ['无音乐', 'one.ogg', 'two.mp3'])
        s.components['名称输入']['Text'] = '新谱面'
        s.components['音乐输入']['Selection'] = 'one.ogg'
        s.event('录制', 'Click')
        self.assertEqual(s.opened[0], '录制屏')
        self.assertEqual(s.opened[1][:4], ['新谱面', 'one.ogg', 1000, 1])
        q = self.runtime(*s.opened, assets=['one.ogg'], cloud=r.cloud)
        q.note(1, 1010)
        q.event('结束', 'Click')
        q.event('保存', 'Click')
        q.cloud_step()
        self.assertFalse(q.closed)
        q.cloud_step()
        self.assertTrue(q.closed)
        self.assertEqual(q.result, r.cloud['新谱面'])
        s.event('制谱设置', 'OtherScreenClosed', 屏幕名='录制屏', 返回值=q.result)
        self.assertTrue(s.closed)
        r.event('Screen1', 'OtherScreenClosed', 屏幕名='制谱设置', 返回值=s.result)
        self.assertEqual(r.globals['当前谱'], q.result)
        self.assertIn('新谱面', r.components['标题']['Text'])

    def test_free_and_snap(self):
        for mode, expected in [(1, [[1,1010],[2,1070],[3,1100]]), (2, [[1,1010],[2,1010.0],[3,1135.0]])]:
            r = self.recorder(mode)
            for lane,t in [(1,1010),(2,1070),(3,1100)]: r.note(lane,t)
            self.assertEqual(r.globals['谱面'], expected)
            r.tap(3)
            self.assertEqual(len(r.globals['谱面']), 3)
            r.event('重开', 'Click')
            self.assertEqual(r.globals['谱面'], [])
            self.assertEqual(r.globals['基准'], -1)

    def test_judgement_and_chords(self):
        for delta, result in [(-160,2),(-80,3),(0,3),(80,3),(160,2),(161,1)]:
            r = self.runtime('游玩屏', self.chart([[1,1000]]))
            r.note(1,1000+delta)
            self.assertEqual(r.globals['判定表'], [result])
        r = self.runtime('游玩屏', self.chart([[1,1000],[2,1000]]))
        r.advance(1000)
        r.tap(2)
        r.tap(1)
        self.assertEqual(r.globals['判定表'], [3,3])
        self.assertEqual(r.globals['准确率'], 100)

    def test_draw_and_end(self):
        r = self.runtime('游玩屏', self.chart())
        r.advance(500)
        self.assertTrue(r.notes())
        r.advance(4000)
        self.assertEqual(r.globals['状态'], 3)
        self.assertIn('Miss', r.components['信息']['Text'])
        r.event('重开', 'Click')
        self.assertEqual(r.globals['状态'], 1)
        r.event('返回', 'Click')
        self.assertTrue(r.closed)
        self.assertFalse(r.components['时钟']['TimerEnabled'])

    def test_save_retry_and_overwrite(self):
        r = self.recorder()
        r.note(1,1000)
        r.event('结束', 'Click')
        r.event('保存', 'Click')
        r.cloud_step(fail=True)
        self.assertFalse(r.closed)
        self.assertEqual(r.globals['谱面'], [[1,1000]])
        r.cloud['新谱面'] = self.chart()
        r.event('保存', 'Click')
        r.cloud_step()
        self.assertEqual(r.globals['云请求'], '等待覆盖')
        r.event('提示', 'AfterChoosing', 选择='取消')
        self.assertFalse(r.closed)
        r.event('保存', 'Click')
        r.cloud_step()
        r.event('提示', 'AfterChoosing', 选择='覆盖')
        self.assertFalse(r.closed)
        r.cloud_step()
        self.assertTrue(r.closed)

    def test_settings_validation_and_back(self):
        r = self.runtime('制谱设置')
        r.event('录制', 'Click')
        self.assertIsNone(r.opened)
        r.components['名称输入']['Text'] = '吸附'
        r.components['模式输入']['SelectionIndex'] = 2
        r.components['速度输入']['Text'] = '0'
        r.event('录制', 'Click')
        self.assertIsNone(r.opened)
        r.event('制谱设置', 'OtherScreenClosed', 屏幕名='录制屏', 返回值='')
        self.assertFalse(r.closed)
        r.event('设置返回', 'Click')
        self.assertTrue(r.closed)

if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    (ROOT/'docs/多屏版测试报告.json').write_text(json.dumps(dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors), passed=result.wasSuccessful(), level='导出 AIA 的积木模拟执行、结构检查及全部音频哈希校验；未验证在线导入、APK 构建或真机'), ensure_ascii=False, indent=2), encoding='utf-8')
    raise SystemExit(not result.wasSuccessful())
