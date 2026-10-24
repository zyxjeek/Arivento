import unittest
import test_simple_calibration as simple
cal=simple.base
h=cal.saved.hold
h.old.base.AIA=simple.AIA
h.AIA=simple.AIA
h.old.Runtime=simple.Runtime
h.AndroidRuntime=simple.Runtime
cal.saved.Runtime=simple.Runtime
suite=unittest.defaultTestLoader.loadTestsFromTestCase(h.Hold)
suite.addTests(cal.saved.Saved(n) for n in unittest.defaultTestLoader.getTestCaseNames(cal.saved.Saved) if n!='test_other_screens_unchanged')
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
