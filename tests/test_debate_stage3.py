"""Offline tests for debate stage 3 (rebuttals, Judge, risk gate, orchestrator). Market values are SYNTHETIC."""
import copy, os, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "trader-debate"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import buyer, seller, judge, debate        # noqa: E402
from test_debate_stage1 import intraday_snap, F   # noqa: E402

GOOD = {"intraday": {"I_PDL": {"n": 120, "expectancy": 45.0, "ci_low": 5.0}, "I_ORB": {"n": 120, "expectancy": 30.0, "ci_low": 2.0}}}


ROOMY = F({"day_high": 104.0, "day_low": 99.5, "prev_high": 101.5, "prev_low": 98.0, "prev_close": 100.0, "or_high": 101.2, "or_low": 99.6})


def snap(t="2026-01-05T10:00:00", **over):
    over.setdefault("levels", ROOMY)
    s = intraday_snap(atr_5m=F(0.3), **over)
    s["snapshot_time_ist"], s["hash"], s["unavailable"] = t, "synthetic", []
    s["fields"]["price"]["as_of"] = t.replace("T", " ")[:16]     # fresh bar unless a test says otherwise
    return s


def verdict(s, stats=None, state=None):
    rec = debate.run(s, state=state, stats=stats if stats is not None else {})
    return rec, rec["messages"][-1]["content"]


class Judge(unittest.TestCase):
    def test_no_validated_setup_means_no_trade(self):
        rec, v = verdict(snap())
        self.assertEqual(v["decision"], "NO TRADE")
        self.assertTrue(any("no validated untouched-test edge" in r for r in v["buyer_assessment"]["reasons"]))

    def test_validated_clean_setup_can_be_bought(self):
        rec, v = verdict(snap(), stats=GOOD)
        self.assertEqual(v["decision"], "BUY", v["buyer_assessment"]["reasons"])
        self.assertEqual(v["plan"]["direction"], "long")

    def test_entry_window_and_risk_flags_block(self):
        _, v = verdict(snap(t="2026-01-05T09:20:00"), stats=GOOD)
        self.assertEqual(v["decision"], "NO TRADE")
        self.assertTrue(any("09:30-14:45" in r for r in v["buyer_assessment"]["reasons"]))
        ext = {"value": 101.0, "price_vs_vwap_pct": 0.99, "deviation_atr": 2.2, "side": "above", "slope_6_bars": 0.4, "crosses_today": 1}
        _, v = verdict(snap(vwap=F(ext)), stats=GOOD)
        self.assertEqual(v["decision"], "NO TRADE")
        self.assertTrue(any("X_EXTENDED" in r for r in v["buyer_assessment"]["reasons"]))

    def test_correlated_exposure_and_daily_loss_block(self):
        _, v = verdict(snap(), stats=GOOD, state={"open_positions": [{"symbol": "OTHER", "sector": "X"}]})
        self.assertEqual(v["decision"], "NO TRADE")
        _, v = verdict(snap(), stats=GOOD, state={"day_pnl": -2100, "daily_loss_limit": 2000})
        self.assertEqual(v["decision"], "NO TRADE")

    def test_tampered_evidence_is_struck(self):
        s = snap()
        b = buyer.analyse(s)
        b["evidence_cited"][0]["observed"] = "invented number"
        a = judge._assess(s, "buy", b, [], GOOD, None)
        self.assertTrue(a["struck"])
        self.assertEqual(a["struck"][0]["id"], b["evidence_cited"][0]["id"])

    def test_tampered_plan_is_caught(self):
        s = snap()
        b = buyer.analyse(s)
        b["plan"]["qty"] *= 3
        probs, _ = judge._verify_plan(s, b)
        self.assertTrue(any("qty" in p for p in probs))

    def test_agent_failure_never_becomes_a_signal(self):
        orig = buyer.analyse
        try:
            buyer.analyse = lambda s: 1 / 0
            rec, v = verdict(snap(), stats=GOOD)
        finally:
            buyer.analyse = orig
        self.assertEqual(v["decision"], "NO TRADE")
        self.assertIn("debate incomplete", v["why"])
        self.assertEqual(rec["messages"][1]["content"]["stance"], "AGENT FAILED")

    def test_judge_explains_both_sides_and_triggers(self):
        _, v = verdict(snap())
        for k in ("buyer_right", "buyer_wrong", "seller_right", "seller_wrong", "more_reliable_evidence",
                  "rejected_arguments", "what_would_change_it"):
            self.assertIn(k, v)
        self.assertTrue(v["what_would_change_it"])


