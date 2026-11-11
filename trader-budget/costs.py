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


DELIVERY = {"as_of": "2026-11-10", "source": "https://zerodha.com/charges (Equity delivery, NSE)",
            "brokerage": 0.0, "stt_pct": 0.1, "exchange_nse_pct": 0.00307, "sebi_per_crore": 10.0,
            "stamp_buy_pct": 0.015, "gst_pct": 18.0, "dp_per_sell": 15.34}


def delivery_costs(qty, buy_price, sell_price, sells=1, slippage_per_share=0.0, rates=None):
    """Itemised delivery (CNC) round-trip costs: zero brokerage, STT 0.1 % on BOTH sides, stamp 0.015 % on the buy,
    exchange + SEBI on turnover, GST on (exchange + SEBI), and a Rs 15.34 DP charge per sell (per scrip per day)."""
    r = rates or DELIVERY
    qty = int(qty)
    buy_val, sell_val = qty * float(buy_price), qty * float(sell_price)
    turnover = buy_val + sell_val
    stt = turnover * r["stt_pct"] / 100.0
    exch = turnover * r["exchange_nse_pct"] / 100.0
    sebi = turnover * r["sebi_per_crore"] / 1e7
    stamp = buy_val * r["stamp_buy_pct"] / 100.0
    gst = (r["brokerage"] + exch + sebi) * r["gst_pct"] / 100.0
    dp = r["dp_per_sell"] * max(1, int(sells)) if qty > 0 else 0.0
    slip = qty * float(slippage_per_share) * 2.0
    total = r["brokerage"] + stt + exch + sebi + stamp + gst + dp
    return {"stt": _r(stt), "exchange": _r(exch), "sebi": _r(sebi), "stamp": _r(stamp), "gst": _r(gst), "dp": _r(dp),
            "charges": _r(total), "slippage": _r(slip), "total_with_slippage": _r(total + slip), "rates_as_of": r["as_of"]}


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
MARGIN_URL = "https://zerodha.com/margin-calculator/Equity/"
AUTO_SQUAREOFF_FEE = 50.0   # Rs per order + 18 % GST, per Zerodha's support page (read 2026-11-10); max 30,000 qty per order


def parse_leverage(html_text):
    """Zerodha's equity margin page -> {SYMBOL: MIS leverage}. Rows: Scrip | MIS margin % | MIS leverage | CO margin % | CO leverage."""
    out = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html_text, flags=re.S):
        cells = [re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.S)]
        if len(cells) >= 3 and cells[2].lower().endswith("x"):
            try:
                out[cells[0].upper()] = float(cells[2][:-1])
            except ValueError:
                pass
    return out


def fetch_leverage(symbols=None, cache="trader/leverage.json"):
    req = urllib.request.Request(MARGIN_URL, headers={"User-Agent": "Mozilla/5.0"})
    table = parse_leverage(urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace"))
    if not table:
        raise RuntimeError("could not read the MIS leverage table from %s" % MARGIN_URL)
    import os
    os.makedirs(os.path.dirname(cache) or ".", exist_ok=True)
    with open(cache, "w", encoding="utf-8") as fh:
        json.dump({"source": MARGIN_URL, "read": __import__("datetime").date.today().isoformat(), "mis_leverage": table}, fh)
    return table


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if a and a[0] == "leverage":
        try:
            table = fetch_leverage()
        except Exception as e:
            print("costs.py: %s" % e, file=sys.stderr)
            return 1
        want = [x.upper() for x in a[1:]]
        for s_ in (want or sorted(table)[:10]):
            print("%-14s MIS leverage %s" % (s_, ("%gx" % table[s_]) if s_ in table else "not listed (treat as 1x, or not intraday-eligible)"))
        print("Wrote trader/leverage.json (%d scrips). Zerodha says margins can change during the day; re-read before relying on it." % len(table))
        return 0
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
