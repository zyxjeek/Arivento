import json
import unittest
import playback_runtime as base
import test_playback as old

base.AIA=base.ROOT/'dist/Rail4K_Offline_v7_CodeOnly.aia'

class Runtime(base.Runtime):
    def evaluate(self,b,env):
        m=b.find('mutation')
        if b.get('type')=='component_method' and m.get('component_type')=='Web':
            v=self.value(b,'ARG0',env)
            if m.get('method_name')=='JsonObjectEncode': return json.dumps(v,ensure_ascii=False,separators=(',',':'))
            if m.get('method_name')=='JsonTextDecode':
                try: return json.loads(v)
                except ValueError:
                    self.event(self.screen,'ErrorOccurred',组件='文本转换',函数='JsonTextDecode',编号=1105,消息='JSON 格式错误')
                    return ''
        return super().evaluate(b,env)

old.Runtime=Runtime
old.AIA=base.AIA

class Tests(unittest.TestCase):
    runtime=old.Tests.runtime
    chart=old.Tests.chart
    recorder=old.Tests.recorder
    test_structure=old.Tests.test_structure
    test_playback_confirmation=old.Tests.test_playback_confirmation
    test_free_and_snap=old.Tests.test_free_and_snap
    test_judgement_and_chords=old.Tests.test_judgement_and_chords
    test_draw_and_end=old.Tests.test_draw_and_end

    def test_settings_validation_and_back(self):
        r=self.runtime('EditorSettings')
        r.components['名称输入']['Text']=''
        r.event('录制','Click')
        self.assertIsNone(r.opened)
        r.components['名称输入']['Text']='新谱'
        r.event('录制','Click')
        self.assertEqual(r.opened[0],'Recorder')
        r.event('设置返回','Click')
        self.assertTrue(r.closed)
        self.assertEqual(r.result,'')

    def home(self):
        r=Runtime();r.initialize()
        self.assertEqual(r.file_requests,['//chart_list.txt'])
        r.event('目录文件','GotText',内容='测试.txt\r\n\n测试.txt\n自制.txt\n')
        self.assertEqual(r.components['选谱']['Elements'],['测试.txt','自制.txt'])
        return r

    def load(self,r,text):
        r.components['选谱']['Selection']='测试.txt'
        r.event('选谱','AfterPicking')
        self.assertFalse(r.components['开始']['Enabled'])
        self.assertFalse(r.components['选谱']['Enabled'])
        r.event('谱面文件','GotText',内容=text)

    def test_asset_play(self):
        r=self.home()
        r.start();self.assertIsNone(r.opened)
        with base.zipfile.ZipFile(base.AIA) as z: text=z.read('assets/测试.txt').decode()
        self.load(r,text)
        self.assertTrue(r.components['开始']['Enabled'])
        self.assertEqual(r.globals['当前谱'][0],'测试')
        self.assertEqual(len(r.globals['当前谱'][7]),300)
        r.start();self.assertEqual(r.opened,('Play',json.loads(text)))
        self.assertFalse(r.pending)

    def test_invalid_and_recovery(self):
        r=self.home()
        for bad in ['oops','null','[]','[1]',json.dumps(self.chart([[5,10]])),json.dumps(self.chart([[1,-1]])),json.dumps(self.chart([[1,9000]]))]:
            self.load(r,bad)
            self.assertFalse(r.components['开始']['Enabled'])
            self.assertEqual(r.globals['当前谱'],[])
            self.assertTrue(r.components['选谱']['Enabled'])
        self.load(r,json.dumps(self.chart()))
        self.assertTrue(r.components['开始']['Enabled'])
        r.event('选谱','AfterPicking')
        r.event('Screen1','ErrorOccurred',组件='谱面文件',函数='ReadFrom',编号=2101,消息='不存在')
        self.assertFalse(r.components['开始']['Enabled'])
        self.assertTrue(r.components['选谱']['Enabled'])

    def test_export_roundtrip_and_independence(self):
        for mode in [1,2]:
            r=self.recorder(mode)
            r.note(1,1000);r.note(2,1080);r.note(4,2040)
            r.event('结束','Click');r.event('导出','Click')
            text=r.components['谱面文本']['Text']
            chart=json.loads(text)
            self.assertEqual(chart[7],r.globals['谱面'])
            self.assertEqual(chart[3],mode)
            self.assertFalse(r.components['游戏']['Visible'])
            self.assertTrue(r.components['导出页']['Visible'])
            self.assertFalse(r.pending)
            self.assertFalse(r.closed)
            home=self.home();self.assertEqual(home.globals['当前谱'],[])
            self.load(home,text);self.assertTrue(home.components['开始']['Enabled'])
            r.event('导出返回','Click');r.event('返回','Click')
            self.assertEqual(r.result,'')
            self.assertNotIn(('EditorSettings','OtherScreenClosed'),Runtime(screen='EditorSettings').events)

    def test_no_cloud_and_source_match(self):
        with base.zipfile.ZipFile(base.AIA) as z:
            for n in z.namelist():
                data=z.read(n)
                self.assertEqual(data,(base.ROOT/'native/Rail4K_Offline'/n).read_bytes())
                self.assertNotIn('CloudDB',data.decode())
                self.assertNotIn('云端',data.decode())
                self.assertNotIn('ListDirectory',data.decode())
                self.assertNotIn('lists_copy',data.decode())
            self.assertEqual({n for n in z.namelist() if n.startswith('assets/')},{'assets/music_list.txt','assets/chart_list.txt','assets/测试.txt'})
        for screen in ['Screen1','EditorSettings','Recorder','Play']:
            r=Runtime(screen=screen)
            self.assertFalse(any('云' in n for n in r.globals))
            for b in r.root.iter('block'):
                m=b.find('mutation')
                if m is not None and m.get('instance_name'):
                    self.assertIn(m.get('instance_name'),r.components)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    (base.ROOT/'docs/离线谱面测试报告.json').write_text(json.dumps({'tests':result.testsRun,'success':result.wasSuccessful(),'failures':[str(x) for x in result.failures+result.errors],'scope':'XML runtime simulation and component metadata; no iPhone device test'},ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(not result.wasSuccessful())
