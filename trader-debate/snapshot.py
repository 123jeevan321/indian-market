#!/usr/bin/env python3
"""Debate STEP 1: one timestamped, provenance-tagged market snapshot shared by the Buyer, Seller and Judge.

    python trader-debate/snapshot.py intraday BAJFINANCE                 # now (IST)
    python trader-debate/snapshot.py intraday BAJFINANCE --now "2026-11-12 10:35"
    python trader-debate/snapshot.py swing BHEL
    python trader-debate/snapshot.py intraday SBIN --no-angel --json

Every field is {"value", "source", "as_of", "class"} with class one of:
  REALTIME     live from the broker feed at snapshot time (Angel One)
  DELAYED      intraday but from a delayed/unofficial feed (Yahoo 5-minute, typically 1-15 minutes behind)
  HISTORICAL   completed earlier sessions (daily bars, previous-day delivery and futures OI)
  UNAVAILABLE  could not be obtained; the reason is in "source". Never filled with a guess.
Read-only: no order function is imported or called.
"""
import argparse, datetime, hashlib, importlib.util, json, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NSE_CACHE = os.path.join(ROOT, "trader", "cache", "nse")
INDUSTRY = os.path.join(ROOT, "trader", "cache", "m15", "industry.json")
M1_CACHE = os.path.join(ROOT, "trader", "cache", "m1")
VERSION = "snapshot-1"


def _load(rel, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


LV = _load("trader-entry/levels.py", "levels")
SW = _load("trader-swing/swing.py", "swing")
SC = _load("trader-scanner/scan.py", "scan")


def ist_now():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=5, minutes=30)


def F(value, source, as_of, cls):
    return {"value": value, "source": source, "as_of": as_of, "class": cls}


def NA(reason):
    return F(None, reason, None, "UNAVAILABLE")


def rnd(x, n=2):
    return round(x, n) if isinstance(x, float) else x


# ---------------------------------------------------------------- shared helpers

def index_5m(now_utc):
    """NIFTY 50 5-minute chart (Yahoo ^NSEI) through levels.compute."""
    url = "https://query2.finance.yahoo.com/v8/finance/chart/%5ENSEI?range=60d&interval=5m"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": LV.UA}), timeout=30) as r:
        return LV.compute(json.loads(r.read().decode("utf-8")), now_utc)


def peers_of(sym):
    try:
        ind = json.load(open(INDUSTRY, encoding="utf-8"))
    except OSError:
        return None, []
    sector = ind.get(sym)
    return sector, sorted(s for s, v in ind.items() if v == sector and s != sym) if sector else []