class ReviewFixes(unittest.TestCase):
    def test_timeout_returns_without_waiting_for_stuck_agent(self):
        import time
        old = debate.TIMEOUT_S
        debate.TIMEOUT_S = 0.3
        try:
            t = time.time()
            res, err = debate.guarded(lambda: time.sleep(3), "X")
            self.assertLess(time.time() - t, 1.5)
            self.assertIsNone(res)
            self.assertIn("timed out", err)
        finally:
            debate.TIMEOUT_S = old

    def test_stale_price_means_no_trade(self):
        s = snap()
        s["fields"]["price"]["as_of"] = "2026-01-05 09:40"            # 20 minutes old at 10:00
        _, v = verdict(s, stats=GOOD)
        self.assertEqual(v["decision"], "NO TRADE")
        self.assertIn("minutes old", v["why"])

    def test_case_from_another_snapshot_is_rejected(self):
        s = snap()
        b = buyer.analyse(s)
        b["snapshot_hash"] = "other"
        a = judge._assess(s, "buy", b, [], GOOD, None)
        self.assertFalse(a["passed"])
        self.assertIn("not the debate's snapshot", a["reasons"][0])

    def test_agents_cannot_alter_what_the_judge_sees(self):
        orig = seller.challenge
        def vandal(own, other, snapshot):
            other["evidence_cited"].clear(); snapshot["fields"].clear()
            return []
        try:
            seller.challenge = vandal
            rec, v = verdict(snap(), stats=GOOD)
        finally:
            seller.challenge = orig
        self.assertEqual(v["decision"], "BUY")
        self.assertTrue(rec["snapshot"]["fields"])

    def test_moved_challenge_uses_its_own_flag(self):
        s = snap(day_change_pct=F(1.0))
        ch = [{"id": "S2b", "fatal": True, "text": "x"}]
        self.assertEqual(judge._fatal_checks(s, "buy", {"setup": "I_PDL"}, ch, GOOD), [])

    def test_angel_skipped_while_recorder_writes(self):
        import snapshot as S
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "_session.log"), "w").close()
            self.assertTrue(S.recorder_active(folder=d))
        self.assertFalse(S.recorder_active(folder=os.path.join(ROOT, "no-such-folder")))


class Debate(unittest.TestCase):
    def test_steps_in_order_with_timestamps(self):
        rec, _ = verdict(snap())
        steps = [m["step"] for m in rec["messages"]]
        self.assertEqual(steps, sorted(steps))
        self.assertEqual(steps[:3], [1, 2, 3])
        self.assertTrue(all(m["t"] and m["snapshot_hash"] == "synthetic" for m in rec["messages"]))
        self.assertTrue(rec["paper_only"])

    def test_seller_challenges_late_buyer(self):
        ext = {"value": 101.0, "price_vs_vwap_pct": 0.99, "deviation_atr": 2.2, "side": "above", "slope_6_bars": 0.4, "crosses_today": 1}
        s = snap(vwap=F(ext))
        ch = seller.challenge({}, buyer.analyse(s), s)
        self.assertTrue(any(c["id"] == "S2" and c["fatal"] for c in ch))
        resp = buyer.respond(buyer.analyse(s), ch, s)
        self.assertTrue(any(r["to"] == "S2" and r["concede"] for r in resp))

    def test_records_are_append_only(self):
        rec, _ = verdict(snap())
        old = debate.OUT
        with tempfile.TemporaryDirectory() as d:
            debate.OUT = d
            try:
                p1, p2 = debate.save(rec), debate.save(rec)
            finally:
                debate.OUT = old
            self.assertNotEqual(p1, p2)


if __name__ == "__main__":
    unittest.main()
