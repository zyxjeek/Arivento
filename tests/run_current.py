import json,sys,unittest
from pathlib import Path

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tests'))
import test_simple_calibration as s

current=root/'dist'/(json.loads((root/'tools/current_release.json').read_text(encoding='utf-8'))['name']+'.aia')
print('CURRENT AIA:',current,flush=True)
cal=s.base;h=cal.saved.hold
s.AIA=current;h.old.base.AIA=current;h.AIA=current;cal.saved.AIA=current
h.old.Runtime=s.Runtime;h.AndroidRuntime=s.Runtime;cal.saved.Runtime=s.Runtime
import test_hit_volume
suite=unittest.defaultTestLoader.loadTestsFromTestCase(s.Simple)
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(test_hit_volume.HitVolume))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(h.Hold))
suite.addTests(cal.saved.Saved(n) for n in unittest.defaultTestLoader.getTestCaseNames(cal.saved.Saved) if n!='test_other_screens_unchanged')
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
