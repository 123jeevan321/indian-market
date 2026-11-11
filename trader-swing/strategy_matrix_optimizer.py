#!/usr/bin/env python3
"""Multi-factor combinatorial backtest on NSE 15-minute bars (Angel One history), LONG ONLY, morning entries.

    python3 strategy_matrix_optimizer.py fetch [--years 5] [--index nifty100]   # Angel One FIFTEEN_MINUTE candles -> trader/cache/m15/
    python3 strategy_matrix_optimizer.py run [--write docs/MATRIX_BACKTEST.md]

DATA: Angel One SmartAPI historical candles (read-only), 15-minute bars 9:15-15:15, prices as Angel serves them (corporate-action adjusted).
Nifty 100 stocks (today's members: survivorship bias). Universe filter: 20-day average traded value >= Rs 50 crore, price >= Rs 100.

TRIGGERS (first occurrence; the trigger bar must END by 10:30; entry at that bar's close + 1 tick, i.e. no look-ahead):
  ORB15   a 15-minute close above the first 15-minute bar's high (9:15-9:30)
  ORB30   a close above the high of the first 30 minutes
  SWEEP   price trades below the previous day's low (PDL) and a bullish displacement bar (body >= 60 % of range) closes back above PDL
  FVG     a bullish fair value gap forms (low[i] > high[i-2], middle bar range >= 1.5 x yesterday's average 15m range) and a later bar
          dips into the gap and closes above it
FILTERS (evaluated on the trigger bar, using only bars up to it):
  RVOL    cumulative volume so far >= 2.5 x the 10-day average cumulative volume at the same time of day
  POC     close above the previous 5 sessions' volume point of control, and the day opened at or below it (a fresh break)
  FVGp    a bullish FVG already formed today          SWEEPp  the previous day's low was swept earlier today
STOPS (structural): ORB -> opening-range midpoint; SWEEP -> the day's low so far; FVG -> gap bottom. Risk must be 0.3 %-3 % of price.
TARGETS: +1.5 %, +2.0 %, +3.0 %. HOLDS: SAME-DAY (MIS, flat at 15:15, intraday costs) or 2-DAY (delivery, exit at the next day's 15:15
close, delivery costs, overnight gaps fill at the open). A bar touching both stop and target counts as the stop.
SIZE: loss at the stop + costs + 1 tick slippage each side <= Rs 1,500; leg <= Rs 1 lakh; max 2 legs at a time in different NSE industries.
BASELINE: random entry bar (9:30-10:30), 0.75 % stop, same targets/holds/sizing/costs.
SELECTION: combos are ranked on the IN-SAMPLE period only (first 60 % of dates, at least 60 trades); the OUT-OF-SAMPLE period then shows
whether the ranking held. With ~200 combinations, the in-sample winner is expected to look better than it is.
"""

import argparse
import csv
import datetime
import importlib.util
import io
import json
import math
import os
import random
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TICK = 0.05
CACHE = "trader/cache/m15"
RISK, LEG_CAP, MAX_LEGS = 1500.0, 100000.0, 2
LAST_ENTRY_SLOT = 4          # bar 4 = 10:15-10:30
FLAT_SLOT = 23               # bar 23 = 15:00-15:15 -> flat by 15:15
INDEX_URL = {"nifty50": "ind_nifty50list.csv", "niftynext50": "ind_niftynext50list.csv", "nifty100": None, "nifty200": "ind_nifty200list.csv"}
ARCH = "https://archives.nseindia.com/content/indices/"


