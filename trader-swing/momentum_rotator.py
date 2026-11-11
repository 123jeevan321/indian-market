#!/usr/bin/env python3
"""2-Stock Sector-Split Rotation (1-2 day BTST momentum, NSE cash delivery, LONG ONLY): backtest + live scan + trade cards.

    python3 momentum_rotator.py backtest [--offline] [--write docs/MOMENTUM_BACKTEST.md]
    python3 momentum_rotator.py scan [--angel]          # after 14:45 with --angel (live snapshot), or after 15:35 from daily bars

RULE (signal on day t, every input known by 15:15 that day):
  - day gain from the previous close between GAIN_MIN and GAIN_MAX (default +1.5 % to +3.5 %), never >= +4 % (no chasing);
  - relative volume >= 2.0 (day volume / 20-day average; at 14:45 the day is not finished, so live RVOL is scaled by time elapsed);
  - close in the top 20 % of the day's range and above the prior 3-day high;
  - sector strength: the median day return of the stock's NSE Industry group beats NIFTY, and the stock beats its group median;
  - liquidity: 20-day average traded value >= Rs 50 crore, price >= Rs 100, universe = today's Nifty 200.
ENTRY: the signal-day close (BTST buy 14:45-15:15); the report also shows next-day-open entry.
STOP: fixed 1.5 % below entry, or structural (signal-day low - 0.1 ATR). SIZE: loss + delivery costs + slippage <= Rs 1,500, leg <= Rs 1 lakh.
EXIT: target (+2.5/3.0/3.5 %), stop, or the close of day 2. A gap through a level fills at the open; a bar touching both counts as the stop.
PORTFOLIO: max 2 legs at a time, never two in the same Industry, ranked by relative volume.
BASELINE: random entries on liquid Nifty 200 stocks with the same stop, target, holding period, sizing and costs.
"""

