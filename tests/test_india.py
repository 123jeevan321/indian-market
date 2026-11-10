"""Offline tests for the India-specific behaviour. No network. Fixtures under tests/fixtures are trimmed
copies of real NSE files; the charts built inside the tests are SYNTHETIC and say so."""

import datetime
import os
import unittest

from _load import FIX, ROOT, load


class Costs(unittest.TestCase):
    """Zerodha equity intraday, hand-computed from the published rates (read 2026-11-10)."""

    def setUp(self):
        self.c = load("trader-budget", "costs")

    def test_known_round_trip(self):
        # 50 x Rs 1500 buy, Rs 1510 sell
        r = self.c.intraday_costs(50, 1500.0, 1510.0)
        self.assertEqual(r["brokerage"], 40.0)                 # 0.03 % of 75,000 = 22.5, capped at 20, twice
        self.assertAlmostEqual(r["stt"], 18.88, places=2)      # 0.025 % of the 75,500 sell value
        self.assertAlmostEqual(r["exchange"], 4.62, places=2)  # 0.00307 % of 150,500
        self.assertAlmostEqual(r["sebi"], 0.15, places=2)      # Rs 10 / crore
        self.assertAlmostEqual(r["stamp"], 2.25, places=2)     # 0.003 % of the 75,000 buy value
        self.assertAlmostEqual(r["gst"], 8.06, places=2)       # 18 % of brokerage + SEBI + exchange
        self.assertAlmostEqual(r["charges"], 73.95, places=2)

    def test_small_order_pays_percentage_not_cap(self):
        r = self.c.intraday_costs(10, 1000.0, 1000.0)          # 10,000 x 0.03 % = 3.0 each way
        self.assertEqual(r["brokerage"], 6.0)

    def test_slippage_is_separate(self):
        r = self.c.intraday_costs(100, 500.0, 505.0, slippage_per_share=0.05)
        self.assertEqual(r["slippage"], 10.0)                  # 100 shares x 0.05 x 2 sides
        self.assertAlmostEqual(r["total_with_slippage"], r["charges"] + 10.0, places=2)

    def test_short_and_long_cost_the_same(self):
        g1, c1, n1 = self.c.net_pnl("buy", 40, 1000.0, 1012.0)
        g2, c2, n2 = self.c.net_pnl("sell", 40, 1012.0, 1000.0)
        self.assertEqual(g1, 480.0)
        self.assertEqual(g2, 480.0)
        self.assertEqual(c1["charges"], c2["charges"])


class Calendar(unittest.TestCase):
    def test_diwali_balipratipada_2026_is_a_holiday(self):
        scan = load("trader-scanner", "scan")
        ok, why = scan.trading_day(datetime.date(2026, 11, 10))
        self.assertFalse(ok)
        self.assertIn("Balipratipada", why)

    def test_normal_weekday_open_and_session_hours(self):
        scan = load("trader-scanner", "scan")
        self.assertTrue(scan.trading_day(datetime.date(2026, 11, 11))[0])
        self.assertEqual(scan.session(datetime.date(2026, 11, 11)), (datetime.time(9, 15), datetime.time(15, 30)))

    def test_weekend_closed(self):
        scan = load("trader-scanner", "scan")
        self.assertFalse(scan.trading_day(datetime.date(2026, 11, 14))[0])

    def test_ist_has_no_dst(self):
        scan = load("trader-scanner", "scan")
        utc = datetime.datetime(2026, 7, 1, 3, 45)
        self.assertEqual(scan.to_ist(utc), datetime.datetime(2026, 7, 1, 9, 15))
        self.assertEqual(scan.ist_to_utc(datetime.datetime(2026, 1, 1, 9, 15)), datetime.datetime(2026, 1, 1, 3, 45))

    def test_every_script_has_the_same_holidays(self):
        mods = [load(f, n) for f, n in (("trader-scanner", "scan"), ("trader-entry", "entry"), ("trader-exit", "exit"),
                                        ("trader-risk", "check"), ("trader-alerts", "alerts"))]
        base = mods[0].NSE_HOLIDAYS
        for m in mods[1:]:
            self.assertEqual(m.NSE_HOLIDAYS, base)
        self.assertEqual(len(base), 20)


