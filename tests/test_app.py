import json,unittest
from runtime import Runtime,Comp

LANES=['轨道一','轨道二','轨道三','轨道四']
GOLD=0xFFFFD54F-2**32

def chart(notes,end=4000,name='测试'):return [name,'song.mp3',500,2,120,4,end,notes]

class Home(unittest.TestCase):
    def home(self,storage=None):return Runtime(storage=storage).initialize()
    def load(self,r,text,uri='content://chart'):
        r.pick('选谱',uri);self.assertEqual(r.reads[-1],uri);r.event('谱面文件','GotText',text)
    def ready(self,storage=None):
        r=self.home(storage);self.load(r,json.dumps(chart([[1,1000],[2,1000,2000]])));r.pick('选音乐','content://music');return r
    def test_import_valid_chart_with_bom_and_tag_line(self):
        r=self.home();self.load(r,'﻿'+json.dumps(chart([[1,1000],[2,1500,2500]]),ensure_ascii=False)+'\r\n//tags:[["副歌",1000]]\r\n')
        self.assertEqual(len(r.globals['当前谱']),8);self.assertEqual(r.components['当前谱名']['Text'],'测试')
        self.assertTrue(r.components['选音乐']['Enabled']);self.assertFalse(r.components['开始']['Enabled']);self.assertEqual(r.alerts,[])
    def test_invalid_charts_are_rejected(self):
        for notes in [[[1,2000],[2,1000]],[[1,1000,2000],[1,1500]],[[1,1000,2000],[1,2000]],[[5,1000]],[[1,1000,1000]],[[1,'x']],[[1]],[]]:
            with self.subTest(notes=notes):
                r=self.home();self.load(r,json.dumps(chart(notes)))
                self.assertEqual(r.globals['当前谱'],[]);self.assertEqual(len(r.alerts),1);self.assertFalse(r.components['选音乐']['Enabled'])
        r=self.home();self.load(r,'[1,2');self.assertEqual(r.globals['当前谱'],[]);self.assertTrue(r.components['选谱']['Enabled'])
        r=self.home();self.load(r,json.dumps(['a',1]));self.assertEqual(r.alerts,['谱面必须为合法八项列表'])
    def test_cross_lane_chords_are_valid(self):
        r=self.home();self.load(r,json.dumps(chart([[1,1000],[2,1000],[3,1000,2000],[4,1000],[3,2001]])));self.assertEqual(r.alerts,[])
    def test_music_check_waits_for_async_permission(self):
        s={};r=self.home(s);self.load(r,json.dumps(chart([[1,1000]])));r.needs_permission=True;r.pick('选音乐','content://music')
        for _ in range(30):r.tick(100)
        self.assertTrue(r.globals['正在检查']);self.assertEqual(r.alerts,[]);self.assertFalse(r.components['选音乐']['Enabled'])
        r.grant();r.tick(100)
        self.assertTrue(r.globals['音乐就绪']);self.assertTrue(r.components['开始']['Enabled']);self.assertEqual(r.components['音乐检查']['Source'],'')
        self.assertEqual(s['保存的谱面'],[['测试','content://chart','content://music']]);self.assertEqual(r.components['保存谱面']['Text'],'保存的谱面（1）')
    def test_permission_denied_and_missing_music_then_retry(self):
        r=self.home();self.load(r,json.dumps(chart([[1,1000]])));r.needs_permission=True;r.pick('选音乐','content://music');r.deny();r.tick(100)
        self.assertFalse(r.globals['音乐就绪']);self.assertIn('未获得音乐访问权限',r.alerts[-1]);self.assertTrue(r.components['选音乐']['Enabled'])
        r.needs_permission=False;r.missing.add('content://gone');r.pick('选音乐','content://gone');self.assertIn('找不到',r.alerts[-1]);self.assertNotIn('保存的谱面',r.storage)
        r.pick('选音乐','content://music');self.assertTrue(r.globals['音乐就绪'])
    def test_saved_chart_restores_and_reconnects_music(self):
        s={};self.ready(s);r=self.home(s)
        self.assertEqual(r.components['保存谱面']['Elements'],['测试']);r.components['保存谱面']['SelectionIndex']=1;r.event('保存谱面','AfterPicking')
        self.assertEqual(r.reads,['content://chart']);r.event('谱面文件','GotText',json.dumps(chart([[1,1000]])))
        self.assertTrue(r.globals['音乐就绪']);self.assertEqual(r.globals['当前谱'][1],'content://music');self.assertEqual(len(s['保存的谱面']),1)
    def test_missing_saved_chart_keeps_record(self):
        s={};self.ready(s);r=self.home(s);r.components['保存谱面']['SelectionIndex']=1;r.event('保存谱面','AfterPicking')
        r.error('谱面文件','ReadFrom','missing');self.assertEqual(r.components['当前谱名']['Text'],'源谱面不可用');self.assertEqual(len(s['保存的谱面']),1)
        self.assertTrue(r.components['选谱']['Enabled'])
    def test_start_passes_chart_delay_approach_and_hit_switch(self):
        s={};r=self.ready(s);r.components['延迟输入']['Text']='-120';r.components['游玩过屏输入']['Text']='700';r.components['打击音设置']['Checked']=False
        r.click('开始');name,value=r.opened
        self.assertEqual(name,'Play');self.assertEqual(value[:8],r.globals['当前谱']);self.assertEqual(value[8:],['-120','700',False,0,4000,False]);self.assertEqual(s['谱面延迟'],'-120')
        for delay,approach in [('401','500'),('abc','500'),('0','0'),('0','x')]:
            r=self.ready();r.components['延迟输入']['Text']=delay;r.components['游玩过屏输入']['Text']=approach;r.click('开始')
            self.assertIsNone(r.opened);self.assertEqual(len(r.alerts),1)
    def test_practice_range_and_autoplay(self):
        r=self.ready();r.components['练习设置']['Checked']=True;r.event('练习设置','Changed');self.assertTrue(r.components['练习区']['Visible'])
        r.components['练习开始']['Text']='1.5';r.components['自动播放']['Checked']=True;r.click('开始');self.assertEqual(r.opened[1][11:],[1500,4000,True])
        r=self.ready();r.components['练习设置']['Checked']=True;r.components['练习开始']['Text']='';r.components['练习结束']['Text']='2';r.click('开始')
        self.assertEqual(r.opened[1][11:],[0,2000,False])
        for start,end in [('3','2'),('-1',''),('x',''),('1','1')]:
            r=self.ready();r.components['练习设置']['Checked']=True;r.components['练习开始']['Text']=start;r.components['练习结束']['Text']=end;r.click('开始')
            self.assertIsNone(r.opened);self.assertIn('练习',r.alerts[-1])
        r=self.ready();r.components['练习开始']['Text']='x';r.click('开始');self.assertEqual(r.opened[1][11:],[0,4000,False])
    def test_settings_persist(self):
        s={'谱面延迟':900,'打击音效':False};r=self.home(s)
        self.assertEqual(r.components['延迟输入']['Text'],0);self.assertFalse(r.components['打击音设置']['Checked'])
        r.components['打击音设置']['Checked']=True;r.event('打击音设置','Changed');self.assertTrue(s['打击音效'])
        r.components['延迟输入']['Text']='35';r.event('延迟输入','LostFocus');self.assertEqual(Runtime(storage=s).initialize().components['延迟输入']['Text'],'35')

