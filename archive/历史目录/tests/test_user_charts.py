import json
import unittest
import test_chart_numbers as old
import playback_runtime as base

TARGET=base.ROOT/'dist/Rail4K_Offline_v10_CodeOnly.aia'
base.AIA=TARGET
old.old.old.old.AIA=TARGET

class Tests(old.Tests):
    def test_archive(self):
        with base.zipfile.ZipFile(TARGET) as z,base.zipfile.ZipFile(base.ROOT/'dist/Rail4K_Offline_v9_CodeOnly.aia') as prev:
            for n in z.namelist():
                self.assertEqual(z.read(n),(base.ROOT/'native/Rail4K_UserChartFix'/n).read_bytes())
            for n in ['assets/Ark.txt','assets/ark2.txt','assets/music_list.txt','assets/chart_list.txt']:
                self.assertEqual(z.read(n),prev.read(n))
            self.assertEqual(json.loads(z.read('assets/测试.txt')),json.loads(prev.read('assets/测试.txt')))
            self.assertTrue(all(type(n[1]) is int for n in json.loads(z.read('assets/测试.txt'))[7]))
            self.assertFalse(any(n.endswith(('.mp3','.ogg')) for n in z.namelist()))
            self.assertEqual({n for n in z.namelist() if n.endswith('.bky')},{n for n in prev.namelist() if n.endswith('.bky')})
            for n in z.namelist():
                if n.endswith(('/Recorder.bky','/Play.bky','/EditorSettings.bky')): self.assertEqual(z.read(n),prev.read(n))

    def test_old_ios_failure_reproduced(self):
        with base.zipfile.ZipFile(TARGET) as z: chart=json.loads(z.read('assets/测试.txt'))
        try:
            base.AIA=base.ROOT/'dist/Rail4K_Offline_v8_CodeOnly.aia'
            r=old.Runtime();r.call('检查谱面',old.ios(chart))
            self.assertFalse(r.globals['有效'])
        finally: base.AIA=TARGET
        r=old.Runtime();data=old.ios(chart);r.call('检查谱面',data)
        self.assertTrue(r.globals['有效'])
        self.assertEqual(data,chart)

    def test_uploaded_charts(self):
        r=self.home()
        with base.zipfile.ZipFile(TARGET) as z:
            for name,count in [('Ark.txt',1150),('测试.txt',300)]:
                self.load(r,z.read('assets/'+name).decode())
                self.assertTrue(r.components['开始']['Enabled'])
                self.assertEqual(len(r.globals['当前谱'][7]),count)
            self.load(r,z.read('assets/ark2.txt').decode())
        self.assertFalse(r.components['开始']['Enabled'])
        self.assertIn('空文件',r.components['读取状态']['Text'])

    def test_fractional_and_diagnostics(self):
        r=self.home()
        for unit in [3,7]:
            chart=['吸附验证','Ark.mp3',500,2,137,unit,10000,[[i%4+1,250+i*60000/137/unit] for i in range(30)]]
            self.load(r,json.dumps(chart))
            self.assertTrue(r.components['开始']['Enabled'])
            self.assertEqual(r.globals['当前谱'][7],chart[7])
        for notes,text in [([[1,500],[2,400]],'早于'),([[5,100]],'轨道'),([[1,-1]],'负数'),([[1,9999]],'不足')]:
            chart=['错误','',500,1,120,4,10000,notes]
            self.load(r,json.dumps(chart))
            self.assertFalse(r.components['开始']['Enabled'])
            self.assertIn(text,r.components['读取状态']['Text'])

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    (base.ROOT/'docs/用户谱面修复测试报告.json').write_text(json.dumps({'tests':result.testsRun,'success':result.wasSuccessful(),'ark_notes':1150,'test_notes':300,'ark2_bytes':0,'failures':[str(x) for x in result.failures+result.errors],'scope':'Actual user archive inspection and XML simulation; no iPhone reproduction'},ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(not result.wasSuccessful())