class Universe(unittest.TestCase):
    def test_nse_universe_from_index_csv(self):
        scan = load("trader-scanner", "scan")
        with open(os.path.join(FIX, "trader-scanner", "ind_nifty50list.csv"), encoding="utf-8") as fh:
            text = fh.read()
        kept, counts, _ = scan.build_universe({"ind_nifty50list.csv": text})
        syms = [k for k, _ in kept]
        self.assertEqual(syms, ["BAJAJ-AUTO", "INFY", "M&M", "RELIANCE"])
        self.assertEqual(counts["not the EQ series"], 1)
        self.assertEqual(counts["dummy row"], 1)

    def test_exclude_list(self):
        scan = load("trader-scanner", "scan")
        with open(os.path.join(FIX, "trader-scanner", "ind_nifty50list.csv"), encoding="utf-8") as fh:
            text = fh.read()
        kept, counts, _ = scan.build_universe({"ind_nifty50list.csv": text}, exclude=["infy"])
        self.assertNotIn("INFY", [k for k, _ in kept])
        self.assertEqual(counts["excluded (ASM / GSM / blocked list)"], 1)

    def test_yahoo_symbol_mapping(self):
        scan = load("trader-scanner", "scan")
        self.assertEqual(scan.to_yahoo("RELIANCE"), "RELIANCE.NS")
        self.assertEqual(scan.to_yahoo("M&M"), "M%26M.NS")
        self.assertEqual(scan.to_yahoo("BAJAJ-AUTO"), "BAJAJ-AUTO.NS")
        self.assertEqual(scan.from_yahoo("M%26M.NS"), "M&M")


def synthetic_chart(symbol, day, bars):
    """A SYNTHETIC Yahoo-shaped 5-minute chart for tests. bars = [(o, h, l, c, v), ...] from 9:15 IST."""
    start = datetime.datetime.combine(day, datetime.time(9, 15)) - datetime.timedelta(hours=5.5)
    t0 = int((start - datetime.datetime(1970, 1, 1)).total_seconds())
    return {"chart": {"result": [{"meta": {"symbol": symbol + ".NS", "regularMarketTime": t0 + 300 * len(bars),
                                           "chartPreviousClose": bars[0][0], "currency": "INR"},
                                  "timestamp": [t0 + 300 * i for i in range(len(bars))],
                                  "indicators": {"quote": [{"open": [b[0] for b in bars], "high": [b[1] for b in bars],
                                                            "low": [b[2] for b in bars], "close": [b[3] for b in bars],
                                                            "volume": [b[4] for b in bars]}]}}], "error": None}}


class EntryTimer(unittest.TestCase):
    def setUp(self):
        self.e = load("trader-entry", "entry")
        self.day = datetime.date(2026, 11, 11)           # a Wednesday, an NSE trading day
        flat = [(1000, 1004, 996, 1000, 1000)] * 3      # opening range 9:15-9:30: high 1004, low 996
        self.up = flat + [(1000, 1003, 999, 1002, 900), (1002, 1010, 1001, 1008, 3000)]      # 9:30 inside, 9:35 closes 1008 > 1004
        self.down = flat + [(1000, 1001, 998, 999, 900), (999, 1000, 990, 992, 3000)]        # 9:35 closes 992 < 996

    def _eval(self, bars, side, hhmm):
        ch = self.e.parse_chart(__import__("json").dumps(synthetic_chart("TEST", self.day, bars)), "TEST")
        now = self.e.ist_to_utc(datetime.datetime.combine(self.day, datetime.time(*hhmm)))
        return self.e.evaluate(ch, now, setup="orb", side=side)

    def test_buy_triggers_on_close_above_range_high(self):
        r = self._eval(self.up, "buy", (9, 41))
        self.assertEqual(r["status"], "triggered")
        self.assertEqual(r["side"], "buy")
        self.assertEqual(r["trigger"]["price"], 1008.0)
        self.assertEqual(r["level"], 1004.0)

    def test_sell_triggers_on_close_below_range_low(self):
        r = self._eval(self.down, "sell", (9, 41))
        self.assertEqual(r["status"], "triggered")
        self.assertEqual(r["side"], "sell")
        self.assertEqual(r["trigger"]["price"], 992.0)
        self.assertEqual(r["level"], 996.0)

    def test_no_cross_trigger(self):
        self.assertEqual(self._eval(self.up, "sell", (9, 41))["status"], "waiting")
        self.assertEqual(self._eval(self.down, "buy", (9, 41))["status"], "waiting")

    def test_nothing_before_the_range_is_set(self):
        r = self._eval(self.up, "buy", (9, 28))
        self.assertNotEqual(r["status"], "triggered")

    def test_closed_on_a_holiday(self):
        e = self.e
        ch = e.parse_chart(__import__("json").dumps(synthetic_chart("TEST", datetime.date(2026, 11, 10), self.up)), "TEST")
        now = e.ist_to_utc(datetime.datetime(2026, 11, 10, 10, 0))
        r = e.evaluate(ch, now, setup="orb")
        self.assertEqual(r["status"], "no-data")
        self.assertIn("holiday", r["reason"])


