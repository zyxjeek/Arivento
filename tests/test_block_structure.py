import sys,unittest,zipfile,xml.etree.ElementTree as E
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from project import check_block_structure

def read(z,n):
    r=E.fromstring(z.read(n))
    for e in r.iter():e.tag=e.tag.split('}')[-1]
    return r

class Structure(unittest.TestCase):
    def test_previous_release_reproduces_duplicate_connection(self):
        p=ROOT/'dist/Arivento_1017_2.aia'
        if not p.exists():p=ROOT/'archive/releases/Arivento_1017_2.aia'
        with zipfile.ZipFile(p) as z:
            r=read(z,next(n for n in z.namelist() if n.endswith('/Screen1.bky')))
            with self.assertRaisesRegex(AssertionError,'重复 next'):check_block_structure(r)
    def test_candidate_all_screens_have_unique_connections(self):
        with zipfile.ZipFile(ROOT/'archive/hold_base_1016/Saved_candidate.aia') as z:
            for n in z.namelist():
                if n.endswith('.bky'):
                    with self.subTest(screen=n):check_block_structure(read(z,n))
    def test_cancel_restores_both_controls(self):
        import test_saved_charts as saved
        r=saved.Runtime();r.initialize()
        r.components['保存谱面']['Enabled']=False;r.components['制谱']['Enabled']=False
        r.event('Screen1','ErrorOccurred',组件='选谱',函数='Open',编号=1,消息='cancel')
        self.assertTrue(r.components['保存谱面']['Enabled']);self.assertTrue(r.components['制谱']['Enabled'])

if __name__=='__main__':unittest.main(verbosity=2)
