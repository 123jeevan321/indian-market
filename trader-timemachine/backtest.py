#!/usr/bin/env python3
"""Rule-based backtest of the opening-range breakout (BUY) and breakdown (SELL) on NSE 5-minute bars,
with Zerodha costs and slippage. Standard library only.

    python3 backtest.py --universe nifty50                  # download 60 days of 5m bars per stock, run, print
    python3 backtest.py --offline trader/cache/backtest      # rerun from the saved bars (no network)
    python3 backtest.py --write docs/BACKTEST.md             # also save the report

THE RULES ARE FIXED BEFORE LOOKING AT RESULTS (nothing is optimised):

  universe     Nifty 50 constituents today (NSE index file). SURVIVORSHIP BIAS: stocks that left the index are absent.
  data         Yahoo Finance 5-minute `.NS` bars, the last ~60 sessions only. Sessions missing any bar from 9:15 to 15:10 are skipped.
  opening range  the 9:15, 9:20 and 9:25 bars (high / low).
  signal       the first COMPLETED 5-minute bar after 9:30 whose close is above the range high (BUY) or below the range low (SELL),
               signal bar ending no later than 14:45. One trade per stock per day.
  entry        the OPEN of the NEXT bar (no look-ahead) with 1 tick (Rs 0.05) of adverse slippage.
  stop         the range midpoint, rounded away from the entry; skipped if it is on the wrong side or the risk is under
               max(0.05 % of price, 3 ticks).
  target 1     entry +/- 1.5 x risk. Skipped if Zerodha costs + slippage at the target exceed 25 % of the gross reward.
  size         floor(Rs 500 / risk per share), capped at 5x of Rs 75,000 = Rs 3,75,000 of exposure.
  fills        a stop fills at the stop (or the bar's open if it gapped through) minus 1 tick of slippage; a target needs price to trade
               THROUGH it by 1 tick; if one bar touches both, the STOP is assumed first; the position is closed at the close of the
               15:10 bar (15:15) minus 1 tick if neither was hit.
  exit modes   ALL_OUT: everything at target 1. LADDER: half at target 1, the rest with the stop moved to breakeven and a 3.5R target.
  costs        Zerodha intraday brokerage, STT, exchange, SEBI, stamp, GST (trader-budget/costs.py) per leg; entry brokerage is charged
               once per exit leg in LADDER (slightly pessimistic).

BASELINES (same stop/target mechanics and costs): (a) a random side at a random time between 9:30 and 14:45 with the stop at half the
opening-range width, repeated with 5 seeds; (b) buy at 9:30 and sell at 15:15 with Rs 75,000.

SPLIT: dates are ordered in time; the first 60 % are the "train" period and the last 40 % the "test" period. Because nothing is fitted,
both are out-of-sample for these fixed rules; the split just shows whether the result is stable across time. This is NOT walk-forward
optimisation, and ~58 sessions of one market phase is NOT enough to call any rule an edge. The report says so.
"""

import argparse
import datetime
import json
import math
import os
import random
import sys
import time
import urllib.error
import urllib.request
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
TICK = 0.05
LAST_SLOT = 71            # the 15:10 bar closes at 15:15
UA = "Mozilla/5.0 (compatible; india-equity-intraday-skill/1.0)"
NIFTY50_URL = "https://archives.nseindia.com/content/indices/ind_nifty50list.csv"
RISK_INR, CAPITAL, LEVERAGE, MIN_RR_COST_PCT = 500.0, 75000.0, 5.0, 25.0


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


COSTS = _load(os.path.join(HERE, "..", "trader-budget", "costs.py"), "costs")
LEVELS = _load(os.path.join(HERE, "..", "trader-entry", "levels.py"), "levels")


def tick_r(x, mode="near"):
    c = x / TICK
    return (math.floor(c + 1e-9) if mode == "floor" else math.ceil(c - 1e-9) if mode == "ceil" else math.floor(c + 0.5)) * TICK


