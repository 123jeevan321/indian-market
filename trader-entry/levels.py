#!/usr/bin/env python3
"""VWAP, relative volume, key levels, impulse detection and an approximate volume profile for trader-entry.
Standard library only. Data: Yahoo Finance 5-minute `.NS` bars (free, unofficial, delayed, no bid/ask).

    python3 levels.py RELIANCE                         # as of now (IST), today's session
    python3 levels.py RELIANCE --now "2026-11-09 10:40"   # replay a past day as of that time
    python3 levels.py "M&M" --json

What it computes, from COMPLETED 5-minute bars only:

  VWAP            session volume-weighted average price using (high + low + close) / 3 per bar. Price vs VWAP, the
                  deviation in % and in ATRs, and the slope over the last 6 bars. VWAP from 5-minute bars approximates
                  the true tick VWAP; it can differ by a few paise.
  relative volume cumulative volume so far vs the average cumulative volume at the same time of day over the previous
                  sessions (same stock, up to 20 sessions). Also the last bar vs the same slot's average.
  levels          previous day high / low / close, gap %, opening range (first 15 minutes), day high / low.
  ATR             average true range of 5-minute bars (14) and the average bar range.
  volume profile  APPROXIMATE point of control (POC), value area high / low (70 %) for today and for the previous session,
                  built by spreading each 5-minute bar's volume evenly over its high-low range. A true profile needs
                  tick data; treat these as approximate levels.
  impulse         the last completed bars: a bar is an IMPULSE when its range >= 1.5 x the average bar range, its volume
                  >= 2 x the same slot's average, and it closes in the outer 25 % of its range. This is a price-and-volume
                  proxy for a burst of participation. It does NOT prove an institution acted: say "impulse-like".

Nothing here uses bid/ask, depth or aggressor data (the free feeds have none). It never says who is buying.
"""

import argparse
import datetime
import json
import sys
import time
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (compatible; india-equity-intraday-skill/1.0)"
OPEN_MIN = 9 * 60 + 15
SLOTS = 75
HOSTS = ("query2", "query1")


class LevelsError(Exception):
    pass


def to_ist(utc):
    return utc + datetime.timedelta(hours=5.5)


def ist_to_utc(local):
    return local - datetime.timedelta(hours=5.5)


def yahoo_symbol(sym):
    s = sym.upper()
    if not s.endswith((".NS", ".BO")):
        s += ".NS"
    return s.replace("&", "%26")


def fetch(sym, offline=None):
    if offline:
        with open(offline, encoding="utf-8") as fh:
            return json.load(fh)
    last = "no answer"
    for host in HOSTS:
        url = "https://%s.finance.yahoo.com/v8/finance/chart/%s?range=60d&interval=5m" % (host, yahoo_symbol(sym))
        for attempt in (0, 1):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=30) as r:
                    return json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                last = "HTTP %d" % e.code
                e.close()
                if e.code == 429 and attempt == 0:
                    time.sleep(5)
                    continue
                break
            except (urllib.error.URLError, OSError, ValueError) as e:
                last = str(getattr(e, "reason", e))
                break
    raise LevelsError("Yahoo did not answer for %s (%s)" % (sym, last))


def sessions(doc, now_utc):
    """{date: {slot: bar}} of complete bars at or before now_utc."""
    try:
        res = doc["chart"]["result"][0]
    except (KeyError, IndexError, TypeError):
        raise LevelsError("Yahoo sent no chart for that symbol")
    q = res["indicators"]["quote"][0]
    out = {}
    for i, ts in enumerate(res.get("timestamp") or []):
        try:
            o, h, l, c, v = (q[k][i] for k in ("open", "high", "low", "close", "volume"))
        except (KeyError, IndexError):
            continue
        if None in (o, h, l, c) or ts % 300:
            continue
        start = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=ts)
        if start + datetime.timedelta(minutes=5) > now_utc:
            continue
        loc = to_ist(start)
        slot = (loc.hour * 60 + loc.minute - OPEN_MIN) // 5
        if 0 <= slot < SLOTS:
            out.setdefault(loc.date(), {})[slot] = {"o": o, "h": h, "l": l, "c": c, "v": v or 0, "slot": slot}
    return out


