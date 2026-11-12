"""Evidence catalogue shared by the debate agents (STEP 1 support).

Each item is a pure function of the snapshot: it returns (passed, observed, threshold) or None when its inputs are UNAVAILABLE.
Agents choose WHICH items to cite; they cannot change how an item is computed. The Judge recomputes every cited item from the same
snapshot, so an argument that does not reproduce is struck out.

`prior` points at earlier research that tested the closest setup, with its untouched-period result. "none" = never tested alone.
"""

def _v(s, key):
    f = s["fields"].get(key)
    return None if not f or f["class"] == "UNAVAILABLE" else f["value"]


def _num(x):
    return x if isinstance(x, (int, float)) else None


# ---------------------------------------------------------------- intraday items

def _vwap_side(s, side):
    want = "above" if side == "buy" else "below"
    v = _v(s, "vwap")
    if not v:
        return None
    ok = v["side"] == want and (v["slope_6_bars"] > 0 if want == "above" else v["slope_6_bars"] < 0)
    return ok, "price %s VWAP %.2f (%+.2f%%), slope %+.2f" % (v["side"], v["value"], v["price_vs_vwap_pct"], v["slope_6_bars"]), \
        "%s VWAP with VWAP sloping %s" % (want, "up" if want == "above" else "down")


def _rvol(s, side):
    rv, ch = _v(s, "relative_volume"), _num(_v(s, "day_change_pct"))
    if not rv or rv.get("cumulative_x") is None or ch is None:
        return None
    ok = rv["cumulative_x"] >= 1.5 and (ch > 0 if side == "buy" else ch < 0)
    return ok, "relative volume %.2fx, day change %+.2f%%" % (rv["cumulative_x"], ch), ">= 1.5x with price moving %s" % (
        "up" if side == "buy" else "down")


def _rs_nifty(s, side):
    ch, n = _num(_v(s, "day_change_pct")), _v(s, "nifty")
    if ch is None or not n or n.get("day_change_pct") is None:
        return None
    d = ch - n["day_change_pct"]
    return (d >= 1.0 if side == "buy" else d <= -1.0), "stock %+.2f%% vs NIFTY %+.2f%% (gap %+.2f)" % (ch, n["day_change_pct"], d), \
        "%s NIFTY by at least 1.0 point" % ("beats" if side == "buy" else "lags")


def _sector(s, side):
    sec, n = _v(s, "sector"), _v(s, "nifty")
    if not sec or not n:
        return None
    nch = n.get("day_change_pct", n.get("change_pct"))
    if nch is None:
        return None
    share = sec["peers_up"] / sec["peers"] if sec["peers"] else 0
    ok = (sec["median_change_pct"] > nch and share >= 0.6) if side == "buy" else (sec["median_change_pct"] < nch and share <= 0.4)
    return ok, "%s peers median %+.2f%% (%d/%d up) vs NIFTY %+.2f%%" % (sec["sector"], sec["median_change_pct"], sec["peers_up"],
                                                                     sec["peers"], nch), \
        "sector median %s NIFTY and %s" % ("above" if side == "buy" else "below", ">= 60% of peers up" if side == "buy" else "<= 40% up")


def _level_break(s, side, hi_key, lo_key, label):
    lv, p = _v(s, "levels"), _num(_v(s, "price"))
    if not lv or p is None or lv.get(hi_key) is None:
        return None
    if side == "buy":
        return p > lv[hi_key], "price %.2f vs %s high %.2f" % (p, label, lv[hi_key]), "above the %s high" % label
    return p < lv[lo_key], "price %.2f vs %s low %.2f" % (p, label, lv[lo_key]), "below the %s low" % label


def _impulse(s, side):
    imp = _v(s, "impulse_last_6_bars")
    if imp is None:
        return None
    want = "up" if side == "buy" else "down"
    hits = [i["bar"] for i in imp if i["direction"] == want]
    return bool(hits), "impulse-like %s bars: %s" % (want, ", ".join(hits) or "none"), "a wide, high-volume %s bar in the last 30 min" % want


def _opening(s, side):
    op = _v(s, "opening_1m")
    if not op or len(op) < 4:
        return None
    o, c = op[0]["o"], op[-1]["c"]
    hi, lo = max(x["h"] for x in op), min(x["l"] for x in op)
    pos = (c - lo) / (hi - lo) if hi > lo else 0.5
    ok = (c > o and pos >= 0.6) if side == "buy" else (c < o and pos <= 0.4)
    return ok, "09:15 open %.2f -> 09:18 close %.2f, close at %.0f%% of the 4-minute range" % (o, c, 100 * pos), \
        "09:18 close %s the 09:15 open and in the %s 40%% of the range" % ("above" if side == "buy" else "below",
                                                                          "upper" if side == "buy" else "lower")


