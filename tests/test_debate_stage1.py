"""Offline tests for debate stage 1 (snapshot helpers + evidence catalogue). All market values are SYNTHETIC."""
import copy, glob, importlib.util, os, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "trader-debate"))


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "trader-debate", name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


EV = load("evidence")


def F(v, cls="DELAYED"):
    return {"value": v, "source": "synthetic", "as_of": "2026-01-01 10:30", "class": cls}


def NA():
    return {"value": None, "source": "missing", "as_of": None, "class": "UNAVAILABLE"}


def intraday_snap(**over):
    f = {"price": F(102.0), "day_change_pct": F(2.0),
         "vwap": F({"value": 101.0, "price_vs_vwap_pct": 0.99, "deviation_atr": 1.0, "side": "above", "slope_6_bars": 0.4, "crosses_today": 1}),
         "relative_volume": F({"cumulative_x": 1.8, "last_bar_x": 1.2}),
         "levels": F({"day_high": 102.5, "day_low": 99.5, "prev_high": 101.5, "prev_low": 98.0, "prev_close": 100.0,
                      "or_high": 101.2, "or_low": 99.6}),
         "impulse_last_6_bars": F([{"bar": "10:15", "direction": "up"}]),
         "nifty": F({"price": 20000, "day_change_pct": 0.3}),
         "sector": F({"sector": "X", "peers": 10, "median_change_pct": 0.8, "peers_up": 7}),
         "delivery_prev": F({"last_pct": 60.0, "avg_pct_prior": 50.0, "stale": False}, "HISTORICAL"),
         "futures_prev": F({"buildup": "long build-up", "oi_change_1d_pct": 2.0, "price_change_1d_pct": 1.0}, "HISTORICAL"),
         "opening_1m": F([{"o": 100, "h": 100.5, "l": 99.8, "c": 100.2}, {"o": 100.2, "h": 100.6, "l": 100.1, "c": 100.4},
                          {"o": 100.4, "h": 100.8, "l": 100.3, "c": 100.7}, {"o": 100.7, "h": 100.9, "l": 100.5, "c": 100.85}], "REALTIME")}
    f.update(over)
    return {"symbol": "TEST", "mode": "intraday", "fields": f}


class Evidence(unittest.TestCase):
    def status(self, snap, side):
        return {e["id"]: e["status"] for e in EV.evaluate(snap, side)}

    def test_bullish_snapshot_passes_buy_items_and_fails_sell_items(self):
        s = intraday_snap()
        b, se = self.status(s, "buy"), self.status(s, "sell")
        for iid in ("I_VWAP", "I_RVOL", "I_RS", "I_SECTOR", "I_ORB", "I_PDL", "I_IMPULSE", "I_OPEN", "I_DELIV", "I_OI"):
            self.assertEqual(b[iid], "PASS", iid)
            self.assertEqual(se[iid], "FAIL", iid)

    def test_unavailable_inputs_never_pass(self):
        s = intraday_snap(vwap=NA(), relative_volume=NA(), opening_1m=NA(), futures_prev=NA())
        b = self.status(s, "buy")
        for iid in ("I_VWAP", "I_RVOL", "I_OPEN", "I_OI", "X_EXTENDED"):
            self.assertEqual(b[iid], "UNAVAILABLE", iid)

    def test_stale_delivery_is_unavailable(self):
        s = intraday_snap(delivery_prev=F({"last_pct": 90.0, "avg_pct_prior": 40.0, "stale": True}, "HISTORICAL"))
        self.assertEqual(self.status(s, "buy")["I_DELIV"], "UNAVAILABLE")

    def test_risk_flags_from_bajfinance_review(self):
        v = {"value": 1103.9, "price_vs_vwap_pct": 0.81, "deviation_atr": 1.97, "side": "above", "slope_6_bars": 2.6, "crosses_today": 4}
        s = intraday_snap(vwap=F(v), day_change_pct=F(3.16))
        b = self.status(s, "buy")
        self.assertEqual(b["X_EXTENDED"], "FLAG")
        self.assertEqual(b["X_MOVED"], "FLAG")

    def test_recompute_matches_evaluate_and_does_not_mutate(self):
        s = intraday_snap()
        before = copy.deepcopy(s)
        e = EV.recompute(s, "buy", "I_RS")
        self.assertEqual(e["status"], "PASS")
        self.assertEqual(s, before)
        self.assertIsNone(EV.recompute(s, "buy", "NOPE"))

    def test_mode_filter(self):
        ids = {e["id"] for e in EV.evaluate(intraday_snap(), "buy")}
        self.assertFalse(any(i.startswith("S_") for i in ids))


class ReadOnly(unittest.TestCase):
    def test_no_order_functions_in_debate_package(self):
        for path in glob.glob(os.path.join(ROOT, "trader-debate", "*.py")):
            src = open(path, encoding="utf-8").read()
            for bad in ("placeOrder", "modifyOrder", "cancelOrder", "gttCreateRule", "gttModifyRule", "place_order"):
                self.assertNotIn(bad, src, "%s mentions %s" % (os.path.basename(path), bad))


if __name__ == "__main__":
    unittest.main()
