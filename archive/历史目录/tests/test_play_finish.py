import copy
import json
import unittest
import test_chart_numbers as old
import playback_runtime as base

TARGET=base.ROOT/'dist/Rail4K_Offline_v12_CodeOnly.aia'
base.AIA=TARGET
old.old.old.old.AIA=TARGET

class Runtime(old.Runtime):
    def __init__(self,*args,**kw):
        self.list_cost=0
        self.property_reads=0
        self.clears=0
        super().__init__(*args,**kw)

    def evaluate(self,b,env):
        if b.get('type')=='lists_select_item':
            seq=self.value(b,'LIST',env);index=int(self.value(b,'NUM',env))
            self.list_cost+=len(seq)+index
            return seq[index-1]
        if b.get('type')=='component_set_get' and b.find('mutation').get('set_or_get')=='get': self.property_reads+=1
        return super().evaluate(b,env)

old.old.old.old.Runtime=Runtime

class Tests(unittest.TestCase):
    def play(self,notes=None,end=4000,music=''):
        chart=['测试',music,1000,1,120,4,end,notes or [[1,1000],[2,2000]]]
        r=Runtime(screen='Play',start=chart);r.initialize();return r

    def states(self,r): return [n[2] for group in r.globals['游玩分段'] for n in group]

    def test_finish_buttons_and_restart(self):
        for music in ['', 'Ark.mp3']:
            r=self.play(music=music)
            r.advance(4000)
            self.assertEqual(r.globals['状态'],3)
            self.assertFalse(r.components['时钟']['TimerEnabled'])
            self.assertTrue(r.components['游戏']['Visible'])
            self.assertFalse(r.components['画布']['Visible'])
            self.assertEqual(r.components['信息']['Height'],-1092)
            self.assertIn('游玩完成',r.components['信息']['Text'])
            self.assertIn('Miss 2',r.components['信息']['Text'])
            self.assertEqual(self.states(r),[1,1])
            result=r.components['信息']['Text']
            r.event('时钟','Timer');r.tap(1)
            self.assertEqual(r.components['信息']['Text'],result)
            r.event('重开','Click')
            self.assertEqual(r.globals['状态'],1)
            self.assertTrue(r.components['画布']['Visible'])
            self.assertEqual(r.components['信息']['Height'],-1012)
            self.assertEqual(self.states(r),[0,0])
            r.note(1,1000);r.note(2,2000);r.advance(4000)
            self.assertIn('100.00',r.components['信息']['Text'])
            r.event('返回','Click');self.assertTrue(r.closed)

    def test_windows_and_chords(self):
        for delta,result in [(-161,0),(-160,2),(-80,3),(0,3),(80,3),(160,2),(161,1)]:
            r=self.play([[1,1000]])
            r.note(1,1000+delta)
            self.assertEqual(self.states(r),[result])
        r=self.play([[1,1000],[2,1000],[3,1000],[4,1000]])
        r.advance(1000)
        for lane in [4,2,1,3]:r.tap(lane)
        self.assertEqual(self.states(r),[3,3,3,3])
        self.assertEqual(r.globals['准确率'],100)
        self.assertEqual(r.globals['连击'],4)
        r.advance(4000)
        self.assertIn('最高连击 4',r.components['信息']['Text'])

    def test_segment_boundaries(self):
        for count in [1,63,64,65,129,1150]:
            notes=[[i%4+1,i*10+700.5] for i in range(count)]
            r=self.play(notes,end=20000)
            self.assertEqual([n[:2] for g in r.globals['游玩分段'] for n in g],notes)
            self.assertTrue(all(len(g)<=64 for g in r.globals['游玩分段']))
            for index in {1,count,min(64,count),min(65,count)}:
                r.call('记录判定',index,3)
                self.assertEqual(r.call('取游玩键',index)[2],3)
            self.assertEqual(r.start_value[7],notes)

    def test_visible_and_frame_cost(self):
        with base.zipfile.ZipFile(TARGET) as z: chart=json.loads(z.read('assets/Ark.txt'))
        reports=[]
        for source in [base.ROOT/'dist/Rail4K_Offline_v10_CodeOnly.aia',TARGET]:
            base.AIA=source
            r=Runtime(screen='Play',start=copy.deepcopy(chart));r.initialize()
            r.globals.update(用时=chart[7][999][1],下一键=1000,已播放=True,状态=1)
            r.list_cost=0;r.property_reads=0
            r.call('绘图')
            self.assertTrue(r.notes())
            reports.append({'file':source.name,'list_traversal_estimate':r.list_cost,'component_getters':r.property_reads,'draws':copy.deepcopy(r.draws)})
        base.AIA=TARGET
        self.assertEqual(reports[0]['draws'],reports[1]['draws'])
        self.assertLess(reports[1]['list_traversal_estimate'],reports[0]['list_traversal_estimate']/5)
        self.assertLess(reports[1]['component_getters'],reports[0]['component_getters'])
        (base.ROOT/'docs/游玩访问开销对比.json').write_text(json.dumps([{k:v for k,v in x.items() if k!='draws'} for x in reports],ensure_ascii=False,indent=2),encoding='utf-8')

    def test_no_touch_redraw(self):
        r=self.play();r.advance(1000)
        before=list(r.text_draws)
        r.tap(1)
        self.assertEqual(r.text_draws,before)
        self.assertIn('1',r.components['信息']['Text'])
        r.event('时钟','Timer')
        self.assertEqual(r.text_draws[-1]['text'],'PERFECT')

    def test_interfaces(self):
        old.old.old.old.Tests.test_structure(self)

    def test_preserved_assets_and_screens(self):
        with base.zipfile.ZipFile(TARGET) as z,base.zipfile.ZipFile(base.ROOT/'dist/Rail4K_Offline_v11_CodeOnly.aia') as prev:
            for n in prev.namelist():
                if n.startswith('assets/') or n.endswith(('/Recorder.bky','/EditorSettings.bky','/Screen1.bky')):self.assertEqual(z.read(n),prev.read(n))
            for n in z.namelist(): self.assertEqual(z.read(n),(base.ROOT/'native/Rail4K_V12'/n).read_bytes())

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    (base.ROOT/'docs/游玩结束与性能测试报告.json').write_text(json.dumps({'tests':result.testsRun,'success':result.wasSuccessful(),'failures':[str(x) for x in result.failures+result.errors],'scope':'XML simulation, frame output comparison and estimated linked-list traversal; no iPhone FPS measurement'},ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(not result.wasSuccessful())
