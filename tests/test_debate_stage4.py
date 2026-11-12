"""Offline tests for debate stage 4 (terminal view, history, reassess). Market values are SYNTHETIC."""
import json, os, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "trader-debate"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import debate, render                      # noqa: E402
from test_debate_stage3 import snap        # noqa: E402


class View(unittest.TestCase):
    def setUp(self):
        self.rec = debate.run(snap(), stats={})

    def test_three_panels_and_timeline(self):
        out = render.render(self.rec)
        for part in ("TIMELINE", "BUYER AGENT", "SELLER AGENT", "JUDGE", "DECISION: NO TRADE", "CHALLENGES RECEIVED FROM SELLER",
                     "FINAL RESPONSE", "WHAT WOULD CHANGE THE DECISION", "PAPER ONLY"):
            self.assertIn(part, out)
        self.assertLess(out.index("TIMELINE"), out.index("BUYER AGENT"))
        self.assertLess(out.index("SELLER AGENT"), out.index("| JUDGE  judge"))

    def test_every_rendered_message_comes_from_the_record(self):
        out = render.render(self.rec)
        for m in self.rec["messages"]:
            self.assertIn(m["t"][11:23], out)

    def test_history_and_reassess_are_append_only(self):
        old = debate.OUT
        with tempfile.TemporaryDirectory() as d:
            debate.OUT = d
            try:
                p1 = debate.save(self.rec)
                before = open(p1, encoding="utf-8").read()
                rec2 = debate.run(snap(t="2026-01-05T11:00:00"), stats={}, reassesses=self.rec["id"])
                p2 = debate.save(rec2)
                hist = debate.history(date="2026-01-05")
                self.assertEqual([h[0] for h in hist], [p1, p2])
                self.assertEqual(open(p1, encoding="utf-8").read(), before)
                self.assertEqual(json.load(open(p2, encoding="utf-8"))["reassesses"], self.rec["id"])
                self.assertIn("reassesses", render.render(rec2))
                self.assertEqual(debate.history(symbol="NOPE"), [])
            finally:
                debate.OUT = old


if __name__ == "__main__":
    unittest.main()
