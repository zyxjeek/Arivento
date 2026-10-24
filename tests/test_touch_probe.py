import itertools,unittest
from pathlib import Path
import test_native_tracks as old

old.base.AIA=Path(__file__).resolve().parents[1]/'archive/多押排查_0925/Rail4K_0925_1.aia'

class TouchProbe(unittest.TestCase):
    def test_combinations(self):
        for size in [3,4]:
            for order in itertools.permutations(range(1,5),size):
                r=old.Runtime(screen='TouchCheck');r.initialize()
                for lane in order:r.tap(lane)
                self.assertEqual(r.globals['当前按住'],size)
                self.assertEqual(r.globals['最高按住'],size)
                self.assertEqual(r.globals['按下次数'],[int(i in order) for i in range(1,5)])
                for lane in order:r.release(lane)
                self.assertEqual(r.globals['当前按住'],0)
                r.event('重开','Click')
                self.assertEqual(r.globals['最高按住'],0)
                self.assertEqual(r.globals['按下次数'],[0]*4)

if __name__=='__main__':unittest.main(verbosity=2)