def hm(slot):
    m = OPEN_MIN + 5 * slot
    return "%02d:%02d" % (m // 60, m % 60)


def vwap_series(bars):
    pv = vv = 0.0
    out = []
    for b in bars:
        tp = (b["h"] + b["l"] + b["c"]) / 3.0
        pv += tp * b["v"]
        vv += b["v"]
        out.append(pv / vv if vv else tp)
    return out


def atr(bars_by_day, n=14):
    trs, prev = [], None
    for d in sorted(bars_by_day):
        for s in sorted(bars_by_day[d]):
            b = bars_by_day[d][s]
            tr = b["h"] - b["l"] if prev is None else max(b["h"] - b["l"], abs(b["h"] - prev), abs(b["l"] - prev))
            trs.append(tr)
            prev = b["c"]
    last = trs[-n:]
    return sum(last) / len(last) if last else 0.0


def profile(bars, tick=0.05):
    """Approximate volume profile: -> {poc, vah, val, bin}. Each bar's volume is spread evenly over its range."""
    if not bars:
        return None
    lo, hi = min(b["l"] for b in bars), max(b["h"] for b in bars)
    px = (lo + hi) / 2.0
    size = max(tick, round(px * 0.0005 / tick) * tick)       # about 0.05 % of price, on the tick grid
    vol = {}
    for b in bars:
        a, z = int(b["l"] / size), int(b["h"] / size)
        n = z - a + 1
        for k in range(a, z + 1):
            vol[k] = vol.get(k, 0.0) + b["v"] / float(n)
    total = sum(vol.values())
    if not total:
        return None
    poc = max(vol, key=lambda k: vol[k])
    inside, acc, lo_k, hi_k = {poc}, vol[poc], poc, poc
    while acc < 0.7 * total:
        up, dn = vol.get(hi_k + 1, 0.0), vol.get(lo_k - 1, 0.0)
        if up == 0 and dn == 0:
            break
        if up >= dn:
            hi_k += 1
            acc += up
        else:
            lo_k -= 1
            acc += dn
    return {"poc": round((poc + 0.5) * size, 2), "vah": round((hi_k + 1) * size, 2), "val": round(lo_k * size, 2),
            "bin": round(size, 2), "approximate": True}


def compute(doc, now_utc, hist_days=20):
    days = sessions(doc, now_utc)
    today = to_ist(now_utc).date()
    if today not in days:
        later = [d for d in days if d <= today]
        raise LevelsError("no completed bars for %s yet (market closed, holiday, or before 9:20 IST); latest data day: %s"
                          % (today, max(later).isoformat() if later else "none"))
    cur = [days[today][s] for s in sorted(days[today])]
    past = [d for d in sorted(days) if d < today]
    prev_day = past[-1] if past else None
    out = {"date": today.isoformat(), "as_of": hm(cur[-1]["slot"] + 1) + " IST (last completed 5-minute bar ends)",
           "bars": len(cur), "source": "Yahoo Finance 5m (.NS), unofficial, delayed"}
    vw = vwap_series(cur)
    last = cur[-1]
    a = atr(days)
    avg_rng = sum(b["h"] - b["l"] for d in past[-hist_days:] for b in days[d].values()) / max(
        1, sum(len(days[d]) for d in past[-hist_days:]))
    slope = (vw[-1] - vw[max(0, len(vw) - 7)]) if len(vw) > 1 else 0.0
    out["price"] = last["c"]
    out["vwap"] = {"value": round(vw[-1], 2), "price_vs_vwap_pct": round(100 * (last["c"] / vw[-1] - 1), 2),
                   "deviation_atr": round((last["c"] - vw[-1]) / a, 2) if a else None,
                   "side": "above" if last["c"] > vw[-1] else "below", "slope_6_bars": round(slope, 2),
                   "crosses_today": sum(1 for i in range(1, len(cur)) if (cur[i]["c"] > vw[i]) != (cur[i - 1]["c"] > vw[i - 1]))}
    # relative volume
    k = last["slot"]
    cum_today = sum(b["v"] for b in cur)
    hist_cum, hist_slot = [], []
    for d in past[-hist_days:]:
        bars = days[d]
        if all(s in bars for s in range(k + 1)):
            hist_cum.append(sum(bars[s]["v"] for s in range(k + 1)))
            hist_slot.append(bars[k]["v"])
    if hist_cum:
        avg_cum, avg_slot = sum(hist_cum) / len(hist_cum), sum(hist_slot) / len(hist_slot)
        out["relative_volume"] = {"cumulative_x": round(cum_today / avg_cum, 2) if avg_cum else None,
                                  "last_bar_x": round(last["v"] / avg_slot, 2) if avg_slot else None,
                                  "compared_with_sessions": len(hist_cum), "volume_so_far": int(cum_today)}
    else:
        out["relative_volume"] = None
    # levels
    lv = {"day_high": max(b["h"] for b in cur), "day_low": min(b["l"] for b in cur)}
    if prev_day:
        pb = [days[prev_day][s] for s in sorted(days[prev_day])]
        lv.update(prev_high=max(b["h"] for b in pb), prev_low=min(b["l"] for b in pb), prev_close=pb[-1]["c"],
                  prev_day=prev_day.isoformat(), gap_pct=round(100 * (cur[0]["o"] / pb[-1]["c"] - 1), 2))
    orb = [b for b in cur if b["slot"] < 3]
    if len(orb) == 3:
        lv.update(or_high=max(b["h"] for b in orb), or_low=min(b["l"] for b in orb))
    out["levels"] = {k2: (round(v, 2) if isinstance(v, float) else v) for k2, v in lv.items()}
    out["atr_5m"] = round(a, 2)
    out["avg_bar_range"] = round(avg_rng, 2)
    out["profile_today"] = profile(cur)
    out["profile_prev_day"] = profile([days[prev_day][s] for s in sorted(days[prev_day])]) if prev_day else None
    # impulse
    imp = []
    for b in cur[-6:]:
        sl = b["slot"]
        samples = [days[d][sl]["v"] for d in past[-hist_days:] if sl in days[d]]
        vx = b["v"] / (sum(samples) / len(samples)) if samples and sum(samples) else None
        rng = b["h"] - b["l"]
        pos = (b["c"] - b["l"]) / rng if rng else 0.5
        big = avg_rng and rng >= 1.5 * avg_rng
        if big and vx and vx >= 2.0 and (pos >= 0.75 or pos <= 0.25):
            imp.append({"bar": hm(sl), "direction": "up" if pos >= 0.75 else "down", "range_x_avg": round(rng / avg_rng, 2),
                        "volume_x": round(vx, 2), "close_in_range": round(pos, 2)})
    out["impulse_last_6_bars"] = imp
    out["note"] = ("Impulse-like = a price-and-volume proxy, not proof of institutional activity. VWAP and profile are "
                   "built from 5-minute bars (approximate; Yahoo's last NSE bar can carry closing-auction volume and skew the previous-day profile). "
                   "No bid/ask or depth data was used.")
    return out


def render(r):
    v = r["vwap"]
    lines = ["%s levels as of %s, price %.2f (%s)" % (r["date"], r["as_of"], r["price"], r["source"]),
             "VWAP %.2f: price is %s it (%+.2f%%, %s ATR), slope over 6 bars %+.2f, %d VWAP crosses today" % (
                 v["value"], v["side"], v["price_vs_vwap_pct"], v["deviation_atr"], v["slope_6_bars"], v["crosses_today"])]
    rv = r["relative_volume"]
    lines.append("Relative volume: %sx so far, last bar %sx its usual (vs %d earlier sessions); %s shares traded" % (
        rv["cumulative_x"], rv["last_bar_x"], rv["compared_with_sessions"], "{:,}".format(rv["volume_so_far"]))
        if rv else "Relative volume: not enough earlier sessions with a full morning")
    l = r["levels"]
    lines.append("Levels: day high %.2f, day low %.2f" % (l["day_high"], l["day_low"]) + (
        "; prev day (%s) high %.2f, low %.2f, close %.2f, gap %+.2f%%" % (l["prev_day"], l["prev_high"], l["prev_low"],
                                                                         l["prev_close"], l["gap_pct"]) if "prev_high" in l else "")
        + ("; opening range %.2f to %.2f" % (l["or_low"], l["or_high"]) if "or_high" in l else ""))
    lines.append("ATR(5m) %.2f, average bar range %.2f" % (r["atr_5m"], r["avg_bar_range"]))
    for key, label in (("profile_today", "Today"), ("profile_prev_day", "Previous day")):
        p = r[key]
        if p:
            lines.append("%s volume profile (approximate): POC %.2f, value area %.2f to %.2f" % (label, p["poc"], p["val"], p["vah"]))
    if r["impulse_last_6_bars"]:
        for i in r["impulse_last_6_bars"]:
            lines.append("IMPULSE-LIKE %s bar %s: range %.1fx average, volume %.1fx usual, closed at %.0f%% of its range" % (
                i["direction"].upper(), i["bar"], i["range_x_avg"], i["volume_x"], 100 * i["close_in_range"]))
    else:
        lines.append("No impulse-like bar in the last 6 bars.")
    lines.append(r["note"])
    return "\n".join(lines)


def parse_now(text):
    if not text:
        return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    try:
        return ist_to_utc(datetime.datetime.fromisoformat(text.strip()))
    except ValueError:
        raise LevelsError('--now wants an IST time like "2026-11-09 10:40"')


def main(argv=None):
    ap = argparse.ArgumentParser(description="VWAP, relative volume, levels, impulse and approximate profile (NSE).")
    ap.add_argument("symbol")
    ap.add_argument("--now", help='IST time to compute as of, e.g. "2026-11-09 10:40"')
    ap.add_argument("--offline", metavar="FILE", help="a saved Yahoo 60d 5m chart JSON")
    ap.add_argument("--days", type=int, default=20, help="earlier sessions for relative volume (20)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        r = compute(fetch(a.symbol, a.offline), parse_now(a.now), a.days)
    except LevelsError as e:
        print("levels.py: %s" % e, file=sys.stderr)
        return 1
    print(json.dumps(r, indent=2) if a.json else render(r))
    return 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    sys.exit(main())
