"""Offline tests for the 2-stock rotation. Bars are SYNTHETIC."""

import datetime
import unittest

from _load import load


def mk(rows, start=datetime.date(2024, 1, 1)):
    out, d = [], start
    for o, h, l, c, v in rows:
        while d.weekday() >= 5:
            d += datetime.timedelta(days=1)
        out.append({"d": d, "o": o, "h": h, "l": l, "c": c, "v": v})
        d += datetime.timedelta(days=1)
    return out


class Rotation(unittest.TestCase):
    def setUp(self):
        self.m = load("trader-swing", "momentum_rotator")

    def base(self):
        rows = [(1000, 1005, 995, 1000, 1000000)] * 30
        rows.append((1001, 1025, 1000, 1024, 3000000))   # +2.4 %, rvol 3, Rs 100 cr a day, closes at 96 % of range, above 3-day high
        b = mk(rows)
        self.m.SW.enrich(b)
        return b

    def test_signal_fires_and_rejects_chasing(self):
        b = self.base()
        self.assertTrue(self.m.is_signal(b, len(b) - 1, 0.015, 0.035))
        b[-1].update(c=1045, h=1046)                      # +4.5 %: chasing
        self.m.SW.enrich(b)
        self.assertFalse(self.m.is_signal(b, len(b) - 1, 0.015, 0.035))

    def test_leg_size_keeps_loss_and_costs_inside_1500(self):
        q = self.m.leg_qty(1000.0, 985.0)
        c = self.m.COSTS.delivery_costs(q, 1000.0, 985.0, slippage_per_share=0.05)["total_with_slippage"]
        self.assertLessEqual(q * 15 + c, 1500)
        self.assertLessEqual(q * 1000.0, 100000)

    def test_day_two_time_exit_and_stop_first(self):
        b = self.base() + []
        b += mk([(1024, 1030, 1020, 1026, 1), (1026, 1031, 1021, 1027, 1)], start=b[-1]["d"] + datetime.timedelta(days=1))
        self.m.SW.enrich(b)
        tr = self.m.simulate(b, 30, "close", "fixed", 0.03)
        self.assertEqual(tr["reason"], "time")
        b[31].update(h=1100, l=900)                       # both levels touched: stop assumed first
        tr = self.m.simulate(b, 30, "close", "fixed", 0.03)
        self.assertTrue(tr["reason"].startswith("stop"))

    def test_sector_filter(self):
        d = datetime.date(2024, 2, 1)
        rets = {d: {"A": 0.03, "B": 0.01, "C": 0.02}}
        ind = {"A": "Auto", "B": "Auto", "C": "IT"}
        self.assertTrue(self.m.sector_ok("A", d, rets, ind, 0.005))
        self.assertFalse(self.m.sector_ok("B", d, rets, ind, 0.005))


if __name__ == "__main__":
    unittest.main()
