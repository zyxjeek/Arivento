import copy,json,unittest,zipfile
from pathlib import Path
import test_hold as hold

AIA=Path(__file__).resolve().parents[1]/'archive/hold_base_1016/Saved_candidate.aia'
hold.old.base.AIA=AIA

class Runtime(hold.AndroidRuntime):
    def __init__(self,*args,db=None,**kwargs):
        self.db={} if db is None else db
        self.missing=set();self.check_playing=False;self.writes=0
        super().__init__(*args,**kwargs)
    def evaluate(self,b,env):
        m=b.find('mutation')
        if m is not None and m.get('instance_name')=='本地记录':return copy.deepcopy(self.db.get(self.value(b,'ARG0',env),self.value(b,'ARG1',env)))
        if m is not None and m.get('instance_name')=='音乐检查' and m.get('property_name')=='IsPlaying':return self.check_playing
        return super().evaluate(b,env)
    def execute(self,b,env=None):
        env={} if env is None else env
        while b is not None:
            nxt=b.find('next/block');one=copy.copy(b);one[:]=[e for e in b if e.tag!='next'];m=one.find('mutation')
            if one.get('type')=='component_method' and m.get('instance_name')=='本地记录':
                self.db[self.value(one,'ARG0',env)]=copy.deepcopy(self.value(one,'ARG1',env));self.writes+=1
            elif m is not None and m.get('instance_name')=='音乐检查':
                if one.get('type')=='component_set_get':
                    source=self.value(one,'VALUE',env);self.components['音乐检查']['Source']=source;self.check_playing=False
                    if source in self.missing:self.event('Screen1','ErrorOccurred',组件='音乐检查',函数='Source',编号=701,消息='missing')
                elif m.get('method_name')=='Start':
                    self.assert_muted();self.check_playing=self.components['音乐检查'].get('Source','') not in self.missing
                else:self.check_playing=False
            else:super().execute(one,env)
            b=nxt
    def assert_muted(self):assert str(self.components['音乐检查']['Volume'])=='0'