def _load(rel, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


COSTS = _load("../trader-budget/costs.py", "costs")


def index_members(name):
    files = ["ind_nifty50list.csv", "ind_niftynext50list.csv"] if name == "nifty100" else [INDEX_URL[name]]
    out = {}
    for f in files:
        t = urllib.request.urlopen(urllib.request.Request(ARCH + f, headers={"User-Agent": "Mozilla/5.0"}), timeout=40).read().decode("utf-8-sig")
        for r in csv.DictReader(io.StringIO(t)):
            if r["Series"].strip() == "EQ":
                out[r["Symbol"].strip().upper()] = r["Industry"].strip()
    return out


# ---------------------------------------------------------------- fetch (Angel One, read-only)

def cmd_fetch(a):
    rec = _load("../trader-flows/angel_recorder.py", "rec")
    members = index_members(a.index)
    os.makedirs(a.cache, exist_ok=True)
    with open(os.path.join(a.cache, "industry.json"), "w", encoding="utf-8") as fh:
        json.dump(members, fh)
    toks = rec.tokens_for(list(members))
    env = rec.credentials()
    api, _ = rec.session(env)
    end = datetime.date.today()
    start = end - datetime.timedelta(days=int(365 * a.years))
    done = 0
    for s in sorted(toks):
        path = os.path.join(a.cache, s.replace("&", "_and_") + ".json")
        if os.path.exists(path):
            done += 1
            continue
        rows, d = [], start
        while d <= end:
            e = min(end, d + datetime.timedelta(days=190))
            for attempt in range(3):
                try:
                    r = api.getCandleData({"exchange": "NSE", "symboltoken": toks[s], "interval": "FIFTEEN_MINUTE",
                                           "fromdate": d.strftime("%Y-%m-%d 09:15"), "todate": e.strftime("%Y-%m-%d 15:30")})
                    break
                except Exception:
                    time.sleep(3)
                    r = None
            rows += (r or {}).get("data") or []
            time.sleep(0.7)
            d = e + datetime.timedelta(days=1)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(rows, fh)
        done += 1
        print("%3d/%d %-12s %6d bars" % (done, len(toks), s, len(rows)), flush=True)
    try:
        api.terminateSession(env["ANGEL_CLIENT_CODE"])
    except Exception:
        pass
    return 0


# ---------------------------------------------------------------- data prep

def load_days(path):
    """-> [(date, {slot: (o,h,l,c,v)})] for sessions with bars 0..23 present."""
    with open(path, encoding="utf-8") as fh:
        rows = json.load(fh)
    days = {}
    for ts, o, h, l, c, v in rows:
        d = datetime.date(int(ts[0:4]), int(ts[5:7]), int(ts[8:10]))
        hh, mm = int(ts[11:13]), int(ts[14:16])
        slot = ((hh * 60 + mm) - 555) // 15
        if 0 <= slot <= FLAT_SLOT:
            days.setdefault(d, {})[slot] = (o, h, l, c, v)
    return [(d, b) for d, b in sorted(days.items()) if all(k in b for k in range(FLAT_SLOT + 1))]


def poc(prev_days):
    vol = {}
    ref = prev_days[-1][1][FLAT_SLOT][3]
    size = max(TICK, ref * 0.001)
    for _, b in prev_days:
        for o, h, l, c, v in b.values():
            lo, hi = int(l / size), int(h / size)
            n = hi - lo + 1
            for k in range(lo, hi + 1):
                vol[k] = vol.get(k, 0.0) + v / float(n)
    return (max(vol, key=vol.get) + 0.5) * size if vol else None


def events_for(sym, days):
    """Per day: the first bar of each trigger with its stop and the filter flags at that bar. -> list of dict."""
    out = []
    for i in range(10, len(days)):
        d, b = days[i]
        pd_, pb = days[i - 1]
        pdh = max(x[1] for x in pb.values()); pdl = min(x[2] for x in pb.values())
        avgval = sum(sum(x[3] * x[4] for x in days[j][1].values()) for j in range(max(0, i - 20), i)) / min(20, i)
        if avgval < 50e7 or b[0][0] < 100:
            continue
        avg_rng = sum(x[1] - x[2] for x in pb.values()) / len(pb)
        cum_hist = []
        for j in range(i - 10, i):
            run, row = 0, []
            for k in range(LAST_ENTRY_SLOT + 1):
                run += days[j][1][k][4]; row.append(run)
            cum_hist.append(row)
        avg_cum = [sum(r[k] for r in cum_hist) / 10.0 for k in range(LAST_ENTRY_SLOT + 1)]
        p5 = poc(days[i - 5:i])
        open_px = b[0][0]
        orh15, orl15 = b[0][1], b[0][2]
        orh30, orl30 = max(b[0][1], b[1][1]), min(b[0][2], b[1][2])
        cum, low_so_far, swept, fvgs = 0, 1e18, False, []
        got = {}
        for k in range(LAST_ENTRY_SLOT + 1):
            o, h, l, c, v = b[k]
            cum += v
            low_so_far = min(low_so_far, l)
            if l < pdl:
                swept = True
            if k >= 2:
                o1, h1, l1, c1, _ = b[k - 1]
                if l > b[k - 2][1] and c1 > o1 and (h1 - l1) >= 1.5 * avg_rng:
                    fvgs.append((k, b[k - 2][1], l))            # (made at, bottom, top)
            flags = {"RVOL": avg_cum[k] > 0 and cum / avg_cum[k] >= 2.5, "POC": p5 is not None and c > p5 and open_px <= p5,
                     "FVGp": bool(fvgs), "SWEEPp": swept}
            def add(name, stop):
                if name not in got and stop is not None and 0.003 * c <= c - stop <= 0.03 * c:
                    got[name] = {"sym": sym, "day": d, "i": i, "k": k, "entry_raw": c, "stop_raw": stop, "flags": dict(flags), "trig": name}
            if k >= 1 and c > orh15:
                add("ORB15", (orh15 + orl15) / 2.0)
            if k >= 2 and c > orh30:
                add("ORB30", (orh30 + orl30) / 2.0)
            rng = h - l
            if swept and c > pdl and c > o and rng > 0 and (c - o) / rng >= 0.6:
                add("SWEEP", low_so_far)
            for made, bot, top in fvgs:
                if k > made and l <= top and c > top:
                    add("FVG", bot)
                    break
        out.extend(got.values())
    return out


def tickr(x, up=False):
    return (math.ceil(x / TICK - 1e-9) if up else math.floor(x / TICK + 1e-9)) * TICK


def size(entry, stop, mode):
    risk = entry - stop
    per = risk + (entry * 0.00222 if mode == "2day" else entry * 0.0006) + 2 * TICK
    q = int(min((RISK - (16 if mode == "2day" else 25)) // per, LEG_CAP // entry))
    while q > 0:
        c = (COSTS.delivery_costs(q, entry, stop, slippage_per_share=TICK) if mode == "2day"
             else COSTS.intraday_costs(q, entry, stop, "NSE", TICK))["total_with_slippage"]
        if q * risk + c <= RISK:
            break
        q -= 1
    return q


def simulate(days, ev, tgt, mode):
    i, k = ev["i"], ev["k"]
    entry = tickr(ev["entry_raw"] + TICK, up=True)
    stop = tickr(ev["stop_raw"] - TICK)
    q = size(entry, stop, mode)
    if q < 1:
        return None
    target = tickr(entry * (1 + tgt), up=True)
    path = [(i, s) for s in range(k + 1, FLAT_SLOT + 1)]
    if mode == "2day" and i + 1 < len(days):
        path += [(i + 1, s) for s in range(0, FLAT_SLOT + 1)]
    exit_px, why, exit_day = None, "time", days[path[-1][0]][0] if path else ev["day"]
    for j, s in path:
        o, h, l, c, v = days[j][1][s]
        if o <= stop:
            exit_px, why, exit_day = o - TICK, "stop", days[j][0]; break
        if o >= target:
            exit_px, why, exit_day = o, "target", days[j][0]; break
        if l <= stop:
            exit_px, why, exit_day = stop - TICK, "stop", days[j][0]; break
        if h >= target:
            exit_px, why, exit_day = target, "target", days[j][0]; break
    if exit_px is None:
        j, s = path[-1] if path else (i, FLAT_SLOT)
        exit_px = days[j][1][s][3] - TICK
    gross = q * (exit_px - entry)
    cost = (COSTS.delivery_costs(q, entry, exit_px) if mode == "2day" else COSTS.intraday_costs(q, entry, exit_px))["charges"]
    return {"entry_day": ev["day"], "exit_day": exit_day, "slot": k, "sym": ev["sym"], "gross": gross, "costs": cost,
            "net": gross - cost, "r": (gross - cost) / RISK, "why": why, "value": q * entry}


def portfolio(trades, industry):
    """Max 2 legs open, different industries; earlier trigger bar first."""
    out, open_legs = [], []
    for t in sorted(trades, key=lambda t: (t["entry_day"], t["slot"])):
        open_legs = [p for p in open_legs if p["exit_day"] >= t["entry_day"]]   # a leg closing today still blocks its slot today
        if len(open_legs) >= MAX_LEGS or any(industry.get(p["sym"]) == industry.get(t["sym"]) for p in open_legs):
            continue
        open_legs.append(t)
        out.append(t)
    return out


def stats(tr):
    n = len(tr)
    if not n:
        return {"n": 0}
    nets = [t["net"] for t in tr]
    w = [x for x in nets if x > 0]; l = [x for x in nets if x <= 0]
    cum = peak = dd = 0.0
    for t in sorted(tr, key=lambda t: (t["exit_day"], t["slot"])):
        cum += t["net"]; peak = max(peak, cum); dd = max(dd, peak - cum)
    rng = random.Random(5)
    boots = sorted(sum(rng.choice(nets) for _ in range(n)) / n for _ in range(800))
    return {"n": n, "win": 100.0 * len(w) / n, "exp": sum(nets) / n, "ci": (boots[20], boots[780]), "pf": sum(w) / -sum(l) if l and sum(l) < 0 else 99,
            "total": sum(nets), "dd": dd, "avg_win": sum(w) / len(w) if w else 0, "avg_loss": sum(l) / len(l) if l else 0,
            "costs": sum(t["costs"] for t in tr)}


def weekly(tr, first, last):
    wk = {}
    for t in tr:
        key = t["exit_day"].isocalendar()[:2]
        wk[key] = wk.get(key, 0.0) + t["net"]
    seq, d, seen = [], first, set()
    while d <= last:
        key = d.isocalendar()[:2]
        if key not in seen:
            seen.add(key); seq.append(wk.get(key, 0.0))
        d += datetime.timedelta(days=1)
    s = sorted(seq)
    pct = lambda p: s[min(len(s) - 1, int(p * len(s)))]
    return {"weeks": len(seq), "mean": sum(seq) / len(seq), "p10": pct(0.1), "p25": pct(0.25), "median": pct(0.5), "p75": pct(0.75),
            "p90": pct(0.9), "worst": s[0], "best": s[-1], "ge5k": 100.0 * sum(1 for x in seq if x >= 5000) / len(seq),
            "ge10k": 100.0 * sum(1 for x in seq if x >= 10000) / len(seq), "neg": 100.0 * sum(1 for x in seq if x < 0) / len(seq)}


def row(name, s):
    if not s.get("n"):
        return "| %s | 0 | | | | | |" % name
    return "| %s | %d | %.1f%% | %+.0f (%+.0f..%+.0f) | %.2f | %+.0f | %.0f | %.0f |" % (
        name, s["n"], s["win"], s["exp"], s["ci"][0], s["ci"][1], s["pf"], s["total"], s["dd"], s["costs"])


HEAD = "| combo | trades | win | expectancy Rs/trade (95% CI) | PF | total Rs | max DD Rs | costs Rs |\n|---|---|---|---|---|---|---|---|"


def cmd_run(a):
    with open(os.path.join(a.cache, "industry.json"), encoding="utf-8") as fh:
        industry = json.load(fh)
    data, events = {}, []
    for f in sorted(os.listdir(a.cache)):
        if not f.endswith(".json") or f == "industry.json":
            continue
        sym = f[:-5].replace("_and_", "&")
        days = load_days(os.path.join(a.cache, f))
        if len(days) < 200:
            continue
        data[sym] = days
        events.extend(events_for(sym, days))
    all_days = sorted({d for days in data.values() for d, _ in days})
    cut = all_days[int(len(all_days) * 0.6)]
    first, last = all_days[0], all_days[-1]
    trig_filters = {"ORB15": ["RVOL", "POC", "FVGp", "SWEEPp"], "ORB30": ["RVOL", "POC", "FVGp", "SWEEPp"],
                    "SWEEP": ["RVOL", "POC", "FVGp"], "FVG": ["RVOL", "POC", "SWEEPp"]}
    sims = {}
    for ev in events:
        for tgt in (0.015, 0.02, 0.03):
            for mode in ("sameday", "2day"):
                sims[(id(ev), tgt, mode)] = simulate(data[ev["sym"]], ev, tgt, mode)
    results = []
    for trig, fl in trig_filters.items():
        subsets = [()] + [(x,) for x in fl] + [(x, y) for i, x in enumerate(fl) for y in fl[i + 1:]]
        evs = [e for e in events if e["trig"] == trig]
        for sub in subsets:
            sel = [e for e in evs if all(e["flags"][f] for f in sub)]
            for tgt in (0.015, 0.02, 0.03):
                for mode in ("sameday", "2day"):
                    tr = [dict(sims[(id(e), tgt, mode)]) for e in sel if sims[(id(e), tgt, mode)]]
                    tr = portfolio(tr, industry)
                    name = "%s%s | +%.1f%% | %s" % (trig, "".join("+" + f for f in sub), tgt * 100, "same-day MIS" if mode == "sameday" else "2-day CNC")
                    si = stats([t for t in tr if t["entry_day"] < cut]); so = stats([t for t in tr if t["entry_day"] >= cut])
                    results.append((name, si, so, tr, mode))
    # random baseline
    rng = random.Random(1)
    base = {}
    for mode in ("sameday", "2day"):
        for tgt in (0.015, 0.02, 0.03):
            tr = []
            for sym, days in data.items():
                for i in range(10, len(days)):
                    if rng.random() < 0.02:
                        d, b = days[i]
                        k = rng.randint(1, LAST_ENTRY_SLOT)
                        c = b[k][3]
                        ev = {"sym": sym, "day": d, "i": i, "k": k, "entry_raw": c, "stop_raw": c * 0.9925}
                        s = simulate(days, ev, tgt, mode)
                        if s:
                            tr.append(s)
            tr = portfolio(tr, industry)
            base[(tgt, mode)] = (stats([t for t in tr if t["entry_day"] < cut]), stats([t for t in tr if t["entry_day"] >= cut]))
    ranked = sorted([r for r in results if r[1].get("n", 0) >= 60], key=lambda r: -r[1]["exp"])
    out = ["# Multi-factor matrix backtest (NSE 15-minute bars, Angel One history, long only, morning entries)", "",
           "Run %s. %d Nifty 100 stocks, %s to %s (%d sessions). IS = before %s, OOS = from %s. %d combinations. Max loss Rs 1,500 per leg incl. costs "
           "and slippage; leg <= Rs 1 lakh; max 2 legs, different industries. Same-day = MIS costs; 2-day = delivery costs." % (
               datetime.date.today(), len(data), first, last, len(all_days), cut, cut, len(results)), "",
           "## Top 10 by IN-SAMPLE expectancy (min 60 IS trades), with their OUT-OF-SAMPLE result", "", HEAD]
    for name, si, so, tr, mode in ranked[:10]:
        out.append(row(name + " **IS**", si)); out.append(row(name + " OOS", so))
    both = sorted([r for r in results if r[1].get("n", 0) >= 40 and r[2].get("n", 0) >= 40 and r[1]["exp"] > 0 and r[2]["exp"] > 0],
                  key=lambda r: -min(r[1]["exp"], r[2]["exp"]))
    out += ["", "## Combos positive in BOTH periods (min 40 trades each), ranked by the weaker period", "", HEAD]
    for name, si, so, tr, mode in both[:15]:
        out.append(row(name + " IS", si)); out.append(row(name + " OOS", so))
    if not both:
        out.append("| none | | | | | | | |")
    win55 = [r for r in results if r[1].get("n", 0) >= 40 and r[2].get("n", 0) >= 40 and r[1]["win"] > 55 and r[2]["win"] > 55]
    out += ["", "Combos with win rate > 55 %% in both periods: %d%s" % (len(win55), (" (" + "; ".join(r[0] for r in win55[:10]) + ")") if win55 else "")]
    out += ["", "## Same-day vs 2-day (average over all combos with >= 40 trades in a period)", "", "| hold | period | combos | mean expectancy Rs | share of combos > 0 |", "|---|---|---|---|---|"]
    for mode in ("sameday", "2day"):
        for idx, per in ((1, "IS"), (2, "OOS")):
            xs = [r[idx]["exp"] for r in results if r[4] == mode and r[idx].get("n", 0) >= 40]
            if xs:
                out.append("| %s | %s | %d | %+.0f | %.0f%% |" % (mode, per, len(xs), sum(xs) / len(xs), 100.0 * sum(1 for x in xs if x > 0) / len(xs)))
    out += ["", "## Random baseline (random entry bar 9:30-10:30, 0.75 % stop, same exits/sizing/costs)", "", HEAD]
    for (tgt, mode), (si, so) in sorted(base.items()):
        out.append(row("random +%.1f%% %s IS" % (tgt * 100, mode), si)); out.append(row("random +%.1f%% %s OOS" % (tgt * 100, mode), so))
    pick = (both[0] if both else ranked[0]) if ranked or both else None
    if pick:
        w_all = weekly(pick[3], first, last)
        w_oos = weekly([t for t in pick[3] if t["entry_day"] >= cut], cut, last)
        out += ["", "## Weekly net Rs distribution for: %s" % pick[0], "", "| period | weeks | mean | p10 | p25 | median | p75 | p90 | worst | best | weeks >= 5k | >= 10k | < 0 |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for lab, w in (("all", w_all), ("OOS", w_oos)):
            out.append("| %s | %d | %+.0f | %+.0f | %+.0f | %+.0f | %+.0f | %+.0f | %+.0f | %+.0f | %.0f%% | %.0f%% | %.0f%% |" % (
                lab, w["weeks"], w["mean"], w["p10"], w["p25"], w["median"], w["p75"], w["p90"], w["worst"], w["best"], w["ge5k"], w["ge10k"], w["neg"]))
    out += ["", "Limits: today's index members (survivorship); 15-minute bars hide the order of moves inside a bar (stop assumed first); entry at the "
            "trigger bar's close + 1 tick; no news filter; multiple testing across %d combos inflates the best in-sample numbers." % len(results)]
    text = "\n".join(out)
    print(text)
    if a.write:
        with open(a.write, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Multi-factor matrix backtest on Angel One 15-minute history.")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("fetch"); p.set_defaults(fn=cmd_fetch)
    p.add_argument("--cache", default=CACHE); p.add_argument("--years", type=float, default=5); p.add_argument("--index", default="nifty100")
    p = sub.add_parser("run"); p.set_defaults(fn=cmd_run)
    p.add_argument("--cache", default=CACHE); p.add_argument("--write")
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
