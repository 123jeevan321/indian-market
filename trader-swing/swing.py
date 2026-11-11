#!/usr/bin/env python3
"""Swing module (1-5 trading days, NSE cash, delivery/CNC, LONG ONLY): setups, backtest, scanner, sizing. Stdlib only.

    python3 swing.py fetch                      # 5 years of daily bars for the liquid NSE universe -> trader/cache/swing/
    python3 swing.py backtest --write docs/SWING_BACKTEST.md
    python3 swing.py scan                       # today's candidates from the last COMPLETED daily bar
    python3 swing.py size --entry 1356 --stop 1331 [--risk 1500] [--capital 100000]

Why long only: an Indian cash-market short cannot be held overnight (no delivery short selling; shorts beyond a day need F&O or
SLB, which this project excludes). Bearish 1-5 day swings are therefore out of scope here.

SETUPS (all decided on a COMPLETED daily bar t; entry at the OPEN of t+1; no look-ahead):
  squeeze   compression -> expansion: the 10 days before t span <= 2.5 x ATR14, then bar t closes above that 10-day high,
            in the top 30 % of its range, on relative volume >= 1.5 (volume / 20-day average). Trend: close > EMA50 > EMA200.
  sweep     liquidity sweep and reclaim: bar t trades below the prior 20-day low, closes back above it in the top 40 % of its
            range, relative volume >= 1.2, close > EMA200.
  choch     change of character: the last two confirmed swing highs (2-bar fractals) are falling (lower highs), and bar t closes
            above the latest swing high on relative volume >= 1.5.
  pullback  EMA trend continuation: EMA20 > EMA50 > EMA200, a low touched EMA20 within the last 3 bars, bar t closes above the
            prior bar's high and above EMA20.
  weekhigh  close above the previous completed week's high (first such close this week), relative volume >= 1.5, close > EMA50.
  fvg       bullish fair value gap: a displacement bar (range >= 1.5 x ATR) leaves low[d+1] > high[d-1]; within 5 bars price
            trades back into the gap and bar t closes above the gap top.
  random    BASELINE: random long entries (about 1 % of eligible bars) with a 1.5 x ATR stop and the same exits.

STOP: the setup's structural level (signal-bar low; sweep low; latest swing low; 3-bar low; gap bottom) minus 0.1 x ATR. If that is
closer than 1 x ATR the stop is set at 1 x ATR (noise guard); if it is wider than 3 x ATR the trade is skipped.
EXITS: T1 = 1.5R (half), then the stop moves to the entry; T2 = 3R (rest); otherwise exit at the close of day 5. A bar that opens
beyond a level fills at its open (gaps hurt); a bar touching both the stop and a target is assumed to hit the STOP first.
SIZE: qty = floor(risk_inr / (entry - stop)), capped by available cash. COSTS: Zerodha delivery (costs.delivery_costs) + 1 tick
slippage per side. UNIVERSE: today's Nifty 500 members with a 20-day average traded value >= Rs 25 crore and price >= Rs 100 at the
signal date (SURVIVORSHIP BIAS: stocks that left the index are missing). REGIME at signal time from NIFTY: bull = close > EMA200
and EMA50 rising over 20 days; bear = close < EMA200 and EMA50 falling; otherwise sideways.
"""

import argparse
import datetime
import importlib.util
import json
import math
import os
import random
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (compatible; india-equity-intraday-skill/1.0)"
CACHE = "trader/cache/swing"
TICK = 0.05
SETUPS = ("squeeze", "sweep", "choch", "pullback", "weekhigh", "fvg")


def _load(rel, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, "..", rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


COSTS = _load("trader-budget/costs.py", "costs")


# ---------------------------------------------------------------- data

def yahoo_daily(sym, rng="5y"):
    ys = sym if sym.startswith("^") else sym + ".NS"
    ys = ys.replace("&", "%26").replace("^", "%5E")
    for host in ("query2", "query1"):
        url = "https://%s.finance.yahoo.com/v8/finance/chart/%s?range=%s&interval=1d" % (host, ys, rng)
        for attempt in (0, 1):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40) as r:
                    return json.loads(r.read().decode())
            except urllib.error.HTTPError as e:
                e.close()
                if e.code == 429 and attempt == 0:
                    time.sleep(5)
                    continue
                break
            except (urllib.error.URLError, OSError, ValueError):
                break
    return None


