from pathlib import Path
import sys,copy,json,unittest,itertools,zipfile,math

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'archive/历史目录/tests'))
import test_local as old
import playback_runtime as base
base.AIA=ROOT/'archive/releases/Rail4K_0924_2.aia'
LANES=['轨道一','轨道二','轨道三','轨道四']

class Runtime(old.Runtime):
    def __init__(self,*a,**kw):
        self.storage={};self.save_requests=[];self.copy_success=True;self.copy_requests=[]
        super().__init__(*a,**kw)
        for n in LANES:
            if n in self.components:self.components[n].update(Width=90,Height=430)
        if '轨道区' in self.components:self.components['轨道区'].update(Width=360,Height=430)
    def evaluate(self,b,env):
        if b.get('type')=='helpers_dropdown':return base.field(b,'OPTION')
        if b.get('type')=='text_replace_all':return self.value(b,'TEXT',env).replace(self.value(b,'SEGMENT',env),self.value(b,'REPLACEMENT',env))
        m=b.find('mutation')
        if b.get('type')=='component_method' and m.get('method_name')=='CopyFile':
            args=[self.value(b,'ARG'+str(i),env) for i in range(4)];self.copy_requests.append(args)
            if self.copy_success:self.storage[args[3]]=self.storage[args[1]]
            return self.copy_success
        return super().evaluate(b,env)
    def execute(self,b,env=None):
        env={} if env is None else env
        while b is not None:
            nxt=b.find('next/block');one=copy.copy(b);one[:]=[e for e in b if e.tag!='next'];m=one.find('mutation')
            if one.get('type')=='component_method' and m.get('component_type')=='Canvas':
                name=self.value(one,'COMPONENT',env);kind=m.get('method_name');args=[self.value(one,'ARG'+str(i),env) for i in range(len(one.findall('value'))-1)]
                if kind=='Clear':
                    self.draws=[d for d in self.draws if d['canvas']!=name];self.text_draws=[d for d in self.text_draws if d['canvas']!=name]
                elif kind=='DrawLine':
                    assert all(math.isfinite(x) for x in args)
                    self.draws.append(dict(canvas=name,args=args,color=self.components[name]['PaintColor'],width=self.components[name]['LineWidth']))
                elif kind=='DrawText':self.text_draws.append(dict(canvas=name,text=args[0],x=args[1],y=args[2]))
                else:raise ValueError(kind)
            elif one.get('type')=='component_method' and m.get('method_name')=='SaveFile':
                args=[self.value(one,'ARG'+str(i),env) for i in range(2)];self.save_requests.append(args)
            else:super().execute(one,env)
            b=nxt
    def tap(self,lane):self.event(LANES[lane-1],'TouchDown',横坐标=45,纵坐标=100)
    def release(self,lane):self.event(LANES[lane-1],'TouchUp',横坐标=45,纵坐标=100)
    def hit(self,lane,time):self.advance(time);self.tap(lane)
    def saved(self):
        data,path=self.save_requests[-1];self.storage[path]=data;self.event('谱面文件','AfterFileSaved',文件名=path)
    def pick(self,name,uri):self.components[name]['Selection']=uri;self.event(name,'AfterPicking')

