import io,unittest,wave,zipfile,xml.etree.ElementTree as E
from pathlib import Path
import test_calibration as base
AIA=Path(__file__).resolve().parents[1]/'archive/hold_base_1016/Simple_candidate.aia'
base.saved.hold.old.base.AIA=AIA
class Runtime(base.Runtime):
    def cal_advance(self,elapsed):
        target=self.globals['校准起点']+elapsed
        while self.now<target:
            self.now=min(self.now+int(self.components['校准时钟']['TimerInterval']),target)
            if self.components['校准时钟']['TimerEnabled']:self.event('校准时钟','Timer')

class Simple(unittest.TestCase):
    def home(self):r=Runtime();r.initialize();return r
    def play(self,notes=None):
        r=Runtime(screen='Play',start=['测试','content://music',500,2,120,4,5000,notes or [[1,1000]]]+[0,500]);r.initialize();return r
    def test_loop_and_delay(self):
        for delay in [-400,0,400]:
            r=self.home();r.components['延迟输入']['Text']=str(delay);r.event('校准入口','Click')
            for n in range(18):
                r.cal_advance(500+n*1000+delay)
                hits=[s for s in r.sounds if s[0]=='校准打击']
                self.assertEqual(len(hits),n+1)
                self.assertAlmostEqual(hits[-1][1]-r.globals['校准起点'],500+n*1000+delay)
            self.assertEqual(r.globals['校准状态'],2);self.assertFalse(r.cal_playing)
            self.assertEqual(str(r.components['校准音乐']['Loop']),'False')
    def test_live_adjust_no_restart_no_duplicate(self):
        r=self.home();r.event('校准入口','Click');r.cal_advance(500);origin=r.globals['校准起点']
        r.event('校准增加','Click');self.assertEqual(r.globals['试听延迟'],10);self.assertEqual(r.globals['校准起点'],origin)
        r.cal_advance(510);self.assertEqual(len([s for s in r.sounds if s[0]=='校准打击']),1)
        r.cal_advance(1510);self.assertEqual(len([s for s in r.sounds if s[0]=='校准打击']),2)
    def test_no_measurement_and_apply_cancel(self):
        r=self.home();self.assertNotIn(('校准画布','TouchDown'),r.events);self.assertNotIn('校准数量',r.globals)
        r.event('校准入口','Click');r.components['校准数值']['Text']='400';r.event('校准应用','Click');self.assertEqual(r.db['谱面延迟'],400);self.assertFalse(r.cal_playing)
        r.event('校准入口','Click');r.components['校准数值']['Text']='-400';r.event('校准返回','Click');self.assertEqual(r.db['谱面延迟'],400)
    def test_bounds_and_countdown_constant(self):
        r=self.home();r.event('校准入口','Click');r.components['校准数值']['Text']='400';r.event('校准增加','Click');self.assertEqual(float(r.components['校准数值']['Text']),400)
        r.components['校准数值']['Text']='401';r.event('校准应用','Click');self.assertNotIn('谱面延迟',r.db)
        with zipfile.ZipFile(AIA) as z:
            root=E.fromstring(z.read(next(n for n in z.namelist() if n.endswith('/Play.bky'))))
            for e in root.iter():e.tag=e.tag.split('}')[-1]
            draw=next(b for b in root if b.findtext("field[@name='NAME']")=='绘图')
            self.assertTrue(any(b.findtext("value[@name='B']/block/field")=='1000' for b in draw.iter('block') if b.get('type')=='math_division'))
    def test_no_empty_sound_good_perfect(self):
        for t in [840,920,1000,1080,1160]:
            r=self.play();r.hit(4,t);self.assertEqual(r.sounds,[]);r.hit(1,t);self.assertEqual(len(r.sounds),1);self.assertEqual(r.sounds[0][2],0)
        for t in [800,1200]:
            r=self.play();r.hit(1,t);self.assertEqual(r.sounds,[])
    def test_hold_quad_and_repeat(self):
        r=self.play([[i,1000,2000] for i in range(1,5)]);r.advance(1000)
        for i in range(1,5):r.tap(i)
        self.assertEqual(len(r.sounds),4);r.tap(1);r.advance(2000);self.assertEqual(len(r.sounds),4)
        r.release(1);r.tap(1);self.assertEqual(len(r.sounds),4)
    def test_skip_stale_ticks_and_stop(self):
        r=self.home();r.event('校准入口','Click');r.cal_advance(400);r.now+=300;r.event('校准时钟','Timer');self.assertEqual(r.sounds,[])
        r.cal_advance(1500);self.assertEqual([s[0] for s in r.sounds],['校准节拍','校准打击']);r.event('Screen1','BackPressed');self.assertFalse(r.cal_playing);self.assertFalse(r.components['校准时钟']['TimerEnabled'])
    def test_zero_delay_stays_paired_with_irregular_callbacks(self):
        r=self.home();r.event('校准入口','Click');origin=r.globals['校准起点']
        steps=[7,13,21,9,16,11,29];i=0
        while r.now-origin<45000:
            r.now+=steps[i%len(steps)];i+=1;r.event('校准时钟','Timer')
        beats=[s[1] for s in r.sounds if s[0]=='校准节拍'];hits=[s[1] for s in r.sounds if s[0]=='校准打击']
        self.assertGreaterEqual(len(beats),45);self.assertEqual(beats,hits)
        self.assertEqual(r.globals['校准起点'],origin);self.assertFalse(r.cal_playing)
    def test_signed_offsets_share_one_absolute_grid_without_drift(self):
        for delay in [-400,-137,137,400]:
            r=self.home();r.components['延迟输入']['Text']=str(delay);r.event('校准入口','Click');origin=r.globals['校准起点']
            steps=[11,17,8,23];i=0
            while r.now-origin<30500+max(delay,0):
                r.now+=steps[i%len(steps)];i+=1;r.event('校准时钟','Timer')
            for name,offset in [('校准节拍',0),('校准打击',delay)]:
                times=[s[1]-origin for s in r.sounds if s[0]==name];self.assertGreaterEqual(len(times),30)
                for n,t in enumerate(times):self.assertGreaterEqual(t,500+n*1000+offset);self.assertLess(t-(500+n*1000+offset),24)
            self.assertEqual(r.globals['校准起点'],origin)
    def test_stall_skips_whole_pair_without_restarting_clock(self):
        r=self.home();r.components['延迟输入']['Text']='400';r.event('校准入口','Click');origin=r.globals['校准起点']
        r.cal_advance(400);r.now=origin+750;r.event('校准时钟','Timer')
        r.cal_advance(1000);self.assertEqual(r.sounds,[])
        r.cal_advance(1900);self.assertEqual([(s[0],s[1]-origin) for s in r.sounds],[('校准节拍',1500),('校准打击',1900)])
        self.assertEqual(r.globals['校准起点'],origin)
    def test_metronome_failure_stops_both_streams(self):
        r=self.home();r.event('校准入口','Click');r.cal_advance(500)
        r.event('Screen1','ErrorOccurred',组件='校准节拍',函数='Play',编号=1,消息='failed')
        self.assertEqual(r.globals['校准状态'],0);self.assertFalse(r.components['校准时钟']['TimerEnabled'])
        count=len(r.sounds);r.cal_advance(2500);self.assertEqual(len(r.sounds),count)
    def test_short_metronome_and_single_clock_structure(self):
        with zipfile.ZipFile(AIA) as z:
            with wave.open(io.BytesIO(z.read('assets/arivento_metronome.wav'))) as w:
                self.assertEqual(w.getnframes(),2205);self.assertEqual(w.getframerate(),22050)
                self.assertNotEqual(w.readframes(2205),b'\0'*4410)
            root=E.fromstring(z.read(next(n for n in z.namelist() if n.endswith('/Screen1.bky'))))
        for e in root.iter():e.tag=e.tag.split('}')[-1]
        for b in root:
            if b.findtext("field[@name='NAME']") not in ['启动校准','更新校准']:continue
            for m in b.iter('mutation'):
                self.assertFalse(m.get('instance_name')=='校准音乐' and (m.get('method_name')=='Start' or m.get('property_name')=='IsPlaying'))

if __name__=='__main__':unittest.main(verbosity=2)