def bars_from(doc):
    """Yahoo daily chart -> [{d, o, h, l, c, v}] (completed and current bars; the caller decides what is complete)."""
    try:
        res = doc["chart"]["result"][0]
        q = res["indicators"]["quote"][0]
    except (KeyError, IndexError, TypeError):
        return []
    out = []
    for i, ts in enumerate(res.get("timestamp") or []):
        o, h, l, c, v = (q[k][i] for k in ("open", "high", "low", "close", "volume"))
        if None in (o, h, l, c) or h <= 0:
            continue
        d = (datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=ts + 19800)).date()
        out.append({"d": d, "o": o, "h": h, "l": l, "c": c, "v": v or 0})
    return out


def universe(path=None):
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return [ln.split("|")[0].strip().upper() for ln in fh if ln.strip() and not ln.startswith("#")]
    import csv, io
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    text = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40).read().decode("utf-8-sig")
    return sorted(r["Symbol"].strip().upper() for r in csv.DictReader(io.StringIO(text)) if r["Series"].strip() == "EQ")


def load_all(cache, syms, fetch=True, pause=0.25):
    os.makedirs(cache, exist_ok=True)
    data, missing = {}, []
    for s in list(syms) + ["^NSEI"]:
        p = os.path.join(cache, s.replace("&", "_and_").replace("^", "IDX_") + ".json")
        doc = None
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                doc = json.load(fh)
        elif fetch:
            time.sleep(pause)
            doc = yahoo_daily(s)
            if doc:
                with open(p, "w", encoding="utf-8") as fh:
                    json.dump(doc, fh)
        b = bars_from(doc) if doc else []
        if len(b) >= 260:
            data[s] = b
        else:
            missing.append(s)
    return data, missing


# ---------------------------------------------------------------- indicators

def ema(vals, n):
    out, k, e = [], 2.0 / (n + 1), None
    for v in vals:
        e = v if e is None else v * k + e * (1 - k)
        out.append(e)
    return out


def enrich(b):
    c = [x["c"] for x in b]
    e20, e50, e200 = ema(c, 20), ema(c, 50), ema(c, 200)
    tr, atr = [], []
    for i, x in enumerate(b):
        t = x["h"] - x["l"] if i == 0 else max(x["h"] - x["l"], abs(x["h"] - b[i - 1]["c"]), abs(x["l"] - b[i - 1]["c"]))
        tr.append(t)
        atr.append(sum(tr[-14:]) / len(tr[-14:]))
    for i, x in enumerate(b):
        x["e20"], x["e50"], x["e200"], x["atr"] = e20[i], e50[i], e200[i], atr[i]
        lo = max(0, i - 20)
        prev = b[lo:i]
        x["avgv"] = sum(p["v"] for p in prev) / len(prev) if prev else 0
        x["avgval"] = sum(p["v"] * p["c"] for p in prev) / len(prev) if prev else 0
        x["rvol"] = x["v"] / x["avgv"] if x["avgv"] else 0
    # confirmed 2-bar fractals: known only 2 bars later
    for i in range(len(b)):
        b[i]["sh_known"] = b[i]["sl_known"] = None
    for i in range(2, len(b) - 2):
        if b[i]["h"] > max(b[i - 1]["h"], b[i - 2]["h"], b[i + 1]["h"], b[i + 2]["h"]):
            b[i + 2]["sh_known"] = (i, b[i]["h"])
        if b[i]["l"] < min(b[i - 1]["l"], b[i - 2]["l"], b[i + 1]["l"], b[i + 2]["l"]):
            b[i + 2]["sl_known"] = (i, b[i]["l"])
    return b


def regime_map(nifty):
    out = {}
    for i, x in enumerate(nifty):
        if i < 220:
            continue
        rising = x["e50"] > nifty[i - 20]["e50"]
        out[x["d"]] = "bull" if (x["c"] > x["e200"] and rising) else "bear" if (x["c"] < x["e200"] and not rising) else "sideways"
    return out


# ---------------------------------------------------------------- setups (bar t is complete)

def pos_in_range(x):
    rng = x["h"] - x["l"]
    return (x["c"] - x["l"]) / rng if rng > 0 else 0.5