class Tests(unittest.TestCase):
    def chart(self,notes=None,mode=1):return ['多押','content://music',1000,mode,137,3,4000,notes or []]
    def record(self,mode=1,merge=True):
        r=Runtime(screen='Recorder',start=self.chart(mode=mode)+[merge]);r.initialize();return r
    def play(self,notes):
        r=Runtime(screen='Play',start=self.chart(notes));r.initialize();return r
    def states(self,r):return [n[2] for group in r.globals['游玩分段'] for n in group]
    def export(self,r):
        r.event('结束','Click');r.event('导出','Click')
        while r.globals['正在导出']:r.event('导出时钟','Timer')
        return r.globals['导出全文']
    def test_held_finger_and_quad(self):
        r=self.record()
        for lane in range(1,5):r.hit(lane,1000+10*lane)
        self.assertEqual(r.globals['谱面'],[[i,1010] for i in range(1,5)])
        self.assertEqual(r.globals['按住轨道'],[1]*4)
        r.release(2);r.hit(2,2000)
        self.assertEqual(r.globals['谱面'][-1],[2,2000])
    def test_release_single_taps(self):
        r=self.record();r.hit(1,1000);r.release(1);r.hit(2,1020)
        self.assertEqual(r.globals['谱面'],[[1,1000],[2,1020]])
        r.release(2);r.hit(2,1050)
        self.assertEqual(r.globals['谱面'][-1],[2,1050])
    def test_window_and_disable(self):
        r=self.record();r.hit(1,1000);r.hit(2,1040);r.hit(3,1041)
        self.assertEqual(r.globals['谱面'],[[1,1000],[2,1000],[3,1041]])
        r=self.record(merge=False);r.hit(1,1000);r.hit(2,1020)
        self.assertEqual(r.globals['谱面'],[[1,1000],[2,1020]])
    def test_duplicate_and_restart(self):
        r=self.record();r.hit(1,1000);r.hit(1,1010);r.hit(2,1020)
        self.assertEqual(r.globals['谱面'],[[1,1000],[2,1000]])
        r.event('重开','Click');self.assertEqual(r.globals['按住轨道'],[0]*4);self.assertEqual(r.globals['多押时间'],-1)
    def test_snap_decimal(self):
        r=self.record(mode=2);r.hit(1,1000);r.hit(4,1020);r.release(1);r.release(4);r.hit(2,1210);r.hit(3,1240)
        notes=r.globals['谱面'];self.assertEqual(notes[0][1],notes[1][1]);self.assertEqual(notes[2][1],notes[3][1])
        for _,t in notes:self.assertAlmostEqual((t-1000)/(60000/137/3),round((t-1000)/(60000/137/3)))
    def test_play_all_permutations(self):
        for order in itertools.permutations(range(1,5)):
            r=self.play([[i,1000] for i in range(1,5)]);r.advance(1000)
            for lane in order:r.tap(lane)
            self.assertEqual(self.states(r),[3]*4);self.assertEqual(r.globals['准确率'],100);self.assertEqual(r.globals['连击'],4)
    def test_four_canvases_and_centered_text(self):
        r=self.play([[i,1000] for i in range(1,5)]);r.advance(800)
        notes=r.notes();self.assertEqual(len(notes),4);self.assertEqual({d['canvas'] for d in notes},set(LANES));self.assertEqual(len({d['args'][1] for d in notes}),1)
        self.assertTrue(all(d['args'][0]==9 and d['args'][2]==81 for d in notes))
        self.assertEqual({d['x']+LANES.index(d['canvas'])*90 for d in r.text_draws},{180})
    def test_independent_judgements_and_finish(self):
        r=self.play([[i,1000] for i in range(1,5)]);r.hit(3,1000);r.hit(1,1120);r.advance(1200)
        self.assertEqual(self.states(r),[2,1,3,1]);self.assertAlmostEqual(r.globals['准确率'],41.25)
        r.advance(4000);self.assertIn('游玩完成',r.components['信息']['Text']);self.assertFalse(r.components['轨道区']['Visible'])
        r.event('重开','Click');self.assertTrue(r.components['轨道区']['Visible'])
    def test_segment_boundary(self):
        r=self.play([[1,i*10] for i in range(62)]+[[i,1000] for i in range(1,5)]);r.advance(1000)
        for i in [4,2,3,1]:r.tap(i)
        self.assertEqual(self.states(r)[62:],[3]*4)
    def test_export_save_import(self):
        r=self.record()
        for i in range(4):r.hit(i+1,1000+i*10)
        data=self.export(r);chart=json.loads(data);self.assertEqual(chart[7],[[i,1000] for i in range(1,5)])
        r.pick('分享全文','content://chart');self.assertNotIn('已保存',r.components['导出进度']['Text']);self.assertEqual(r.copy_requests,[])
        r.saved();self.assertEqual(r.storage['content://chart'],data);self.assertIn('已保存',r.components['导出进度']['Text'])
        h=Runtime();h.initialize();h.pick('选谱','content://chart');self.assertEqual(h.file_requests[-1],'content://chart');h.event('谱面文件','GotText',内容=data)
        self.assertEqual(h.globals['当前谱'][7],chart[7]);self.assertFalse(h.components['开始']['Enabled'])
        h.pick('选音乐','content://new-song');h.event('开始','Click');self.assertEqual(h.opened[1][1],'content://new-song')
    def test_failed_save_retry_and_cancel(self):
        r=self.record();r.hit(1,1000);data=self.export(r);r.pick('分享全文','content://chart');r.copy_success=False;r.saved()
        self.assertFalse(r.globals['正在保存']);self.assertEqual(r.globals['导出全文'],data);self.assertTrue(r.components['分享全文']['Enabled'])
        r.copy_success=True;r.pick('分享全文','content://chart');r.saved();self.assertEqual(r.storage['content://chart'],data)
        r.event('Recorder','ErrorOccurred',组件='分享全文',函数='Open',编号=1,消息='取消选择');self.assertFalse(r.globals['正在保存']);self.assertEqual(r.globals['导出全文'],data)
    def test_large_export(self):
        r=self.record();notes=[[i%4+1,i*123.4567] for i in range(3000)];r.globals.update(谱面=notes,物量=len(notes),状态=4,结束时间=notes[-1][1]+500)
        data=self.export(r);self.assertEqual(json.loads(data)[7],notes);self.assertLessEqual(len(r.components['谱面文本']['Text']),2100)
        r.pick('分享全文','content://large');r.saved();self.assertEqual(r.storage['content://large'],data)
    def test_music_settings(self):
        r=Runtime(screen='EditorSettings');r.components['名称输入']['Text']='多押';r.pick('音乐输入','content://music')
        for enable in [True,False]:
            r.components['多押设置']['Checked']=enable;r.event('录制','Click');self.assertEqual(r.opened[1][8],enable);self.assertEqual(r.opened[1][1],'content://music')
    def test_import_bom_cancel_and_invalid(self):
        h=Runtime();h.initialize();h.pick('选谱','content://chart');h.event('谱面文件','GotText',内容='\ufeff'+json.dumps(self.chart([[1,1000]])))
        self.assertTrue(h.globals['有效']);h.pick('选音乐','content://music');before=copy.deepcopy(h.globals['当前谱'])
        h.event('Screen1','ErrorOccurred',组件='选谱',函数='Open',编号=1,消息='取消选择')
        self.assertEqual(h.globals['当前谱'],before);self.assertTrue(h.components['开始']['Enabled'])
        for data in ['', '[]', 'null', 'oops']:
            h.pick('选谱','content://chart');h.event('谱面文件','GotText',内容=data)
            self.assertFalse(h.components['开始']['Enabled']);self.assertFalse(h.components['选音乐']['Enabled']);self.assertEqual(h.globals['当前谱'],[])
        h.pick('选谱','content://bad');h.event('Screen1','ErrorOccurred',组件='谱面文件',函数='ReadFrom',编号=1,消息='无法读取')
        self.assertTrue(h.components['选谱']['Enabled']);self.assertFalse(h.globals['读取中'])
    def test_structure(self):
        with zipfile.ZipFile(base.AIA) as z:
            self.assertFalse(any('external_comps' in n for n in z.namelist()))
            for n in z.namelist():
                if n.endswith('.bky'):self.assertNotIn(b'LocalFiles',z.read(n))
        for screen in ['Play','Recorder']:
            r=Runtime(screen=screen,start=self.chart()+[True]);self.assertNotIn('画布',r.components);self.assertNotIn('本地文件',r.components)
            for n in LANES:self.assertIn((n,'TouchDown'),r.events)

if __name__=='__main__':unittest.main(verbosity=2)