class Calibration(unittest.TestCase):
    def open(self,delay='0'):
        r=Runtime().initialize();r.components['延迟输入']['Text']=delay;r.click('校准入口');return r
    def sounds(self,r,name):
        start=r.globals['校准起点'];return [t-start for n,t in r.plays if n==name]
    def test_metronome_and_hit_share_one_clock(self):
        for delay in [-400,0,250,400]:
            r=self.open(str(delay));r.advance(5000,10)
            beats=self.sounds(r,'校准节拍');hits=self.sounds(r,'校准打击')
            self.assertEqual(len(beats),5);self.assertTrue(all(abs(t-(500+i*1000))<10 for i,t in enumerate(beats)))
            self.assertTrue(all(abs(t-(500+i*1000+delay))<10 for i,t in enumerate(hits)));self.assertGreaterEqual(len(hits),4)
            self.assertFalse(r.components['首页']['Visible'])
    def test_adjust_apply_cancel(self):
        r=self.open('100');self.assertEqual(r.globals['试听延迟'],'100');r.click('校准增加');self.assertEqual(r.components['校准数值']['Text'],110)
        for _ in range(40):r.click('校准增加')
        self.assertEqual(r.components['校准数值']['Text'],400);r.click('校准应用')
        self.assertEqual(r.components['延迟输入']['Text'],400);self.assertEqual(r.storage['谱面延迟'],400);self.assertTrue(r.components['首页']['Visible']);self.assertFalse(r.components['校准时钟']['TimerEnabled'])
        r=self.open('50');r.components['校准数值']['Text']='999';r.event('校准数值','LostFocus');self.assertIn('-400',r.components['校准提示']['Text'])
        r.click('校准应用');self.assertTrue(r.components['校准页']['Visible']);r.click('校准返回');self.assertEqual(r.components['延迟输入']['Text'],'50')
        r=self.open();r.event('Screen1','BackPressed');self.assertTrue(r.components['首页']['Visible']);self.assertFalse(r.closed)
    def test_stalled_callback_skips_late_sounds_and_clock_reversal_restarts(self):
        r=self.open();r.advance(400,10);r.tick(900)
        self.assertEqual(self.sounds(r,'校准节拍'),[]);r.advance(1000,10);self.assertEqual(len(self.sounds(r,'校准节拍')),1)
        start=r.globals['校准起点'];r.now-=5000;r.tick(10);self.assertNotEqual(r.globals['校准起点'],start);self.assertEqual(r.globals['校准节拍号'],0)