def _delivery(s, side):
    d = _v(s, "delivery_prev")
    if not d or d.get("stale"):
        return None
    diff = d["last_pct"] - d["avg_pct_prior"]
    return (diff >= 5 if side == "buy" else diff <= -5), "previous-day delivery %.1f%% vs 20-day average %.1f%%" % (
        d["last_pct"], d["avg_pct_prior"]), "%s the average by 5 points (previous session only)" % ("above" if side == "buy" else "below")


def _oi(s, side):
    f = _v(s, "futures_prev")
    if not f or not f.get("buildup"):
        return None
    want = ("long build-up", "short covering") if side == "buy" else ("short build-up", "long unwinding")
    return f["buildup"] in want, "previous session: %s (OI %+.2f%%, price %+.2f%%)" % (
        f["buildup"], f["oi_change_1d_pct"] or 0, f["price_change_1d_pct"] or 0), " or ".join(want)


def _extended(s):
    v = _v(s, "vwap")
    if not v or v.get("deviation_atr") is None:
        return None
    return abs(v["deviation_atr"]) > 1.5, "price %.2f ATR(5m) from VWAP" % v["deviation_atr"], "more than 1.5 ATR(5m) from VWAP"


def _moved(s):
    ch = _num(_v(s, "day_change_pct"))
    if ch is None:
        return None
    return abs(ch) > 2.5, "already %+.2f%% on the day" % ch, "more than 2.5% from the previous close"


# ---------------------------------------------------------------- swing items

def _trend(s, side):
    t, p = _v(s, "trend"), _num(_v(s, "price"))
    if not t or p is None:
        return None
    if side == "buy":
        ok = p > t["ema20"] > t["ema50"] > t["ema200"]
    else:
        ok = p < t["ema20"] < t["ema50"] and p < t["ema200"]
    return ok, "close %.2f, EMA20 %.2f, EMA50 %.2f, EMA200 %.2f" % (p, t["ema20"], t["ema50"], t["ema200"]), \
        "close > EMA20 > EMA50 > EMA200" if side == "buy" else "close < EMA20 < EMA50 and below EMA200"


def _rs_swing(s, side):
    r = _v(s, "relative_strength")
    if not r or r.get("rs60_pct") is None:
        return None
    ok = (r["rs20_pct"] > 0 and r["rs60_pct"] > 0) if side == "buy" else (r["rs20_pct"] < 0 and r["rs60_pct"] < 0)
    return ok, "vs NIFTY: 20 days %+.2f%%, 60 days %+.2f%%" % (r["rs20_pct"], r["rs60_pct"]), \
        "both %s" % ("positive" if side == "buy" else "negative")


def _breakout20(s, side):
    t, p = _v(s, "trend"), _num(_v(s, "price"))
    if not t or p is None:
        return None
    if side == "buy":
        return p > t["high20"], "close %.2f vs prior 20-day high %.2f" % (p, t["high20"]), "close above the prior 20-day high"
    return p < t["low20"], "close %.2f vs prior 20-day low %.2f" % (p, t["low20"]), "close below the prior 20-day low"


def _adx(s, side):
    t = _v(s, "trend")
    if not t or not t.get("adx14_pdi_mdi"):
        return None
    a, pdi, mdi = t["adx14_pdi_mdi"]
    ok = a >= 20 and (pdi > mdi if side == "buy" else mdi > pdi)
    return ok, "ADX %.1f, +DI %.1f, -DI %.1f" % (a, pdi, mdi), "ADX >= 20 with %s" % ("+DI > -DI" if side == "buy" else "-DI > +DI")


def _weekly(s, side):
    w = _v(s, "weekly")
    if not w:
        return None
    n = w["weeks"] - 1
    ok = (w["higher_highs"] + w["higher_lows"] >= n * 1.25) if side == "buy" else (w["higher_highs"] + w["higher_lows"] <= n * 0.75)
    return ok, "last %d weeks: %d higher highs, %d higher lows" % (w["weeks"], w["higher_highs"], w["higher_lows"]), \
        "mostly rising weekly structure" if side == "buy" else "mostly falling weekly structure"


def _close_strength(s, side):
    d = _v(s, "daily")
    if not d:
        return None
    if side == "buy":
        ok = d["close_in_range"] >= 0.7 and d["rvol"] >= 1.5 and d["change_pct"] > 0
        return ok, "closed at %.0f%% of the day's range on %.2fx volume (%+.2f%%)" % (100 * d["close_in_range"], d["rvol"], d["change_pct"]), \
            "up day, close in the top 30% of the range, volume >= 1.5x"
    ok = d["close_in_range"] <= 0.3 and d["rvol"] >= 1.5
    return ok, "closed at %.0f%% of the day's range on %.2fx volume (%+.2f%%)" % (100 * d["close_in_range"], d["rvol"], d["change_pct"]), \
        "close in the bottom 30% of the range (upper-wick rejection) on volume >= 1.5x"