class Saved(unittest.TestCase):
    def chart(self,name='谱面',notes=None):return [name,'song.mp3',500,2,120,4,4000,notes or [[1,1000,2000]]]
    def home(self,db=None):
        r=Runtime(db=db);r.initialize();return r
    def read(self,r,name='谱面'):
        r.event('谱面文件','GotText',内容=json.dumps(self.chart(name),ensure_ascii=False))
    def choose(self,r,path='content://chart',music='content://music',name='谱面'):
        r.pick('选谱',path);self.read(r,name);r.pick('选音乐',music)
    def test_home_layout(self):
        r=self.home();self.assertEqual(r.components['标题']['Text'],'Arivento')
        self.assertEqual(r.components['保存谱面']['Text'],'保存的谱面（0）')
        with zipfile.ZipFile(AIA) as z:
            d=json.loads(z.read(next(n for n in z.namelist() if n.endswith('/Screen1.scm'))).decode().split('$JSON')[1].rsplit('|#',1)[0])['Properties']
            self.assertEqual(d['Title'],'Arivento');self.assertEqual(d['$Components'][0]['$Components'][-1]['$Components'][0]['$Name'],'制谱')
    def test_only_complete_pair_saved(self):
        r=self.home();r.pick('选谱','content://chart');self.read(r)
        self.assertEqual(r.db,{});r.pick('选音乐','content://music')
        self.assertEqual(r.db['保存的谱面'],[['谱面','content://chart','content://music']]);self.assertTrue(r.components['开始']['Enabled'])
        self.assertFalse(r.check_playing);self.assertEqual(r.components['音乐检查']['Source'],'');self.assertEqual(r.components['标题']['Text'],'Arivento')
    def test_restart_restore_reads_source_and_starts(self):
        r=self.home();self.choose(r);h=self.home(r.db)
        self.assertEqual(h.globals['保存列表'],r.globals['保存列表']);h.components['保存谱面']['SelectionIndex']=1;h.event('保存谱面','AfterPicking')
        self.assertEqual(h.file_requests[-1],'content://chart');self.assertFalse(h.components['保存谱面']['Enabled'])
        self.read(h,'更新后的名称');self.assertTrue(h.components['开始']['Enabled']);h.start()
        self.assertEqual(h.opened[0],'Play');self.assertEqual(h.opened[1][1],'content://music');self.assertEqual(h.opened[1][7],[[1,1000,2000]])
    def test_duplicate_uri_updates_music(self):
        r=self.home();self.choose(r);self.choose(r,music='content://new',name='新名称')
        self.assertEqual(r.db['保存的谱面'],[['新名称','content://chart','content://new']])
        self.choose(r,path='content://chart2');self.assertEqual(len(r.db['保存的谱面']),2)
    def test_missing_chart_keeps_entry_and_recovers(self):
        r=self.home();self.choose(r);before=copy.deepcopy(r.db)
        r.components['保存谱面']['SelectionIndex']=1;r.event('保存谱面','AfterPicking')
        r.event('Screen1','ErrorOccurred',组件='谱面文件',函数='ReadFrom',编号=2101,消息='missing')
        self.assertEqual(r.db,before);self.assertIn('谱面源文件找不到',r.components['读取状态']['Text']);self.assertFalse(r.components['开始']['Enabled'])
        self.assertTrue(r.components['选谱']['Enabled']);self.choose(r);self.assertTrue(r.components['开始']['Enabled'])
    def test_missing_music_does_not_save_and_can_relink(self):
        r=self.home();r.missing.add('content://bad');self.choose(r,music='content://bad')
        self.assertEqual(r.db,{});self.assertFalse(r.components['开始']['Enabled']);self.assertIn('音乐源文件找不到',r.components['读取状态']['Text'])
        r.pick('选音乐','content://good');self.assertEqual(r.db['保存的谱面'][0][2],'content://good')
        r.missing.add('content://good');r.components['保存谱面']['SelectionIndex']=1;r.event('保存谱面','AfterPicking');self.read(r)
        self.assertFalse(r.components['开始']['Enabled']);self.assertEqual(len(r.db['保存的谱面']),1)
    def test_invalid_chart_not_restored(self):
        r=self.home();self.choose(r);r.components['保存谱面']['SelectionIndex']=1;r.event('保存谱面','AfterPicking')
        r.event('谱面文件','GotText',内容='[]');self.assertFalse(r.components['开始']['Enabled']);self.assertTrue(r.components['保存谱面']['Enabled']);self.assertEqual(r.writes,1)
    def test_cancel_and_permission(self):
        r=self.home();self.choose(r);r.event('Screen1','ErrorOccurred',组件='选谱',函数='Open',编号=1,消息='cancel')
        self.assertTrue(r.components['开始']['Enabled']);self.assertEqual(len(r.db['保存的谱面']),1)
        r.event('Screen1','PermissionDenied',组件='音乐检查',函数='Source',权限='read')
        self.assertFalse(r.components['开始']['Enabled']);self.assertIn('访问权限',r.components['读取状态']['Text'])
    def test_corrupt_database_rows_filtered(self):
        r=self.home({'保存的谱面':[None,[],['bad',1,2],['good','content://a','content://b']]})
        self.assertEqual(r.globals['保存列表'],[['good','content://a','content://b']])
        r=self.home({'保存的谱面':'bad'});self.assertEqual(r.globals['保存列表'],[])
    def test_other_screens_unchanged(self):
        original=AIA.parents[2]/'archive/releases/Arivento_1017_1.aia'
        if not original.exists():original=AIA.parents[2]/'dist/Arivento_1017_1.aia'
        with zipfile.ZipFile(AIA) as z,zipfile.ZipFile(original) as old:
            for n in z.namelist():
                if n.endswith(('.scm','.bky')) and not n.endswith(('/Screen1.scm','/Screen1.bky')):self.assertEqual(z.read(n),old.read(n))

if __name__=='__main__':unittest.main(verbosity=2)