class ExitPlanner(unittest.TestCase):
    def setUp(self):
        self.x = load("trader-exit", "exit")
        self.D = self.x.D

    def test_long_plan_ticks_and_ladder(self):
        c = self.x.compute(1330.00, "or_mid", None, "r", self.D("1.5"), 1328.50, 1315.00, side="buy")
        self.assertEqual(c["stop"], self.D("1321.75"))              # (1328.50 + 1315.00) / 2, already on a tick
        self.assertEqual(c["risk"], self.D("8.25"))
        self.assertEqual(c["target"], self.D("1342.40"))            # 1330 + 1.5 x 8.25 = 1342.375 -> nearest 0.05
        self.assertEqual([t["name"] for t in c["targets"]], ["T1", "T2", "T3"])
        self.assertEqual([t["r"] for t in c["targets"]], [1.5, 2.5, 3.5])

    def test_short_plan_stop_rounds_up_away_from_entry(self):
        c = self.x.compute(1313.00, "or_mid", None, "r", self.D("1.5"), 1328.50, 1315.00, side="sell")
        self.assertGreater(c["stop"], c["entry"])
        self.assertLess(c["target"], c["entry"])
        self.assertEqual(c["side"], "sell")
        self.assertEqual(c["stop"] % self.x.TICK, 0)

    def test_stop_on_the_wrong_side_is_refused(self):
        with self.assertRaises(self.x.PlanError):
            self.x.compute(1330.00, "price", self.D("1335.00"), "r", self.D("1.5"), side="buy")
        with self.assertRaises(self.x.PlanError):
            self.x.compute(1330.00, "price", self.D("1325.00"), "r", self.D("1.5"), side="sell")

    def test_stop_too_tight_for_the_spread_is_refused(self):
        with self.assertRaises(self.x.PlanError):
            self.x.compute(1330.00, "price", self.D("1329.90"), "r", self.D("1.5"), side="buy")

    def test_pct_stop_pads_the_right_way(self):
        long_ = self.x.compute(1000.00, "pct", self.D("0.5"), "r", self.D("1.5"), side="buy")
        short = self.x.compute(1000.00, "pct", self.D("0.5"), "r", self.D("1.5"), side="sell")
        self.assertEqual(long_["stop"], self.D("995.00"))
        self.assertEqual(short["stop"], self.D("1005.00"))


