import unittest,zipfile,xml.etree.ElementTree as E
from pathlib import Path
import test_calibration as base
AIA=Path(__file__).resolve().parents[1]/'archive/hold_base_1016/Simple_candidate.aia'
base.saved.hold.old.base.AIA=AIA
Runtime=base.Runtime

class Simple(unittest.TestCase):
    def home(self):r=Runtime();r.initialize();return r
    def play(self,notes=None):
        r=Runtime(screen='Play',start=['测试','content://music',500,2,120,4,5000,notes or [[1,1000]]]+[0,500]);r.initialize();return r
    def test_loop_and_delay(self):
        for delay in [-400,0,400]:
            r=self.home();r.components['延迟输入']['Text']=str(delay);r.event('校准入口','Click')
            for n in range(18):
                r.cal_advance(500+n*1000+delay)
                self.assertEqual(len(r.sounds),n+1)
                self.assertAlmostEqual(r.sounds[-1][1]-r.globals['校准起点'],500+n*1000+delay)
            self.assertEqual(r.globals['校准状态'],2);self.assertEqual(str(r.components['校准音乐']['Loop']),'True')
    def test_live_adjust_no_restart_no_duplicate(self):
        r=self.home();r.event('校准入口','Click');r.cal_advance(500);origin=r.globals['校准起点']
        r.event('校准增加','Click');self.assertEqual(r.globals['试听延迟'],10);self.assertEqual(r.globals['校准起点'],origin)
        r.cal_advance(510);self.assertEqual(len(r.sounds),1);r.cal_advance(1510);self.assertEqual(len(r.sounds),2)
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
        r.cal_advance(1500);self.assertEqual(len(r.sounds),1);r.event('Screen1','BackPressed');self.assertFalse(r.cal_playing);self.assertFalse(r.components['校准时钟']['TimerEnabled'])

if __name__=='__main__':unittest.main(verbosity=2)

