#!/usr/bin/env python3
"""Zerodha equity-intraday trading costs for trader-budget and trader-risk. Standard library only.

The rates below were read from https://zerodha.com/charges on 2026-11-10 (Equity intraday column,
NSE). They change: SEBI/NSE/STT/stamp revisions happen a few times a year. RATES["as_of"] says when
they were read; `costs.py verify` re-reads the page and warns if a number moved. Never trust an old
rate: re-verify before relying on a net-reward figure.

    python3 costs.py 500 1000.00 1010.00          # qty, buy price, sell price (long or short: same costs)
    python3 costs.py 500 1000.00 1010.00 --slip 0.05
    python3 costs.py verify                        # compare RATES with zerodha.com/charges

Charges on an intraday (MIS) round trip, per Zerodha's published table:

  brokerage    the lower of 0.03 % of the order value or Rs 20, per EXECUTED order (so twice a round trip)
  STT          0.025 % of the SELL value only
  exchange     NSE 0.00307 % of turnover (buy value + sell value)
  SEBI         Rs 10 per crore of turnover
  stamp duty   0.003 % of the BUY value only
  GST          18 % of (brokerage + SEBI + exchange transaction charges)

A long buys first and sells later; a short sells first and buys later. The charges are the same for
both because they depend on the buy leg and the sell leg, not on the order they happened in.
Slippage is NOT a charge: it is the price you actually get versus the price you planned. It is added
separately (per share, each side) so a "net reward" is honest about both.
"""

import html as _html
import json
import re
import sys
import urllib.request

RATES = {
    "as_of": "2026-11-10",
    "source": "https://zerodha.com/charges (Equity intraday, NSE)",
    "brokerage_pct": 0.03,        # percent of order value
    "brokerage_cap": 20.0,        # rupees per executed order
    "stt_sell_pct": 0.025,        # percent of sell value
    "exchange_nse_pct": 0.00307,  # percent of turnover
    "exchange_bse_pct": 0.00375,
    "sebi_per_crore": 10.0,       # rupees per crore of turnover
    "stamp_buy_pct": 0.003,       # percent of buy value
    "gst_pct": 18.0,              # percent of brokerage + SEBI + exchange charges
}


def _r(x):
    return round(x + 1e-12, 2)


def intraday_costs(qty, buy_price, sell_price, exchange="NSE", slippage_per_share=0.0, rates=None):
    """Itemised round-trip costs in rupees for `qty` shares bought at buy_price and sold at sell_price."""
    r = rates or RATES
    qty = int(qty)
    buy_val = qty * float(buy_price)
    sell_val = qty * float(sell_price)
    turnover = buy_val + sell_val
    brok_buy = min(buy_val * r["brokerage_pct"] / 100.0, r["brokerage_cap"]) if qty > 0 else 0.0
    brok_sell = min(sell_val * r["brokerage_pct"] / 100.0, r["brokerage_cap"]) if qty > 0 else 0.0
    brokerage = brok_buy + brok_sell
    stt = sell_val * r["stt_sell_pct"] / 100.0
    ex_pct = r["exchange_bse_pct"] if str(exchange).upper() == "BSE" else r["exchange_nse_pct"]
    exchange_chg = turnover * ex_pct / 100.0
    sebi = turnover * r["sebi_per_crore"] / 1e7
    stamp = buy_val * r["stamp_buy_pct"] / 100.0
    gst = (brokerage + sebi + exchange_chg) * r["gst_pct"] / 100.0
    slip = qty * float(slippage_per_share) * 2.0          # each side
    total = brokerage + stt + exchange_chg + sebi + stamp + gst
    return {
        "brokerage": _r(brokerage), "stt": _r(stt), "exchange": _r(exchange_chg), "sebi": _r(sebi),
        "stamp": _r(stamp), "gst": _r(gst), "charges": _r(total), "slippage": _r(slip),
        "total_with_slippage": _r(total + slip), "rates_as_of": r["as_of"],
    }


def net_pnl(side, qty, entry, exit_price, exchange="NSE", slippage_per_share=0.0):
    """(gross, costs dict, net) for a trade closed at exit_price. side is 'buy' (long) or 'sell' (short)."""
    qty = int(qty)
    if str(side).lower() in ("buy", "long"):
        gross = qty * (float(exit_price) - float(entry))
        c = intraday_costs(qty, entry, exit_price, exchange, slippage_per_share)
    else:
        gross = qty * (float(entry) - float(exit_price))
        c = intraday_costs(qty, exit_price, entry, exchange, slippage_per_share)
    return _r(gross), c, _r(gross - c["total_with_slippage"])


def verify():
    """Re-read zerodha.com/charges and compare the equity-intraday numbers. Returns a list of warnings."""
    req = urllib.request.Request(RATES_URL, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    text = re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style).*?</\1>", "", html, flags=re.S | re.I))
    text = re.sub(r"\s*\|\s*(\|\s*)*", "|", _html.unescape(text))
    warns = []
    checks = [("0.025% on the sell side", "STT 0.025% sell side"), ("NSE: 0.00307%", "NSE transaction charge 0.00307%"),
              ("0.003% or", "stamp duty 0.003% buy side"), ("10 / crore", "SEBI Rs 10 per crore"),
              ("18% on (brokerage", "GST 18%"), ("0.03% or Rs. 20", "brokerage 0.03% or Rs 20")]
    for needle, label in checks:
        if needle not in text:
            warns.append("could not find %r on the page: %s may have changed" % (needle, label))
    return warns


RATES_URL = "https://zerodha.com/charges"


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if a and a[0] == "verify":
        try:
            w = verify()
        except Exception as e:  # network trouble is not a rate change
            print("costs.py: could not read %s: %s" % (RATES_URL, e), file=sys.stderr)
            return 1
        if w:
            print("Rates may be out of date (built-in rates are from %s):" % RATES["as_of"])
            for x in w:
                print("  - " + x)
            return 1
        print("The built-in rates (read %s) still match %s" % (RATES["as_of"], RATES_URL))
        return 0
    slip = 0.0
    if "--slip" in a:
        i = a.index("--slip")
        slip = float(a[i + 1])
        del a[i:i + 2]
    if len(a) != 3:
        print(__doc__)
        return 1
    qty, buy, sell = int(a[0]), float(a[1]), float(a[2])
    c = intraday_costs(qty, buy, sell, "NSE", slip)
    print(json.dumps(c, indent=2))
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):  # the rupee sign on a Windows console
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    sys.exit(main())