import argparse
import csv
import datetime
import importlib.util
import io
import json
import os
import random
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(rel, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


SW = _load("swing.py", "swing")
COSTS = SW.COSTS
TICK = SW.TICK
N200 = "https://archives.nseindia.com/content/indices/ind_nifty200list.csv"
N500 = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
RISK, LEG_CAP, MAX_LEGS = 1500.0, 100000.0, 2


def index_list(url):
    text = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": SW.UA}), timeout=40).read().decode("utf-8-sig")
    return {r["Symbol"].strip().upper(): r["Industry"].strip() for r in csv.DictReader(io.StringIO(text)) if r["Series"].strip() == "EQ"}


def leg_qty(entry, stop):
    """Shares so that (entry - stop) loss + delivery costs + slippage <= RISK and the leg <= LEG_CAP."""
    return SW.capped_qty(entry, entry - stop, RISK, LEG_CAP)


def day_returns(data):
    """{date: {symbol: day return}} for the industry medians."""
    out = {}
    for s, b in data.items():
        for i in range(1, len(b)):
            out.setdefault(b[i]["d"], {})[s] = b[i]["c"] / b[i - 1]["c"] - 1
    return out


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return (xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0) if n else 0.0


def sector_ok(sym, d, rets, industry, nifty_ret):
    ind = industry.get(sym)
    if not ind or d not in rets or sym not in rets[d]:
        return False
    peers = [r for s, r in rets[d].items() if industry.get(s) == ind]
    med = median(peers)
    return med > nifty_ret and rets[d][sym] > med


def is_signal(b, t, gmin, gmax, rvol_min=2.0):
    x, p = b[t], b[t - 1]
    g = x["c"] / p["c"] - 1
    rng = x["h"] - x["l"]
    if not (gmin <= g <= gmax) or g >= 0.04 or rng <= 0:
        return False
    if (x["c"] - x["l"]) / rng < 0.8 or x["rvol"] < rvol_min:
        return False
    if x["c"] <= max(q["h"] for q in b[t - 3:t]):
        return False
    return x["avgval"] >= 50e7 and x["c"] >= 100


def simulate(b, t, entry_at, stop_mode, tgt, hold=2):
    """One trade. Returns dict or None (skipped)."""
    if t + 1 >= len(b):
        return None
    atr = b[t]["atr"]
    entry = SW.tick((b[t]["c"] if entry_at == "close" else b[t + 1]["o"]) + TICK, up=True)
    stop = SW.tick(entry * 0.985) if stop_mode == "fixed" else SW.tick(b[t]["l"] - 0.1 * atr)
    if entry - stop <= 2 * TICK:
        return None
    qty = leg_qty(entry, stop)
    if qty < 1:
        return None
    target = SW.tick(entry * (1 + tgt), up=True)
    first = t + 1
    last = min(t + hold, len(b) - 1)
    exit_px, reason, exit_k = None, "time", last
    for k in range(first, last + 1):
        x = b[k]
        o = x["o"] if (k > t + 1 or entry_at == "close") else entry
        if o <= stop:
            exit_px, reason, exit_k = o - TICK, "stop-gap", k; break
        if o >= target:
            exit_px, reason, exit_k = o, "target-gap", k; break
        if x["l"] <= stop:
            exit_px, reason, exit_k = stop - TICK, "stop", k; break
        if x["h"] >= target:
            exit_px, reason, exit_k = target, "target", k; break
    if exit_px is None:
        exit_px = b[last]["c"] - TICK
    gross = qty * (exit_px - entry)
    cost = COSTS.delivery_costs(qty, entry, exit_px)["charges"]
    return {"entry_day": b[t]["d"] if entry_at == "close" else b[t + 1]["d"], "exit_day": b[exit_k]["d"], "entry": entry, "stop": stop,
            "qty": qty, "risk": entry - stop, "value": qty * entry, "gross": gross, "costs": cost, "net": gross - cost,
            "r": (gross - cost) / RISK, "reason": reason, "days_held": exit_k - t if entry_at == "close" else exit_k - t}


def run(data, industry, rets, nifty_ret, variant, rng=None):
    """Chronological 2-leg portfolio. variant: dict(gmin,gmax,entry_at,stop_mode,tgt,random)."""
    sigs = {}
    for s, b in data.items():
        if s not in industry:
            continue
        for t in range(25, len(b) - 1):
            x = b[t]
            if variant.get("random"):
                if x["avgval"] >= 50e7 and x["c"] >= 100 and rng.random() < 0.004:
                    sigs.setdefault(x["d"], []).append((rng.random(), s, t))
                continue
            if is_signal(b, t, variant["gmin"], variant["gmax"]) and sector_ok(s, x["d"], rets, industry, nifty_ret.get(x["d"], 0)):
                sigs.setdefault(x["d"], []).append((x["rvol"], s, t))
    open_legs, trades = [], []
    both_stopped = {}
    for d in sorted(sigs):
        open_legs = [p for p in open_legs if p["exit_day"] >= d]
        for _, s, t in sorted(sigs[d], reverse=True):
            if len(open_legs) >= MAX_LEGS:
                break
            if any(industry.get(p["symbol"]) == industry.get(s) or p["symbol"] == s for p in open_legs):
                continue
            tr = simulate(data[s], t, variant["entry_at"], variant["stop_mode"], variant["tgt"])
            if tr:
                tr["symbol"], tr["signal_day"] = s, d
                open_legs.append(tr)
                trades.append(tr)
                if tr["reason"].startswith("stop"):
                    both_stopped[tr["exit_day"]] = both_stopped.get(tr["exit_day"], 0) + 1
    return trades, sum(1 for v in both_stopped.values() if v >= 2)


def cmd_backtest(a):
    industry = index_list(N200)
    syms = list(industry)
    data, missing = SW.load_all(a.cache, syms, fetch=not a.offline)
    nifty = data.pop("^NSEI")
    for b in data.values():
        SW.enrich(b)
    nret = {nifty[i]["d"]: nifty[i]["c"] / nifty[i - 1]["c"] - 1 for i in range(1, len(nifty))}
    rets = day_returns(data)
    days = sorted(nret)
    cut = days[int(len(days) * 0.6)]
    out = ["# 2-Stock Sector-Split Rotation: backtest (NSE Nifty 200, daily bars, 1-2 days, long only)", "",
           "Run %s. Data: Yahoo daily %s to %s, %d of %d Nifty 200 symbols. Max loss per leg Rs 1,500 INCLUDING delivery costs and 1 tick slippage "
           "each side; leg <= Rs 1 lakh; max 2 legs, different NSE Industry groups. IS = before %s, OOS = from %s. Survivorship bias: today's members." % (
               datetime.date.today(), days[0], days[-1], len(data), len(syms), cut, cut), "", SW.HEAD]
    variants = []
    for gmin, gmax, gname in ((0.015, 0.020, "+1.5-2.0%"), (0.015, 0.035, "+1.5-3.5%")):
        for entry_at in ("close", "open"):
            for stop_mode in ("fixed", "struct"):
                for tgt in (0.025, 0.03, 0.035):
                    variants.append(dict(gmin=gmin, gmax=gmax, entry_at=entry_at, stop_mode=stop_mode, tgt=tgt,
                                         name="%s %s-entry %s-stop +%.1f%%" % (gname, entry_at, "1.5%" if stop_mode == "fixed" else "struct", tgt * 100)))
    summary = []
    for v in variants:
        tr, both = run(data, industry, rets, nret, v)
        si = SW.stats([t for t in tr if t["signal_day"] < cut], v["name"] + " | IS")
        so = SW.stats([t for t in tr if t["signal_day"] >= cut], v["name"] + " | OOS")
        out.append(SW.fmt(si)); out.append(SW.fmt(so))
        summary.append((so.get("exp", -1e9), si.get("exp", -1e9), v["name"], so.get("n", 0), si.get("n", 0), both))
    out += ["", "## Random baseline (same exits, sizing and costs; 5 seeds; fixed 1.5 % stop, +3 % target, close entry)", "", SW.HEAD]
    for seed in range(5):
        v = dict(random=True, entry_at="close", stop_mode="fixed", tgt=0.03)
        tr, _ = run(data, industry, rets, nret, v, rng=random.Random(seed))
        out.append(SW.fmt(SW.stats([t for t in tr if t["signal_day"] >= cut], "random seed %d | OOS" % seed)))
    summary.sort(reverse=True)
    out += ["", "## Ranking by out-of-sample expectancy (Rs per trade)", "", "| variant | OOS exp | IS exp | OOS n | IS n | days both legs stopped |",
            "|---|---|---|---|---|---|"]
    for so_exp, si_exp, name, n_o, n_i, both in summary:
        out.append("| %s | %+.0f | %+.0f | %d | %d | %d |" % (name, so_exp, si_exp, n_o, n_i, both))
    out += ["", "Reading guide: a variant is usable only if BOTH IS and OOS expectancy are positive, the OOS confidence interval is mostly above zero, "
            "and it beats the random rows. Picking the best of 24 variants by OOS alone overfits; prefer variants positive in both periods."]
    text = "\n".join(out)
    print(text)
    if a.write:
        with open(a.write, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    return 0


def angel_snapshot(symbols):
    """Live OHLC + volume for up to 50 symbols per call from Angel One (read-only market data). -> {SYM: dict}"""
    rec = _load("../trader-flows/angel_recorder.py", "rec")
    env = rec.credentials()
    api, _ = rec.session(env)
    toks = rec.tokens_for(symbols)
    by_tok = {v: k for k, v in toks.items()}
    out = {}
    items = list(toks.values())
    for i in range(0, len(items), 50):
        r = api.getMarketData("FULL", {"NSE": items[i:i + 50]})
        for q in ((r or {}).get("data") or {}).get("fetched") or []:
            s = by_tok.get(str(q.get("symbolToken")))
            if s:
                out[s] = {"o": q.get("open"), "h": q.get("high"), "l": q.get("low"), "c": q.get("ltp"), "v": q.get("tradeVolume"),
                          "prev": q.get("close")}
    try:
        api.terminateSession(env["ANGEL_CLIENT_CODE"])
    except Exception:
        pass
    return out


def cmd_scan(a):
    industry = index_list(N200)
    syms = list(industry)
    data, missing = SW.load_all(a.cache_live, syms, fetch=True)
    nifty = data.pop("^NSEI", None)
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=5.5)
    src = "Yahoo daily (delayed)"
    if a.angel:
        snap = angel_snapshot(syms + ["NIFTY"] if False else syms)
        src = "Angel One live snapshot %s IST" % now.strftime("%H:%M")
        elapsed = max(0.1, min(1.0, ((now.hour * 60 + now.minute) - 555) / 375.0))      # share of the 9:15-15:30 session gone
        for s, q in snap.items():
            b = data.get(s)
            if not b or not q.get("c"):
                continue
            bar = {"d": now.date(), "o": q["o"], "h": q["h"], "l": q["l"], "c": q["c"], "v": (q["v"] or 0) / elapsed}
            if b[-1]["d"] == now.date():
                b[-1] = bar
            else:
                b.append(bar)
    for b in data.values():
        SW.enrich(b)
    if nifty:
        SW.enrich(nifty)
    rets = day_returns(data)
    day = max(rets)
    nifty_ret = (nifty[-1]["c"] / nifty[-2]["c"] - 1) if nifty and nifty[-1]["d"] == day else median(list(rets[day].values()))
    rows = []
    for s, b in data.items():
        t = len(b) - 1
        if b[t]["d"] != day:
            continue
        if is_signal(b, t, 0.015, 0.035) and sector_ok(s, day, rets, industry, nifty_ret):
            rows.append((b[t]["rvol"], s, t))
    rows.sort(reverse=True)
    picks, used = [], set()
    for _, s, t in rows:
        if industry[s] in used:
            continue
        picks.append((s, t)); used.add(industry[s])
        if len(picks) == MAX_LEGS:
            break
    print("Rotation scan %s | data: %s | NIFTY day %+.2f%% | %d of %d symbols | %d raw signals" % (
        day, src, 100 * nifty_ret, len(data), len(syms), len(rows)))
    if not picks:
        print("NO TRADE: no stock met every condition.")
        return 1
    for s, t in picks:
        x, p = data[s][t], data[s][t - 1]
        entry = SW.tick(x["c"] + TICK, up=True)
        stop = SW.tick(entry * 0.985)
        qty = leg_qty(entry, stop)
        tgt = SW.tick(entry * 1.03, up=True)
        c_s = COSTS.delivery_costs(qty, entry, stop, slippage_per_share=TICK)["total_with_slippage"]
        c_t = COSTS.delivery_costs(qty, entry, tgt, slippage_per_share=TICK)["total_with_slippage"]
        print("\nROTATION [LONG] %s (%s) | %s close/LTP %.2f, day %+.2f%%, RVOL %.1fx, closed at %.0f%% of range, above 3-day high %.2f" % (
            s, industry[s], x["d"], x["c"], 100 * (x["c"] / p["c"] - 1), x["rvol"], 100 * (x["c"] - x["l"]) / (x["h"] - x["l"]),
            max(q["h"] for q in data[s][t - 3:t])))
        print("  Buy range %.2f - %.2f | stop %.2f (-1.5%%) | book profit %.2f (+3%%) | time exit: close of day 2" % (entry - 2 * TICK, entry + 4 * TICK, stop, tgt))
        print("  Qty %d (Rs %s) | max loss incl. costs Rs %.0f | net at target Rs %.0f" % (qty, "{:,.0f}".format(qty * entry), qty * (entry - stop) + c_s,
                                                                                          qty * (tgt - entry) - c_t))
    print("\nDecision follows the backtest gate in docs/MOMENTUM_BACKTEST.md (BUY only if the variant passed; otherwise PAPER).")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="2-Stock Sector-Split Rotation (BTST momentum).")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("backtest"); p.set_defaults(fn=cmd_backtest)
    p.add_argument("--cache", default=SW.CACHE); p.add_argument("--offline", action="store_true"); p.add_argument("--write")
    p = sub.add_parser("scan"); p.set_defaults(fn=cmd_scan)
    p.add_argument("--cache-live", default="trader/cache/rotation-live"); p.add_argument("--angel", action="store_true")
    a = ap.parse_args(argv)
    if not getattr(a, "fn", None):
        ap.print_help(); return 1
    return a.fn(a)


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    sys.exit(main())
