import copy
import json
import unittest
import test_offline as old
import playback_runtime as base

base.AIA=base.ROOT/'dist/Rail4K_Offline_v8_CodeOnly.aia'
old.old.AIA=base.AIA

class Runtime(old.Runtime):
    def __init__(self,*args,**kw):
        self.encoded=[]
        self.shared=[]
        self.fail_encode=False
        super().__init__(*args,**kw)

    def evaluate(self,b,env):
        m=b.find('mutation')
        if b.get('type')=='component_method' and m.get('method_name')=='JsonObjectEncode':
            v=self.value(b,'ARG0',env)
            self.encoded.append(len(v) if isinstance(v,list) else 0)
            if self.fail_encode:
                self.event('Recorder','ErrorOccurred',组件='文本转换',函数='JsonObjectEncode',编号=1106,消息='模拟编码失败')
                return ''
        return super().evaluate(b,env)

    def execute(self,b,env=None):
        if b is not None and b.get('type')=='component_method' and b.find('mutation').get('component_type')=='Sharing':
            self.shared.append(self.value(b,'ARG0',env or {}))
            return
        return super().execute(b,env)

old.Runtime=Runtime
old.old.Runtime=Runtime

class Tests(unittest.TestCase):
    runtime=old.Tests.runtime
    chart=old.Tests.chart
    recorder=old.Tests.recorder
    home=old.Tests.home
    load=old.Tests.load
    test_structure=old.Tests.test_structure
    test_asset_play=old.Tests.test_asset_play
    test_invalid_and_recovery=old.Tests.test_invalid_and_recovery
    test_playback_confirmation=old.Tests.test_playback_confirmation
    test_free_and_snap=old.Tests.test_free_and_snap
    test_judgement_and_chords=old.Tests.test_judgement_and_chords
    test_draw_and_end=old.Tests.test_draw_and_end
    test_settings_validation_and_back=old.Tests.test_settings_validation_and_back

    def finish(self,r):
        ticks=0
        while r.globals['正在导出']:
            before=len(r.encoded)
            r.event('导出时钟','Timer')
            self.assertLessEqual(len(r.encoded)-before,32)
            self.assertLessEqual(len(r.components['谱面文本']['Text']),2000)
            ticks+=1
            self.assertLess(ticks,10000)
        return ticks

    def test_large_roundtrip(self):
        for count in [1,32,33,300,10000,50000]:
            r=self.recorder()
            notes=[[i%4+1,i*125.5] for i in range(count)]
            r.globals.update(谱面=notes,物量=count,状态=4,结束时间=notes[-1][1]+500,谱面名='测试"换行\n中文😀',音乐名='曲目\\引号".mp3')
            original=copy.deepcopy(notes)
            r.event('导出','Click')
            self.assertEqual(len(r.encoded),1)
            self.assertFalse(r.components['分享全文']['Enabled'])
            self.assertEqual(self.finish(r),(count+31)//32)
            data=json.loads(r.globals['导出全文'])
            self.assertEqual(data[7],original)
            self.assertEqual(data[0],r.globals['谱面名'])
            self.assertEqual(data[1],r.globals['音乐名'])
            self.assertIs(r.globals['谱面'],notes)
            self.assertEqual(notes,original)
            self.assertEqual(r.encoded,[7]+[2]*count)
            self.assertTrue(r.components['分享全文']['Enabled'])
            r.event('分享全文','Click')
            self.assertEqual(r.shared,[r.globals['导出全文']])
            home=self.home()
            self.load(home,r.shared[0])
            self.assertTrue(home.components['开始']['Enabled'])

    def test_cancel_retry_and_back(self):
        r=self.recorder()
        r.globals.update(谱面=[[1,i*100] for i in range(100)],物量=100,状态=4,结束时间=11000)
        for action in [('导出返回','Click'),('Recorder','BackPressed')]:
            r.event('导出','Click');r.event('导出时钟','Timer')
            r.event(*action)
            self.assertFalse(r.globals['正在导出'])
            self.assertFalse(r.components['导出时钟']['TimerEnabled'])
            self.assertEqual(r.globals['导出全文'],'')
            self.assertTrue(r.components['游戏']['Visible'])
            r.event('导出时钟','Timer')
            self.assertEqual(r.globals['导出全文'],'')
        for _ in range(2):
            r.event('导出','Click');self.finish(r)
            self.assertEqual(len(json.loads(r.globals['导出全文'])[7]),100)
            r.event('导出返回','Click')
        r.event('返回','Click')
        self.assertTrue(r.closed)
        self.assertEqual(r.result,'')

    def test_error_preserves_notes(self):
        r=self.recorder()
        r.globals.update(谱面=[[1,100]],物量=1,状态=4,结束时间=1000)
        r.event('导出','Click')
        r.event('Recorder','ErrorOccurred',组件='文本转换',函数='JsonObjectEncode',编号=1106,消息='模拟失败')
        self.assertFalse(r.globals['正在导出'])
        self.assertEqual(r.globals['谱面'],[[1,100]])
        self.assertFalse(r.components['分享全文']['Enabled'])
        r.event('导出返回','Click');r.event('导出','Click');self.finish(r)
        self.assertEqual(json.loads(r.globals['导出全文'])[7],[[1,100]])

    def test_encoding_failure_in_event(self):
        for header in [True,False]:
            r=self.recorder()
            r.globals.update(谱面=[[1,100]],物量=1,状态=4,结束时间=1000)
            r.fail_encode=header
            r.event('导出','Click')
            if not header:
                r.fail_encode=True
                r.event('导出时钟','Timer')
            self.assertFalse(r.globals['正在导出'])
            self.assertFalse(r.components['导出时钟']['TimerEnabled'])
            self.assertFalse(r.components['分享全文']['Enabled'])
            self.assertEqual(r.globals['导出全文'],'')
            self.assertEqual(r.globals['谱面'],[[1,100]])

    def test_archive(self):
        with base.zipfile.ZipFile(base.AIA) as z:
            self.assertEqual({n for n in z.namelist() if n.startswith('assets/')},{'assets/music_list.txt','assets/chart_list.txt','assets/测试.txt'})
            for n in z.namelist():
                data=z.read(n)
                self.assertEqual(data,(base.ROOT/'native/Rail4K_LargeExport'/n).read_bytes())
                self.assertNotIn(b'CloudDB',data)
                self.assertNotIn(b'lists_copy',data)
        r=Runtime(screen='Recorder')
        self.assertEqual(r.components['谱面文本']['ReadOnly'],'True')
        event=r.events['导出','Click']
        self.assertNotIn('复制列表',base.ET.tostring(event,encoding='unicode'))

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    (base.ROOT/'docs/大谱面导出测试报告.json').write_text(json.dumps({'tests':result.testsRun,'success':result.wasSuccessful(),'max_notes':50000,'batch_notes':32,'preview_chars':2000,'failures':[str(x) for x in result.failures+result.errors],'scope':'XML simulation and interface checks; no iPhone or native sharing test'},ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(not result.wasSuccessful())
