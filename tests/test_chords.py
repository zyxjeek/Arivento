from pathlib import Path
import sys,copy,json,unittest,itertools,zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'archive/历史目录/tests'))
import test_local as old
import playback_runtime as base
base.AIA=ROOT/'archive/历史目录/dist/Rail4K_0924_1.aia'

class Runtime(old.Runtime):
    def tap(self,lane,count=1):self.event('本地文件','轨道按下',轨道=lane,触点数=count)
    def hit(self,lane,time,count=1):self.advance(time);self.tap(lane,count)

class Tests(unittest.TestCase):
    def chart(self,notes=None,mode=1):return ['多押','content://music',1000,mode,137,3,4000,notes or []]
    def record(self,mode=1,merge=True):
        r=Runtime(screen='Recorder',start=self.chart(mode=mode)+[merge]);r.initialize();return r
    def play(self,notes):
        r=Runtime(screen='Play',start=self.chart(notes));r.initialize();return r
    def states(self,r):return [n[2] for group in r.globals['游玩分段'] for n in group]
    def test_free_chords(self):
        for lanes in [[1,4],[2,4,1],[4,2,1,3]]:
            r=self.record()
            for i,lane in enumerate(lanes):r.hit(lane,1000+i*10,i+1)
            self.assertEqual(r.globals['谱面'],[[lane,1000] for lane in lanes])
            self.assertEqual(r.globals['物量'],len(lanes))
    def test_free_exact_and_window(self):
        r=self.record(merge=False)
        r.hit(1,1000);r.hit(2,1020,2);self.assertEqual(r.globals['谱面'],[[1,1000],[2,1020]])
        r=self.record();r.hit(1,1000);r.hit(2,1040,2);r.hit(3,1041,3)
        self.assertEqual(r.globals['谱面'],[[1,1000],[2,1000],[3,1041]])
        r=self.record();r.hit(1,1000);r.hit(2,1020,1)
        self.assertEqual(r.globals['谱面'],[[1,1000],[2,1020]])
    def test_duplicate_and_restart(self):
        r=self.record();r.hit(1,1000);r.hit(1,1010,2);r.hit(2,1020,3)
        self.assertEqual(r.globals['谱面'],[[1,1000],[2,1000]])
        r.event('重开','Click');self.assertEqual(r.globals['多押时间'],-1)
        r.hit(4,1000);self.assertEqual(r.globals['谱面'],[[4,1000]])
    def test_snap_grid(self):
        r=self.record(mode=2)
        r.hit(1,1000);r.hit(4,1020,2)
        r.hit(2,1210);r.hit(3,1240,2)
        notes=r.globals['谱面'];self.assertEqual(notes[0][1],notes[1][1]);self.assertEqual(notes[2][1],notes[3][1])
        gap=60000/137/3
        for _,t in notes:self.assertAlmostEqual((t-1000)/gap,round((t-1000)/gap))
    def test_play_all_orders(self):
        notes=[[i,1000] for i in range(1,5)]
        for order in itertools.permutations(range(1,5)):
            r=self.play(notes);r.advance(1000)
            for i,lane in enumerate(order):r.tap(lane,i+1)
            self.assertEqual(self.states(r),[3]*4);self.assertEqual(r.globals['连击'],4);self.assertEqual(r.globals['准确率'],100)
    def test_visible_chord(self):
        r=self.play([[i,1000] for i in range(1,5)]);r.advance(800)
        notes=r.notes();self.assertEqual(len(notes),4)
        self.assertEqual(len({n['args'][1] for n in notes}),1)
        self.assertEqual(len({n['args'][0] for n in notes}),4)
    def test_partial_and_independent_judgements(self):
        r=self.play([[i,1000] for i in range(1,5)])
        r.hit(3,1000);r.hit(1,1120,2);r.advance(1200)
        self.assertEqual(self.states(r),[2,1,3,1])
        self.assertAlmostEqual(r.globals['准确率'],41.25)
        r.advance(4000);self.assertIn('游玩完成',r.components['信息']['Text'])
    def test_segment_boundary_chord(self):
        notes=[[1,i*10] for i in range(62)]+[[i,1000] for i in range(1,5)]
        r=self.play(notes);r.advance(1000)
        for i in [4,2,3,1]:r.tap(i,4)
        self.assertEqual(self.states(r)[62:],[3]*4)
    def test_export_import(self):
        r=self.record()
        for i in range(4):r.hit(i+1,1000+i*10,i+1)
        r.advance(1800);r.event('结束','Click');r.event('导出','Click')
        while r.globals['正在导出']:r.event('导出时钟','Timer')
        chart=json.loads(r.globals['导出全文']);self.assertEqual(len(chart),8);self.assertEqual(chart[7],[[i,1000] for i in range(1,5)])
        h=Runtime();h.initialize();h.event('本地文件','谱面已读',内容=r.globals['导出全文'],名称='多押.txt')
        self.assertTrue(h.globals['有效']);self.assertEqual(h.globals['当前谱'][7],chart[7])
    def test_settings_and_binding(self):
        r=Runtime(screen='EditorSettings');r.components['名称输入']['Text']='多押';r.event('本地文件','音乐已选',地址='content://music',名称='歌.mp3')
        for enabled in [True,False]:
            r.components['多押设置']['Checked']=enabled;r.event('录制','Click');self.assertEqual(r.opened[1][8],enabled)
        for screen in ['Recorder','Play']:
            r=Runtime(screen=screen,start=self.chart([[1,1000]])+[True]);r.initialize()
            self.assertIn(('启用多点',['画布']),r.requests)
            self.assertNotIn(('画布','TouchDown'),r.events)
            self.assertEqual(r.components['本地文件']['$Version'],'2')

if __name__=='__main__':unittest.main(verbosity=2)
