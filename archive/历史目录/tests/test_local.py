import copy,json,re,unittest,zipfile
import test_play_finish as previous
import playback_runtime as base

base.AIA=base.ROOT/'dist/Rail4K_0919_1.aia'

class Runtime(previous.Runtime):
    def __init__(self,*a,**k):
        self.requests=[]
        super().__init__(*a,**k)
    def local_request(self,method,args):self.requests.append((method,copy.deepcopy(args)))

class Tests(unittest.TestCase):
    def chart(self,music=''):
        return ['本地测试',music,1000,2,137,3,4000,[[1,1000],[2,1145.985401459854]]]
    def home(self):
        r=Runtime();r.initialize();return r
    def load(self,r,chart):
        r.event('选谱','Click');r.event('本地文件','谱面已读',内容=json.dumps(chart,ensure_ascii=False),名称='测试.txt')
    def recorder(self):
        r=Runtime(screen='Recorder',start=self.chart());r.initialize();return r
    def export(self,r,count):
        notes=[[i%4+1,i*123.4567] for i in range(count)]
        r.globals.update(谱面=notes,物量=count,状态=4,结束时间=notes[-1][1]+500)
        r.event('导出','Click')
        while r.globals['正在导出']:r.event('导出时钟','Timer')
        return notes
    def test_local_import_and_relink(self):
        r=self.home();self.assertEqual(r.file_requests,[])
        self.load(r,self.chart('content://old/music'))
        self.assertFalse(r.components['开始']['Enabled'])
        r.event('开始','Click');self.assertIsNone(r.opened)
        r.event('选音乐','Click');self.assertEqual(r.requests[-1],('选择音乐',[]))
        r.event('本地文件','音乐已选',地址='content://new/music',名称='曲目.mp3')
        r.event('开始','Click');self.assertEqual(r.opened[1][1],'content://new/music')
        p=Runtime(screen='Play',start=r.opened[1]);p.initialize()
        self.assertEqual(p.components['音乐']['Source'],'content://new/music')
    def test_cancel_and_error(self):
        r=self.home();self.load(r,self.chart())
        before=copy.deepcopy(r.globals['当前谱'])
        r.event('选谱','Click');r.event('本地文件','取消')
        self.assertEqual(r.globals['当前谱'],before)
        self.assertFalse(r.globals['读取中'])
        r.event('选谱','Click');r.event('本地文件','出错',消息='无法读取')
        self.assertFalse(r.globals['读取中'])
        self.assertEqual(r.globals['当前谱'],before)
        for bad in ['', 'oops','[]','null']:
            r.event('选谱','Click');r.event('本地文件','谱面已读',内容=bad,名称='坏谱.txt')
            self.assertFalse(r.components['开始']['Enabled'])
            self.assertEqual(r.globals['当前谱'],[])
        self.load(r,self.chart());self.assertTrue(r.components['开始']['Enabled'])
    def test_silent_option(self):
        r=self.home();self.load(r,self.chart('old.mp3'));r.event('不放音乐','Click')
        r.event('开始','Click');self.assertEqual(r.opened[1][1],'')
    def test_editor_local_music(self):
        r=Runtime(screen='EditorSettings');self.assertEqual(r.file_requests,[])
        r.components['名称输入']['Text']='新谱'
        r.event('音乐输入','Click');self.assertEqual(r.requests[-1],('选择音乐',[]))
        r.event('本地文件','音乐已选',地址='content://audio/1',名称='本地.mp3')
        r.event('录制','Click');self.assertEqual(r.opened[0],'Recorder');self.assertEqual(r.opened[1][1],'content://audio/1')
        r.event('清除音乐','Click');r.event('录制','Click');self.assertEqual(r.opened[1][1],'')
    def test_large_save_roundtrip(self):
        for count in [1,33,10000,50000]:
            r=self.recorder();notes=self.export(r,count)
            self.assertLessEqual(len(r.components['谱面文本']['Text']),2000)
            r.event('分享全文','Click')
            name,args=r.requests[-1];self.assertEqual(name,'保存谱面')
            self.assertEqual(json.loads(args[1])[7],notes)
            self.assertTrue(r.globals['正在保存'])
            self.assertFalse(r.components['分享全文']['Enabled'])
            r.event('Recorder','BackPressed');self.assertTrue(r.components['导出页']['Visible'])
            r.event('本地文件','谱面已保存',名称='本地测试.txt')
            self.assertFalse(r.globals['正在保存'])
            self.assertIn('已保存',r.components['导出进度']['Text'])
            if count<=10000:
                h=self.home();self.load(h,json.loads(args[1]));self.assertTrue(h.components['开始']['Enabled'])
    def test_save_cancel_failure_retry(self):
        r=self.recorder();notes=self.export(r,33);text=r.globals['导出全文']
        for event,params in [('取消',{}),('出错',{'消息':'空间不足'})]:
            r.event('分享全文','Click');r.event('本地文件',event,**params)
            self.assertFalse(r.globals['正在保存']);self.assertTrue(r.components['分享全文']['Enabled'])
            self.assertTrue(r.components['导出返回']['Enabled']);self.assertEqual(r.globals['导出全文'],text)
            self.assertEqual(r.globals['谱面'],notes)
        r.event('分享全文','Click');r.event('本地文件','谱面已保存',名称='重试.txt')
        r.event('导出返回','Click');self.assertTrue(r.components['游戏']['Visible'])
    def test_play_regression(self):
        suite=previous.Tests()
        suite.test_finish_buttons_and_restart()
        suite.test_windows_and_chords()
    def test_compatibility(self):
        root=base.ROOT/'reference/nb190'
        versions=dict(re.findall(r'public static final int (\w+)_COMPONENT_VERSION = (\d+);',(root/'YaVersion.java').read_text()))
        inheritance={'Form':[],'TextBox':['TextBoxBase','AndroidViewComponent'],'Button':['ButtonBase','AndroidViewComponent'],'Label':['AndroidViewComponent'],'Canvas':['AndroidViewComponent'],'Spinner':['AndroidViewComponent'],'VerticalArrangement':['HVArrangement','AndroidViewComponent'],'HorizontalArrangement':['HVArrangement','AndroidViewComponent']}
        sources={}
        blocks='\n'.join(p.read_text(encoding='utf8') for p in (root/'blocks').glob('*.js'))
        with zipfile.ZipFile(base.AIA) as z:
            self.assertIsNone(z.testzip())
            for n in z.namelist():
                self.assertEqual(z.read(n),(base.ROOT/'native/Rail4K_0919_1'/n).read_bytes())
                if n.endswith('.scm'):
                    d=json.loads(z.read(n).decode().split('$JSON')[1].rsplit('|#',1)[0]);self.assertEqual(d['YaVersion'],'219')
                    def check(c):
                        kind=c['$Type']
                        if kind!='LocalFiles':
                            self.assertEqual(c['$Version'],versions[kind.upper()])
                            sources[kind]='\n'.join((root/(k+'.java')).read_text() for k in [kind]+inheritance.get(kind,[]))
                            for key in c:
                                if not key.startswith('$') and key!='Uuid':self.assertRegex(sources[kind],r'\b'+key+r'\s*\(',(kind,key))
                        for x in c.get('$Components',[]):check(x)
                    check(d['Properties'])
            for n in z.namelist():
                if not n.endswith('.bky'):continue
                r=base.ET.fromstring(z.read(n))
                for e in r.iter():e.tag=e.tag.split('}')[-1]
                self.assertEqual(r.find('yacodeblocks').attrib,{'ya-version':'219','language-version':'34'})
                self.assertEqual(list(r.iter('comment')),[])
                for b in r.iter('block'):
                    self.assertTrue(re.search(r"Blockly\.Blocks(?:\['"+b.get('type')+r"'\]|\."+b.get('type')+r"\b)",blocks),b.get('type'))
                for m in r.iter('mutation'):
                    kind=m.get('component_type')
                    if not kind or kind=='LocalFiles':continue
                    member=m.get('property_name') or m.get('method_name') or m.get('event_name')
                    if member:self.assertRegex(sources[kind],r'\b'+member+r'\s*\(',(kind,member))
            ext='assets/external_comps/rail4k.local.LocalFiles/'
            info=json.loads(z.read(ext+'components.json'))[0]
            self.assertEqual(info['androidMinSdk'],19)
            self.assertEqual(json.loads(z.read(ext+'files/component_build_infos.json'))[0]['permissions'],[])
            with zipfile.ZipFile(__import__('io').BytesIO(z.read(ext+'classes.jar'))) as dex:
                self.assertTrue(dex.read('classes.dex').startswith(b'dex\n035\0'))

if __name__=='__main__':unittest.main(verbosity=2)