def fetch(sym, cache):
    path = os.path.join(cache, sym.replace("&", "_and_") + ".json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    ys = ("^NSEI" if sym == "NIFTY" else sym + ".NS").replace("&", "%26")
    for host in ("query2", "query1"):
        url = "https://%s.finance.yahoo.com/v8/finance/chart/%s?range=60d&interval=5m" % (host, ys)
        for attempt in (0, 1):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
                    doc = json.loads(r.read().decode())
                os.makedirs(cache, exist_ok=True)
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(doc, fh)
                return doc
            except urllib.error.HTTPError as e:
                e.close()
                if e.code == 429 and attempt == 0:
                    time.sleep(5)
                    continue
                break
            except (urllib.error.URLError, OSError, ValueError):
                break
    return None


def universe(offline):
    if offline:
        return sorted(f[:-5].replace("_and_", "&") for f in os.listdir(offline) if f.endswith(".json") and f != "NIFTY.json")
    import csv, io
    text = urllib.request.urlopen(urllib.request.Request(NIFTY50_URL, headers={"User-Agent": UA}), timeout=30).read().decode("utf-8-sig")
    return sorted(r["Symbol"].strip().upper() for r in csv.DictReader(io.StringIO(text)) if r["Series"].strip() == "EQ")


def full_days(doc):
    """{date: [bar per slot 0..71]} for sessions that have every bar from 9:15 to 15:10."""
    sess = LEVELS.sessions(doc, datetime.datetime(2100, 1, 1))
    return {d: [b[s] for s in range(LAST_SLOT + 1)] for d, b in sess.items() if all(s in b for s in range(LAST_SLOT + 1))}


def settle(side, entry, qty, risk, stop, t1, bars, start, mode, slip=TICK):
    """Walk the bars from `start` (the entry bar). -> (gross, costs, reason). Stop first when a bar touches both."""
    long = side == "buy"
    sgn = 1 if long else -1
    t3 = tick_r(entry + sgn * 3.5 * risk)
    legs = []       # (qty, exit_price)
    rem, cur_stop, took_t1 = qty, stop, False
    reason = "flat"
    for s in range(start, LAST_SLOT + 1):
        b = bars[s]
        hit_stop = b["l"] <= cur_stop if long else b["h"] >= cur_stop
        if hit_stop:
            px = (min(b["o"], cur_stop) if long else max(b["o"], cur_stop)) - sgn * slip
            legs.append((rem, px)); rem = 0
            reason = "breakeven" if took_t1 else "stop"
            break
        if not took_t1:
            thru = b["h"] >= t1 + TICK if long else b["l"] <= t1 - TICK
            if thru:
                if mode == "all_out":
                    legs.append((rem, t1)); rem = 0; reason = "target"
                    break
                q1 = rem // 2 if rem > 1 else rem
                legs.append((q1, t1)); rem -= q1; took_t1 = True; cur_stop = entry
                if rem == 0:
                    reason = "target"
                    break
        else:
            thru3 = b["h"] >= t3 + TICK if long else b["l"] <= t3 - TICK
            if thru3:
                legs.append((rem, t3)); rem = 0; reason = "target3"
                break
    if rem:
        legs.append((rem, bars[LAST_SLOT]["c"] - sgn * slip))
    gross = sum(q * (px - entry) * sgn for q, px in legs)
    costs = 0.0
    for q, px in legs:
        buy, sell = (entry, px) if long else (px, entry)
        costs += COSTS.intraday_costs(q, buy, sell, "NSE", 0.0)["charges"]
    return gross, costs, reason


def make_trade(sym, day, side, bars, sig, risk_override=None, mode="all_out", stop_mode="mid"):
    """Entry on the open of bar sig+1. Returns a trade dict, or None when the rules skip it."""
    if sig + 1 > LAST_SLOT:
        return None
    long = side == "buy"
    sgn = 1 if long else -1
    oh = max(b["h"] for b in bars[:3]); ol = min(b["l"] for b in bars[:3])
    entry = tick_r(bars[sig + 1]["o"] + sgn * TICK)
    if stop_mode == "mid":
        stop = tick_r((oh + ol) / 2.0, "floor" if long else "ceil")
    else:
        half = max((oh - ol) / 2.0, TICK)
        stop = tick_r(entry - sgn * half, "floor" if long else "ceil")
    risk = (entry - stop) if long else (stop - entry)
    if risk <= 0 or risk < max(entry * 0.0005, 3 * TICK):
        return None
    qty = int(min(RISK_INR // risk, (CAPITAL * LEVERAGE) // entry))
    if qty < 1:
        return None
    t1 = tick_r(entry + sgn * 1.5 * risk)
    gross_t = qty * 1.5 * risk
    buy, sell = (entry, t1) if long else (t1, entry)
    c_t = COSTS.intraday_costs(qty, buy, sell, "NSE", TICK)["total_with_slippage"]
    if gross_t <= 0 or 100.0 * c_t / gross_t > MIN_RR_COST_PCT:
        return None
    gross, costs, reason = settle(side, entry, qty, risk, stop, t1, bars, sig + 1, mode)
    return {"date": day.isoformat(), "symbol": sym, "side": side, "slot": sig + 1, "entry": entry, "stop": stop, "qty": qty,
            "risk": risk, "reason": reason, "gross": gross, "costs": costs, "net": gross - costs, "r": (gross - costs) / (qty * risk)}


def orb_signal(bars, side):
    oh = max(b["h"] for b in bars[:3]); ol = min(b["l"] for b in bars[:3])
    for k in range(3, 66):         # the signal bar ends 9:35 .. 14:45
        c = bars[k]["c"]
        if (side == "buy" and c > oh) or (side == "sell" and c < ol):
            return k
    return None


def stats(trades, label, n_boot=2000, seed=11):
    n = len(trades)
    if not n:
        return "%-34s no trades" % label
    nets = [t["net"] for t in trades]
    wins = [x for x in nets if x > 0]
    losses = [x for x in nets if x <= 0]
    pf = (sum(wins) / -sum(losses)) if losses and sum(losses) < 0 else float("inf")
    cum = peak = dd = 0.0
    for t in sorted(trades, key=lambda t: (t["date"], t["slot"])):
        cum += t["net"]
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(nets) for _ in range(n)) / n for _ in range(n_boot))
    lo, hi = means[int(0.025 * n_boot)], means[int(0.975 * n_boot)]
    return ("%-34s n=%4d  win %4.1f%%  avg win %7.0f  avg loss %7.0f  expectancy Rs %7.1f/trade (95%% CI %7.1f..%7.1f)  "
            "avgR %+.2f  PF %s  total Rs %9.0f  maxDD Rs %8.0f  costs Rs %7.0f" % (
                label, n, 100.0 * len(wins) / n, sum(wins) / len(wins) if wins else 0, sum(losses) / len(losses) if losses else 0,
                sum(nets) / n, lo, hi, sum(t["r"] for t in trades) / n, ("%.2f" % pf) if pf != float("inf") else "inf",
                sum(nets), dd, sum(t["costs"] for t in trades)))


def main(argv=None):
    ap = argparse.ArgumentParser(description="ORB backtest on NSE 5-minute bars with Zerodha costs.")
    ap.add_argument("--offline", metavar="DIR", help="folder of saved bars (default trader/cache/backtest)")
    ap.add_argument("--cache", default="trader/cache/backtest")
    ap.add_argument("--limit", type=int, help="first N symbols only")
    ap.add_argument("--write", metavar="FILE", help="save the report as markdown")
    ap.add_argument("--seeds", type=int, default=5)
    a = ap.parse_args(argv)
    cache = a.offline or a.cache
    syms = universe(a.offline)[: a.limit] if a.limit else universe(a.offline)
    data, missing = {}, []
    for i, s in enumerate(syms):
        doc = fetch(s, cache)
        if not doc:
            missing.append(s); continue
        try:
            data[s] = full_days(doc)
        except Exception:
            missing.append(s)
    ndoc = fetch("NIFTY", cache)
    nifty = full_days(ndoc) if ndoc else {}
    dates = sorted({d for v in data.values() for d in v})
    cut = dates[int(len(dates) * 0.6)]
    out = []
    P = out.append
    P("Backtest of the opening-range breakout/breakdown, NSE Nifty 50 (today's members), 5-minute Yahoo bars")
    P("Sessions: %d (%s to %s); stocks with usable data: %d of %d%s" % (len(dates), dates[0], dates[-1], len(data), len(syms),
                                                                    ("; missing: " + ", ".join(missing)) if missing else ""))
    P("Train = sessions before %s; test = from %s on. Costs: Zerodha intraday + 1 tick slippage each side. Rs 500 risk per trade." % (cut, cut))
    P("")
    results = {}
    for side in ("buy", "sell"):
        for mode in ("all_out", "ladder"):
            tr = []
            for s, days in data.items():
                for d, bars in days.items():
                    k = orb_signal(bars, side)
                    if k is None:
                        continue
                    t = make_trade(s, d, side, bars, k, mode=mode)
                    if t:
                        tr.append(t)
            results[(side, mode)] = tr
            tag = "ORB %s %s" % ("BUY" if side == "buy" else "SELL", mode)
            P(stats([t for t in tr if t["date"] < cut.isoformat()], tag + " | train"))
            P(stats([t for t in tr if t["date"] >= cut.isoformat()], tag + " | test"))
            P(stats(tr, tag + " | all"))
            reasons = {}
            for t in tr:
                reasons[t["reason"]] = reasons.get(t["reason"], 0) + 1
            P("    exits: " + ", ".join("%s %d" % kv for kv in sorted(reasons.items())))
    P("")
    P("BASELINES (all sessions)")
    for mode in ("all_out",):
        for seed in range(a.seeds):
            rng = random.Random(100 + seed)
            tr = []
            for s, days in data.items():
                for d, bars in days.items():
                    side = rng.choice(["buy", "sell"])
                    k = rng.randint(3, 64)
                    t = make_trade(s, d, side, bars, k, mode=mode, stop_mode="half")
                    if t:
                        tr.append(t)
            P(stats(tr, "random entry, seed %d" % seed))
    bh = []
    for s, days in data.items():
        for d, bars in days.items():
            e = bars[3]["o"]
            q = int(CAPITAL // e)
            if q < 1:
                continue
            x = bars[LAST_SLOT]["c"]
            g = q * (x - e)
            c = COSTS.intraday_costs(q, e, x, "NSE", TICK)["total_with_slippage"]
            bh.append({"date": d.isoformat(), "slot": 3, "net": g - c, "gross": g, "costs": c, "r": 0.0})
    P(stats(bh, "buy 9:30 / sell 15:15, Rs 75k"))
    P("")
    P("REGIME (Nifty open-to-close on the day: trend up > +0.4 %, trend down < -0.4 %, else range) for ORB all_out, all sessions")
    reg = {}
    for d, bars in nifty.items():
        ch = 100.0 * (bars[LAST_SLOT]["c"] / bars[0]["o"] - 1)
        reg[d.isoformat()] = "up" if ch > 0.4 else "down" if ch < -0.4 else "range"
    for side in ("buy", "sell"):
        for r in ("up", "down", "range"):
            sel = [t for t in results[(side, "all_out")] if reg.get(t["date"]) == r]
            P(stats(sel, "ORB %s on %s days" % (side.upper(), r)))
    P("")
    P("READ THIS: ~%d sessions of one market phase; survivorship bias; Yahoo bars; stop-first on ambiguous bars; no news/event filter; no 2-position or" % len(dates))
    P("daily-loss limit applied (trades are independent); the expectancy confidence interval assumes independent trades, which same-day trades are not.")
    P("A rule is not an edge unless it beats the baselines out of sample over far more data and regimes. This run cannot show that.")
    text = "\n".join(out)
    print(text)
    if a.write:
        os.makedirs(os.path.dirname(a.write) or ".", exist_ok=True)
        with open(a.write, "w", encoding="utf-8") as fh:
            fh.write("```\n" + text + "\n```\n")
    return 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    sys.exit(main())
