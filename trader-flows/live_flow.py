#!/usr/bin/env python3
"""Live order-flow pressure screen over the last N minutes of today's Round 10 recording (25 stocks). Read-only, descriptive.

    python trader-flows/live_flow.py [--minutes 10]

Per stock, from the recorded SnapQuote rows in the window:
  est. buy / sell volume   traded volume split by the estimated aggressor side (quote rule, then tick rule) - an ESTIMATE
  delta %                  (buy - sell) / (buy + sell)
  price change             first to last traded price in the window
  resting buy share        total bid qty / (bid + ask qty), averaged; RESTING orders that can be cancelled at any time
  book imbalance (top 5)   (bid - ask) / (bid + ask) over the best 5 levels, last snapshot
Classification (descriptive, NOT a validated prediction):
  BUYERS IN CONTROL   delta >= +20 % AND price up AND resting buy share >= 0.5
  BUYING, NO PROGRESS delta >= +20 % but price flat or down (absorption by sellers?)
  SELLERS IN CONTROL  delta <= -20 % AND price down
  MIXED               anything else
"""
import argparse, datetime, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from angel_recorder import side_of, ist_now     # noqa: E402


def read(path, since):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            if r.get("recv", "") >= since:
                rows.append(r)
    return rows


def screen(minutes=10, day=None, now=None):
    now = now or ist_now()
    day = day or now.strftime("%Y-%m-%d")
    since = (now - datetime.timedelta(minutes=minutes)).isoformat(timespec="milliseconds")
    folder = os.path.join(ROOT, "trader", "ticks_r10", day)
    out = []
    for f in sorted(os.listdir(folder)):
        if not f.endswith(".jsonl"):
            continue
        ticks = read(os.path.join(folder, f), since)
        if len(ticks) < 20:
            continue
        buy = sell = 0
        prev = None
        share = []
        for t in ticks:
            if prev is not None and t.get("volume") is not None and prev.get("volume") is not None:
                dv = max(0, t["volume"] - prev["volume"])
                s = side_of(t, prev)
                buy += dv if s > 0 else 0
                sell += dv if s < 0 else 0
            if t.get("tbq") and t.get("tsq"):
                share.append(t["tbq"] / (t["tbq"] + t["tsq"]))
            prev = t
        last = ticks[-1]
        bq = sum(q for _, q, _ in last.get("bids") or [])
        aq = sum(q for _, q, _ in last.get("asks") or [])
        tot = buy + sell
        delta = (buy - sell) / tot if tot else 0.0
        chg = last["ltp"] / ticks[0]["ltp"] - 1 if ticks[0]["ltp"] else 0.0
        rs = sum(share) / len(share) if share else None
        if delta >= 0.2 and chg > 0.001 and (rs or 0) >= 0.5:
            label = "BUYERS IN CONTROL"
        elif delta >= 0.2:
            label = "BUYING, NO PROGRESS"
        elif delta <= -0.2 and chg < -0.001:
            label = "SELLERS IN CONTROL"
        else:
            label = "MIXED"
        out.append({"sym": f[:-6], "ticks": len(ticks), "first": ticks[0]["recv"][11:19], "last_t": last["recv"][11:19], "ltp": last["ltp"],
                    "buy": buy, "sell": sell, "delta_pct": round(100 * delta, 1), "chg_pct": round(100 * chg, 2),
                    "resting_buy_share": round(rs, 2) if rs is not None else None,
                    "book_imb5": round((bq - aq) / (bq + aq), 2) if bq + aq else None, "label": label})
    out.sort(key=lambda r: (r["label"] != "BUYERS IN CONTROL", -r["delta_pct"]))
    return out


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--minutes", type=int, default=10)
    a = p.parse_args(argv)
    rows = screen(a.minutes)
    print("| Stock | Window (IST) | LTP | Est. buy vol | Est. sell vol | Delta | Price change | Resting buy share | Book imbalance (top 5) | Read |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        print("| %s | %s-%s | ₹%.2f | %s | %s | %+.1f%% | %+.2f%% | %s | %s | %s |" % (
            r["sym"], r["first"], r["last_t"], r["ltp"], format(r["buy"], ","), format(r["sell"], ","), r["delta_pct"], r["chg_pct"],
            r["resting_buy_share"], r["book_imb5"], r["label"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
