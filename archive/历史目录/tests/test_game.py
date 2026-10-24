"""Regression checks execute the XML extracted from dist/Rail4K_MVP.aia."""
import hashlib
import json
import random
import re
import unittest
import zipfile
from bky_runtime import Runtime, AIA, ROOT, field


class GameTests(unittest.TestCase):
    def new(self, seed=7, **kw):
        r = Runtime(seed, **kw)
        r.start()
        return r

    def test_archive_and_original_preserved(self):
        with zipfile.ZipFile(AIA) as z:
            self.assertIsNone(z.testzip())
            self.assertEqual(len(z.namelist()), 3)
            self.assertTrue(all('\\' not in n and not n.startswith('/') for n in z.namelist()))
        with zipfile.ZipFile(ROOT / 'test.aia') as z:
            for name in z.namelist():
                self.assertEqual(z.read(name), (ROOT / 'original' / 'test' / name).read_bytes())

    def test_block_references_and_bindings(self):
        r = Runtime()
        blocks = list(r.root.iter('block'))
        self.assertEqual(len({b.get('id') for b in blocks}), len(blocks))
        for b in blocks:
            m = b.find('mutation')
            if b.get('type').startswith('component_') and m.get('is_generic') != 'true':
                self.assertIn(m.get('instance_name'), r.components)
                self.assertEqual(m.get('component_type'), r.components[m.get('instance_name')]['$Type'])
            if b.get('type') == 'procedures_callnoreturn':
                name = field(b, 'PROCNAME')
                self.assertIn(name, r.procedures)
                expected = [a.get('name') for a in r.procedures[name].find('mutation').findall('arg')]
                self.assertEqual([a.get('name') for a in m.findall('arg')], expected)
                self.assertEqual(len(b.findall('value')), len(expected))
            if b.get('type') in ('lexical_variable_get', 'lexical_variable_set'):
                name = field(b, 'VAR')
                if name.startswith('global '): self.assertIn(name[7:], r.globals)
        self.assertEqual(r.design['YaVersion'], '219')
        self.assertEqual(r.components['时钟']['TimerInterval'], '16')
        self.assertEqual(r.components['Screen1']['ScreenOrientation'], 'portrait')
        self.assertNotIn('WebViewer', [c['$Type'] for c in r.components.values()])

    def test_chart_count_density_randomness_and_windows(self):
        charts = []
        for seed in range(16):
            r = self.new(seed)
            lanes = r.globals['谱面']
            self.assertEqual(len(lanes), 60)
            self.assertEqual(set(lanes), {1, 2, 3, 4})
            charts.append(tuple(lanes))
        self.assertEqual(len(set(charts)), 16)
        times = [i*1000-500 for i in range(1, 61)]
        self.assertEqual(set(b-a for a, b in zip(times, times[1:])), {1000})
        self.assertEqual((times[0], times[-1]), (500, 59500))
        self.assertLess(times[-1]+160, 60000)

    def test_judgement_boundaries(self):
        for offset, p, g in [(-160, 0, 1), (-159, 0, 1), (-81, 0, 1), (-80, 1, 0),
                              (0, 1, 0), (80, 1, 0), (81, 0, 1), (159, 0, 1), (160, 0, 1)]:
            with self.subTest(offset=offset):
                r = self.new()
                r.hit(1, offset)
                self.assertEqual((r.globals['完美'], r.globals['良好'], r.globals['漏击']), (p, g, 0))
                self.assertEqual(r.globals['下一键'], 2)

    def test_early_161_ignored_late_161_missed(self):
        r = self.new()
        r.hit(1, -161)
        self.assertEqual(r.globals['下一键'], 1)
        r.hit(1, 161)
        self.assertEqual((r.globals['完美'], r.globals['良好'], r.globals['漏击']), (0, 0, 1))
        self.assertEqual(r.globals['下一键'], 2)

    def test_touch_samples_time_after_last_timer(self):
        r = self.new()
        r.advance(580)
        r.now += 1  # Last rendered frame was +80; actual touch is +81.
        r.tap(r.globals['谱面'][0])
        self.assertEqual((r.globals['完美'], r.globals['良好']), (0, 1))

    def test_wrong_lane_empty_and_repeat_ignore(self):
        r = self.new()
        r.advance(500)
        lane = r.globals['谱面'][0]
        r.tap(lane % 4 + 1)
        self.assertEqual(r.globals['下一键'], 1)
        r.tap(lane)
        for _ in range(20): r.tap(lane)
        self.assertEqual((r.globals['完美'], r.globals['连击'], r.globals['下一键']), (1, 1, 2))

    def test_all_perfect_full_minute(self):
        r = self.new()
        for i in range(1, 61): r.hit(i)
        self.assertEqual(r.globals['状态'], 1)
        r.advance(59999)
        self.assertEqual(r.globals['状态'], 1)
        r.advance(60000)
        self.assertEqual(r.globals['状态'], 3)
        self.assertEqual(r.globals['准确率'], 100)
        self.assertEqual((r.globals['准确率'] / 100), 1)
        self.assertEqual(r.globals['最大连击'], 60)
        self.assertIn('Perfect 60', r.components['标题']['Text'])
        self.assertFalse(r.components['时钟']['TimerEnabled'])
        self.assertEqual(len(r.judgements), 60)

    def test_all_good(self):
        r = self.new()
        for i in range(1, 61): r.hit(i, 120)
        r.advance(60000)
        self.assertEqual((r.globals['准确率'], r.globals['最大连击']), (65, 60))
        self.assertIn('Good 60', r.components['标题']['Text'])

    def test_no_input_all_miss(self):
        r = self.new()
        r.advance(60000)
        self.assertEqual((r.globals['准确率'], r.globals['漏击']), (0, 60))
        self.assertEqual(r.globals['下一键'], 61)
        self.assertEqual(r.globals['状态'], 3)

    def test_mixed_accuracy_and_max_combo(self):
        r = self.new()
        for i in range(1, 31): r.hit(i)
        r.advance(30661)  # note 31 missed; max combo stays 30
        for i in range(32, 61): r.hit(i, 100)
        r.advance(60000)
        self.assertEqual((r.globals['完美'], r.globals['良好'], r.globals['漏击']), (30, 29, 1))
        self.assertEqual((r.globals['连击'], r.globals['最大连击']), (29, 30))
        self.assertAlmostEqual((r.globals['准确率'] / 100), 48.85/60)

    def test_end_miss_keeps_max_combo(self):
        r = self.new()
        for i in range(1, 60): r.hit(i)
        r.advance(60000)
        self.assertEqual((r.globals['连击'], r.globals['最大连击']), (0, 59))
        self.assertAlmostEqual(r.globals['准确率'], 5900/60)

    def test_no_pause_on_callback_gap_or_clock_rollback(self):
        r = self.new()
        r.advance(400)
        r.now += 5000
        r.event('时钟', 'Timer')
        self.assertEqual(r.globals['状态'], 1)
        self.assertEqual(r.globals['用时'], 5400)
        self.assertEqual(r.globals['漏击'], 5)
        r.now -= 100
        r.event('时钟', 'Timer')
        self.assertEqual(r.globals['状态'], 1)
        self.assertEqual(r.globals['用时'], 5400)

    def test_jitter_does_not_accumulate_drift(self):
        r = self.new()
        rng = random.Random(17)
        for i in range(1, 61):
            target = r.globals['起点'] + i*1000-500
            while r.now < target:
                r.now = min(target, r.now+rng.randint(7, 110))
                r.event('时钟', 'Timer')
            r.tap(r.globals['谱面'][i-1])
        r.advance(60000)
        self.assertEqual(r.globals['准确率'], 100)

    def test_restart_replay_home_and_back(self):
        r = self.new()
        r.hit(1)
        chart = r.globals['谱面'][:]
        r.event('重开', 'Click')
        self.assertEqual(r.globals['用时'], -3000)
        self.assertEqual((r.globals['完美'], r.globals['准确率'], r.globals['下一键']), (0, 100, 1))
        self.assertNotEqual(r.globals['谱面'], chart)
        r.event('Screen1', 'BackPressed')
        self.assertEqual(r.globals['状态'], 0)
        r.event('开始', 'Click')
        r.advance(60000)
        r.event('开始', 'Click')
        self.assertEqual(r.globals['状态'], 1)
        r.advance(60000)
        r.event('Screen1', 'BackPressed')
        self.assertTrue(r.components['首页']['Visible'])
        r.event('Screen1', 'BackPressed')
        self.assertTrue(r.closed)

    def test_canvas_lane_mapping_and_rendered_position(self):
        for width, height in [(320, 250), (360, 430), (412, 570), (800, 800)]:
            with self.subTest(width=width):
                r = self.new(width=width, height=height)
                r.advance(0)
                judge = height*0.85
                note = self.notes(r)[0]
                self.assertAlmostEqual(note['args'][1], judge*(1-500/1500))
                r.advance(500)
                lane = r.globals['谱面'][0]
                r.event('画布', 'TouchDown', x=(lane-0.5)*width/4, y=10)
                self.assertEqual(r.globals['完美'], 1)
        # Clamp the Canvas right edge to lane 4 instead of nonexistent lane 5.
        r = self.new()
        r.globals['谱面'][0] = 4
        r.advance(500)
        r.event('画布', 'TouchDown', x=360, y=0)
        self.assertEqual(r.globals['完美'], 1)

    def test_chinese_names_and_minimal_home(self):
        r = Runtime()
        chinese = lambda s: bool(re.fullmatch(r'[\u4e00-\u9fff0-9]+', s))
        self.assertEqual(len(r.components), 9)
        for name in r.components:
            if name != 'Screen1': self.assertTrue(chinese(name), name)
        for name in [*r.globals, *r.procedures]: self.assertTrue(chinese(name), name)
        for f in r.root.iter('field'):
            if f.get('name', '').startswith('VAR'):
                self.assertTrue(chinese((f.text or '').removeprefix('global ')), f.text)
        for tag in ('arg', 'localname'):
            for e in r.root.iter(tag): self.assertTrue(chinese(e.get('name')), e.attrib)
        self.assertEqual([c['$Name'] for c in r.components['首页']['$Components']], ['标题', '开始'])
        self.assertEqual([c['$Name'] for c in r.components['游戏']['$Components'] if c['$Type'] == 'Label'], ['信息'])
        m = r.events['画布', 'TouchDown'].find('mutation')
        self.assertEqual((m.get('param_name0'), m.get('param_name1')), ('横坐标', '纵坐标'))

    def test_feedback_at_screen_center_and_expiry(self):
        for offset, expected in [(0, 'PERFECT'), (120, 'GOOD'), (161, 'MISS')]:
            with self.subTest(expected=expected):
                r = self.new()
                r.hit(1, offset)
                matches = [d for d in r.text_draws if d['text'] == expected]
                self.assertEqual(len(matches), 1)
                self.assertEqual((matches[0]['x'], matches[0]['y']), (180, r.components['画布']['Height'] * 0.475))
                self.assertLess(matches[0]['y'], r.components['画布']['Height'])
                r.advance(500 + offset + 550)
                self.assertFalse(any(d['text'] == expected for d in r.text_draws))

    @staticmethod
    def notes(r):
        return [d for d in r.draws if d['color'] & 0xffffffff == 0xff56deef]

    def test_all_60_notes_visible_and_descending(self):
        r = self.new()
        for i in range(1, 61):
            r.advance((i-1)*1000)
            note = self.notes(r)[0]
            self.assertEqual(r.globals['下一键'], i)
            self.assertEqual(note['width'], 16)
            self.assertEqual((note['color'] & 0xffffffff) >> 24, 255)
            self.assertAlmostEqual(note['args'][0], (r.globals['谱面'][i-1]-1)*90+9)
            self.assertAlmostEqual(note['args'][2] - note['args'][0], 72)
            before = note['args'][1]
            r.advance((i-1)*1000+100)
            self.assertGreater(self.notes(r)[0]['args'][1], before)
        r.advance(59661)
        self.assertFalse(self.notes(r))

    def test_vertical_judgement_ignores_touch_height(self):
        for lane in range(1, 5):
            for y in (0, 30, 200, 429):
                with self.subTest(lane=lane, y=y):
                    r = self.new()
                    r.globals['谱面'][0] = lane
                    r.advance(500)
                    r.tap(lane, y=y)
                    self.assertEqual(r.globals['完美'], 1)

    def test_removed_features_absent_and_top_hud_layout(self):
        r = self.new()
        names = ' '.join([*r.components, *r.globals, *r.procedures])
        for text in ('暂停', '继续', '分数', '记分', '按键', '键盘'):
            self.assertNotIn(text, names)
        self.assertEqual([c['$Name'] for c in r.components['游戏']['$Components']], ['信息', '画布', '重开'])
        self.assertEqual(r.components['信息']['Height'], '-1012')
        self.assertEqual(r.components['游戏']['$Components'][1]['Height'], '-1080')
        self.assertEqual(r.components['重开']['Height'], '-1008')
        self.assertEqual({n for n, c in r.components.items() if c['$Type'] == 'Button'}, {'开始', '重开'})
        r.advance(0)
        self.assertTrue(r.components['信息']['Text'].startswith('准确率'))
        self.assertFalse(any('剩余' in str(t['text']) for t in r.text_draws))

    def test_clock_foreground_gate_and_asset_independent_render(self):
        # Clock.java Timer dispatches only when timerAlwaysFires || onScreen.
        r = self.new()
        r.on_screen = False
        r.components['时钟']['TimerAlwaysFires'] = 'False'
        r.advance(0)
        self.assertEqual(r.globals['用时'], -3000)
        self.assertFalse(self.notes(r))
        r.components['时钟']['TimerAlwaysFires'] = 'True'
        r.advance(100)
        self.assertEqual(r.globals['用时'], 100)
        self.assertTrue(self.notes(r))
        r.advance(60000)
        self.assertEqual(r.globals['漏击'], 60)
        self.assertEqual(r.globals['状态'], 3)
        with zipfile.ZipFile(AIA) as z:
            self.assertFalse(any(n.startswith('assets/') for n in z.namelist()))
        self.assertFalse(any(c['$Type'] == 'ImageSprite' for c in r.components.values()))

    def test_exported_clock_runs_without_foreground_notification(self):
        r = self.new()
        r.on_screen = False
        r.advance(0)
        self.assertTrue(self.notes(r))
        self.assertEqual(r.globals['用时'], 0)
        r.advance(500)
        self.assertAlmostEqual(self.notes(r)[0]['args'][1], r.globals['判定线'])

    def test_layout_not_ready_recovers_on_next_frame(self):
        r = self.new(width=0, height=0)
        self.assertFalse(r.draws)
        r.components['画布'].update(Width=360, Height=430)
        r.advance(0)
        self.assertTrue(self.notes(r))
        self.assertGreater(self.notes(r)[0]['args'][1], 0)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GameTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {'suite': 'Exported BKY regression tests', 'tests_run': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors),
              'success': result.wasSuccessful(), 'aia_sha256': hashlib.sha256(AIA.read_bytes()).hexdigest(),
              'scope': 'Archive integrity, native XML program execution with mocked Clock/Canvas; not an Android device or MIT import/build test.'}
    (ROOT / 'docs' / 'test-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
