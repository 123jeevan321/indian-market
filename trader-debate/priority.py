#!/usr/bin/env python3
"""TOP-10 STRATEGY PRIORITY SCANNER (user directive 2026-11-12). Read-only; paper analysis; the user places every order.

    python trader-debate/priority.py                      # live: latest data, strict priority order, stop at the first level with setups
    python trader-debate/priority.py --date 2026-11-12    # replay a past session (decision at 09:30 for intraday levels)
    python trader-debate/priority.py --all                # evaluate all 10 levels (only when the user asks for a complete scan)

Each strategy uses EXACTLY the definition that was tested (sources in brackets). Win rates are from those untouched test periods.
  1 gap >= +2 %, first 15 min (09:15-09:30) rising, its volume >= 2x the same window's 20-session average -> BUY 09:30 [Round 11 F_gap_continue_long]
  2 first-15-min volume >= 2x, price <= -1 % from the open, close below the bar's typical price -> SHORT 09:30 (MIS) [Round 11 C_vol_progress_short]
  3 first-15-min volume >= 2x, |price change| < 0.3 %, 5-day return to yesterday > +5 % -> SHORT 09:30 (MIS) [Round 11 X_absorb_fade]
  4 first-15-min volume >= 2x, price >= +1 %, close above typical price -> BUY 09:30 [Round 11 C_vol_progress_long]
  5 daily close above the prior 20-day high -> BUY-STOP next session above that day's high [debate validation, S_BRK20 rule]
  6 CHoCH: close crosses the last lower swing high on volume >= 1.5x [Round 2-3 swing.py "choch"]
  7 pullback: EMA20 > EMA50 > EMA200, a low touched EMA20 in the last 3 days, close above the previous high [swing.py "pullback"]
  8 gap <= -2 %, first 15 min falling, volume >= 2x -> SHORT 09:30 (MIS) [Round 11 F_gap_continue_short]
  9 squeeze: 10-day range <= 2.5 ATR, close above it in the top 30 % of the bar, volume >= 1.5x, above EMA50 > EMA200 [swing.py "squeeze"]
 10 sector leader: beats its sector (20 d) and NIFTY (60 d), sector +2 % in 5 days, stock 5-day return 0-5 % -> BUY next open [Round 11 B_sector_leader]
Intraday exits as tested: +2 % target / -1 % stop, else square off by 15:15 (MIS). Swing plans as in swing.py / the debate Buyer.
"""
import argparse, concurrent.futures as cf, datetime, json, math, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import common as C, snapshot as S     # noqa: E402

STRATEGIES = {
    1: ("Gap-up >= 2% still rising at 09:30 on high volume", "Intraday", "long", 61.3,
        "+0.29 % (n 119; lost money in 2022-24). With the 09:45 volume follow-through rule: +0.19 % over 212 trades, TEST +0.59 % (n 54, 69 % wins)"),
    2: ("Heavy-volume fall in the first 15 minutes", "Intraday", "short", 52.0, "+0.06 % (about breakeven)"),
    3: ("Absorption: heavy volume, flat price after a rally", "Intraday", "short", 51.2, "-0.32 %"),
    4: ("Heavy-volume rise in the first 15 minutes", "Intraday", "long", 47.7,
        "-0.04 %. With the 09:45 volume follow-through rule: +0.18 % over 1,106 trades, TEST +0.07 %, VALIDATION -0.07 %"),
    5: ("20-day breakout", "Swing", "long", 46.9, "-Rs 39 per trade"),
    6: ("CHoCH (change of character)", "Swing", "long", 46.5, "-Rs 8 per trade"),
    7: ("Pullback in an established uptrend", "Swing", "long", 46.4, "-Rs 84 per trade"),
    8: ("Gap-down still falling on volume", "Intraday", "short", 45.3, "-0.19 %"),
    9: ("Squeeze (tight-range breakout)", "Swing", "long", 44.4, "-Rs 116 per trade"),
    10: ("Sector-leader momentum", "Next day", "long", 43.6, "-0.16 %"),
}
INTRADAY_LEVELS = (1, 2, 3, 4, 8)
ENTRY_WINDOW_MIN = 15          # entry window after the 09:45 confirmation (09:45-10:00)
# Volume follow-through rule (user directive 12 Nov 2026; tested in research/round11_followthrough.py for #1 and #4):
# at 09:45 the 09:30-09:45 volume must be >= its 20-session average AND price must have kept moving the setup's way
# (above the 09:30 price for longs, below for shorts). Otherwise the setup is NOT VALID (volume faded) and the scan moves to
# the next stock, then the next level. Entry is the 09:45 bar's open. Shorts (#2, #3, #8) use the mirror, which is untested.
UNIVERSE = os.path.join(ROOT, "trader", "universe.txt")
DAILY_CACHE = os.path.join(ROOT, "trader", "cache", "swing-live")
IND500 = os.path.join(ROOT, "research", "cache", "industry500.json")