class Sizing(unittest.TestCase):
    def setUp(self):
        self.s = load("trader-budget", "size")
        self.cfg = {}   # the module's India defaults

    def plan(self, side="buy", entry=1330.0, stop=1322.4, target=1345.2):
        return {"symbol": "RELIANCE", "side": side, "setup": "orb", "date": "2026-11-11", "entry": entry,
                "stop": stop, "target": target, "flat_by": "15:15"}

    def test_defaults_are_the_confirmed_risk_rules(self):
        d = self.s.DEFAULTS
        self.assertEqual(d["budget"], 75000)
        self.assertEqual(d["max_loss_per_trade_inr"], 500)
        self.assertEqual(d["max_daily_loss_inr"], 2000)   # the user allows 1,000 to 3,000
        self.assertEqual(d["max_trades_per_day"], 0)      # 0 = no cap on the number of trades
        self.assertEqual(d["max_open_positions"], 2)
        self.assertEqual(d["max_open_risk_inr"], 1000)
        self.assertEqual(d["mis_leverage"], 5)            # usual Zerodha MIS figure; per-stock table can lower it
        self.assertEqual(d["flat_by"], "15:15")

    def test_quantity_is_risk_over_stop_distance_rounded_down(self):
        r = self.s.size_trade(self.plan(entry=500.0, stop=495.0, target=512.5), self.cfg, limit=500.0)
        self.assertEqual(r["qty"], 100)                 # 500 / 5
        self.assertEqual(r["max_loss"], 500.0)
        r = self.s.size_trade(self.plan(entry=500.0, stop=493.0, target=520.0), self.cfg, limit=500.0)
        self.assertEqual(r["qty"], 71)                  # floor(500 / 7)

    def test_short_quantity_uses_stop_minus_entry(self):
        r = self.s.size_trade(self.plan("sell", entry=500.0, stop=505.0, target=492.5), self.cfg, limit=500.0)
        self.assertEqual(r["side"], "sell")
        self.assertEqual(r["qty"], 100)

    def test_capital_caps_the_quantity_without_leverage(self):
        r = self.s.size_trade(self.plan(entry=1330.0, stop=1322.4, target=1345.2), {"mis_leverage": 1, "max_position_pct": 100,
                                                                                   "max_order_inr": 75000}, limit=1330.0)
        self.assertEqual(r["qty"], 56)                  # 75,000 / 1,330 beats 500 / 7.6 = 65
        self.assertEqual(r["bound_by"], "position cap")

    def test_with_5x_leverage_the_risk_rule_binds(self):
        r = self.s.size_trade(self.plan(entry=1330.0, stop=1322.4, target=1345.2), self.cfg, limit=1330.0)
        self.assertEqual(r["qty"], 65)                  # floor(500 / 7.6)
        self.assertEqual(r["bound_by"], "max loss")

    def test_tiny_target_is_refused_because_of_costs(self):
        # risk 2.00, target 2.00 away: the target pays ~Rs 100 on 50 shares and costs are far over 25 % of it
        r = self.s.size_trade(self.plan(entry=1000.0, stop=998.0, target=1002.0), self.cfg, limit=1000.0)
        self.assertGreater(r["qty"], 0)
        self.assertIsNotNone(r["refusal"])

    def test_stop_is_rounded_away_from_the_entry(self):
        r = self.s.size_trade(self.plan(stop=1322.43, target=1345.2), self.cfg, limit=1330.0)
        self.assertEqual(r["stop"], 1322.40)            # a long's stop floors to the tick
        r = self.s.size_trade(self.plan("sell", entry=1330.0, stop=1337.62, target=1315.0), self.cfg, limit=1330.0)
        self.assertEqual(r["stop"], 1337.65)            # a short's stop ceils to the tick

    def test_net_reward_is_after_costs(self):
        r = self.s.size_trade(self.plan(), self.cfg, limit=1330.0)
        gross = r["qty"] * (r["target"] - r["entry"])
        self.assertLess(r["net_reward"], gross)
        self.assertGreater(r["net_loss"], r["max_loss"])