def signal(b, t, setup, state):
    """-> structural stop level or None. `state` carries per-symbol memory (swing highs, week, fvgs)."""
    x = b[t]
    if setup == "squeeze":
        base = b[t - 10:t]
        hi, lo = max(p["h"] for p in base), min(p["l"] for p in base)
        if (hi - lo) <= 2.5 * b[t - 1]["atr"] and x["c"] > hi and pos_in_range(x) >= 0.7 and x["rvol"] >= 1.5 \
                and x["c"] > x["e50"] > x["e200"]:
            return x["l"]
    elif setup == "sweep":
        lo20 = min(p["l"] for p in b[t - 20:t])
        if x["l"] < lo20 and x["c"] > lo20 and pos_in_range(x) >= 0.6 and x["rvol"] >= 1.2 and x["c"] > x["e200"]:
            return x["l"]
    elif setup == "choch":
        sh = state["swing_highs"]
        if len(sh) >= 2 and sh[-1][1] < sh[-2][1] and x["c"] > sh[-1][1] and b[t - 1]["c"] <= sh[-1][1] and x["rvol"] >= 1.5:
            lows = state["swing_lows"]
            return lows[-1][1] if lows else x["l"]
    elif setup == "pullback":
        if x["e20"] > x["e50"] > x["e200"] and any(b[k]["l"] <= b[k]["e20"] for k in range(t - 2, t + 1)) \
                and x["c"] > b[t - 1]["h"] and x["c"] > x["e20"]:
            return min(b[k]["l"] for k in range(t - 2, t + 1))
    elif setup == "weekhigh":
        wk = x["d"].isocalendar()[:2]
        prev = [p for p in b[max(0, t - 12):t] if p["d"].isocalendar()[:2] != wk]
        if prev:
            pw = prev[-1]["d"].isocalendar()[:2]
            pwh = max(p["h"] for p in prev if p["d"].isocalendar()[:2] == pw)
            this_week = [p for p in b[max(0, t - 6):t] if p["d"].isocalendar()[:2] == wk]
            first = all(p["c"] <= pwh for p in this_week)
            if x["c"] > pwh and first and x["rvol"] >= 1.5 and x["c"] > x["e50"]:
                return x["l"]
    elif setup == "fvg":
        for g in list(state["fvgs"]):
            if t - g["made"] > 5:
                state["fvgs"].remove(g)
                continue
            if t == g["made"]:
                continue
            if x["l"] <= g["top"] and x["c"] > g["top"] and x["l"] > g["bottom"] - x["atr"]:
                state["fvgs"].remove(g)
                return g["bottom"]
    return None


def update_state(b, t, state):
    x = b[t]
    if x["sh_known"]:
        state["swing_highs"].append(x["sh_known"])
    if x["sl_known"]:
        state["swing_lows"].append(x["sl_known"])
    if t >= 2:
        d = t - 1
        if b[d]["h"] - b[d]["l"] >= 1.5 * b[d]["atr"] and b[d]["c"] > b[d]["o"] and b[t]["l"] > b[d - 1]["h"]:
            state["fvgs"].append({"made": t, "top": b[t]["l"], "bottom": b[d - 1]["h"]})


# ---------------------------------------------------------------- trade simulation

def tick(x, up=False):
    return (math.ceil(x / TICK - 1e-9) if up else math.floor(x / TICK + 1e-9)) * TICK