def universe():
    if not os.path.exists(UNIVERSE):
        import subprocess
        subprocess.run([sys.executable, os.path.join(ROOT, "trader-scanner", "scan.py"), "universe"], cwd=ROOT, check=True, capture_output=True)
    with open(UNIVERSE, encoding="utf-8") as fh:
        return [ln.split("|")[0].strip() for ln in fh if ln.strip() and not ln.startswith("#")]


# ---------------------------------------------------------------- intraday data (Yahoo 5-minute, delayed)

def _days(doc):
    r = doc["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    out = {}
    for i, t in enumerate(r.get("timestamp") or []):
        o, h, l, c, v = (q[k][i] for k in ("open", "high", "low", "close", "volume"))
        if None in (o, h, l, c):
            continue
        ts = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=t + 19800)
        slot = ((ts.hour * 60 + ts.minute) - 555) // 5
        if 0 <= slot < 75:
            out.setdefault(ts.date(), {})[slot] = (o, h, l, c, v or 0)
    return out


def opening_row(sym, day, now_ist=None):
    """09:15-09:30 facts for `day` (needs the three 5-minute bars), the previous close, 20-session volume baseline, 5-day return.
    Only bars that had ENDED by now_ist are used (Yahoo also returns the bar still forming)."""
    D = _days(S.LV.fetch(sym))
    if now_ist is not None and day in D:
        D[day] = {k: v for k, v in D[day].items() if datetime.datetime.combine(day, datetime.time(9, 15)) + datetime.timedelta(minutes=5 * k + 5) <= now_ist}
    if day not in D or not all(k in D[day] for k in range(3)):
        return None
    prev_days = sorted(d for d in D if d < day)
    if not prev_days:
        return None
    pd_ = D[prev_days[-1]]
    prev_close = pd_[max(pd_)][3]
    base = [sum(D[d][k][4] for k in range(3)) for d in prev_days[-20:] if all(k in D[d] for k in range(3))]
    b = D[day]
    o0 = b[0][0]
    h15, l15, c15 = max(b[k][1] for k in range(3)), min(b[k][2] for k in range(3)), b[2][3]
    v15 = sum(b[k][4] for k in range(3))
    closes = [D[d][max(D[d])][3] for d in prev_days[-6:]]
    ft_base = [sum(D[d][k][4] for k in (3, 4, 5)) for d in prev_days[-20:] if all(k in D[d] for k in (3, 4, 5))]
    has_ft = all(k in b for k in (3, 4, 5))
    return {"sym": sym, "prev_close": prev_close, "open": o0, "gap": o0 / prev_close - 1, "r15": c15 / o0 - 1, "c15": c15,
            "tp15": (h15 + l15 + c15) / 3, "h15": h15, "l15": l15, "rvol15": v15 / (sum(base) / len(base)) if base and sum(base) else None,
            "ret5": closes[-1] / closes[0] - 1 if len(closes) >= 6 else None, "entry_open": b[3][0] if 3 in b else None,
            "ft_rvol": (sum(b[k][4] for k in (3, 4, 5)) / (sum(ft_base) / len(ft_base))) if has_ft and ft_base and sum(ft_base) else None,
            "ft_move": (b[5][3] / b[3][0] - 1) if has_ft else None, "entry_0945": b[6][0] if 6 in b else (b[5][3] if has_ft else None),
            "last": b[max(b)][3], "last_bar": "%02d:%02d" % divmod(555 + 5 * max(b) + 5, 60),
            "after": [(datetime.datetime.combine(day, datetime.time(9, 15)) + datetime.timedelta(minutes=5 * k + 5),) + b[k] for k in sorted(b) if k >= 3]}


