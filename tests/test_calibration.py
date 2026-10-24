import copy,json,sys,unittest,wave,io,zipfile
from pathlib import Path
import test_saved_charts as saved
AIA=Path(__file__).resolve().parents[1]/'archive/hold_base_1016/Calibration_candidate.aia'
saved.hold.old.base.AIA=AIA

class Runtime(saved.Runtime):
    def __init__(self,*a,**kw):
        self.sounds=[];self.cal_playing=False;self.cal_fail=False;self.calls=[]
        super().__init__(*a,**kw)
        if '校准画布' in self.components:self.components['校准画布'].update(Width=360,Height=170)
    def evaluate(self,b,env):
        m=b.find('mutation')
        if m is not None:
            if m.get('instance_name')=='本地设置':return copy.deepcopy(self.db.get(self.value(b,'ARG0',env),self.value(b,'ARG1',env)))
            if m.get('instance_name')=='校准音乐' and m.get('property_name')=='IsPlaying':return self.cal_playing
            if m.get('instance_name')=='校准时钟' and m.get('method_name')=='SystemTime':return self.now
        return super().evaluate(b,env)
    def call(self,name,*args):
        self.calls.append(name);return super().call(name,*args)
    def execute(self,b,env=None):
        env={} if env is None else env
        while b is not None:
            nxt=b.find('next/block');one=copy.copy(b);one[:]=[e for e in b if e.tag!='next'];m=one.find('mutation')
            if one.get('type')=='component_method' and m.get('component_type')=='Sound':
                if m.get('method_name')=='Play':self.sounds.append((m.get('instance_name'),self.now,self.globals.get('完美',0)))
            elif one.get('type')=='component_method' and m.get('instance_name')=='校准音乐':self.cal_playing=m.get('method_name')=='Start' and not self.cal_fail
            elif one.get('type')=='component_method' and m.get('instance_name')=='校准画布':
                for v in one.findall('value'):self.evaluate(v.find('block'),env)
            else:super().execute(one,env)
            b=nxt
    def cal_advance(self,elapsed):
        target=self.globals['校准起点']+elapsed
        while self.now<target:
            self.now=min(self.now+100,target)
            if self.components['校准时钟']['TimerEnabled']:self.event('校准时钟','Timer')

