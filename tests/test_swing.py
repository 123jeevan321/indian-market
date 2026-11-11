"""Offline tests for trader-swing. The bars are SYNTHETIC and built here."""

import datetime
import unittest

from _load import load


def bars(closes, vol=1000, spread=1.0, start=datetime.date(2024, 1, 1)):
    out, d = [], start
    for c in closes:
        while d.weekday() >= 5:
            d += datetime.timedelta(days=1)
        out.append({"d": d, "o": c, "h": c + spread, "l": c - spread, "c": c, "v": vol})
        d += datetime.timedelta(days=1)
    return out


class Swing(unittest.TestCase):
    def setUp(self):
        self.s = load("trader-swing", "swing")

    def test_delivery_costs_match_hand_calc(self):
        c = self.s.COSTS.delivery_costs(27, 3579.0, 3640.69)
        self.assertAlmostEqual(c["stt"], 194.93, places=2)      # 0.1 % of (96,633 + 98,298.63)
        self.assertAlmostEqual(c["stamp"], 14.49, places=2)     # 0.015 % of the buy
        self.assertEqual(c["dp"], 15.34)
        self.assertAlmostEqual(c["charges"], 232.06, places=2)

    def test_quantity_keeps_loss_plus_costs_inside_the_cap(self):
        for entry, stop in ((1356.0, 1331.0), (250.0, 240.0), (4000.0, 3880.0)):
            q = self.s.capped_qty(entry, entry - stop, 1500, 10 ** 7)
            c = self.s.COSTS.delivery_costs(q, entry, stop, slippage_per_share=0.05)["total_with_slippage"]
            self.assertLessEqual(q * (entry - stop) + c, 1500, (entry, stop, q))
            q2 = q + 2
            c2 = self.s.COSTS.delivery_costs(q2, entry, stop, slippage_per_share=0.05)["total_with_slippage"]
            self.assertGreater(q2 * (entry - stop) + c2, 1500)

    def test_capital_caps_quantity(self):
        self.assertEqual(self.s.capped_qty(1000.0, 1.0, 1500, 50000), 50)

    def test_squeeze_fires_on_breakout_from_tight_base(self):
        closes = [100 + 0.2 * i for i in range(220)] + [144.0] * 10 + [147.0]
        b = bars(closes, vol=1000)
        b[-1]["v"] = 3000
        b[-1]["h"], b[-1]["l"] = 147.2, 144.5
        self.s.enrich(b)
        st = self.s.signal(b, len(b) - 1, "squeeze", {"swing_highs": [], "swing_lows": [], "fvgs": []})
        self.assertEqual(st, 144.5)

    def test_sweep_needs_a_reclaim(self):
        closes = [100 + 0.1 * i for i in range(230)]
        b = bars(closes)
        lo20 = min(x["l"] for x in b[-21:-1])
        b[-1].update(l=lo20 - 1.0, c=b[-2]["c"] + 0.5, h=b[-2]["c"] + 0.6, v=2000)
        self.s.enrich(b)
        self.assertIsNotNone(self.s.signal(b, len(b) - 1, "sweep", {"swing_highs": [], "swing_lows": [], "fvgs": []}))
        b[-1]["c"] = lo20 - 0.5                                   # closes below: no reclaim
        self.s.enrich(b)
        self.assertIsNone(self.s.signal(b, len(b) - 1, "sweep", {"swing_highs": [], "swing_lows": [], "fvgs": []}))

    def test_trade_hits_stop_first_on_ambiguous_bar(self):
        b = bars([100.0] * 230)
        self.s.enrich(b)
        t = 220
        b[t + 1].update(o=100.0, h=200.0, l=50.0, c=100.0)        # touches everything
        tr = self.s.make_trade(b, t, 98.0, 1500, 10 ** 6)
        self.assertLess(tr["gross"], 0)

    def test_fractal_swing_high_is_known_only_two_bars_later(self):
        b = bars([1, 2, 5, 2, 1, 1, 1], spread=0.1)
        self.s.enrich(b)
        self.assertIsNone(b[2]["sh_known"])
        self.assertEqual(b[4]["sh_known"][0], 2)


if __name__ == "__main__":
    unittest.main()
