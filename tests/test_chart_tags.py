import json,unittest
import test_simple_calibration as s

class Runtime(s.Runtime):
    def evaluate(self,b,env):
        m=b.find('mutation')
        if b.get('type')=='component_method' and m.get('method_name')=='JsonTextDecode':
            return json.JSONDecoder().raw_decode(self.value(b,'ARG0',env))[0]
        return super().evaluate(b,env)

class ChartTags(unittest.TestCase):
    chart=['标签谱','song.mp3',500,2,120,4,4000,[[1,1000],[2,1500,2500]]]
    def test_tag_line_after_chart_loads_as_eight_items(self):
        for end in ('\n','\r\n'):
            r=Runtime();r.initialize();r.pick('选谱','content://chart')
            r.event('谱面文件','GotText',内容=json.dumps(self.chart,ensure_ascii=False)+end+'//tags:[["副歌",2000],["A]\\"[",3000]]'+end)
            self.assertTrue(r.globals['有效']);self.assertEqual(r.globals['当前谱'],self.chart);self.assertEqual(r.components['当前谱名']['Text'],'标签谱')
