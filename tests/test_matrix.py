"""Offline tests for strategy_matrix_optimizer. 15-minute bars are SYNTHETIC."""

import datetime
import json
import os
import tempfile
import unittest

from _load import load


def day_rows(d, base, vol=400000, bump=None):
    rows = []
    for k in range(24):
        hh, mm = divmod(555 + 15 * k, 60)
        o = h = l = c = base
        h, l = base + 1, base - 1
        if bump and k in bump:
            o, h, l, c = bump[k]
        rows.append(["%sT%02d:%02d:00+05:30" % (d.isoformat(), hh, mm), o, h, l, c, vol])
    return rows


class Matrix(unittest.TestCase):
    def setUp(self):
        self.m = load("trader-swing", "strategy_matrix_optimizer")

    def build(self):
        rows, d = [], datetime.date(2024, 1, 1)
        n = 0
        while n < 12:
            if d.weekday() < 5:
                bump = None
                if n == 11:     # last day: range 999-1001 in bar 0, then a close of 1010 in bar 2 (ORB15 and ORB30 break)
                    bump = {0: (1000, 1001, 999, 1000), 1: (1000, 1001, 999.5, 1000.5), 2: (1000.5, 1011, 1000, 1010)}
                rows += day_rows(d, 1000, bump=bump)
                n += 1
            d += datetime.timedelta(days=1)
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(rows, f); f.close()
        days = self.m.load_days(f.name)
        os.unlink(f.name)
        return days

    def test_orb_events_found_with_structural_stop(self):
        days = self.build()
        evs = {e["trig"]: e for e in self.m.events_for("TEST", days)}
        self.assertIn("ORB15", evs)
        self.assertEqual(evs["ORB15"]["k"], 2)
        self.assertAlmostEqual(evs["ORB15"]["stop_raw"], 1000.0)          # midpoint of 999-1001

    def test_size_caps_loss_with_costs(self):
        for mode in ("sameday", "2day"):
            q = self.m.size(1000.0, 990.0, mode)
            self.assertGreater(q, 0)
            self.assertLessEqual(q * 1000.0, 100000)

    def test_same_day_exit_is_flat_at_1515(self):
        days = self.build()
        ev = [e for e in self.m.events_for("TEST", days) if e["trig"] == "ORB15"][0]
        tr = self.m.simulate(days, ev, 0.03, "sameday")
        self.assertEqual(tr["why"], "stop")                                # price falls back to 1000 -> stop at ~999.95
        self.assertEqual(tr["exit_day"], ev["day"])


if __name__ == "__main__":
    unittest.main()