def intraday_hits(rows):
    hits = {k: [] for k in INTRADAY_LEVELS}
    for r in rows:
        if r is None or r["rvol15"] is None:
            continue
        v2 = r["rvol15"] >= 2
        if r["gap"] >= 0.02 and r["r15"] > 0 and v2:
            hits[1].append(r)
        if v2 and r["r15"] <= -0.01 and r["c15"] < r["tp15"]:
            hits[2].append(r)
        if v2 and abs(r["r15"]) < 0.003 and r["ret5"] is not None and r["ret5"] > 0.05:
            hits[3].append(r)
        if v2 and r["r15"] >= 0.01 and r["c15"] > r["tp15"]:
            hits[4].append(r)
        if r["gap"] <= -0.02 and r["r15"] < 0 and v2:
            hits[8].append(r)
    for k in hits:
        hits[k].sort(key=lambda r: -r["rvol15"])
    return hits


def intraday_plan(r, side, now_ist, day):
    sgn = 1 if side == "long" else -1
    confirm_at = datetime.datetime.combine(day, datetime.time(9, 45))
    ft_state, ft_why = None, None
    if now_ist >= confirm_at:
        if r.get("ft_rvol") is None or r.get("ft_move") is None:
            ft_state, ft_why = "NO DATA", "09:30-09:45 bars unavailable"
        elif r["ft_rvol"] >= 1.0 and sgn * r["ft_move"] > 0:
            ft_state, ft_why = "CONFIRMED", "09:30-09:45 volume %.1fx usual, price %+.2f%%" % (r["ft_rvol"], 100 * r["ft_move"])
        else:
            ft_state, ft_why = "FADED", "09:30-09:45 volume %.1fx usual, price %+.2f%%" % (r["ft_rvol"], 100 * r["ft_move"])
    e = (r.get("entry_0945") if ft_state == "CONFIRMED" else None) or r["entry_open"] or r["c15"]
    stop, tgt = C.tick(e * (1 - sgn * 0.01), up=sgn < 0), C.tick(e * (1 + sgn * 0.02), up=sgn > 0)
    qty = max(0, int(C.CONFIG["intraday"]["risk_inr"] // abs(e - stop)))
    while qty and abs(e - stop) * qty + C.round_trip("intraday", qty, min(e, stop), max(e, stop)) > C.CONFIG["intraday"]["risk_inr"]:
        qty -= 1
    loss = abs(e - stop) * qty + C.round_trip("intraday", qty, min(e, stop), max(e, stop)) if qty else 0
    gain = abs(tgt - e) * qty - C.round_trip("intraday", qty, min(e, tgt), max(e, tgt)) if qty else 0
    def walk(bars):
        for (end, o, h, l, c, v) in bars:
            if (side == "long" and l <= stop) or (side == "short" and h >= stop):
                return "INVALIDATED", "stop %.2f traded by %s" % (stop, end.strftime("%H:%M"))
            if (side == "long" and h >= tgt) or (side == "short" and l <= tgt):
                return "TARGET HIT", "target %.2f traded by %s; do not chase" % (tgt, end.strftime("%H:%M"))
        return None, None
    decided = datetime.datetime.combine(day, datetime.time(9, 30))
    trade_bars = [x for x in r["after"] if x[0] > confirm_at]                # bars after the 09:45 entry
    if now_ist < decided:
        status, why = "WAIT", "conditions are measured at 09:30"
    elif now_ist < confirm_at:
        status, why = "WAIT", "09:45 volume follow-through check pending (entry only if volume holds and price keeps moving)"
    elif ft_state != "CONFIRMED":
        status, why = "NOT VALID", "volume follow-through %s (%s)" % (ft_state.lower(), ft_why)
    else:
        status, why = "VALID", "follow-through confirmed (%s); entry window 09:45-10:00" % ft_why
        st, wy = walk([x for x in trade_bars if x[0] <= now_ist])
        if st:
            status, why = st, wy
        elif now_ist > confirm_at + datetime.timedelta(minutes=ENTRY_WINDOW_MIN):
            status, why = "EXPIRED", "entry was at 09:45; after 10:00 the tested setup no longer applies"
    outcome, _ = walk(trade_bars) if ft_state == "CONFIRMED" else ("not traded (%s)" % (ft_state or "pending").lower(), None)
    if outcome is None and trade_bars:
        last_c = trade_bars[-1][4]
        outcome = "closed %+.2f%% (%s)" % (100 * sgn * (last_c / e - 1), "data to %s" % trade_bars[-1][0].strftime("%H:%M"))
    return {"entry": round(e, 2), "stop": stop, "target": tgt, "qty": qty, "max_loss": round(loss, 2), "net_at_target": round(gain, 2),
            "rr": round(gain / loss, 2) if loss else None, "costs_round_trip": round(C.round_trip("intraday", qty, e, tgt), 2) if qty else 0,
            "status": status if (gain / loss if loss else 0) >= 1.5 or status != "VALID" else "VALID, R:R BELOW 1.5",
            "status_why": why, "outcome_so_far": outcome}


# ---------------------------------------------------------------- daily data (swing levels 5-7, 9 and next-day level 10)

def daily_bars(syms, asof):
    os.makedirs(DAILY_CACHE, exist_ok=True)
    fresh_after = datetime.datetime.combine(asof, datetime.time(15, 35)).timestamp() - 19800 + time.timezone * 0
    out = {}

    def one(s):
        p = os.path.join(DAILY_CACHE, s.replace("&", "_and_").replace("^", "IDX_") + ".json")
        doc = None
        if os.path.exists(p) and os.path.getmtime(p) >= fresh_after:
            doc = json.load(open(p, encoding="utf-8"))
        else:
            doc = S.SW.yahoo_daily(s)
            if doc:
                json.dump(doc, open(p, "w", encoding="utf-8"))
        b = [x for x in S.SW.bars_from(doc) if x["d"] <= asof] if doc else []
        return s, b
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        for s, b in ex.map(one, list(syms) + ["^NSEI"]):
            if len(b) >= 260:
                out[s] = S.SW.enrich(b)
    return out


def swing_hits(data, asof):
    hits = {5: [], 6: [], 7: [], 9: [], 10: []}
    nifty = data.get("^NSEI")
    ind = json.load(open(IND500, encoding="utf-8")) if os.path.exists(IND500) else {}
    ret5 = {s: b[-1]["c"] / b[-6]["c"] - 1 for s, b in data.items() if s != "^NSEI" and b[-1]["d"] == asof}
    ret20 = {s: b[-1]["c"] / b[-21]["c"] - 1 for s, b in data.items() if s != "^NSEI" and b[-1]["d"] == asof}
    sec5, sec20 = {}, {}
    for s in ret5:
        sec5.setdefault(ind.get(s), []).append(ret5[s]); sec20.setdefault(ind.get(s), []).append(ret20[s])
    med = lambda xs: sorted(xs)[len(xs) // 2]
    for s, b in data.items():
        if s == "^NSEI" or b[-1]["d"] != asof:
            continue
        t = len(b) - 1
        x = b[t]
        if x["avgval"] < 10e7 or x["c"] < 50:
            continue
        state = {"swing_highs": [], "swing_lows": [], "fvgs": []}
        for k in range(2, t + 1):
            S.SW.update_state(b, k, state)
        if x["c"] > max(p["h"] for p in b[t - 20:t]):
            stop = min(x["l"], x["e20"]) - 0.1 * x["atr"]
            hits[5].append((s, x["rvol"], C.build_plan("swing", "long", C.tick(x["h"] + C.TICK, up=True), stop, "buy-stop above %.2f" % x["h"])))
        for lvl, name in ((6, "choch"), (7, "pullback"), (9, "squeeze")):
            st = S.SW.signal(b, t, name, state)
            if st is not None:
                p = S.SW.plan(b, t, st, C.CONFIG["swing"]["risk_inr"], C.CONFIG["capital"])
                if p:
                    hits[lvl].append((s, x["rvol"], {"direction": "long", "entry": p["entry"], "stop": p["stop"], "target1": p["t1"],
                                                     "target2": p["t2"], "qty": p["qty"], "max_loss_incl_costs": round(p["max_loss"], 2),
                                                     "net_at_t1": round(p["net_t1"], 2), "net_rr_t1": round(p["net_t1"] / p["max_loss"], 2),
                                                     "entry_kind": "buy-stop above %.2f" % x["h"]}))
        if nifty and s in ret5 and ind.get(s) and len(b) > 61:
            rs60 = (x["c"] / b[-61]["c"]) - (nifty[-1]["c"] / nifty[-61]["c"])
            if ret20[s] > med(sec20[ind[s]]) and rs60 > 0 and med(sec5[ind[s]]) > 0.02 and 0 <= ret5[s] <= 0.05:
                e = x["c"]
                hits[10].append((s, x["rvol"], {"direction": "long", "entry": round(e, 2), "stop": C.tick(e * 0.99), "target1": C.tick(e * 1.02, up=True),
                                                 "target2": None, "qty": None, "entry_kind": "buy at the next open (reference: last close)"}))
    for k in hits:
        hits[k].sort(key=lambda h: -h[1])
    return hits


# ---------------------------------------------------------------- report

def table(level, rows, kind):
    name = STRATEGIES[level][0]
    L = ["| Rank | Stock | Strategy No. | Strategy Name | Entry | Stop Loss | Target | Risk:Reward | Setup Status |", "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        if kind == "intraday":
            p = r["plan"]
            L.append("| %d | %s | %d | %s | ₹%.2f | ₹%.2f | ₹%.2f | %s | %s |" % (i, r["sym"], level, name, p["entry"], p["stop"], p["target"],
                                                                          "1:%s" % p["rr"] if p["rr"] else "-", p["status"]))
        else:
            s, rv, p = r
            L.append("| %d | %s | %d | %s | ₹%.2f | ₹%.2f | ₹%.2f | %s | %s |" % (i, s, level, name, p["entry"], p["stop"], p["target1"],
                                                                          "1:%s" % p.get("net_rr_t1") if p.get("net_rr_t1") else "1:2.0 gross",
                                                                          "PENDING next session"))
    return "\n".join(L)


def details(level, rows, kind):
    out = []
    for r in rows[:5]:
        if kind == "intraday":
            p = r["plan"]
            out.append("- **%s**: gap %+.2f%%, 09:15-09:30 %+.2f%%, opening volume %.1fx its 20-session average%s; entry ₹%.2f (09:30 open), "
                       "stop ₹%.2f, target ₹%.2f, qty %d at ₹500 risk, max loss ₹%.0f, net at target ₹%.0f (costs ₹%.0f). Status: %s (%s). "
                       "What happened after (for review only, not known at entry): %s. Last data: %s IST (Yahoo, delayed)." % (
                           r["sym"], 100 * r["gap"], 100 * r["r15"], r["rvol15"], ", 5-day return %+.1f%%" % (100 * r["ret5"]) if r["ret5"] is not None else "",
                           p["entry"], p["stop"], p["target"], p["qty"], p["max_loss"], p["net_at_target"], p["costs_round_trip"], p["status"], p["status_why"], p["outcome_so_far"], r["last_bar"]))
        else:
            s, rv, p = r
            out.append("- **%s**: signal-day volume %.1fx; %s; stop ₹%.2f; target ₹%.2f%s." % (
                s, rv, p["entry_kind"], p["stop"], p["target1"], "; qty %s, max loss ₹%s, net at T1 ₹%s" % (p["qty"], p.get("max_loss_incl_costs"), p.get("net_at_t1")) if p.get("qty") else ""))
    return "\n".join(out)


def run(day=None, all_levels=False, limit=None):
    now = S.ist_now()
    live = day is None
    day = day or now.date()
    if not live:
        now = datetime.datetime.combine(day, datetime.time(9, 46))          # replay just after the 09:45 confirmation
    syms = universe()[:limit] if limit else universe()
    lines = ["# 🎯 Top-10 Strategy Priority Scan", "", "| Session | Mode | Universe | Data |", "|---|---|---|---|",
             "| %s | %s | %d stocks (Nifty 500 lists) | Yahoo 5-minute and daily bars: DELAYED, unofficial; NOT VERIFIED against a live broker feed |" % (
                 day, "live" if live else "replay (as of 09:46, after the follow-through check)", len(syms)), ""]
    market_open = now.weekday() < 5 and datetime.time(9, 15) <= now.time() <= datetime.time(15, 30)
    if live and not market_open:
        lines.append("Market is closed now (%s IST); intraday levels are evaluated on the latest session for reference only." % now.strftime("%H:%M"))
    if live and market_open and now.time() < datetime.time(9, 30, 30):
        lines += ["## ⏳ WAIT: too early", "", "The intraday strategies (#1-#4, #8) are measured on the completed 09:15-09:30 bars. Run the scan after "
                  "09:31, and again after 09:46 for the volume follow-through check. Nothing is judged on incomplete bars."]
        return "
".join(lines), None
    found, evaluated = None, []
    ihits = None
    swing = None
    for level in range(1, 11):
        if level in INTRADAY_LEVELS:
            if ihits is None:
                with cf.ThreadPoolExecutor(max_workers=4) as ex:
                    rows = list(ex.map(lambda s: _safe(opening_row, s, day, now), syms))
                ihits = intraday_hits(rows)
                ihits["_coverage"] = sum(1 for r in rows if r)
            rows = ihits[level]
            for r in rows:
                r["plan"] = intraday_plan(r, STRATEGIES[level][2], now, day)
            kind = "intraday"
        else:
            if swing is None:
                asof = day if (not live or now.time() >= datetime.time(15, 35)) else day - datetime.timedelta(days=1)
                data = daily_bars(syms, asof)
                last = max((b[-1]["d"] for s, b in data.items() if s != "^NSEI"), default=asof)
                swing = swing_hits(data, last)
                swing["_asof"] = last
            rows, kind = swing[level], "swing"
        live_rows = [r for r in rows if (r["plan"]["status"] if kind == "intraday" else "VALID").startswith(("VALID", "WAIT"))]
        evaluated.append((level, len(rows), len(live_rows)))
        if rows:
            lines += ["## Priority %d: %s (%s), historical win rate %.1f%%, tested result %s" % (level, STRATEGIES[level][0], STRATEGIES[level][1],
                                                                                             STRATEGIES[level][3], STRATEGIES[level][4]), "",
                      table(level, rows[:10], kind), "", "**Why they qualify (exact conditions met):**", "", details(level, rows, kind), ""]
            if live_rows and found is None:
                found = level
            if live_rows and not all_levels:
                break
            if not live_rows:
                lines += ["No valid setup at priority %d (all %d not valid / expired / already resolved); moving to priority %d." % (
                    level, len(rows), level + 1), ""]
    lines += ["**Levels checked in order:** " + ", ".join("#%d: %d found, %d valid" % x for x in evaluated)]
    if ihits is not None:
        lines.append("Opening data available for %d of %d stocks." % (ihits["_coverage"], len(syms)))
    if found is None:
        lines += ["", "## 🟡 NO TRADE", "None of the 10 approved strategies has a valid setup. Conditions were not loosened."]
    lines += ["", "_Win rates are historical; none of these strategies is proven profitable after costs (#2 is about breakeven, #1 lost money "
              "in 2022-24, #3 wins 51 % but loses on average). Paper analysis; you place every order yourself._"]
    return "\n".join(lines), found


def _safe(fn, *a):
    try:
        return fn(*a)
    except Exception:
        return None


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--date"); p.add_argument("--all", action="store_true"); p.add_argument("--limit", type=int)
    a = p.parse_args(argv)
    md, _ = run(datetime.date.fromisoformat(a.date) if a.date else None, a.all, a.limit)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