class Play(unittest.TestCase):
    def play(self,notes,delay=0,approach=500,hit=True,end=4000,start=0,stop=None,auto=False):
        r=Runtime('Play',chart(notes,end)+[delay,approach,hit,start,end if stop is None else stop,auto]).initialize();r.advance(3000);self.assertTrue(r.globals['已播放']);return r
    def at(self,r,t):r.now=r.globals['起点']+t
    def down(self,r,lane,t=None):
        if t is not None:self.at(r,t)
        r.event(LANES[lane-1],'TouchDown',45,100)
    def up(self,r,lane,t=None):
        if t is not None:self.at(r,t)
        r.event(LANES[lane-1],'TouchUp',45,100)
    def states(self,r):return [n[2] for g in r.globals['游玩分段'] for n in g]
    def test_head_windows_and_accuracy(self):
        for d,grade in [(-161,None),(-160,2),(-81,2),(-80,3),(0,3),(80,3),(81,2),(160,2),(161,1)]:
            with self.subTest(d=d):
                r=self.play([[1,1000]]);self.down(r,1,1000+d);self.at(r,1300);r.tick(0)
                self.assertEqual(self.states(r),[grade or 1])
        r=self.play([[1,1000],[2,1000],[3,1000]]);self.down(r,1,1000);self.up(r,1);self.down(r,2,1100);r.advance(400)
        self.assertEqual((r.globals['完美'],r.globals['良好'],r.globals['漏击']),(1,1,1));self.assertAlmostEqual(r.globals['准确率'],55)
    def test_hold_settles_once_at_tail(self):
        r=self.play([[1,1000,2000]]);self.down(r,1,1000);self.assertEqual(r.globals['连击'],0);self.assertEqual(self.states(r),[5])
        self.at(r,1999);r.tick(0);self.assertEqual(r.globals['连击'],0);self.at(r,2000);r.tick(0);self.assertEqual(self.states(r),[3]);self.assertEqual(r.globals['完美'],1)
        self.up(r,1,2010);self.assertEqual(r.globals['漏击'],0)
    def test_hold_release_or_slide_out_is_unrecoverable_miss(self):
        r=self.play([[1,1000,2000]]);self.down(r,1,1000);self.up(r,1,1500);self.down(r,1,1600);self.at(r,2100);r.tick(0);self.assertEqual(self.states(r),[1])
        for x,y in [(0,100),(90,100),(45,0),(45,430)]:
            r=self.play([[1,1000,2000]]);self.down(r,1,1000);r.event('轨道一','Dragged',45,100,45,100,x,y,False);self.assertEqual(self.states(r),[1])
        r=self.play([[1,1000,2000]]);self.down(r,1,1000);self.up(r,1,2000.5);self.assertEqual(self.states(r),[3])
    def test_unhit_hold_and_late_head_miss(self):
        r=self.play([[1,1000,1100],[2,1000,3000]]);self.at(r,1200);r.tick(0);self.assertEqual(self.states(r),[1,1])
    def test_hit_sound_only_on_valid_heads(self):
        r=self.play([[1,1000],[2,1000,1500]]);self.down(r,3,1000);self.down(r,1,1000);self.down(r,2,1000);self.up(r,2,1600);self.down(r,1,2000)
        self.assertEqual(len(r.plays),2)
        r=self.play([[1,1000]],hit=False);self.down(r,1,1000);self.assertEqual(r.plays,[]);self.assertEqual(r.globals['完美'],1)
        r=self.play([[1,1000],[1,2000]]);r.event('Play','ErrorOccurred',Comp('打击音'),'Play',0,'x');self.down(r,1,1000);self.assertEqual(r.plays,[]);self.assertEqual(r.globals['状态'],1)
    def test_delay_shifts_heads_and_tails(self):
        r=self.play([[1,1000,2000]],delay=300);n=r.globals['游玩分段'][0][0];self.assertEqual((n[1],n[3]),(1300,2300));self.assertEqual(r.globals['结束时间'],4300)
    def test_chord_flags_across_segments_and_gold_border(self):
        notes=[[1,1000],[2,1000],[3,1500,2500],[4,1500],[1,2000]]+[[i%4+1,3000+i*10] for i in range(58)]+[[1,4000],[2,4000]]
        r=self.play(notes);flags=[n[4] for g in r.globals['游玩分段'] for n in g]
        self.assertEqual(flags[:5],[True,True,True,True,False]);self.assertFalse(any(flags[5:63]));self.assertEqual(flags[63:],[True,True])
        r=self.play([[1,1000],[2,1000],[3,1000,1800],[4,1200]]);self.at(r,700);r.tick(0)
        gold={n for n,d in r.draws.items() for x in d if x['color']==GOLD};self.assertEqual(gold,{'轨道一','轨道二','轨道三'})
        for x in [x for d in r.draws.values() for x in d if x['color']==GOLD]:self.assertEqual((x['width'],x['args'][0]),(24,5))
        lane=r.draws['轨道一'];i=next(i for i,x in enumerate(lane) if x['color']==GOLD);self.assertEqual(lane[i+1]['width'],16);self.assertNotEqual(lane[i+1]['color'],GOLD)
    def test_finish_restart_and_back(self):
        r=self.play([[1,1000]]);self.down(r,1,1000);self.at(r,4000);r.tick(0)
        self.assertEqual(r.globals['状态'],3);self.assertIn('游玩完成',r.components['信息']['Text']);self.assertFalse(r.components['轨道区']['Visible'])
        r.click('重开');self.assertEqual(r.globals['状态'],1);self.assertEqual(self.states(r),[0]);self.assertEqual(r.globals['完美'],0);self.assertTrue(r.components['轨道区']['Visible'])
        r.click('返回');self.assertTrue(r.closed);self.assertFalse(r.components['时钟']['TimerEnabled'])
    def test_music_that_never_plays_fails_cleanly(self):
        r=Runtime('Play',chart([[1,1000]])+[0,500,True,0,4000,False]).initialize();r.music_fail=True;r.advance(3000);r.advance(1600)
        self.assertEqual(r.globals['状态'],3);self.assertIn('无法播放',r.alerts[-1]);self.assertFalse(r.components['时钟']['TimerEnabled'])
    def test_countdown_text_and_judgement_text(self):
        r=Runtime('Play',chart([[1,1000]])+[0,500,True,0,4000,False]).initialize();r.tick(0)
        self.assertEqual(r.texts['轨道一'][0][0],'准备 3');self.assertEqual(r.texts['轨道一'][0][1],180)
        r.advance(3000);self.down(r,1,1000);self.at(r,1100);r.tick(0);self.assertEqual(r.texts['轨道二'][0][0],'PERFECT')
    def test_practice_segment_seeks_music_and_keeps_only_its_notes(self):
        notes=[[1,1000],[2,3000],[3,5000,6000],[4,8000]]
        r=self.play(notes,end=9000,start=3000,stop=6000);v=r.components['练习音乐']
        self.assertEqual((v['Source'],v['Position'],v['Playing']),('song.mp3',3000,True));self.assertEqual(r.globals['用时'],3000);self.assertIsNone(r.music_started)
        self.assertEqual(r.globals['物量'],2);self.assertEqual([n[1] for g in r.globals['游玩分段'] for n in g],[3000,5000]);self.assertEqual(r.globals['结束时间'],6500)
        self.down(r,2,3000);self.assertEqual(r.globals['完美'],1);self.at(r,6500);r.tick(0)
        self.assertEqual(r.globals['状态'],3);self.assertEqual(r.globals['漏击'],1);self.assertFalse(v['Playing'])
        r.click('重开');self.assertEqual((v['Position'],v['Playing']),(3000,False));self.assertEqual(r.globals['用时'],0)
        r.tick(0);self.assertEqual(r.texts['轨道一'][0][0],'准备 3')
    def test_practice_start_with_negative_delay_and_plain_start(self):
        r=self.play([[1,2000],[2,3000]],delay=-200,start=3000);self.assertEqual(r.components['练习音乐']['Position'],2800);self.assertEqual(r.globals['用时'],2800)
        self.assertEqual([n[1] for g in r.globals['游玩分段'] for n in g],[2800])
        r=self.play([[1,1000],[2,3000]],stop=2000);self.assertFalse(r.components['练习音乐']['Playing']);self.assertIsNotNone(r.music_started)
        self.assertEqual(r.globals['物量'],1);self.assertEqual(r.globals['结束时间'],2000)
    def test_autoplay_hits_every_note_perfect_and_follows_hit_switch(self):
        r=self.play([[1,1000],[2,1000,2000],[3,1500],[4,2500,3000]],auto=True)
        self.down(r,1,900);self.at(r,1010);r.tick(0);self.assertEqual(self.states(r)[:2],[3,5]);self.assertEqual(r.globals['连击'],1)
        self.up(r,2,1200);r.event('轨道二','Dragged',45,100,45,100,0,0,False);self.assertEqual(self.states(r)[1],5)
        r.advance(3000)
        self.assertEqual((r.globals['完美'],r.globals['良好'],r.globals['漏击']),(4,0,0));self.assertEqual(len(r.plays),4)
        self.assertIn('AutoPlay 完成',r.components['信息']['Text'])
        r=self.play([[1,1000],[2,1500,2000]],hit=False,auto=True);r.advance(3000);self.assertEqual(r.globals['完美'],2);self.assertEqual(r.plays,[])
