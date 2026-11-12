"""Offline tests for the Three-Agent Trading Report. Market values are SYNTHETIC."""
import os, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "trader-debate"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import debate, report                       # noqa: E402
from test_debate_stage3 import snap, GOOD   # noqa: E402


class Report(unittest.TestCase):
    def test_four_sections_in_order_and_no_trade_badge(self):
        md = report.report_md(debate.run(snap(), stats={}))
        heads = ["🟢 1. BUYER AGENT", "🔴 2. SELLER AGENT", "⚖️ 3. JUDGE AGENT", "📊 4. FINAL TRADE REPORT"]
        pos = [md.index(h) for h in heads]
        self.assertEqual(pos, sorted(pos))
        self.assertIn("🟡 WAIT / NO TRADE", md)
        self.assertIn("DELAYED", md)
        self.assertNotIn("guaranteed profit", md.lower())

    def test_buy_decision_shows_plan_and_pick_prefers_it(self):
        buy = debate.run(snap(), stats=GOOD)
        no = debate.run(snap(), stats={})
        md = report.report_md(buy)
        self.assertIn("### 🟢 BUY", md)
        self.assertIn("Net R:R at T1", md)
        self.assertIs(report.pick([no, buy]), buy)
        self.assertIsNone(report.pick([]))


if __name__ == "__main__":
    unittest.main()
