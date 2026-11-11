"""Offline tests for the read-only Angel One recorder. Ticks are SYNTHETIC."""

import os
import re
import unittest

from _load import ROOT, load


def tick(ltp, vol, bid, ask, bq=100, aq=100):
    return {"recv": "2026-11-12T10:00:00.000", "ltp": ltp, "volume": vol, "bids": [(bid, bq, 1)], "asks": [(ask, aq, 1)]}


class Recorder(unittest.TestCase):
    def setUp(self):
        self.r = load("trader-flows", "angel_recorder")

    def test_never_places_orders(self):
        with open(os.path.join(ROOT, "trader-flows", "angel_recorder.py"), encoding="utf-8") as fh:
            code = fh.read()
        for bad in ("placeOrder", "modifyOrder", "cancelOrder", "gttCreateRule", "gttModifyRule", "place_order"):
            self.assertNotIn(bad, code)

    def test_book_sides_decided_by_price(self):
        raw = {"best_5_buy_data": [{"price": 100100, "quantity": 5}], "best_5_sell_data": [{"price": 100000, "quantity": 9}]}
        bids, asks = self.r.split_book(raw)
        self.assertEqual(bids[0][0], 1000.0)
        self.assertEqual(asks[0][0], 1001.0)

    def test_flow_estimates_delta(self):
        ticks = [tick(1000.0, 1000, 999.95, 1000.0),
                 tick(1000.0, 1300, 999.95, 1000.05),     # traded at the ask -> buy 300
                 tick(999.95, 1500, 999.90, 1000.0),      # traded at the bid -> sell 200
                 tick(1000.10, 1600, 1000.05, 1000.15, bq=300, aq=100)]  # above the ask -> buy 100
        rows = self.r.flow(ticks)
        self.assertEqual(rows[0]["est_buy"], 400)
        self.assertEqual(rows[0]["est_sell"], 200)
        self.assertEqual(rows[0]["est_cum_delta"], 200)
        self.assertGreater(rows[0]["book_imbalance_top5"], 0)


if __name__ == "__main__":
    unittest.main()