def sector_strength(sym, asof_ist):
    """Median change vs the previous close of same-industry Nifty 100 peers, using only bars that ended by `asof_ist`
    (5-minute bars for an intraday time, daily closes for a swing date). Unavailable when the stock has no mapped peers."""
    sector, peers = peers_of(sym)
    if not peers:
        return NA("no industry peers mapped for %s (map covers Nifty 100 only)" % sym)
    intraday_t = isinstance(asof_ist, datetime.datetime)
    try:
        data = SC.parse_spark(SC.yahoo_get(SC.spark_path(peers[:20], "5d" if intraday_t else "10d", "5m" if intraday_t else "1d")))
    except Exception as e:
        return NA("Yahoo spark failed for peers: %s" % e)
    chg = []
    for p_, s_ in data.items():
        rows = []
        for t, c in zip(s_["t"], s_["c"]):
            if c is None:
                continue
            ts = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=t + 19800)
            end = ts + datetime.timedelta(minutes=5) if intraday_t else ts
            if (intraday_t and end <= asof_ist) or (not intraday_t and ts.date() <= asof_ist):
                rows.append((ts.date(), c))
        if not rows:
            continue
        today = rows[-1][0]
        prev = [r for r in rows if r[0] < today]
        if prev:
            chg.append(100 * (rows[-1][1] / prev[-1][1] - 1))
    if not chg:
        return NA("no peer data as of %s" % asof_ist)
    chg.sort()
    return F({"sector": sector, "peers": len(chg), "median_change_pct": round(chg[len(chg) // 2], 2),
              "peers_up": sum(1 for c in chg if c > 0)}, "Yahoo spark %s (delayed)" % ("5m" if intraday_t else "1d"),
             str(asof_ist), "DELAYED" if intraday_t else "HISTORICAL")


def nse_file(kind, before):
    """Latest cached NSE delivery/futures file dated strictly before `before` -> (date, {sym: [rows]})."""
    folder = os.path.join(NSE_CACHE, kind)
    try:
        names = sorted(f for f in os.listdir(folder) if f.endswith(".csv") and f[:8] < before.strftime("%Y%m%d"))
    except OSError:
        return None, {}
    for name in reversed(names):
        path = os.path.join(folder, name)
        if os.path.getsize(path) < 10:
            continue
        import csv
        table = {}
        with open(path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                table.setdefault(row.get("sym"), []).append(row)
        if table:
            return datetime.datetime.strptime(name[:8], "%Y%m%d").date(), table
    return None, {}


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def delivery(sym, before, n=20):
    """Previous sessions' delivery % (NSE sec_bhavdata_full cache): last value and its 20-session average."""
    folder = os.path.join(NSE_CACHE, "deliv")
    try:
        names = sorted(f for f in os.listdir(folder) if f.endswith(".csv") and f[:8] < before.strftime("%Y%m%d"))[-n:]
    except OSError:
        return NA("no NSE delivery cache")
    import csv
    series = []
    for name in names:
        with open(os.path.join(folder, name), encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row.get("sym") == sym:
                    series.append((name[:8], num(row.get("deliv_pct")), num(row.get("deliv_qty"))))
                    break
    series = [s for s in series if s[1] is not None]
    if not series:
        return NA("no delivery rows for %s before %s" % (sym, before))
    last = series[-1]
    avg = sum(s[1] for s in series[:-1]) / max(1, len(series) - 1)
    stale = (before - datetime.datetime.strptime(last[0], "%Y%m%d").date()).days > 4
    return F({"last_pct": last[1], "avg_pct_prior": round(avg, 2), "sessions": len(series), "last_date": last[0],
              "stale": stale}, "NSE sec_bhavdata_full (cached; published after each close)", last[0], "HISTORICAL")


def futures(sym, before, close_unadj=None):
    """Previous sessions' total futures OI change (1 and 5 sessions), near-month premium, price/OI build-up label."""
    folder = os.path.join(NSE_CACHE, "fut")
    try:
        names = sorted(f for f in os.listdir(folder) if f.endswith(".csv") and f[:8] < before.strftime("%Y%m%d"))[-7:]
    except OSError:
        return NA("no NSE futures cache")
    import csv
    days = []
    for name in names:
        rows = []
        with open(os.path.join(folder, name), encoding="utf-8") as fh:
            rows = [r for r in csv.DictReader(fh) if r.get("sym") == sym]
        if rows:
            d = datetime.datetime.strptime(name[:8], "%Y%m%d").date()
            oi = sum(num(r["oi"]) or 0 for r in rows)
            near = sorted((r for r in rows if (datetime.date.fromisoformat(r["expiry"]) - d).days >= 3), key=lambda r: r["expiry"])
            n0 = near[0] if near else None
            days.append({"d": d, "oi": oi, "fut": num(n0["close"]) if n0 else None, "und": num(n0["underlying"]) if n0 else None,
                         "dte": (datetime.date.fromisoformat(n0["expiry"]) - d).days if n0 else None})
    if len(days) < 2:
        return NA("%s has no stock futures in the cache (not in F&O, or no data before %s)" % (sym, before))
    a, b = days[-2], days[-1]
    oi1 = b["oi"] / a["oi"] - 1 if a["oi"] else None
    oi5 = b["oi"] / days[max(0, len(days) - 6)]["oi"] - 1 if len(days) >= 6 and days[-6]["oi"] else None
    pr1 = b["und"] / a["und"] - 1 if a["und"] and b["und"] else None
    label = None
    if oi1 is not None and pr1 is not None:
        label = {(True, True): "long build-up", (False, True): "short build-up", (True, False): "short covering",
                 (False, False): "long unwinding"}[(pr1 > 0, oi1 > 0)]
    prem = (b["fut"] / b["und"] - 1) if b["fut"] and b["und"] else None
    return F({"date": b["d"].isoformat(), "oi_change_1d_pct": rnd(100 * oi1) if oi1 is not None else None,
              "oi_change_5d_pct": rnd(100 * oi5) if oi5 is not None else None, "price_change_1d_pct": rnd(100 * pr1) if pr1 else None,
              "buildup": label, "premium_pct": rnd(100 * prem, 3) if prem is not None else None,
              "premium_annualised_pct": rnd(100 * prem / max(3, b["dte"]) * 365) if prem is not None else None},
             "NSE F&O bhavcopy (cached; previous session, published after the close)", b["d"].isoformat(), "HISTORICAL")


def angel_live(sym):
    """Best bid/ask, total buy/sell quantity and the 09:15-09:18 one-minute candles from Angel One (read-only)."""
    try:
        rec = _load("trader-flows/angel_recorder.py", "rec")
        tok = rec.tokens_for([sym]).get(sym)
        if not tok:
            return NA("no Angel token for %s" % sym), NA("no Angel token")
        env = rec.credentials()
        api, _ = rec.session(env)
    except BaseException as e:  # SystemExit from missing credentials included
        return NA("Angel login unavailable: %s" % str(e)[:80]), NA("Angel login unavailable")
    now = ist_now()
    depth = NA("Angel market data failed")
    try:
        r = api.getMarketData("FULL", {"NSE": [tok]})
        q = ((r or {}).get("data") or {}).get("fetched") or []
        if q:
            q = q[0]
            dp = q.get("depth") or {}
            bids = [(x.get("price"), x.get("quantity")) for x in dp.get("buy") or [] if x.get("price")]
            asks = [(x.get("price"), x.get("quantity")) for x in dp.get("sell") or [] if x.get("price")]
            depth = F({"ltp": q.get("ltp"), "best_bid": bids[0] if bids else None, "best_ask": asks[0] if asks else None,
                       "total_buy_qty": q.get("totBuyQuan"), "total_sell_qty": q.get("totSellQuan"),
                       "note": "resting orders; can be cancelled at any time"},
                      "Angel One getMarketData FULL", now.isoformat(timespec="seconds"), "REALTIME")
    except Exception as e:
        depth = NA("Angel market data error: %s" % str(e)[:80])
    opening = NA("before 09:19 IST or Angel candle request failed")
    if now.time() >= datetime.time(9, 19):
        try:
            d = now.strftime("%Y-%m-%d")
            r = api.getCandleData({"exchange": "NSE", "symboltoken": tok, "interval": "ONE_MINUTE",
                                   "fromdate": d + " 09:15", "todate": d + " 09:18"})
            rows = [x for x in (r or {}).get("data") or [] if "09:15" <= x[0][11:16] <= "09:18"]
            if rows:
                opening = F([{"t": x[0][11:16], "o": x[1], "h": x[2], "l": x[3], "c": x[4], "v": x[5]} for x in rows],
                            "Angel One ONE_MINUTE candles", d + " 09:18", "REALTIME")
        except Exception as e:
            opening = NA("Angel candle error: %s" % str(e)[:80])
    try:
        api.terminateSession(env["ANGEL_CLIENT_CODE"])
    except Exception:
        pass
    return depth, opening


def opening_from_cache(sym, day):
    """The 09:15-09:18 one-minute candles for a past day from the Round 10B cache (replays)."""
    path = os.path.join(M1_CACHE, sym.replace("&", "_and_") + ".csv.gz")
    if not os.path.exists(path):
        return NA("no one-minute cache for %s" % sym)
    import csv, gzip
    rows = []
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for r in csv.reader(fh):
            if r[0][:10] == day and "09:15" <= r[0][11:16] <= "09:18":
                rows.append({"t": r[0][11:16], "o": float(r[1]), "h": float(r[2]), "l": float(r[3]), "c": float(r[4]), "v": float(r[5])})
    return F(rows, "Angel One ONE_MINUTE (cached)", day + " 09:18", "HISTORICAL") if rows else NA("no cached candles for %s" % day)


# ---------------------------------------------------------------- intraday

def intraday(sym, now_ist=None, use_angel=True):
    live = now_ist is None
    now_ist = now_ist or ist_now()
    now_utc = now_ist - datetime.timedelta(hours=5, minutes=30)
    day = now_ist.date()
    snap = {"symbol": sym, "mode": "intraday", "snapshot_time_ist": now_ist.isoformat(timespec="seconds"), "version": VERSION, "fields": {}}
    f = snap["fields"]
    try:
        r = LV.compute(LV.fetch(sym), now_utc)
        src = r["source"]
        asof = "%s %s" % (r["date"], r["as_of"][:5])
        lvl = r["levels"]
        f["price"] = F(r["price"], src, asof, "DELAYED")
        f["vwap"] = F(r["vwap"], src, asof, "DELAYED")
        f["relative_volume"] = F(r["relative_volume"], src, asof, "DELAYED") if r["relative_volume"] else NA("fewer than 1 comparable session")
        f["levels"] = F(lvl, src, asof, "DELAYED")
        f["atr_5m"] = F(r["atr_5m"], src, asof, "DELAYED")
        f["profile_today"] = F(r["profile_today"], src, asof, "DELAYED")
        f["impulse_last_6_bars"] = F(r["impulse_last_6_bars"], src, asof, "DELAYED")
        prev_close = lvl.get("prev_close")
        f["day_change_pct"] = F(round(100 * (r["price"] / prev_close - 1), 2) if prev_close else None, src, asof, "DELAYED")
    except Exception as e:
        f["price"] = NA("Yahoo 5-minute data failed: %s" % e)
    try:
        n = index_5m(now_utc)
        pc = n["levels"].get("prev_close")
        f["nifty"] = F({"price": n["price"], "day_change_pct": round(100 * (n["price"] / pc - 1), 2) if pc else None,
                        "vs_vwap": n["vwap"]["side"], "vwap_slope_6_bars": n["vwap"]["slope_6_bars"]},
                       "Yahoo ^NSEI 5m (delayed)", "%s %s" % (n["date"], n["as_of"][:5]), "DELAYED")
    except Exception as e:
        f["nifty"] = NA("NIFTY 5-minute data failed: %s" % e)
    f["sector"] = sector_strength(sym, now_ist)
    f["delivery_prev"] = delivery(sym, day)
    f["futures_prev"] = futures(sym, day)
    if live and use_angel:
        f["depth"], f["opening_1m"] = angel_live(sym)
    else:
        f["depth"] = NA("replay or --no-angel: historical depth does not exist")
        f["opening_1m"] = opening_from_cache(sym, day.isoformat())
    return finish(snap)


# ---------------------------------------------------------------- swing

def adx(b, n=14):
    """Wilder's ADX on daily bars (dicts with h, l, c)."""
    if len(b) < 2 * n + 1:
        return None
    tr, pdm, mdm = [], [], []
    for i in range(1, len(b)):
        up, dn = b[i]["h"] - b[i - 1]["h"], b[i - 1]["l"] - b[i]["l"]
        pdm.append(up if up > dn and up > 0 else 0.0)
        mdm.append(dn if dn > up and dn > 0 else 0.0)
        tr.append(max(b[i]["h"] - b[i]["l"], abs(b[i]["h"] - b[i - 1]["c"]), abs(b[i]["l"] - b[i - 1]["c"])))
    atr, p, m = sum(tr[:n]), sum(pdm[:n]), sum(mdm[:n])
    dx = []
    for i in range(n, len(tr)):
        atr, p, m = atr - atr / n + tr[i], p - p / n + pdm[i], m - m / n + mdm[i]
        pdi, mdi = 100 * p / atr if atr else 0, 100 * m / atr if atr else 0
        dx.append(100 * abs(pdi - mdi) / (pdi + mdi) if pdi + mdi else 0)
    a = sum(dx[:n]) / n
    for x in dx[n:]:
        a = (a * (n - 1) + x) / n
    return round(a, 1), round(pdi, 1), round(mdi, 1)


def weekly(b, n=8):
    wk = {}
    for x in b:
        k = x["d"].isocalendar()[:2]
        w = wk.setdefault(k, {"h": x["h"], "l": x["l"], "c": x["c"], "end": x["d"]})
        w["h"], w["l"], w["c"], w["end"] = max(w["h"], x["h"]), min(w["l"], x["l"]), x["c"], x["d"]
    ws = [wk[k] for k in sorted(wk)][-n:]
    hh = sum(1 for i in range(1, len(ws)) if ws[i]["h"] > ws[i - 1]["h"])
    hl = sum(1 for i in range(1, len(ws)) if ws[i]["l"] > ws[i - 1]["l"])
    return {"weeks": len(ws), "higher_highs": hh, "higher_lows": hl, "last_week_high": round(ws[-1]["h"], 2),
            "last_week_low": round(ws[-1]["l"], 2), "prev_week_high": round(ws[-2]["h"], 2), "prev_week_low": round(ws[-2]["l"], 2)}


def swing(sym, asof=None):
    """Daily snapshot from bars COMPLETED on or before `asof` (default: before today while the market is open, else today)."""
    now = ist_now()
    if asof is None:
        asof = now.date() if now.time() >= datetime.time(15, 35) else now.date() - datetime.timedelta(days=1)
    snap = {"symbol": sym, "mode": "swing", "snapshot_time_ist": now.isoformat(timespec="seconds"),
            "bars_through": asof.isoformat(), "version": VERSION, "fields": {}}
    f = snap["fields"]
    b = [x for x in SW.bars_from(SW.yahoo_daily(sym) or {}) if x["d"] <= asof]
    nb = [x for x in SW.bars_from(SW.yahoo_daily("^NSEI") or {}) if x["d"] <= asof]
    if len(b) < 220 or len(nb) < 220:
        f["price"] = NA("fewer than 220 daily bars (stock %d, NIFTY %d)" % (len(b), len(nb)))
        return finish(snap)
    SW.enrich(b); SW.enrich(nb)
    x, src, d = b[-1], "Yahoo daily (unofficial, adjusted)", b[-1]["d"].isoformat()
    closes = [y["c"] for y in b]
    f["price"] = F(round(x["c"], 2), src, d, "HISTORICAL")
    f["daily"] = F({"open": rnd(x["o"]), "high": rnd(x["h"]), "low": rnd(x["l"]), "close": rnd(x["c"]),
                    "change_pct": rnd(100 * (x["c"] / b[-2]["c"] - 1)), "close_in_range": rnd(SW.pos_in_range(x)),
                    "rvol": rnd(x["rvol"]), "avg_traded_value_cr": rnd(x["avgval"] / 1e7, 1)}, src, d, "HISTORICAL")
    f["trend"] = F({"ema20": rnd(x["e20"]), "ema50": rnd(x["e50"]), "ema200": rnd(x["e200"]), "atr14": rnd(x["atr"]),
                    "rsi14": rnd(SC.rsi(closes[-120:])), "adx14_pdi_mdi": adx(b[-120:]),
                    "ret5_pct": rnd(100 * (x["c"] / b[-6]["c"] - 1)), "ret20_pct": rnd(100 * (x["c"] / b[-21]["c"] - 1)),
                    "high20": rnd(max(y["h"] for y in b[-21:-1])), "low20": rnd(min(y["l"] for y in b[-21:-1])),
                    "high250": rnd(max(y["h"] for y in b[-250:])), "low250": rnd(min(y["l"] for y in b[-250:]))}, src, d, "HISTORICAL")
    f["weekly"] = F(weekly(b), src, d, "HISTORICAL")
    nmap = {y["d"]: y for y in nb}
    if b[-21]["d"] in nmap and x["d"] in nmap:
        rs20 = (x["c"] / b[-21]["c"]) / (nmap[x["d"]]["c"] / nmap[b[-21]["d"]]["c"]) - 1
        rs60 = (x["c"] / b[-61]["c"]) / (nmap[x["d"]]["c"] / nmap[b[-61]["d"]]["c"]) - 1 if b[-61]["d"] in nmap else None
        f["relative_strength"] = F({"rs20_pct": rnd(100 * rs20), "rs60_pct": rnd(100 * rs60) if rs60 is not None else None},
                                   src + " vs ^NSEI", d, "HISTORICAL")
    else:
        f["relative_strength"] = NA("NIFTY bar missing for an aligned date")
    reg = SW.regime_map(nb)
    f["nifty"] = F({"close": rnd(nb[-1]["c"]), "change_pct": rnd(100 * (nb[-1]["c"] / nb[-2]["c"] - 1)),
                    "regime": reg.get(nb[-1]["d"]), "above_ema200": nb[-1]["c"] > nb[-1]["e200"]}, "Yahoo ^NSEI daily", nb[-1]["d"].isoformat(), "HISTORICAL")
    f["sector"] = sector_strength(sym, asof)
    after = asof + datetime.timedelta(days=1)
    f["delivery_prev"] = delivery(sym, after)
    f["futures_prev"] = futures(sym, after)
    return finish(snap)


def finish(snap):
    blob = json.dumps(snap["fields"], sort_keys=True, default=str).encode()
    snap["hash"] = hashlib.sha256(blob).hexdigest()[:16]
    snap["unavailable"] = sorted(k for k, v in snap["fields"].items() if v["class"] == "UNAVAILABLE")
    return snap


def render(snap):
    out = ["%s snapshot %s  %s  hash %s" % (snap["mode"].upper(), snap["symbol"], snap["snapshot_time_ist"], snap["hash"])]
    for k, v in snap["fields"].items():
        val = v["value"] if v["class"] != "UNAVAILABLE" else "-- " + v["source"]
        out.append("  %-20s %-11s %s" % (k, v["class"], json.dumps(val, default=str)[:150]))
    return "\n".join(out)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["intraday", "swing"])
    p.add_argument("symbol")
    p.add_argument("--now", help='replay time "YYYY-MM-DD HH:MM" IST (intraday) or date (swing)')
    p.add_argument("--no-angel", action="store_true")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    sym = a.symbol.upper()
    if a.mode == "intraday":
        now = datetime.datetime.strptime(a.now, "%Y-%m-%d %H:%M") if a.now else None
        s = intraday(sym, now, use_angel=not a.no_angel)
    else:
        s = swing(sym, datetime.date.fromisoformat(a.now[:10]) if a.now else None)
    print(json.dumps(s, indent=1, default=str) if a.json else render(s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