def capped_qty(entry, risk, risk_inr, cash):
    """Shares so that (loss at the stop + delivery costs + slippage) stays within risk_inr, and the cost fits the cash."""
    per_share = risk + entry * 0.00222 + 2 * TICK          # STT 0.2 % round trip, stamp, exchange, GST, slippage
    return int(max(0, min((risk_inr - 16) // per_share, cash // entry)))


def make_trade(b, t, struct_stop, risk_inr, cash, hold=5, mode="ladder"):
    if t + 1 >= len(b):
        return None
    atr = b[t]["atr"]
    entry = tick(b[t + 1]["o"] + TICK, up=True)
    stop = tick(struct_stop - 0.1 * atr)
    if entry - stop < 1.0 * atr:
        stop = tick(entry - 1.0 * atr)
    risk = entry - stop
    if risk <= 0 or risk > 3.0 * atr:
        return None
    qty = capped_qty(entry, risk, risk_inr, cash)
    if qty < 1:
        return None
    t1, t2 = tick(entry + 1.5 * risk, up=True), tick(entry + 3.0 * risk, up=True)
    legs, rem, cur, took = [], qty, stop, False
    last = min(t + hold, len(b) - 1)
    exit_day = last
    for k in range(t + 1, last + 1):
        x = b[k]
        o = x["o"] if k > t + 1 else entry
        if o <= cur:                                   # gapped through the stop
            legs.append((rem, o - TICK, k)); rem = 0; exit_day = k; break
        if x["l"] <= cur:
            legs.append((rem, cur - TICK, k)); rem = 0; exit_day = k; break
        if mode == "single":
            if x["h"] >= t2:
                legs.append((rem, max(o, t2), k)); rem = 0; exit_day = k; break
            continue
        if not took and x["h"] >= t1:
            q1 = rem // 2 if rem > 1 else rem
            legs.append((q1, max(o, t1), k)); rem -= q1; took = True; cur = entry
        if rem and took and x["h"] >= t2:
            legs.append((rem, max(o, t2), k)); rem = 0; exit_day = k; break
    if rem:
        legs.append((rem, b[last]["c"] - TICK, last))
    gross = sum(q * (px - entry) for q, px, _ in legs)
    days = sorted({k for _, _, k in legs})
    cost = 0.0
    for i, (q, px, k) in enumerate(legs):
        c = COSTS.delivery_costs(q, entry, px, sells=1)
        cost += c["charges"]
    return {"entry_day": b[t + 1]["d"], "exit_day": b[exit_day]["d"], "entry": entry, "stop": stop, "qty": qty, "risk": risk,
            "gross": gross, "costs": cost, "net": gross - cost, "r": (gross - cost) / (qty * risk), "value": qty * entry,
            "days_held": len([1 for k in range(t + 1, max(days) + 1)]), "hit_t1": took or any(px >= t1 for _, px, _ in legs)}


# ---------------------------------------------------------------- backtest

def signals_for(data, setup, seed=7):
    """All signals for a setup -> list of (signal_date, symbol, index, struct_stop, rvol)."""
    rng = random.Random(seed)
    out = []
    for s, b in data.items():
        if s.startswith("^"):
            continue
        state = {"swing_highs": [], "swing_lows": [], "fvgs": []}
        for t in range(1, len(b)):
            if t >= 2:
                update_state(b, t, state)
            if t < 210 or t + 1 >= len(b):
                continue
            x = b[t]
            if x["avgval"] < 25e7 or x["c"] < 100:
                continue
            if setup == "random":
                if rng.random() < 0.01:
                    out.append((x["d"], s, t, x["c"] - 1.5 * x["atr"] + 0.1 * x["atr"], 0))
                continue
            st = signal(b, t, setup, state)
            if st is not None:
                out.append((x["d"], s, t, st, x["rvol"]))
    return out


def portfolio(data, sigs, capital, risk_inr, max_pos, mode="ladder"):
    """Chronological portfolio: highest relative volume first; at most max_pos open; cash-limited; one position per stock."""
    by_day = {}
    for sig in sigs:
        by_day.setdefault(sig[0], []).append(sig)
    open_pos, trades = [], []
    cash = capital
    for d in sorted(by_day):
        still = []
        for p in open_pos:
            if p["exit_day"] < d:
                cash += p["value"] + p["net"]
            else:
                still.append(p)
        open_pos = still
        for sig in sorted(by_day[d], key=lambda z: -z[4]):
            if len(open_pos) >= max_pos or any(p["symbol"] == sig[1] for p in open_pos):
                continue
            tr = make_trade(data[sig[1]], sig[2], sig[3], risk_inr, cash, mode=mode)
            if not tr:
                continue
            tr["symbol"], tr["signal_day"] = sig[1], d
            cash -= tr["value"]
            open_pos.append(tr)
            trades.append(tr)
    return trades


def stats(trades, label):
    n = len(trades)
    if not n:
        return {"label": label, "n": 0}
    nets = [t["net"] for t in trades]
    w = [x for x in nets if x > 0]
    l = [x for x in nets if x <= 0]
    cum = peak = dd = 0.0
    streak = worst = 0
    for t in sorted(trades, key=lambda t: t["exit_day"]):
        cum += t["net"]; peak = max(peak, cum); dd = max(dd, peak - cum)
        streak = streak + 1 if t["net"] <= 0 else 0
        worst = max(worst, streak)
    weeks = {}
    for t in trades:
        k = t["exit_day"].isocalendar()[:2]
        weeks[k] = weeks.get(k, 0.0) + t["net"]
    first, last = min(t["entry_day"] for t in trades), max(t["exit_day"] for t in trades)
    all_weeks, d = [], first
    seen = set()
    while d <= last:
        k = d.isocalendar()[:2]
        if k not in seen:
            seen.add(k); all_weeks.append(weeks.get(k, 0.0))
        d += datetime.timedelta(days=1)
    mw = sum(all_weeks) / len(all_weeks)
    sd = (sum((x - mw) ** 2 for x in all_weeks) / max(1, len(all_weeks) - 1)) ** 0.5
    rng = random.Random(3)
    boots = sorted(sum(rng.choice(nets) for _ in range(n)) / n for _ in range(1000))
    return {"label": label, "n": n, "win": 100.0 * len(w) / n, "avg_win": sum(w) / len(w) if w else 0, "avg_loss": sum(l) / len(l) if l else 0,
            "exp": sum(nets) / n, "ci": (boots[25], boots[975]), "avg_r": sum(t["r"] for t in trades) / n,
            "pf": (sum(w) / -sum(l)) if l and sum(l) < 0 else float("inf"), "total": sum(nets), "dd": dd, "streak": worst,
            "costs": sum(t["costs"] for t in trades), "weeks": len(all_weeks), "week_mean": mw,
            "sharpe": (mw / sd * 52 ** 0.5) if sd else 0.0, "w5k": 100.0 * sum(1 for x in all_weeks if x >= 5000) / len(all_weeks),
            "w10k": 100.0 * sum(1 for x in all_weeks if x >= 10000) / len(all_weeks),
            "wneg": 100.0 * sum(1 for x in all_weeks if x < 0) / len(all_weeks), "hold": sum(t["days_held"] for t in trades) / n}


def fmt(s):
    if not s.get("n"):
        return "| %s | 0 | | | | | | | | | | |" % s["label"]
    return ("| %s | %d | %.1f%% | %.0f / %.0f | %+.0f (%+.0f..%+.0f) | %+.2f | %s | %.0f | %.0f | %d | %+.0f | %.2f | %.0f%% / %.0f%% / %.0f%% |" % (
        s["label"], s["n"], s["win"], s["avg_win"], s["avg_loss"], s["exp"], s["ci"][0], s["ci"][1], s["avg_r"],
        ("%.2f" % s["pf"]) if s["pf"] != float("inf") else "inf", s["total"], s["dd"], s["streak"], s["week_mean"], s["sharpe"],
        s["w5k"], s["w10k"], s["wneg"]))


HEAD = ("| setup | trades | win | avg win / loss Rs | expectancy Rs (95% CI) | avg R | PF | total Rs | max DD Rs | worst losing streak | "
        "avg week Rs | Sharpe (weekly) | weeks >=5k / >=10k / <0 |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|")


def cmd_backtest(a):
    syms = universe(a.universe)
    data, missing = load_all(a.cache, syms, fetch=not a.offline)
    nifty = data.pop("^NSEI", None)
    if not nifty:
        raise SystemExit("no NIFTY data")
    for b in data.values():
        enrich(b)
    enrich(nifty)
    reg = regime_map(nifty)
    days = sorted({x["d"] for b in data.values() for x in b})
    cut = days[int(len(days) * 0.6)]
    out = ["# Swing backtest (NSE, daily bars, long only, 1-5 days)", "",
           "Run %s. Data: Yahoo daily bars %s to %s for %d of %d Nifty 500 symbols (missing or short history: %d). Liquidity filter at signal time: "
           "20-day average traded value >= Rs 25 crore, price >= Rs 100. In-sample (IS) = before %s, out-of-sample (OOS) = from %s. Costs: Zerodha delivery "
           "(STT 0.1%% both sides, stamp 0.015%% buy, exchange, SEBI, GST, DP Rs 15.34 per sell) + 1 tick slippage each side." % (
               datetime.date.today(), days[0], days[-1], len(data), len(syms), len(missing), cut, cut), ""]
    scen = [("A", 100000, 1500), ("B", 200000, 2000)]
    results = {}
    for name, cap, risk in scen:
        out += ["## Scenario %s: capital Rs %s, risk Rs %s per trade, max %d open positions" % (name, "{:,}".format(cap), risk, a.max_pos), "", HEAD]
        for setup in SETUPS + ("random",):
            sigs = signals_for(data, setup)
            trades = portfolio(data, sigs, cap, risk, a.max_pos)
            results[(name, setup)] = trades
            out.append(fmt(stats([t for t in trades if t["signal_day"] < cut], "%s IS" % setup)))
            out.append(fmt(stats([t for t in trades if t["signal_day"] >= cut], "%s OOS" % setup)))
            out.append(fmt(stats(trades, "**%s all**" % setup)))
        out.append("")
    out += ["## Scenario A by market regime (NIFTY at the signal date: known in advance, no look-ahead)", "", HEAD]
    for setup in SETUPS + ("random",):
        for r in ("bull", "sideways", "bear"):
            out.append(fmt(stats([t for t in results[("A", setup)] if reg.get(t["signal_day"]) == r], "%s / %s" % (setup, r))))
    out += ["", "## Exit variant check (Scenario A, single 3R target instead of the half-at-1.5R ladder)", "", HEAD]
    for setup in SETUPS:
        out.append(fmt(stats(portfolio(data, signals_for(data, setup), 100000, 1500, a.max_pos, mode="single"), setup + " single-3R")))
    out += ["", "Limits: survivorship bias (today's index members); Yahoo daily bars (split-adjusted, not dividend-adjusted); a bar touching stop and "
            "target counts as the stop; signals are ranked by relative volume when more appear than open slots; no news/results filter; the CI "
            "assumes independent trades. FAILED/UNTESTED concepts are listed in the strategy document."]
    text = "\n".join(out)
    print(text)
    if a.write:
        os.makedirs(os.path.dirname(a.write) or ".", exist_ok=True)
        with open(a.write, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    return 0


def plan(b, t, struct_stop, risk_inr, capital):
    """A live plan from the last completed bar: entry = above the signal bar's high (a stop-limit buy for the next session)."""
    x = b[t]
    atr = x["atr"]
    entry = tick(x["h"] + TICK, up=True)
    stop = tick(struct_stop - 0.1 * atr)
    if entry - stop < atr:
        stop = tick(entry - atr)
    risk = entry - stop
    if risk > 3 * atr:
        return None
    qty = capped_qty(entry, risk, risk_inr, capital)
    if qty < 1:
        return None
    t1, t2, t3 = (tick(entry + m * risk, up=True) for m in (1.5, 3.0, 4.5))
    c_stop = COSTS.delivery_costs(qty, entry, stop, slippage_per_share=TICK)["total_with_slippage"]
    c_t1 = COSTS.delivery_costs(qty, entry, t1, slippage_per_share=TICK)["total_with_slippage"]
    return {"entry": entry, "stop": stop, "risk_ps": risk, "qty": qty, "value": qty * entry, "t1": t1, "t2": t2, "t3": t3,
            "max_loss": qty * risk + c_stop, "net_t1": qty * (t1 - entry) - c_t1, "move_t1_pct": 100 * (t1 / entry - 1),
            "move_t2_pct": 100 * (t2 / entry - 1)}


def cmd_scan(a):
    syms = universe(a.universe)
    if a.symbols:
        syms = [s.strip().upper() for s in a.symbols.split(",")]
    data, missing = load_all(a.cache_live, syms, fetch=True)
    nifty = data.pop("^NSEI", None)
    for b in list(data.values()) + ([nifty] if nifty else []):
        enrich(b)
    reg = regime_map(nifty) if nifty else {}
    now_ist = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=5.5)
    rows = []
    for s, b in data.items():
        t = len(b) - 1
        if b[t]["d"] == now_ist.date() and now_ist.time() < datetime.time(15, 35):
            t -= 1                                           # today's bar is not complete yet
        state = {"swing_highs": [], "swing_lows": [], "fvgs": []}
        for k in range(2, t + 1):
            update_state(b, k, state)
            if k == t:
                break
        x = b[t]
        if x["avgval"] < 25e7 or x["c"] < 100:
            continue
        for setup in (a.setups.split(",") if a.setups else SETUPS):
            st = signal(b, t, setup, state)
            if st is None:
                continue
            p = plan(b, t, st, a.risk, a.capital)
            if p:
                ext = 100 * (x["c"] / b[t - 5]["c"] - 1)
                rows.append(dict(p, symbol=s, setup=setup, close=x["c"], date=x["d"].isoformat(), rvol=x["rvol"], ext5=ext,
                                 regime=reg.get(nifty[-1]["d"] if nifty else None)))
    rows.sort(key=lambda r: (r["ext5"] > 6, -r["rvol"]))
    nreg = reg.get(nifty[-2]["d"]) if nifty else None
    print("Swing scan (long only) from the last COMPLETED daily bar; NIFTY regime: %s. Data: Yahoo daily (unofficial). %d symbols, %d missing." % (
        nreg, len(data), len(missing)))
    if not rows:
        print("NO TRADE: no setup fired on the last completed bar.")
        return 1
    for r in rows[:a.top]:
        print("%-11s %-8s close %9.2f (%s) rvol %.1fx, 5-day move %+.1f%% | BUY STOP above %.2f, stop %.2f, T1 %.2f (+%.1f%%), T2 %.2f (+%.1f%%), "
              "T3 %.2f | qty %d (Rs %s) | max loss Rs %.0f incl. costs | net at T1 Rs %.0f" % (
                  r["symbol"], r["setup"], r["close"], r["date"], r["rvol"], r["ext5"], r["entry"], r["stop"], r["t1"], r["move_t1_pct"],
                  r["t2"], r["move_t2_pct"], r["t3"], r["qty"], "{:,.0f}".format(r["value"]), r["max_loss"], r["net_t1"]))
    print("Candidates only: check news/results dates, sector and the setup's backtest row before any order. Stocks up more than 6%% in 5 days are listed last (extended).")
    return 0


def cmd_size(a):
    risk = a.entry - a.stop
    if risk <= 0:
        raise SystemExit("long only: the stop must be below the entry")
    qty = capped_qty(a.entry, risk, a.risk, a.capital)
    c = COSTS.delivery_costs(qty, a.entry, a.stop, slippage_per_share=TICK)
    print("qty %d (Rs %s) | loss at stop Rs %.0f + costs Rs %.0f = Rs %.0f (limit Rs %.0f) | T1 1.5R %.2f, T2 3R %.2f" % (
        qty, "{:,.0f}".format(qty * a.entry), qty * risk, c["total_with_slippage"], qty * risk + c["total_with_slippage"], a.risk,
        a.entry + 1.5 * risk, a.entry + 3 * risk))
    if qty * risk + c["total_with_slippage"] > a.risk:
        q2 = qty
        while q2 > 0 and q2 * risk + COSTS.delivery_costs(q2, a.entry, a.stop, slippage_per_share=TICK)["total_with_slippage"] > a.risk:
            q2 -= 1
        print("With costs the cap needs %d shares." % q2)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Swing module (NSE, 1-5 days, long only).")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("backtest"); p.set_defaults(fn=cmd_backtest)
    p.add_argument("--cache", default=CACHE); p.add_argument("--universe"); p.add_argument("--offline", action="store_true")
    p.add_argument("--max-pos", type=int, default=3); p.add_argument("--write")
    p = sub.add_parser("scan"); p.set_defaults(fn=cmd_scan)
    p.add_argument("--cache-live", default="trader/cache/swing-live"); p.add_argument("--universe"); p.add_argument("--symbols")
    p.add_argument("--setups"); p.add_argument("--risk", type=float, default=1500); p.add_argument("--capital", type=float, default=100000)
    p.add_argument("--top", type=int, default=10)
    p = sub.add_parser("size"); p.set_defaults(fn=cmd_size)
    p.add_argument("--entry", type=float, required=True); p.add_argument("--stop", type=float, required=True)
    p.add_argument("--risk", type=float, default=1500); p.add_argument("--capital", type=float, default=100000)
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
