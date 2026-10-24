import json
import unittest
import test_large_export as old
import playback_runtime as base

TARGET=base.ROOT/'dist/Rail4K_Offline_v9_CodeOnly.aia'
base.AIA=TARGET
old.old.old.AIA=TARGET

def ios(v):
    if isinstance(v,list): return [ios(x) for x in v]
    if type(v) in [int,float] and v in [0,1]: return bool(v)
    return v

class Runtime(old.Runtime):
    def evaluate(self,b,env):
        m=b.find('mutation')
        if b.get('type')=='component_method' and m.get('method_name')=='JsonTextDecode':
            try: return ios(json.loads(self.value(b,'ARG0',env)))
            except ValueError: return super().evaluate(b,env)
        if b.get('type')=='math_compare' and base.field(b,'OP') in ['EQ','NEQ']:
            a,c=self.value(b,'A',env),self.value(b,'B',env)
            if isinstance(a,bool)!=isinstance(c,bool): return base.field(b,'OP')=='NEQ'
        if b.get('type')=='lists_is_in':
            v=self.value(b,'ITEM',env)
            return any(isinstance(v,bool)==isinstance(x,bool) and v==x for x in self.value(b,'LIST',env))
        return super().evaluate(b,env)

old.Runtime=Runtime
old.old.Runtime=Runtime
old.old.old.Runtime=Runtime

class Tests(old.Tests):
    def test_archive(self):
        with base.zipfile.ZipFile(TARGET) as z,base.zipfile.ZipFile(base.ROOT/'dist/Rail4K_Offline_v8_CodeOnly.aia') as prev:
            for n in z.namelist():
                data=z.read(n)
                self.assertEqual(data,(base.ROOT/'native/Rail4K_ChartFix'/n).read_bytes())
                self.assertNotIn(b'CloudDB',data)
            self.assertEqual(z.read('assets/测试.txt'),prev.read('assets/测试.txt'))
            names=z.read('assets/music_list.txt').decode().splitlines()
            self.assertEqual(len(names),322)
            self.assertEqual(len(set(names)),322)
            self.assertTrue(all(n.endswith('.mp3') for n in names))
            self.assertTrue(all((base.ROOT/'Phigros_Music_3.20.0_MP3'/n).is_file() for n in names))
            self.assertFalse(any(n.endswith(('.mp3','.ogg')) for n in z.namelist()))

    def test_old_ios_failure_reproduced(self):
        with base.zipfile.ZipFile(TARGET) as z: chart=json.loads(z.read('assets/测试.txt'))
        self.assertIs(ios(chart)[3],True)
        try:
            base.AIA=base.ROOT/'dist/Rail4K_Offline_v8_CodeOnly.aia'
            r=Runtime()
            r.call('检查谱面',ios(chart))
            self.assertFalse(r.globals['有效'])
        finally: base.AIA=TARGET
        r=Runtime()
        decoded=ios(chart)
        r.call('检查谱面',decoded)
        self.assertTrue(r.globals['有效'])
        self.assertEqual(decoded,chart)
        self.assertIs(type(decoded[3]),int)
        self.assertTrue(all(type(n[0]) is int for n in decoded[7]))

    def test_zero_time_and_fraction(self):
        for mode in [1,2]:
            r=self.home()
            chart=['测试','song.mp3',1000,mode,120,1,1000,[[1,0],[2,1],[3,125.5],[4,250]]]
            self.load(r,json.dumps(chart))
            self.assertTrue(r.components['开始']['Enabled'])
            self.assertEqual(r.globals['当前谱'],chart)
            self.assertIs(type(r.globals['当前谱'][7][0][1]),int)
            self.assertEqual(r.globals['当前谱'][7][2][1],125.5)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    (base.ROOT/'docs/谱面数字兼容测试报告.json').write_text(json.dumps({'tests':result.testsRun,'success':result.wasSuccessful(),'failures':[str(x) for x in result.failures+result.errors],'scope':'iOS JSON 0/1 coercion simulation, XML runtime and component interfaces; not device verification'},ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(not result.wasSuccessful())
