from 制谱运行器 import Runtime, AIA, ROOT, field
import copy
import hashlib
import json
import re
import unittest
import zipfile

class 制谱测试(unittest.TestCase):
    def 新建(self, **参数):
        r = Runtime(**参数)
        r.initialize()
        r.cloud_flush()
        return r

    def test_原文件和积木结构(self):
        self.assertEqual(hashlib.sha256((ROOT/'Rail4K_0910.aia').read_bytes()).hexdigest(), 'baa86ed9aadc0df44943d2e48e8188a6b65d35bffd64885b8903c128d6b65fab')
        r = self.新建()
        blocks = list(r.root.iter('block'))
        self.assertEqual(len(blocks), len({b.get('id') for b in blocks}))
        self.assertFalse(list(r.root.iter('comment')))
        for name in [*r.globals, *r.procedures, *r.components]:
            if name != 'Screen1': self.assertRegex(name, r'^[\u4e00-\u9fff]+$')
        metadata = {c['name']: c for c in json.loads((ROOT/'reference/component-types.json').read_text(encoding='utf-8'))}
        for c in r.components.values():
            md=metadata[c['$Type']]
            self.assertLessEqual(int(c['$Version']),int(md['version']))
            props={p['name'] for p in md['properties']}|{'Width','Height'}
            self.assertFalse({n for n in c if not n.startswith('$') and n!='Uuid'}-props-{'Elements','SelectionIndex','Selection'})
        for b in blocks:
            t=b.get('type');m=b.find('mutation')
            if t.startswith('component_'):
                self.assertEqual(r.components[m.get('instance_name')]['$Type'],m.get('component_type'))
                md=metadata[m.get('component_type')]
                if t=='component_method':
                    meth=next(x for x in md['methods'] if x['name']==m.get('method_name'))
                    self.assertEqual(len(meth['params']),len(b.findall('value')))
                if t=='component_set_get':
                    self.assertIn(m.get('property_name'),[p['name'] for p in md['blockProperties']])
                if t=='component_event':
                    ev=next(x for x in md['events'] if x['name']==m.get('event_name'))
                    overrides=[x for x in m.attrib if x.startswith('param_name')]
                    self.assertTrue(not overrides or len(overrides)==len(ev['params']))
            if t=='procedures_callnoreturn':
                target=r.procedures[field(b,'PROCNAME')]
                self.assertEqual(len(b.findall('value')),len(target.find('mutation').findall('arg')))

    def test_测试谱面迁移一次(self):
        r=self.新建()
        data=r.cloud['测试']
        self.assertEqual(data[:7],['测试','',1000,1,120,4,61000])
        self.assertEqual(len(data[7]),300)
        self.assertEqual([n[1] for n in data[7]],[500+i*200 for i in range(1,301)])
        old=copy.deepcopy(data)
        other=self.新建(seed=91,cloud=r.cloud)
        self.assertEqual(other.globals['当前谱'],old)
        self.assertEqual(r.cloud['测试'],old)

    def test_素材从电脑打包后自动枚举(self):
        r=self.新建(assets=['一首歌.mp3','SONG.WAV','notes.txt','图.png','短','节奏.m4a'])
        self.assertEqual(r.components['音乐输入']['Elements'],['无音乐','一首歌.mp3','SONG.WAV','节奏.m4a'])

    def test_自由模式和过屏时间(self):
        r=self.新建()
        r.record(mode=1,bpm='',unit='',approach='1750')
        r.note(2,123);r.note(4,399);r.note(1,1007)
        self.assertEqual(r.globals['谱面'],[[2,123],[4,399],[1,1007]])
        self.assertEqual(r.globals['过屏时间'],1750)
        r.event('结束','Click')
        self.assertEqual(r.globals['状态'],4)
        self.assertEqual(r.globals['结束时间'],1507)

    def test_吸附首键基准和相邻格点(self):
        r=self.新建();r.record(mode=2,bpm='120',unit='4')
        for lane,t in [(1,103),(2,164),(3,166),(4,350),(1,419)]:r.note(lane,t)
        self.assertEqual(r.globals['间隔时间'],125)
        self.assertEqual(r.globals['谱面'],[[1,103],[2,103],[3,228],[4,353],[1,478]])
        for a in r.globals['谱面']:
            for b in r.globals['谱面']:
                self.assertAlmostEqual((a[1]-b[1])/125,round((a[1]-b[1])/125))

    def test_吸附小数间隔不累积舍入(self):
        r=self.新建();r.record(mode=2,bpm='137',unit='3')
        times=[19,100,270,500,999,1732]
        for t in times:r.note(1,t)
        step=60000/137/3
        for n in r.globals['谱面']:
            self.assertAlmostEqual((n[1]-19)/step,round((n[1]-19)/step),places=10)

    def test_同轨重复和不同轨同押(self):
        r=self.新建();r.record(mode=2)
        r.note(1,100);r.note(1,110);r.note(2,120)
        self.assertEqual(r.globals['谱面'],[[1,100],[2,100]])

    def test_空录制和无效设置(self):
        for field_name,bad in [('过屏输入','0'),('过屏输入','abc'),('速度输入','0'),('单位输入','0'),('单位输入','-1')]:
            r=self.新建();r.event('制谱','Click')
            r.components['名称输入']['Text']='校验'
            r.components['模式输入']['SelectionIndex']=2
            r.components[field_name]['Text']=bad
            r.event('录制','Click')
            self.assertNotEqual(r.globals['状态'],2)
        r=self.新建();r.record();r.event('结束','Click');r.event('保存','Click')
        self.assertNotIn('新谱面',r.cloud)
        self.assertEqual(r.globals['云请求'],'')

    def test_准备期间不录入音乐同零点启动(self):
        r=self.新建(assets=['曲.mp3']);r.record(music='曲.mp3')
        r.tap(1);r.advance(-100);r.tap(2)
        self.assertFalse(r.globals['谱面']);self.assertFalse(r.music_starts)
        r.advance(0);r.tap(3)
        self.assertEqual(len(r.music_starts),1)
        self.assertEqual(r.globals['谱面'],[[3,0]])
        self.assertEqual(r.music_starts[0],r.globals['起点'])

    def test_云端确认前不声称成功(self):
        r=self.新建();r.record();r.note(1,100);r.event('结束','Click');r.event('保存','Click')
        self.assertEqual(r.globals['云请求'],'检查保存')
        self.assertEqual(r.globals['状态'],4)
        r.cloud_step()
        self.assertEqual(r.globals['云请求'],'写入')
        self.assertNotIn('新谱面',r.cloud)
        r.cloud_step()
        self.assertEqual(r.globals['状态'],0)
        self.assertIn('新谱面',r.cloud)
        self.assertEqual(r.globals['当前谱'],r.cloud['新谱面'])

    def test_云保存后重启设备选谱游玩(self):
        r=self.新建(assets=['歌.mp3']);r.record(name='自制曲',music='歌.mp3',approach='2000')
        r.note(3,123);r.note(1,887);r.event('结束','Click');r.event('保存','Click');r.cloud_flush()
        other=self.新建(cloud=r.cloud,assets=['歌.mp3'])
        self.assertIn('自制曲',other.components['选谱']['Elements'])
        other.components['选谱']['Selection']='自制曲';other.event('选谱','AfterPicking');other.cloud_flush();other.start()
        self.assertEqual(other.globals['过屏时间'],2000)
        self.assertEqual(other.components['音乐']['Source'],'歌.mp3')
        other.note(3,123);other.note(1,887);other.advance(1387)
        self.assertEqual((other.globals['完美'],other.globals['准确率'],other.globals['状态']),(2,100,3))

    def test_覆盖确认取消和确认(self):
        r=self.新建();old=copy.deepcopy(r.cloud['测试'])
        r.record(name='测试');r.note(1,100);r.event('结束','Click');r.event('保存','Click');r.cloud_flush()
        self.assertEqual(r.globals['云请求'],'等待覆盖')
        r.event('提示','AfterChoosing',选择='取消')
        self.assertEqual(r.cloud['测试'],old)
        r.event('保存','Click');r.cloud_flush();r.event('提示','AfterChoosing',选择='覆盖');r.cloud_flush()
        self.assertEqual(r.cloud['测试'][7],[[1,100]])

    def test_保存失败超时和重试(self):
        r=self.新建();r.record();r.note(4,200);r.event('结束','Click');r.event('保存','Click')
        r.cloud_step(fail=True)
        self.assertEqual(r.globals['状态'],4);self.assertEqual(r.globals['谱面'],[[4,200]])
        r.event('保存','Click');r.cloud_flush()
        self.assertIn('新谱面',r.cloud)
        r.record(name='超时');r.note(1,250);r.event('结束','Click');r.event('保存','Click')
        r.event('云时钟','Timer')
        self.assertEqual(r.globals['云请求'],'');self.assertEqual(r.globals['状态'],4)
        r.cloud_flush()
        self.assertNotIn('超时',r.cloud)

    def test_不同轨逆序同押不被全局下一键阻塞(self):
        r=self.新建()
        r.globals['当前谱']=['同押','',1000,1,120,4,1600,[[1,500],[2,500],[3,500],[4,1000]]]
        r.start();r.advance(500)
        for lane in [3,2,1]:r.tap(lane)
        self.assertEqual(r.globals['完美'],3)
        self.assertEqual(r.globals['下一键'],4)
        r.advance(1161);self.assertEqual(r.globals['漏击'],1)
        self.assertEqual(r.globals['准确率'],75)

    def test_判定边界(self):
        for offset,p,g,m in [(-161,0,0,0),(-160,0,1,0),(-80,1,0,0),(0,1,0,0),(80,1,0,0),(160,0,1,0),(161,0,0,1)]:
            r=self.新建();r.globals['当前谱']=['边界','',1000,1,120,4,1000,[[1,500]]]
            r.start();r.note(1,500+offset)
            self.assertEqual((r.globals['完美'],r.globals['良好'],r.globals['漏击']),(p,g,m))

    def test_密集谱面全部可见和时间正确(self):
        r=self.新建()
        rows=[[(i%4)+1,1000+i*30] for i in range(30)]
        r.globals['当前谱']=['密集','',1000,1,120,4,2500,rows]
        r.start();r.advance(900)
        self.assertEqual(len(r.notes()),30)
        first=r.notes()[0]['args'];self.assertAlmostEqual(first[1],r.globals['判定线']*.9)
        r.advance(2500)
        self.assertEqual(r.globals['漏击'],30)

    def test_原300键全流程(self):
        r=self.新建();r.start()
        for lane,t in r.globals['谱面']:r.note(lane,t)
        r.advance(61000)
        self.assertEqual((r.globals['完美'],r.globals['准确率'],r.globals['最大连击']),(300,100,300))

    def test_坏数据拒绝不替换当前谱(self):
        r=self.新建();old=copy.deepcopy(r.globals['当前谱'])
        samples=[None,42,[],['少字段'],['坏','',0,1,120,4,1000,[[1,100]]],['坏','',1000,1,120,4,1000,[[5,100]]],['坏','',1000,1,120,4,1000,[[1,500],[2,100]]],['坏','',1000,1,120,4,1000,[[1,950]]]]
        for data in samples:
            r.cloud['坏']=data;r.components['选谱']['Selection']='坏';r.event('选谱','AfterPicking');r.cloud_flush()
            self.assertEqual(r.globals['当前谱'],old)

    def test_没有素材和音乐加载失败(self):
        r=self.新建();r.globals['当前谱']=['缺歌','不存在.mp3',1000,1,120,4,1000,[[1,500]]];r.start()
        self.assertEqual(r.globals['状态'],0)
        r=self.新建(assets=['坏.mp3']);r.fail_music=True;r.record(music='坏.mp3')
        self.assertEqual(r.globals['状态'],4)
        self.assertIsNot(r.components['时钟']['TimerEnabled'],True)

    def test_音乐结束录制和重开(self):
        r=self.新建();r.record();r.note(1,100);r.event('音乐','Completed')
        self.assertEqual(r.globals['状态'],4)
        r.event('重开','Click')
        self.assertEqual(r.globals['物量'],0);self.assertEqual(r.globals['基准'],-1)
        self.assertEqual(r.globals['状态'],2)

    def test_刷新缺失测试不错误写入当前自制谱(self):
        r=self.新建();original=copy.deepcopy(r.cloud['测试'])
        custom=['自制','',1000,1,120,4,1000,[[1,500]]]
        r.globals['当前谱']=custom
        del r.cloud['测试']
        r.event('刷新','Click');r.cloud_flush()
        self.assertEqual(r.cloud['测试'],original)
        self.assertEqual(r.globals['当前谱'],custom)

    def test_吸附单位接受正小数(self):
        r=self.新建();r.record(mode=2,unit='1.5')
        r.note(1,100);r.note(2,450)
        self.assertAlmostEqual(r.globals['谱面'][1][1],100+60000/120/1.5)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(制谱测试))
    report=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),success=result.wasSuccessful(),
        aia_sha256=hashlib.sha256(AIA.read_bytes()).hexdigest(),scope='Exported BKY execution, mocked native Clock/Canvas/Player/CloudDB/File and component metadata; not device, online import or live cloud validation.')
    (ROOT/'docs/制谱版测试报告.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
