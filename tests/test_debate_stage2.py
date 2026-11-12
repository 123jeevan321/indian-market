"""Offline tests for debate stage 2 (Buyer and Seller agents, plan arithmetic). Market values are SYNTHETIC."""
import ast, copy, os, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "trader-debate"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import buyer, seller, common as C          # noqa: E402
from test_debate_stage1 import intraday_snap, F, NA   # noqa: E402


def bearish_snap():
    return intraday_snap(
        price=F(98.0), day_change_pct=F(-2.0),
        vwap=F({"value": 99.0, "price_vs_vwap_pct": -1.0, "deviation_atr": -1.0, "side": "below", "slope_6_bars": -0.4, "crosses_today": 1}),
        relative_volume=F({"cumulative_x": 1.8, "last_bar_x": 1.2}),
        levels=F({"day_high": 100.5, "day_low": 97.6, "prev_high": 101.0, "prev_low": 98.5, "prev_close": 100.0, "or_high": 100.4, "or_low": 98.8}),
        impulse_last_6_bars=F([{"bar": "10:15", "direction": "down"}]), atr_5m=F(0.3),
        nifty=F({"price": 20000, "day_change_pct": 0.4}),
        sector=F({"sector": "X", "peers": 10, "median_change_pct": -0.5, "peers_up": 3}),
        futures_prev=F({"buildup": "short build-up", "oi_change_1d_pct": 2.0, "price_change_1d_pct": -1.0}, "HISTORICAL"),
        delivery_prev=F({"last_pct": 40.0, "avg_pct_prior": 50.0, "stale": False}, "HISTORICAL"),
        opening_1m=F([{"o": 100, "h": 100.1, "l": 99.5, "c": 99.6}] * 4, "REALTIME"))


class Plans(unittest.TestCase):
    def test_size_keeps_loss_within_budget(self):
        for mode, entry, stop in (("intraday", 1110.5, 1104.9), ("swing", 431.2, 418.0), ("intraday", 50.0, 49.7)):
            qty, loss = C.size(mode, "long", entry, stop)
            self.assertGreater(qty, 0)
            self.assertLessEqual(loss, C.CONFIG[mode]["risk_inr"])

    def test_targets_are_net_of_costs(self):
        p = C.build_plan("intraday", "long", 1110.5, 1104.9, "test")
        self.assertGreaterEqual(p["net_rr_t1"], 1.5 - 0.02)
        self.assertGreater(p["target2"], p["target1"])
        s = C.build_plan("intraday", "short", 98.0, 98.6, "test")
        self.assertLess(s["target1"], 98.0)
        self.assertLess(s["do_not_enter_past"], 98.0)

    def test_plan_problems_flag_t1_beyond_day_high(self):
        p = C.build_plan("intraday", "long", 100.0, 99.0, "test")
        self.assertTrue(any("needs a new high" in x for x in C.plan_problems("intraday", p, day_high=100.5, day_low=98)))


class Agents(unittest.TestCase):
    def test_buyer_builds_case_on_bullish_data_and_seller_does_not(self):
        s = intraday_snap(atr_5m=F(0.3))
        b, se = buyer.analyse(s), seller.analyse(s)
        self.assertEqual(b["stance"], "BUY CASE")
        self.assertEqual(se["stance"], "NO SELL CASE")
        self.assertLess(b["plan"]["stop"], b["plan"]["entry"])
        self.assertTrue(all(e["status"] == "PASS" for e in b["evidence_cited"]))

    def test_seller_builds_intraday_short_with_square_off(self):
        se = seller.analyse(bearish_snap())
        self.assertEqual(se["stance"], "SELL CASE")
        self.assertIn("MIS", se["sell_type"])
        self.assertGreater(se["plan"]["stop"], se["plan"]["entry"])
        self.assertTrue(any("15:15" in x for x in se["invalidation"]))
        self.assertIsNotNone(se["hidden_weakness_note"])          # NIFTY up, stock down

    def test_missing_data_gives_no_case_never_a_signal(self):
        s = intraday_snap(price=NA(), vwap=NA(), levels=NA(), relative_volume=NA(), atr_5m=NA(), impulse_last_6_bars=NA(),
                          day_change_pct=NA(), opening_1m=NA(), sector=NA(), futures_prev=NA(), delivery_prev=NA(), nifty=NA())
        self.assertEqual(buyer.analyse(s)["stance"], "NO BUY CASE")
        self.assertEqual(seller.analyse(s)["stance"], "NO SELL CASE")

    def test_agents_do_not_mutate_snapshot(self):
        s = intraday_snap(atr_5m=F(0.3))
        before = copy.deepcopy(s)
        buyer.analyse(s); seller.analyse(s)
        self.assertEqual(s, before)

    def test_confidence_is_never_validated(self):
        b = buyer.analyse(intraday_snap(atr_5m=F(0.3)))
        self.assertFalse(b["confidence"]["validated_out_of_sample"])

    def test_agents_are_independent_modules(self):
        for me, other in (("buyer", "seller"), ("seller", "buyer")):
            with open(os.path.join(ROOT, "trader-debate", me + ".py"), encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            names = {a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
            mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
            self.assertNotIn(other, names | mods)


if __name__ == "__main__":
    unittest.main()
