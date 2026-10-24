import copy,json,unittest,itertools
from pathlib import Path
import test_native_tracks as old

old.base.AIA=Path(__file__).resolve().parents[1]/'archive/releases/Rail4K_1011_1.aia'

class Settings(unittest.TestCase):
    def chart(self):return ['旧谱','content://music',1700,2,137,3,2000,[[i,1000] for i in range(1,5)]]
    def home(self):
        r=old.Runtime();r.initialize();r.pick('选谱','content://chart');r.event('谱面文件','GotText',内容=json.dumps(self.chart()));r.pick('选音乐','content://music');return r
    def play(self,delay=0,speed=500,chart=None):
        r=old.Runtime(screen='Play',start=(chart or self.chart())+[delay,speed]);r.initialize();return r
    def test_defaults_and_old_format(self):
        h=self.home();original=copy.deepcopy(h.globals['当前谱']);h.start()
        self.assertEqual(h.opened[1][:8],original);self.assertEqual(h.opened[1][8:],[0,500])
        r=old.Runtime(screen='Play',start=self.chart());r.initialize()
        self.assertEqual(r.globals['过屏时间'],500);self.assertEqual(r.globals['谱面延迟'],0)
    def test_settings_do_not_mutate_chart(self):
        h=self.home();before=copy.deepcopy(h.globals['当前谱'])
        h.components['延迟输入']['Text']='-123.5';h.components['游玩过屏输入']['Text']='750';h.start()
        self.assertEqual(h.opened[1][8:],[-123.5,750]);self.assertEqual(h.globals['当前谱'],before)
        h.pick('选谱','content://chart');h.event('谱面文件','GotText',内容=json.dumps(self.chart()))
        self.assertEqual(h.components['延迟输入']['Text'],'-123.5');self.assertEqual(h.components['游玩过屏输入']['Text'],'750')
    def test_validation(self):
        for delay,speed in [('201','500'),('-201','500'),('','500'),('abc','500'),('0','0'),('0','-1'),('0','abc')]:
            r=self.home();r.components['延迟输入']['Text']=delay;r.components['游玩过屏输入']['Text']=speed;r.start()
            self.assertIsNone(r.opened);self.assertTrue(r.alerts)
        for delay in [-200,0,200]:
            r=self.home();r.components['延迟输入']['Text']=str(delay);r.start();self.assertEqual(r.opened[1][8],delay)
    def test_chords_and_restart(self):
        for delay in [-200,0,200]:
            r=self.play(delay);original=copy.deepcopy(r.globals['谱面']);r.advance(1000+delay)
            for i in [4,2,1,3]:r.tap(i)
            self.assertEqual(r.globals['完美'],4);self.assertEqual(r.globals['准确率'],100)
            r.event('重开','Click');r.advance(1000+delay)
            for i in range(1,5):r.tap(i)
            self.assertEqual(r.globals['完美'],4);self.assertEqual(r.globals['谱面'],original)
    def test_judgement_boundaries(self):
        for delay in [-200,200]:
            for error,expected in [(-161,0),(-160,2),(-80,3),(80,3),(160,2),(161,1)]:
                c=self.chart();c[7]=[[1,1000]];r=self.play(delay,chart=c);r.advance(1000+delay+error);r.tap(1)
                self.assertEqual(r.globals['游玩分段'][0][0][2],expected)
    def test_speed_only_changes_drawing(self):
        for speed in [250,500,2000]:
            r=self.play(0,speed);self.assertEqual(r.globals['过屏时间'],speed)
            r.advance(1000)
            for i in range(1,5):r.tap(i)
            self.assertEqual(r.globals['完美'],4)
    def test_negative_first_note_and_music_start(self):
        c=self.chart();c[7]=[[1,0]];r=self.play(-200,chart=c);r.advance(-200);r.tap(1)
        self.assertEqual(r.globals['完美'],1);self.assertFalse(r.globals['已播放'])
        r.advance(0);self.assertTrue(r.globals['已播放'])
    def test_positive_delay_defers_finish(self):
        c=self.chart();c[6]=1200;r=self.play(200,chart=c)
        r.advance(1200)
        self.assertTrue(r.components['轨道区']['Visible'])
        for i in range(1,5):r.tap(i)
        self.assertEqual(r.globals['完美'],4)
        r.advance(1400);self.assertIn('游玩完成',r.components['信息']['Text'])

if __name__=='__main__':
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(Settings),unittest.defaultTestLoader.loadTestsFromTestCase(old.Tests)])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
