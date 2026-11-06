import unittest
import test_simple_calibration as s

GOLD=0xFFFFD54F-2**32
LANES=['轨道一','轨道二','轨道三','轨道四']

class ChordHint(unittest.TestCase):
    def play(self,notes):
        r=s.Runtime(screen='Play',start=['多押','content://music',500,2,120,4,5000,notes,0,500]);r.initialize();return r
    def gold(self,r):return sorted({LANES.index(d['canvas'])+1 for d in r.draws if d['color']==GOLD})
    def test_same_head_time_marks_every_note_including_hold_and_segment_edge(self):
        notes=[[1,1000],[2,1000],[3,1500,2500],[4,1500],[1,2000]]+[[i%4+1,3000+i*10] for i in range(58)]+[[1,4000],[2,4000]]
        r=self.play(notes)
        flags=[n[4] for group in r.globals['游玩分段'] for n in group]
        self.assertEqual(flags[:5],[True,True,True,True,False]);self.assertFalse(any(flags[5:63]));self.assertEqual(flags[63:],[True,True])
        self.assertEqual(len(r.globals['游玩分段'][0]),64)
    def test_gold_border_drawn_wider_under_visible_chord_heads_only(self):
        r=self.play([[1,1000],[2,1000],[3,1000,1800],[4,1200]]);r.advance(700)
        self.assertEqual(self.gold(r),[1,2,3])
        for d in [d for d in r.draws if d['color']==GOLD]:self.assertEqual(d['width'],24);self.assertEqual(d['args'][0],5)
        lane=[d for d in r.draws if d['canvas']=='轨道一'];i=next(i for i,d in enumerate(lane) if d['color']==GOLD)
        self.assertEqual(lane[i+1]['width'],16);self.assertNotEqual(lane[i+1]['color'],GOLD)
    def test_single_notes_and_replay_have_no_stale_flag(self):
        r=self.play([[1,1000],[2,1100]]);r.advance(700);self.assertEqual(self.gold(r),[])
        r.event('重开','Click');self.assertEqual([n[4] for g in r.globals['游玩分段'] for n in g],[False,False])
