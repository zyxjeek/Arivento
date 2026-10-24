import sys,unittest
from pathlib import Path
import test_play_settings as settings
import test_hold as hold

hold.old.base.AIA=hold.AIA
hold.old.Runtime=hold.AndroidRuntime

class Settings(settings.Settings):
    def test_positive_delay_defers_finish(self):
        c=self.chart();c[6]=1200;r=self.play(200,chart=c)
        r.advance(1200)
        for i in range(1,5):r.tap(i)
        self.assertEqual(r.globals['完美'],4)
        r.advance(1699);self.assertTrue(r.components['轨道区']['Visible'])
        r.advance(1700);self.assertIn('游玩完成',r.components['信息']['Text'])

suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(Settings),unittest.defaultTestLoader.loadTestsFromTestCase(hold.old.Tests)])
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