class Calibration(unittest.TestCase):
    def home(self,db=None):r=Runtime(db=db);r.initialize();return r
    def play(self,notes=None,delay=0,db=None):
        chart=['测试','content://music',500,2,120,4,5000,notes or [[1,1000]]]
        r=Runtime(screen='Play',start=chart+[delay,500],db=db);r.initialize();return r
    def measure(self,offsets):
        r=self.home();r.event('校准入口','Click');r.event('校准开始','Click')
        for i,offset in enumerate(offsets):r.cal_advance(7000+i*2500+offset);r.event('校准画布','TouchDown',横坐标=180,纵坐标=80)
        return r
    def test_positive_negative_and_limits(self):
        for offset in [-1000,-850,0,160,1000]:
            with self.subTest(offset=offset):
                r=self.measure([offset]*12);self.assertEqual(float(r.components['校准数值']['Text']),offset);self.assertEqual(r.globals['校准状态'],0)
    def test_trimmed_average_and_duplicate(self):
        r=self.measure([100]*8+[80,120,90,110]);self.assertEqual(float(r.components['校准数值']['Text']),100)
        r=self.measure([100]);r.event('校准画布','TouchDown',横坐标=180,纵坐标=80);self.assertEqual(r.globals['校准数量'],1)
    def test_warmup_and_outside_window(self):
        r=self.home();r.event('校准开始','Click');r.cal_advance(2000);r.event('校准画布','TouchDown',横坐标=1,纵坐标=1);self.assertEqual(r.globals['校准数量'],0)
        r.cal_advance(8100);r.event('校准画布','TouchDown',横坐标=1,纵坐标=1);self.assertEqual(r.globals['校准数量'],0)
    def test_unstable_and_insufficient_do_not_overwrite(self):
        r=self.measure([-200,200]*6);self.assertEqual(float(r.components['校准数值']['Text']),0);self.assertIn('波动',r.components['校准提示']['Text'])
        r=self.measure([100]*7);r.cal_advance(36000);self.assertIn('不足',r.components['校准提示']['Text'])
        r=self.measure([100]*8);r.cal_advance(36000);self.assertEqual(float(r.components['校准数值']['Text']),100)
    def test_apply_restart_cancel_manual(self):
        r=self.measure([100]*12);r.event('校准应用','Click');self.assertEqual(r.db['谱面延迟'],100)
        h=self.home(r.db);self.assertEqual(float(h.components['延迟输入']['Text']),100)
        h.event('校准入口','Click');h.components['校准数值']['Text']='900';h.event('校准返回','Click');self.assertEqual(h.db['谱面延迟'],100)
        h.components['延迟输入']['Text']='-1000';h.event('延迟输入','LostFocus');self.assertEqual(h.db['谱面延迟'],-1000)
        h.components['校准数值']['Text']='1001';h.event('校准应用','Click');self.assertEqual(h.db['谱面延迟'],-1000)
    def test_preview_and_nudge(self):
        r=self.home();r.event('校准入口','Click');r.components['校准数值']['Text']='100';r.event('校准试听','Click');r.cal_advance(2100);r.event('校准画布','TouchDown',横坐标=180,纵坐标=80)
        self.assertIn('0',r.components['校准提示']['Text']);self.assertEqual(r.globals['校准数量'],0)
        r.event('校准增加','Click');self.assertEqual(float(r.components['校准数值']['Text']),110);self.assertFalse(r.cal_playing)
        r.components['校准数值']['Text']='1000';r.event('校准增加','Click');self.assertEqual(float(r.components['校准数值']['Text']),1000)
    def test_interrupt_failure_back(self):
        r=self.home();r.event('校准入口','Click');r.event('校准开始','Click');r.now+=600;r.event('校准时钟','Timer');self.assertEqual(r.globals['校准状态'],0)
        r.event('校准开始','Click');r.event('校准音乐','OtherPlayerStarted');self.assertFalse(r.cal_playing)
        r.event('校准开始','Click');r.event('Screen1','BackPressed');self.assertFalse(r.components['校准页']['Visible']);self.assertFalse(r.cal_playing)
        r.cal_fail=True;r.event('校准开始','Click');r.cal_advance(1600);self.assertEqual(r.globals['校准状态'],0)
    def test_sound_before_judgement_and_empty_press(self):
        r=self.play();r.advance(1000);r.calls.clear();r.tap(1)
        self.assertEqual(r.sounds[0][2],0);self.assertEqual(r.globals['完美'],1);self.assertEqual(r.calls.count('走时'),1)
        r.tap(1);self.assertEqual(len(r.sounds),1);r.release(1);r.tap(4);self.assertEqual(len(r.sounds),2)
    def test_hold_no_tail_sound_and_quad(self):
        r=self.play([[i,1000,2000] for i in range(1,5)]);r.advance(1000)
        for i in range(1,5):r.tap(i)
        self.assertEqual(len(r.sounds),4);r.advance(2000);self.assertEqual(len(r.sounds),4);self.assertEqual(r.globals['完美'],4)
    def test_disabled_miss_and_sound_failure(self):
        r=self.play(db={'打击音效':False});r.hit(1,1000);self.assertEqual(r.sounds,[]);self.assertEqual(r.globals['完美'],1)
        r=self.play();r.advance(1300);self.assertEqual(r.sounds,[])
        r.event('Play','ErrorOccurred',组件='打击音一',函数='Play',编号=1,消息='bad');self.assertEqual(r.globals['状态'],1);self.assertFalse(r.globals['打击音开启'])
    def test_extended_delay_in_game_and_header(self):
        for delay in [-1000,1000]:
            r=self.play([[1,1500,2000]],delay);r.hit(1,1500+delay);r.advance(2000+delay);self.assertEqual(r.globals['完美'],1)
            h=self.home();h.globals.update(当前谱=['测试','content://music',500,2,120,4,4000,[[1,1000]]],音乐就绪=True,有效=True);h.components['延迟输入']['Text']=str(delay);h.start();self.assertEqual(h.opened[1][8],delay);self.assertEqual(h.db['谱面延迟'],delay)
    def test_audio_assets(self):
        with zipfile.ZipFile(AIA) as z:
            with wave.open(io.BytesIO(z.read('assets/arivento_calibration.wav'))) as w:
                self.assertEqual(w.getnframes(),36*22050);self.assertEqual(w.getframerate(),22050)
                w.setpos(2*22050);self.assertNotEqual(w.readframes(2205),b'\0'*4410)
            with wave.open(io.BytesIO(z.read('assets/arivento_hit.wav'))) as w:self.assertLess(w.getnframes()/w.getframerate(),.06)

if __name__=='__main__':unittest.main(verbosity=2)