class RiskGate(unittest.TestCase):
    def setUp(self):
        self.r = load("trader-risk", "check")
        self.now = self.r.ist_to_utc(datetime.datetime(2026, 11, 11, 10, 5))

    def order(self, **kw):
        o = {"symbol": "RELIANCE", "side": "buy", "qty": "56", "type": "limit", "time_in_force": "day",
             "limit_price": "1330.00", "order_class": "bracket", "take_profit_limit_price": "1345.20",
             "stop_loss_stop_price": "1322.40", "exchange": "NSE", "product": "MIS"}
        o.update(kw)
        return o

    def run_check(self, orders, state=None):
        return self.r.check(orders, {}, None, None, state, None, self.now)

    def test_clean_order_passes(self):
        res = self.run_check([self.order()])
        self.assertEqual(res["results"][0]["verdict"], "PASS", res["results"][0]["reasons"])

    def test_index_futures_and_options_are_blocked(self):
        for sym in ("NIFTY", "BANKNIFTY", "NIFTY26NOVFUT", "BANKNIFTY26NOV48000CE"):
            res = self.run_check([self.order(symbol=sym)])
            self.assertEqual(res["results"][0]["verdict"], "BLOCK", sym)

    def test_delivery_product_is_blocked(self):
        res = self.run_check([self.order(product="CNC")])
        self.assertEqual(res["results"][0]["verdict"], "BLOCK")

    def test_off_tick_price_is_blocked(self):
        res = self.run_check([self.order(limit_price="1330.02")])
        self.assertEqual(res["results"][0]["verdict"], "BLOCK")

    def test_loss_over_the_cap_is_blocked(self):
        res = self.run_check([self.order(qty="100")])        # 100 x 7.60 = 760 > 500
        self.assertEqual(res["results"][0]["verdict"], "BLOCK")

    def test_window_blocks_the_opening_minutes_and_the_holiday(self):
        early = self.r.ist_to_utc(datetime.datetime(2026, 11, 11, 9, 20))
        res = self.r.check([self.order()], {}, None, None, None, None, early)
        self.assertEqual(res["results"][0]["verdict"], "BLOCK")
        holiday = self.r.ist_to_utc(datetime.datetime(2026, 11, 10, 10, 5))
        res = self.r.check([self.order()], {}, None, None, None, None, holiday)
        self.assertEqual(res["results"][0]["verdict"], "BLOCK")

    def test_third_open_position_is_blocked(self):
        state = {"orders": [
            {"status": "placed", "date": "2026-11-11", "symbol": "TCS", "side": "buy", "kind": "entry", "max_loss": 300},
            {"status": "placed", "date": "2026-11-11", "symbol": "INFY", "side": "buy", "kind": "entry", "max_loss": 300}]}
        res = self.run_check([self.order()], state)
        self.assertEqual(res["results"][0]["verdict"], "BLOCK")
        self.assertTrue(any("positions" in x or "open risk" in x for x in res["results"][0]["reasons"]))


class FlowsData(unittest.TestCase):
    def setUp(self):
        self.f = load("trader-flows", "flows")
        self.dir = os.path.join(FIX, "trader-flows")

    def test_parse_bhavcopy_keeps_eq_series_only(self):
        with open(os.path.join(self.dir, "sec_bhavdata_full_09112026.csv"), encoding="utf-8") as fh:
            table = self.f.parse_bhav(fh.read())
        self.assertIn("RELIANCE", table)
        self.assertEqual(float(table["RELIANCE"]["DELIV_PER"]), 51.98)

    def test_a_holiday_file_with_the_previous_days_data_is_skipped(self):
        files = self.f.trading_files(3, end=datetime.date(2026, 11, 10), offline=self.dir)
        self.assertEqual([d.isoformat() for d, _ in files], ["2026-11-09", "2026-11-06"])

    def test_delivery_command_runs_offline(self):
        rows = self.f.delivery_rows(["RELIANCE"], 2, self.f.trading_files(2, end=datetime.date(2026, 11, 10), offline=self.dir))
        series = rows[0][1]
        self.assertEqual(series[0]["deliv_pct"], 51.98)
        self.assertEqual(series[1]["deliv_pct"], 66.83)


class LeverageAndDeals(unittest.TestCase):
    def test_leverage_table_parse(self):
        c = load("trader-budget", "costs")
        html = ("<table><tr><td>Scrip</td><td>MIS/CO</td><td>CO</td></tr><tr><td>Margin %</td><td>Leverage</td></tr>"
                "<tr><td>INFY</td><td>20%</td><td>5x</td><td>20%</td><td>5x</td></tr>"
                "<tr><td>20MICRONS</td><td>23.41%</td><td>4.27x</td><td>23.41%</td><td>4.27x</td></tr></table>")
        self.assertEqual(c.parse_leverage(html), {"INFY": 5.0, "20MICRONS": 4.27})

    def test_deals_parse(self):
        f = load("trader-flows", "flows")
        text = ("Date,Symbol,Security Name,Client Name,Buy/Sell,Quantity Traded,Trade Price / Wght. Avg. Price,Remarks\n"
                "09-NOV-2026,AARTIDRUGS,Aarti Drugs Ltd.,QE SECURITIES LLP,BUY,885686,497.86,-\n")
        rows = f.parse_deals(text, "bulk")
        self.assertEqual(rows[0]["symbol"], "AARTIDRUGS")
        self.assertEqual(rows[0]["side"], "BUY")
        self.assertAlmostEqual(rows[0]["value_lacs"], 4409.5, places=1)


