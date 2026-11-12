"""Offline tests for debate stage 5 (replay trade simulation). Bars are SYNTHETIC."""
import datetime, os, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "trader-debate"))
import validate as V, common as C      # noqa: E402


def bars(rows):
    d0 = datetime.date(2026, 1, 1)
    return [{"d": d0 + datetime.timedelta(days=k), "o": o, "h": h, "l": l, "c": c} for k, (o, h, l, c) in enumerate(rows)]


PLAN = C.build_plan("swing", "long", 100.0, 97.0, "test")


class Simulate(unittest.TestCase):
    def test_no_fill_when_high_below_entry_or_gap_past_cap(self):
        self.assertIsNone(V.simulate_long(bars([(99, 99, 98, 99), (99, 99.9, 98, 99)]), 0, PLAN))
        self.assertIsNone(V.simulate_long(bars([(99, 99, 98, 99), (101, 102, 100.5, 101)]), 0, PLAN))

    def test_target_and_stop(self):
        t = V.simulate_long(bars([(99, 99, 98, 99), (99.5, 100.5, 99, 100), (100, PLAN["target1"] + 1, 99.5, 104)]), 0, PLAN)
        self.assertEqual(t["why"], "T1")
        self.assertGreater(t["net"], 0)
        t = V.simulate_long(bars([(99, 99, 98, 99), (99.5, 100.5, 99, 100), (99, 100, 96, 97)]), 0, PLAN)
        self.assertEqual(t["why"], "stop")
        self.assertLess(t["net"], -(3 * PLAN["qty"]) + 1)          # loss plus costs

    def test_same_bar_stop_and_target_counts_as_stop(self):
        t = V.simulate_long(bars([(99, 99, 98, 99), (100, PLAN["target1"] + 1, 96, 100)]), 0, PLAN)
        self.assertEqual(t["why"], "stop")

    def test_gap_down_fills_at_open_and_time_exit(self):
        t = V.simulate_long(bars([(99, 99, 98, 99), (99.5, 100.5, 99, 100), (95, 96, 94, 95)]), 0, PLAN)
        self.assertEqual((t["why"], t["exit"]), ("stop (gap)", 95))
        flat = [(99, 99, 98, 99), (99.5, 100.5, 99, 100)] + [(100, 101, 99, 100.5)] * 6
        t = V.simulate_long(bars(flat), 0, PLAN)
        self.assertEqual((t["why"], t["days"]), ("time", V.HOLD))

    def test_exit_score(self):
        plan = {"stop": 105.0, "target1": 95.0}
        self.assertTrue(V.score_exit(bars([(100, 100, 99, 100), (100, 101, 94, 95)]), 0, plan)["correct"])
        self.assertFalse(V.score_exit(bars([(100, 100, 99, 100), (100, 106, 99, 105)]), 0, plan)["correct"])

    def test_split_is_chronological(self):
        rows = [{"date": datetime.date(2026, 1, 1) + datetime.timedelta(days=k)} for k in range(100)]
        V.split(rows)
        order = [r["period"] for r in rows]
        self.assertEqual(order, sorted(order, key=["TRAIN", "VALIDATION", "TEST"].index))
        self.assertEqual(order.count("TEST"), 20)


if __name__ == "__main__":
    unittest.main()
