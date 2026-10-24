import io,struct,unittest,wave,zipfile
import test_simple_calibration as s

class HitVolume(unittest.TestCase):
    def home(self,db=None):
        r=s.Runtime(db=db);r.initialize();return r
    def change(self,r,value):r.event('打击音量滑条','PositionChanged',位置=value)
    def play(self,volume,enabled=True):
        r=s.Runtime(screen='Play',start=['测试','content://music',500,2,120,4,4000,[[i,1000,2000] for i in range(1,5)]]+[0,500],db={'打击音量':volume,'打击音效':enabled});r.initialize();return r
    def test_default_20_preserves_existing_settings(self):
        r=self.home({'打击音效':False})
        self.assertEqual(r.globals['打击音量'],20);self.assertEqual(r.components['打击音量滑条']['ThumbPosition'],20)
        self.assertEqual(r.components['校准打击']['Source'],'arivento_hit_20.wav')
        self.assertEqual(r.components['打击音设置']['Checked'],False)
        self.assertEqual(int(r.components['打击音量滑条']['MinValue']),0)
        self.assertEqual(int(r.components['打击音量滑条']['MaxValue']),100)
        self.assertEqual(int(r.components['打击音量滑条']['NumberOfSteps']),100)
    def test_every_percent_selects_matching_source_and_persists(self):
        r=self.home()
        for v in range(101):
            self.change(r,v);self.assertEqual(r.db['打击音量'],v)
            self.assertEqual(r.components['校准打击']['Source'],f'arivento_hit_{v}.wav')
            self.assertIn(f'{v}%',r.components['打击音量标题']['Text'])
        for v in [0,20,73,100]:
            self.change(r,v);restored=self.home(r.db)
            self.assertEqual(restored.globals['打击音量'],v)
            self.assertEqual(restored.components['打击音量滑条']['ThumbPosition'],v)
    def test_saved_value_bounds_and_initialization_event_guard(self):
        for value,expected in [(-5,0),(150,100),('bad',20),(33.7,34),('75',75)]:
            r=self.home({'打击音量':value});self.assertEqual(r.globals['打击音量'],expected)
        r=self.home({'打击音量':73});r.globals['音量已就绪']=False
        self.change(r,20);self.assertEqual(r.db['打击音量'],73)
    def test_game_quad_sources_and_mute_do_not_change_judgement(self):
        for v in [0,20,100]:
            r=self.play(v)
            for n in ['一','二','三','四']:self.assertEqual(r.components['打击音'+n]['Source'],f'arivento_hit_{v}.wav')
            r.advance(1000)
            for i in range(1,5):r.tap(i)
            self.assertEqual(len(r.sounds),0 if v==0 else 4)
            r.advance(2000);self.assertEqual(r.globals['完美'],4)
            self.assertEqual(len(r.sounds),0 if v==0 else 4)
        r=self.play(100,False);r.hit(1,1000);self.assertEqual(r.sounds,[])
    def test_calibration_uses_volume_without_changing_metronome_or_anchor(self):
        for v in [0,20,100]:
            r=self.home();metronome=r.components['校准节拍']['Source'];self.change(r,v)
            r.event('校准入口','Click');origin=r.globals['校准起点'];r.cal_advance(2500)
            self.assertEqual(len([x for x in r.sounds if x[0]=='校准节拍']),3)
            self.assertEqual(len([x for x in r.sounds if x[0]=='校准打击']),0 if v==0 else 3)
            self.assertEqual(r.components['校准节拍']['Source'],metronome)
            self.assertEqual(r.globals['校准起点'],origin)
    def test_waveforms_preserve_20_and_have_no_clipping_or_time_shift(self):
        def samples(data):
            with wave.open(io.BytesIO(data)) as w:
                self.assertEqual((w.getnchannels(),w.getsampwidth(),w.getframerate()),(1,2,22050))
                return struct.unpack('<'+'h'*w.getnframes(),w.readframes(w.getnframes()))
        with zipfile.ZipFile(s.AIA) as z:
            original=z.read('assets/arivento_hit.wav');baseline=samples(original);peak=max(map(abs,baseline));last=0
            self.assertEqual(z.read('assets/arivento_hit_20.wav'),original)
            for v in range(101):
                actual=samples(z.read(f'assets/arivento_hit_{v}.wav'))
                gain=v/20 if v<=20 else 1+(v-20)/80*(32767/peak-1)
                self.assertEqual(actual,tuple(round(x*gain) for x in baseline))
                current=max(map(abs,actual));self.assertGreaterEqual(current,last);last=current
                self.assertEqual(len(actual),len(baseline))
                self.assertTrue(all(-32768<=x<=32767 for x in actual))
            self.assertEqual(last,32767)
