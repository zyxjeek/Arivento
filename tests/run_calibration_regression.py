import unittest
import test_calibration as cal
h=cal.saved.hold
h.old.base.AIA=cal.AIA
h.AIA=cal.AIA
h.old.Runtime=cal.Runtime
h.AndroidRuntime=cal.Runtime
cal.saved.Runtime=cal.Runtime
suite=unittest.defaultTestLoader.loadTestsFromTestCase(h.Hold)
suite.addTests(cal.saved.Saved(n) for n in unittest.defaultTestLoader.getTestCaseNames(cal.saved.Saved) if n!='test_other_screens_unchanged')
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