def _rsi_zone(s, side):
    t = _v(s, "trend")
    if not t or t.get("rsi14") is None:
        return None
    r = t["rsi14"]
    return ((50 <= r <= 70) if side == "buy" else (30 <= r <= 50)), "RSI(14) %.1f" % r, "50-70" if side == "buy" else "30-50"


def _overbought(s):
    t = _v(s, "trend")
    if not t or t.get("rsi14") is None:
        return None
    return t["rsi14"] > 75 or t["rsi14"] < 25, "RSI(14) %.1f" % t["rsi14"], "RSI above 75 or below 25 (stretched)"


# ---------------------------------------------------------------- catalogue

SWING_PRIOR = "docs/SWING_BACKTEST.md"
CATALOGUE = [
    # id, mode, side ("buy", "sell", "risk"), function, description, prior research reference
    ("I_VWAP", "intraday", "both", _vwap_side, "Trend vs session VWAP", "docs/MATRIX_BACKTEST.md: VWAP filters, none positive in both periods"),
    ("I_RVOL", "intraday", "both", _rvol, "Volume expansion in the move's direction", "docs/MATRIX_BACKTEST.md: RVOL grid, none positive"),
    ("I_RS", "intraday", "both", _rs_nifty, "Relative strength vs NIFTY today", "none (intraday)"),
    ("I_SECTOR", "intraday", "both", _sector, "Sector breadth vs NIFTY", "none"),
    ("I_ORB", "intraday", "both", lambda s, side: _level_break(s, side, "or_high", "or_low", "15-minute opening range"),
     "Opening-range break", "docs/BACKTEST_2026-11-11.md: ORB lost Rs 56-90 per trade; Round 5-6 grid none positive"),
    ("I_PDL", "intraday", "both", lambda s, side: _level_break(s, side, "prev_high", "prev_low", "previous-day"),
     "Previous-day high/low break", "Round 9: PDL sweep stream negative after costs"),
    ("I_IMPULSE", "intraday", "both", _impulse, "Impulse-like bar", "none"),
    ("I_OPEN", "intraday", "both", _opening, "09:15-09:18 opening structure", "Round 10B (opening study): pending"),
    ("I_DELIV", "both", "both", _delivery, "Previous-day delivery vs average",
     "docs/ROUND8_DELIVERY_OI.md: relative signal at 5-20 days; >65% + long build-up negative at 1-5 days"),
    ("I_OI", "both", "both", _oi, "Previous-day futures build-up", "docs/ROUND8_DELIVERY_OI.md: OI raises next-day rank IC 0.043 -> 0.062"),
    ("X_EXTENDED", "intraday", "risk", lambda s, side=None: _extended(s), "Stretched from VWAP", "CLAUDE.md card rule 1 (BAJFINANCE review)"),
    ("X_MOVED", "intraday", "risk", lambda s, side=None: _moved(s), "Large move already done", "CLAUDE.md card rule 1"),
    ("S_TREND", "swing", "both", _trend, "EMA stack", SWING_PRIOR + ": pullback-in-trend OOS -Rs 84/trade"),
    ("S_RS", "swing", "both", _rs_swing, "Relative strength vs NIFTY (20 and 60 days)", "docs/SWING_BACKTEST.md round 3: RS filter, CI includes 0"),
    ("S_BRK20", "swing", "both", _breakout20, "20-day breakout/breakdown", SWING_PRIOR + ": weekhigh OOS 37% win, -Rs 128/trade"),
    ("S_ADX", "swing", "both", _adx, "Trend strength (ADX/DI)", "none"),
    ("S_WEEKLY", "swing", "both", _weekly, "Weekly structure", "none"),
    ("S_CLOSE", "swing", "both", _close_strength, "Close location on volume", "docs/MOMENTUM_BACKTEST.md: 24 of 24 variants negative"),
    ("S_RSI", "swing", "both", _rsi_zone, "RSI zone", "none"),
    ("X_RSI", "swing", "risk", lambda s, side=None: _overbought(s), "RSI stretched", "none"),
]


def evaluate(snapshot, side):
    """All catalogue items for this mode and side, evaluated on the snapshot. side: 'buy' or 'sell'."""
    out = []
    for iid, mode, sides, fn, desc, prior in CATALOGUE:
        if mode not in (snapshot["mode"], "both"):
            continue
        r = fn(snapshot) if sides == "risk" else fn(snapshot, side)
        if r is None:
            out.append({"id": iid, "description": desc, "status": "UNAVAILABLE", "prior": prior})
            continue
        ok, observed, threshold = r
        out.append({"id": iid, "description": desc, "status": ("FLAG" if ok else "CLEAR") if sides == "risk" else ("PASS" if ok else "FAIL"),
                    "observed": observed, "threshold": threshold, "prior": prior})
    return out


def recompute(snapshot, side, item_id):
    """The Judge's check: recompute one item from the snapshot."""
    for e in evaluate(snapshot, side):
        if e["id"] == item_id:
            return e
    return None
