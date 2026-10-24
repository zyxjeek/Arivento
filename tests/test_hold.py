import copy,itertools,json,sys,unittest,zipfile
from pathlib import Path
import test_native_tracks as old

ROOT=Path(__file__).resolve().parents[1]
AIA=ROOT/'archive/hold_base_1016/Hold_candidate.aia'
old.base.AIA=AIA

class AndroidRuntime(old.Runtime):
    def evaluate(self,b,env):
        m=b.find('mutation')
        if b.get('type')=='component_method' and m.get('method_name')=='JsonTextDecode':
            try:return json.loads(self.value(b,'ARG0',env))
            except ValueError:
                self.event(self.screen,'ErrorOccurred',组件='文本转换',函数='JsonTextDecode',编号=1105,消息='JSON 格式错误')
                return ''
        return super().evaluate(b,env)

class Hold(unittest.TestCase):
    def chart(self,notes,end=4000):return ['Hold测试','content://music',500,2,120,4,end,notes]
    def play(self,notes,delay=0,speed=500,end=4000):
        r=old.Runtime(screen='Play',start=self.chart(notes,end)+[delay,speed]);r.initialize();return r
    def load(self,notes):
        r=AndroidRuntime();r.initialize();r.pick('选谱','content://chart');r.event('谱面文件','GotText',内容=json.dumps(self.chart(notes),ensure_ascii=False));return r
    def states(self,r):return [n[2] for group in r.globals['游玩分段'] for n in group]
    def drag(self,r,lane,x=0,y=100):r.event(old.LANES[lane-1],'Dragged',起横=45,起纵=100,前横=45,前纵=100,横坐标=x,纵坐标=y,精灵=False)
    def test_head_windows(self):
        for d,grade in [(-161,1),(-160,2),(-81,2),(-80,3),(0,3),(80,3),(81,2),(160,2),(161,1)]:
            with self.subTest(d=d):
                r=self.play([[1,1000,2000]]);r.hit(1,1000+d)
                self.assertEqual(r.globals['完美']+r.globals['良好'],0)
                r.advance(2000);self.assertEqual(self.states(r),[grade]);self.assertEqual(r.globals['完美']+r.globals['良好']+r.globals['漏击'],1)
    def test_release_before_exact_after_tail(self):
        for t,result in [(1999.99,1),(2000,3),(2000.01,3)]:
            r=self.play([[1,1000,2000]]);r.hit(1,1000);r.now=r.globals['起点']+t;r.release(1);r.advance(2500)
            self.assertEqual(self.states(r),[result]);self.assertEqual(r.globals['漏击'],result==1)
    def test_break_cannot_recover(self):
        r=self.play([[1,1000,2000]]);r.hit(1,1000);r.advance(1500);r.release(1);r.tap(1);r.advance(2100);self.assertEqual(self.states(r),[1]);self.assertEqual(r.globals['漏击'],1)
    def test_drag_out_each_boundary(self):
        for x,y in [(0,100),(90,100),(45,0),(45,430)]:
            r=self.play([[1,1000,2000]]);r.hit(1,1000);r.advance(1500);self.drag(r,1,x,y);self.drag(r,1,45,100);r.advance(2000);self.assertEqual(self.states(r),[1])
    def test_drag_inside_and_preheld(self):
        r=self.play([[1,1000,2000]]);r.hit(1,1000);self.drag(r,1,30,80);r.advance(2000);self.assertEqual(self.states(r),[3])
        r=self.play([[1,1000,2000]]);r.hit(1,700);r.hit(1,1000);r.advance(2000);self.assertEqual(self.states(r),[1])
    def test_short_hold_and_missed_head(self):
        r=self.play([[1,1000,1020]]);r.hit(1,1020);self.assertEqual(self.states(r),[1])
        r=self.play([[1,1000,1020]]);r.hit(1,1019);r.advance(1020);self.assertEqual(self.states(r),[3])
        r=self.play([[1,1000,3000]]);r.advance(1161);self.assertEqual(self.states(r),[1])
    def test_short_hold_not_blocked_by_other_pending_note(self):
        r=self.play([[1,1000,3000],[2,1010,1020]]);r.advance(1020);self.assertEqual(self.states(r),[0,1])
    def test_quad_all_press_orders(self):
        for order in itertools.permutations(range(1,5)):
            r=self.play([[i,1000,2000] for i in range(1,5)]);r.advance(1000)
            for lane in order:r.tap(lane)
            self.assertEqual(r.globals['连击'],0);r.advance(2000);self.assertEqual(self.states(r),[3]*4);self.assertEqual(r.globals['连击'],4)
    def test_mixed_notes_and_accuracy(self):
        r=self.play([[1,1000,3000],[2,1000,2000],[3,1200],[4,1500,2500]])
        r.hit(1,1000);r.hit(2,1100);r.hit(3,1200);r.hit(4,1500);r.advance(1600);r.release(4);r.advance(3000)
        self.assertEqual(self.states(r),[3,2,3,1]);self.assertAlmostEqual(r.globals['准确率'],66.25);self.assertEqual(r.globals['连击'],2)
    def test_delay_and_speed(self):
        for delay in [-200,0,200]:
            for speed in [250,500,1500]:
                r=self.play([[1,1000,2000]],delay,speed);r.hit(1,1000+delay);r.advance(2000+delay);self.assertEqual(self.states(r),[3])
        r=self.play([[1,0]],-200);r.hit(1,-200);self.assertEqual(self.states(r),[3])
    def test_restart_return_and_failure_clear(self):
        for event in [('重开','Click'),('返回','Click')]:
            r=self.play([[1,1000,2000]]);r.hit(1,1000);r.event(*event);self.assertEqual(r.globals['持续长条'],[0]*4);self.assertEqual(r.globals['按住轨道'],[0]*4)
        r=self.play([[1,1000,2000]]);r.hit(1,1000);r.call('播放失败');self.assertEqual(r.globals['持续长条'],[0]*4)
    def test_tail_end_repair_and_finish(self):
        r=self.play([[1,1000,5000]],end=2000);r.hit(1,1000);r.advance(5000);self.assertEqual(self.states(r),[3]);self.assertEqual(r.globals['结束时间'],5500);r.advance(5500);self.assertEqual(r.globals['状态'],3)
    def test_visible_body_and_failed_gray(self):
        r=self.play([[1,1000,4000]]);r.hit(1,1000);r.advance(2000)
        vertical=[d for d in r.draws if d['canvas']=='轨道一' and d['args'][0]==45 and d['args'][2]==45]
        self.assertTrue(vertical);self.assertEqual(vertical[0]['args'][1],r.globals['判定线'])
        r.release(1);r.advance(2100);self.assertTrue(any(d['color']==-10066330 for d in r.draws))
    def test_import_dedup_tail_and_decimals(self):
        r=self.load([[1,1000],[1,1000],[2,1234.56789,6000.12345]]);self.assertTrue(r.globals['有效']);self.assertEqual(len(r.globals['当前谱'][7]),2);self.assertAlmostEqual(r.globals['当前谱'][6],6500.12345)
    def test_invalid_charts(self):
        invalid=[[[1,1000,1000]],[[1,1000,999]],[[1,1000,2000],[1,2000]],[[1,1000,2000],[1,1500,3000]],[[1,1000],[1,1000,2000]],[[1,2000],[2,1000]],[[5,1000]],[[1,-1]],[[1,'1000']],[[True,1000]],[[1,1000,float('inf')]],[[1,1000,float('nan')]]]
        for notes in invalid:
            with self.subTest(notes=notes):
                r=self.load(notes);self.assertFalse(r.globals['有效']);self.assertIn('音符',r.globals['校验问题'])
    def test_legacy_unchanged(self):
        with zipfile.ZipFile(AIA) as z,zipfile.ZipFile(ROOT/'archive/hold_base_1016/Arivento.aia') as oldz:
            for n in z.namelist():
                if Path(n).stem in ['Recorder','EditorSettings']:self.assertEqual(z.read(n),oldz.read(n))
    def test_many_segmented_notes(self):
        r=self.play([[i%4+1,1000+i*200,1100+i*200] for i in range(180)],end=38000)
        for i in range(180):r.hit(i%4+1,1000+i*200);r.advance(1100+i*200);r.release(i%4+1)
        self.assertEqual(r.globals['完美'],180);self.assertEqual(len(r.globals['游玩分段']),3)

if __name__=='__main__':unittest.main(verbosity=2)