class Levels(unittest.TestCase):
    """SYNTHETIC session: flat morning at 1000 with normal volume, then an impulse bar up on big volume."""

    def setUp(self):
        self.L = load("trader-entry", "levels")

    def doc(self):
        days = [datetime.date(2026, 11, d) for d in (2, 3, 4, 5, 6, 9, 11)]       # 11 Nov is the 'today' under test
        bars_by_day = {}
        for d in days:
            bars = [(1000, 1001, 999, 1000, 1000)] * 8
            if d == days[-1]:
                bars[6] = (1000, 1010, 1000, 1009, 5000)                         # impulse: range 10 vs 2, volume 5x
            bars_by_day[d] = bars
        ts, o, h, l, c, v = [], [], [], [], [], []
        for d, bars in bars_by_day.items():
            t0 = int((datetime.datetime.combine(d, datetime.time(9, 15)) - datetime.timedelta(hours=5.5)
                      - datetime.datetime(1970, 1, 1)).total_seconds())
            for i, b in enumerate(bars):
                ts.append(t0 + 300 * i); o.append(b[0]); h.append(b[1]); l.append(b[2]); c.append(b[3]); v.append(b[4])
        return {"chart": {"result": [{"timestamp": ts, "indicators": {"quote": [{"open": o, "high": h, "low": l, "close": c, "volume": v}]}}]}}

    def test_vwap_relative_volume_and_impulse(self):
        now = self.L.ist_to_utc(datetime.datetime(2026, 11, 11, 9, 55))        # 8 bars have completed
        r = self.L.compute(self.doc(), now)
        self.assertEqual(r["bars"], 8)
        self.assertEqual(r["vwap"]["side"], "below")      # the last bar went back to 1000, under the spike-lifted VWAP
        self.assertGreater(r["relative_volume"]["cumulative_x"], 1.3)
        self.assertEqual(r["levels"]["prev_high"], 1001)
        self.assertEqual([i["direction"] for i in r["impulse_last_6_bars"]], ["up"])
        self.assertEqual(r["profile_today"]["approximate"], True)

    def test_vwap_is_volume_weighted(self):
        bars = [{"h": 10, "l": 10, "c": 10, "v": 1}, {"h": 20, "l": 20, "c": 20, "v": 3}]
        self.assertAlmostEqual(self.L.vwap_series(bars)[-1], 17.5)


class RepoShape(unittest.TestCase):
    SKILLS = ["trader-scanner", "trader-news", "trader-entry", "trader-exit", "trader-timemachine", "trader-risk",
              "trader-budget", "trader-broker", "trader-alerts", "trader-analyst", "trader-flows", "trader-desk"]

    def test_skill_folders_have_a_skill_md_with_frontmatter(self):
        for s in self.SKILLS:
            p = os.path.join(ROOT, s, "SKILL.md")
            self.assertTrue(os.path.isfile(p), s)
            with open(p, encoding="utf-8") as fh:
                head = fh.read(600)
            self.assertIn("name: %s" % s, head, s)

    def test_no_us_market_leftovers_in_the_tools(self):
        banned = ("alpaca", "nasdaqtrader", "sec.gov", "edgar", "america/new_york", "stooq", "jakeschincariol")
        for s in self.SKILLS:
            for f in os.listdir(os.path.join(ROOT, s)):
                if f.endswith(".py"):
                    with open(os.path.join(ROOT, s, f), encoding="utf-8") as fh:
                        text = fh.read().lower()
                    for b in banned:
                        self.assertNotIn(b, text, "%s/%s still mentions %s" % (s, f, b))

    def test_readme_says_it_is_for_india(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
            self.assertIn("India", fh.read()[:600])


if __name__ == "__main__":
    unittest.main()
