"""Offline tests for the top-10 priority scanner (synthetic rows)."""
import datetime, os, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "trader-debate"))
import priority as P     # noqa: E402

DAY = datetime.date(2026, 1, 5)


def row(sym, gap, r15, rvol, c_vs_tp=1, ret5=0.0, after=()):
    o = 100.0
    c15 = o * (1 + r15)
    return {"sym": sym, "prev_close": o / (1 + gap), "open": o, "gap": gap, "r15": r15, "c15": c15, "tp15": c15 - c_vs_tp * 0.1,
            "h15": max(o, c15) + 0.2, "l15": min(o, c15) - 0.2, "rvol15": rvol, "ret5": ret5, "entry_open": c15, "last": c15,
            "last_bar": "09:30", "after": list(after)}


class Priority(unittest.TestCase):
    def test_exact_definitions(self):
        h = P.intraday_hits([row("A", 0.03, 0.01, 2.5), row("B", 0.0, -0.012, 3.0, c_vs_tp=-1), row("C", 0.0, 0.001, 2.2, ret5=0.06),
                             row("D", 0.0, 0.015, 2.1), row("E", -0.03, -0.004, 2.4, c_vs_tp=-1), row("F", 0.03, 0.01, 1.9)])
        self.assertEqual([r["sym"] for r in h[1]], ["A"])          # F fails volume
        self.assertEqual([r["sym"] for r in h[2]], ["B"])
        self.assertEqual([r["sym"] for r in h[3]], ["C"])
        self.assertIn("D", [r["sym"] for r in h[4]])
        self.assertEqual([r["sym"] for r in h[8]], ["E"])

    def test_follow_through_rule(self):
        t = lambda hm: datetime.datetime.combine(DAY, datetime.time(*hm))
        bars = [(t((9, 35)), 101, 101.2, 100.9, 101.1, 1), (t((9, 40)), 101.1, 101.3, 101.0, 101.2, 1), (t((9, 45)), 101.2, 101.5, 101.1, 101.4, 1),
                (t((10, 0)), 101.4, 101.5, 99.0, 99.5, 1)]
        ok = row("A", 0.03, 0.01, 2.5, after=bars); ok.update(ft_rvol=1.3, ft_move=0.004, entry_0945=101.4)
        faded = row("B", 0.03, 0.01, 2.5, after=bars); faded.update(ft_rvol=0.7, ft_move=0.004, entry_0945=101.4)
        self.assertEqual(P.intraday_plan(ok, "long", t((9, 40)), DAY)["status"], "WAIT")            # before 09:45
        self.assertTrue(P.intraday_plan(ok, "long", t((9, 46)), DAY)["status"].startswith("VALID"))
        self.assertEqual(P.intraday_plan(ok, "long", t((9, 46)), DAY)["entry"], 101.4)             # entry = 09:45 open
        self.assertEqual(P.intraday_plan(faded, "long", t((9, 46)), DAY)["status"], "NOT VALID")
        self.assertEqual(P.intraday_plan(ok, "long", t((10, 5)), DAY)["status"], "INVALIDATED")     # stop traded in the 10:00 bar
        self.assertEqual(P.intraday_plan(ok, "long", t((9, 46)), DAY)["outcome_so_far"], "INVALIDATED")
        self.assertEqual(P.intraday_plan(ok, "long", t((9, 20)), DAY)["status"], "WAIT")

    def test_expired_after_entry_window(self):
        t = lambda hm: datetime.datetime.combine(DAY, datetime.time(*hm))
        r = row("A", 0.03, 0.01, 2.5, after=[(t((9, 35)), 101, 101.2, 100.9, 101.1, 1)])
        r.update(ft_rvol=1.2, ft_move=0.003, entry_0945=101.1)
        self.assertEqual(P.intraday_plan(r, "long", t((11, 0)), DAY)["status"], "EXPIRED")

    def test_ten_strategies_in_order(self):
        self.assertEqual(sorted(P.STRATEGIES), list(range(1, 11)))
        self.assertEqual(P.STRATEGIES[1][3], 61.3)


if __name__ == "__main__":
    unittest.main()
