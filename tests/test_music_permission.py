import copy,json,unittest,zipfile
import test_simple_calibration as s

class Runtime(s.Runtime):
    def __init__(self,*args,needs_permission=True,**kwargs):
        self.needs_permission=needs_permission;self.pending=None;self.requests=[];self.starts=[];self.cleared_while_pending=False
        super().__init__(*args,**kwargs)
    def execute(self,b,env=None):
        env={} if env is None else env
        while b is not None:
            nxt=b.find('next/block');one=copy.copy(b);one[:]=[e for e in b if e.tag!='next'];m=one.find('mutation')
            if m is not None and m.get('instance_name')=='音乐检查' and one.get('type')=='component_set_get' and m.get('set_or_get')=='set' and m.get('property_name')=='Source':
                value=self.value(one,'VALUE',env);self.requests.append(value)
                if value and self.needs_permission:self.pending=value
                else:
                    if not value and self.pending:self.cleared_while_pending=True
                    super().execute(one,env)
            else:
                start=m is not None and m.get('instance_name')=='音乐检查' and m.get('method_name')=='Start'
                if start:self.starts.append(self.components['音乐检查'].get('Source',''))
                if start and (self.pending or not self.components['音乐检查'].get('Source','')):self.check_playing=False
                else:super().execute(one,env)
            b=nxt
    def grant(self):
        self.needs_permission=False;path=self.pending;self.pending=None
        if path:
            self.components['音乐检查']['Source']=path;self.check_playing=False
            if path in self.missing:self.event('Screen1','ErrorOccurred',组件='音乐检查',函数='Source',编号=701,消息='missing')
    def deny(self):
        self.pending=None;self.event('Screen1','PermissionDenied',组件='音乐检查',函数='Source',权限='android.permission.READ_MEDIA_AUDIO')
    def tick(self):
        if self.components['音乐检查时钟']['TimerEnabled']:self.event('音乐检查时钟','Timer')

class MusicPermission(unittest.TestCase):
    def home(self,**kwargs):r=Runtime(**kwargs);r.initialize();return r
    def read(self,r):r.event('谱面文件','GotText',内容=json.dumps(['测试','song.mp3',500,2,120,4,4000,[[1,1000]]],ensure_ascii=False))
    def pick(self,r,path='content://music'):
        r.pick('选谱','content://chart');self.read(r);r.pick('选音乐',path)
    def test_first_selection_waits_for_permission_then_completes(self):
        r=self.home();self.pick(r)
        self.assertTrue(r.globals['正在检查']);self.assertFalse(r.components['开始']['Enabled'])
        self.assertEqual(r.pending,'content://music');self.assertEqual(r.starts,[]);self.assertFalse(r.cleared_while_pending)
        self.assertNotIn('保存的谱面',r.db)
        for i in range(120):r.now+=1000;r.tick()
        self.assertEqual(r.requests,['content://music']);self.assertEqual(r.starts,[])
        self.assertTrue(r.globals['正在检查']);r.grant();r.tick()
        self.assertTrue(r.components['开始']['Enabled']);self.assertEqual(r.starts,['content://music'])
        self.assertEqual(r.db['保存的谱面'],[['测试','content://chart','content://music']])
        self.assertFalse(r.globals['正在检查']);self.assertFalse(r.components['音乐检查时钟']['TimerEnabled'])
        self.assertEqual(r.components['音乐检查']['Source'],'');self.assertFalse(r.check_playing)
        self.assertNotIn('失败',r.components['读取状态']['Text'])
    def test_permission_denial_recovers_without_reprompt_or_false_save(self):
        r=self.home();self.pick(r);r.deny();r.tick()
        self.assertFalse(r.components['开始']['Enabled']);self.assertTrue(r.components['选音乐']['Enabled'])
        self.assertFalse(r.components['音乐检查时钟']['TimerEnabled']);self.assertIn('访问权限',r.components['读取状态']['Text'])
        self.assertNotIn('保存的谱面',r.db);self.assertEqual(r.requests.count('content://music'),1)
        r.pick('选音乐','content://music');r.grant();r.tick();self.assertTrue(r.components['开始']['Enabled'])
    def test_already_granted_selection_finishes_synchronously(self):
        r=self.home(needs_permission=False);self.pick(r)
        self.assertTrue(r.components['开始']['Enabled']);self.assertFalse(r.components['音乐检查时钟']['TimerEnabled'])
        self.assertEqual(r.db['保存的谱面'][0][2],'content://music')
    def test_missing_file_after_grant_is_not_reported_success(self):
        r=self.home();r.missing.add('content://missing');self.pick(r,'content://missing');r.grant();r.tick()
        self.assertFalse(r.components['开始']['Enabled']);self.assertNotIn('保存的谱面',r.db)
        self.assertIn('音乐源文件找不到',r.components['读取状态']['Text']);self.assertEqual(r.starts,[])
        self.assertTrue(r.components['选音乐']['Enabled'])
    def test_restore_saved_association_keeps_pending_uri_after_chart_callback(self):
        r=self.home(db={'保存的谱面':[['测试','content://chart','content://saved']]})
        r.components['保存谱面']['SelectionIndex']=1;r.event('保存谱面','AfterPicking');self.read(r)
        self.assertEqual(r.globals['检查音乐地址'],'content://saved');self.assertTrue(r.globals['读取中'])
        self.assertFalse(r.components['选谱']['Enabled']);self.assertFalse(r.components['保存谱面']['Enabled'])
        r.grant();r.tick();self.assertTrue(r.components['开始']['Enabled']);self.assertEqual(r.globals['当前谱'][1],'content://saved')
    def test_pending_selection_cannot_be_replaced(self):
        r=self.home();self.pick(r);r.pick('选音乐','content://other')
        self.assertEqual(r.pending,'content://music');self.assertEqual(r.requests,['content://music'])
        r.grant();r.tick();self.assertEqual(r.globals['当前谱'][1],'content://music')
    def test_volume_label_is_plain_before_and_after_adjustment(self):
        r=self.home();self.assertEqual(r.components['打击音量标题']['Text'],'打击音量：20%')
        r.event('打击音量滑条','PositionChanged',位置=73)
        self.assertEqual(r.components['打击音量标题']['Text'],'打击音量：73%')
        with zipfile.ZipFile(s.AIA) as z:
            scm=z.read(next(n for n in z.namelist() if n.endswith('/Screen1.scm'))).decode()
            self.assertNotIn('原音量',scm)
