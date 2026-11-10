#!/usr/bin/env python3
"""Delivery and participation context for trader-flows (NSE India). Standard library only.

What it can and cannot tell you. NSE publishes, free and after the close, the full "bhavcopy with
delivery position" file: for every stock, the day's OHLC, traded quantity, traded value, number of
trades, DELIVERED quantity and delivery %. That is genuine, official, end-of-day data. From it this
tool shows how a stock's delivery % and volume compare with its own recent days.

It is a CONTEXT tool, not an order-flow tool:
  - It says nothing about intraday bid/ask aggression, depth, footprint or CVD: NSE's free files do not
    contain them, and neither does Yahoo's bar data.
  - A high delivery % means more of the day's volume was taken home instead of squared off intraday.
    It is a proxy for conviction, never proof that an institution bought or sold.

    python3 flows.py delivery RELIANCE TCS --days 10        # one line per stock per day
    python3 flows.py screen --top 20 --min-turnover 100      # liquid names with unusual delivery / volume
    python3 flows.py fii-dii                                 # FII/FPI and DII cash-market net, if NSE answers
    python3 flows.py deals --min-value 500                   # latest bulk + block deals (archives bulk.csv / block.csv)
    python3 flows.py deals RELIANCE INFY --kind bulk
    python3 flows.py delivery INFY --offline tests/fixtures/trader-flows   # saved files, no network

The bhavcopy URL is https://archives.nseindia.com/products/content/sec_bhavdata_full_DDMMYYYY.csv. Files
exist for trading days only, and appear in the evening. Downloaded files are cached in trader/cache/.
The FII/DII table comes from NSE's website API (unofficial; NSE may refuse scripted access, and then this
tool says so and you paste the numbers from nseindia.com/reports/fii-dii instead).
"""

import argparse
import csv
import datetime
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (compatible; india-equity-intraday-skill/1.0)"
URL = "https://archives.nseindia.com/products/content/sec_bhavdata_full_%s.csv"
CACHE = "trader/cache"
PAUSE = 0.5
SLEEP = time.sleep


class FlowError(Exception):
    pass


def ist_today(now_utc=None):
    now_utc = now_utc or datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    return (now_utc + datetime.timedelta(hours=5.5)).date()


def stamp(d):
    return d.strftime("%d%m%Y")


def fetch_day(d, offline=None, cache=CACHE, pause=PAUSE):
    """The bhavcopy text for one date, or None when there is no file (weekend, holiday, not yet out)."""
    name = "sec_bhavdata_full_%s.csv" % stamp(d)
    folders = [offline] if offline else [cache]
    for f in folders:
        p = os.path.join(f, name)
        if f and os.path.isfile(p):
            with open(p, encoding="utf-8", errors="replace") as fh:
                return fh.read()
    if offline:
        return None
    SLEEP(pause)
    try:
        req = urllib.request.Request(URL % stamp(d), headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=40) as r:
            text = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        e.close()
        if e.code in (403, 404):
            return None
        raise FlowError("archives.nseindia.com answered HTTP %d for %s" % (e.code, d))
    except (urllib.error.URLError, OSError) as e:
        raise FlowError("could not reach archives.nseindia.com: %s" % getattr(e, "reason", e))
    if not text.startswith("SYMBOL"):
        return None
    os.makedirs(cache, exist_ok=True)
    with open(os.path.join(cache, name), "w", encoding="utf-8") as fh:
        fh.write(text)
    return text


def parse_bhav(text):
    """-> {SYMBOL: row} for the EQ series only."""
    out = {}
    rdr = csv.reader(io.StringIO(text))
    hdr = [h.strip() for h in next(rdr)]
    for row in rdr:
        if len(row) != len(hdr):
            continue
        r = dict(zip(hdr, [c.strip() for c in row]))
        if r.get("SERIES") != "EQ":
            continue
        out[r["SYMBOL"].upper()] = r
    return out


def num(x):
    try:
        return float(str(x).replace(",", ""))
    except ValueError:
        return None


def trading_files(n, end=None, offline=None, max_back=40, pause=PAUSE):
    """[(date, {symbol: row})] newest first, n files, walking back over weekends and holidays."""
    d = end or ist_today()
    out, back = [], 0
    while len(out) < n and back < max_back:
        if d.weekday() < 5:
            text = fetch_day(d, offline, pause=pause)
            table = parse_bhav(text) if text else {}
            # NSE posts a copy of the previous session under a holiday's date: trust the DATE1 column, not the file name
            stamp_in_file = next((r.get("DATE1") for r in table.values()), None)
            if table and stamp_in_file:
                try:
                    if datetime.datetime.strptime(stamp_in_file, "%d-%b-%Y").date() != d:
                        table = {}
                except ValueError:
                    pass
            if table:
                out.append((d, table))
        d -= datetime.timedelta(days=1)
        back += 1
    return out


def delivery_rows(symbols, days, files):
    rows = []
    for sym in symbols:
        series = []
        for d, table in files:
            r = table.get(sym)
            if not r:
                continue
            series.append({"date": d.isoformat(), "close": num(r.get("CLOSE_PRICE")), "prev_close": num(r.get("PREV_CLOSE")),
                           "volume": num(r.get("TTL_TRD_QNTY")), "turnover_lacs": num(r.get("TURNOVER_LACS")),
                           "trades": num(r.get("NO_OF_TRADES")), "deliv_qty": num(r.get("DELIV_QTY")),
                           "deliv_pct": num(r.get("DELIV_PER"))})
        rows.append((sym, series))
    return rows


def avg(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def cmd_delivery(a):
    syms = [s.upper() for s in a.symbols]
    files = trading_files(a.days, offline=a.offline, pause=a.pause)
    if not files:
        raise FlowError("no bhavcopy files found (the newest appears in the evening; use --offline DIR for saved files)")
    out = []
    for sym, series in delivery_rows(syms, a.days, files):
        if not series:
            out.append({"symbol": sym, "error": "not in the EQ series of these files"})
            continue
        latest, rest = series[0], series[1:]
        dp, vol = avg([x["deliv_pct"] for x in rest]), avg([x["volume"] for x in rest])
        out.append({"symbol": sym, "days": series,
                    "latest_vs_average": {
                        "delivery_pct": latest["deliv_pct"], "avg_delivery_pct": round(dp, 2) if dp else None,
                        "volume_x": round(latest["volume"] / vol, 2) if vol and latest["volume"] else None}})
    if a.json:
        print(json.dumps(out, indent=2))
        return 0
    for item in out:
        if "error" in item:
            print("%s: %s" % (item["symbol"], item["error"]))
            continue
        print("%s  (delivery %% = share of the day's traded quantity that was delivered, NSE official, end of day)" % item["symbol"])
        print("  %-10s %9s %8s %12s %10s" % ("date", "close", "chg %", "volume", "deliv %"))
        for x in item["days"]:
            chg = 100.0 * (x["close"] / x["prev_close"] - 1) if x["close"] and x["prev_close"] else None
            print("  %-10s %9.2f %8s %12s %10s" % (
                x["date"], x["close"] or 0, ("%+.2f" % chg) if chg is not None else "-",
                "{:,.0f}".format(x["volume"] or 0), ("%.1f" % x["deliv_pct"]) if x["deliv_pct"] is not None else "-"))
        lv = item["latest_vs_average"]
        print("  latest delivery %s%% vs %s%% average of the earlier days; volume %sx its average." % (
            lv["delivery_pct"], lv["avg_delivery_pct"], lv["volume_x"]))
    print("Context only: delivery % is a proxy for conviction, not proof of institutional buying or selling.")
    return 0


def cmd_screen(a):
    files = trading_files(a.days + 1, offline=a.offline, pause=a.pause)
    if len(files) < 2:
        raise FlowError("need at least 2 bhavcopy files; found %d" % len(files))
    (d0, today), rest = files[0], files[1:]
    rows = []
    allowed = None
    if a.universe and os.path.isfile(a.universe):
        with open(a.universe, encoding="utf-8") as fh:
            allowed = {ln.split("|")[0].strip().upper() for ln in fh if ln.strip() and not ln.startswith("#")}
    for sym, r in today.items():
        if allowed is not None and sym not in allowed:
            continue
        if allowed is None and any(k in sym for k in ("ETF", "BEES", "IETF", "GOLD", "LIQUID", "NIFTY", "SENSEX")):
            continue      # funds are not the stocks this pack trades; pass --universe to be exact
        to = num(r.get("TURNOVER_LACS"))
        dp = num(r.get("DELIV_PER"))
        vol = num(r.get("TTL_TRD_QNTY"))
        if to is None or to < a.min_turnover or dp is None or vol is None:
            continue
        hist = [t[sym] for _, t in rest if sym in t]
        if len(hist) < max(2, a.days // 2):
            continue
        avg_v = avg([num(h.get("TTL_TRD_QNTY")) for h in hist])
        avg_d = avg([num(h.get("DELIV_PER")) for h in hist])
        if not avg_v or avg_d is None:
            continue
        pc, cl = num(r.get("PREV_CLOSE")), num(r.get("CLOSE_PRICE"))
        rows.append({"symbol": sym, "close": cl, "chg_pct": round(100.0 * (cl / pc - 1), 2) if pc and cl else None,
                     "turnover_lacs": to, "volume_x": round(vol / avg_v, 2), "deliv_pct": dp,
                     "avg_deliv_pct": round(avg_d, 1), "deliv_delta": round(dp - avg_d, 1)})
    rows.sort(key=lambda x: -(x["volume_x"] * max(x["deliv_delta"], 0.1)))
    rows = rows[:a.top]
    if a.json:
        print(json.dumps({"date": d0.isoformat(), "compared_with_days": len(rest), "rows": rows}, indent=2))
        return 0
    print("Liquid stocks (turnover >= %s lakh) ranked by volume vs its %d-day average and delivery %% vs its average, %s:" % (
        a.min_turnover, len(rest), d0.isoformat()))
    print("  %-12s %10s %7s %12s %8s %8s %8s %8s" % ("symbol", "close", "chg %", "turnover L", "vol x", "deliv %", "avg %", "delta"))
    for x in rows:
        print("  %-12s %10.2f %7s %12s %8.2f %8.1f %8.1f %+8.1f" % (
            x["symbol"], x["close"] or 0, ("%+.2f" % x["chg_pct"]) if x["chg_pct"] is not None else "-",
            "{:,.0f}".format(x["turnover_lacs"]), x["volume_x"], x["deliv_pct"], x["avg_deliv_pct"], x["deliv_delta"]))
    print("These are end-of-day leads for tomorrow's watchlist. High delivery + high volume + a rising price MAY mean accumulation; "
          "it may also be news. Check the announcements before you act.")
    return 0 if rows else 1


DEALS = {"bulk": "https://archives.nseindia.com/content/equities/bulk.csv",
         "block": "https://archives.nseindia.com/content/equities/block.csv"}


def fetch_deals(kind, offline=None):
    if offline:
        p = os.path.join(offline, "%s.csv" % kind)
        if not os.path.isfile(p):
            raise FlowError("no %s.csv in %s" % (kind, offline))
        with open(p, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    SLEEP(PAUSE)
    try:
        req = urllib.request.Request(DEALS[kind], headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        e.close()
        raise FlowError("archives.nseindia.com answered HTTP %d for %s deals" % (e.code, kind))
    except (urllib.error.URLError, OSError) as e:
        raise FlowError("could not reach archives.nseindia.com: %s" % getattr(e, "reason", e))


def parse_deals(text, kind):
    rows = []
    for r in csv.DictReader(io.StringIO(text.lstrip("\ufeff"))):
        r = {(k or "").strip(): (v or "").strip() for k, v in r.items()}
        try:
            qty = float(r.get("Quantity Traded", "0").replace(",", ""))
            px = float(r.get("Trade Price / Wght. Avg. Price", "0").replace(",", ""))
        except ValueError:
            continue
        rows.append({"kind": kind, "date": r.get("Date"), "symbol": r.get("Symbol", "").upper(), "client": r.get("Client Name"),
                     "side": r.get("Buy/Sell", "").upper(), "qty": qty, "price": px, "value_lacs": round(qty * px / 1e5, 1)})
    return rows


def cmd_deals(a):
    rows = []
    for kind in (["bulk", "block"] if a.kind == "both" else [a.kind]):
        rows += parse_deals(fetch_deals(kind, a.offline), kind)
    if a.symbols:
        want = {s.upper() for s in a.symbols}
        rows = [r for r in rows if r["symbol"] in want]
    rows = [r for r in rows if r["value_lacs"] >= a.min_value]
    rows.sort(key=lambda r: -r["value_lacs"])
    if a.json:
        print(json.dumps(rows[:a.top], indent=2))
        return 0
    if not rows:
        print("No bulk/block deals matched.")
        return 1
    print("NSE bulk / block deals (official, published AFTER the trades; the file's date is the trade date):")
    for r in rows[:a.top]:
        print("  %-10s %-5s %-5s %-10s %12s @ %9.2f = Rs %s lakh  %s" % (
            r["date"], r["kind"], r["side"], r["symbol"], "{:,.0f}".format(r["qty"]), r["price"], "{:,.0f}".format(r["value_lacs"]),
            (r["client"] or "")[:44]))
    print("TIMING WARNING: a deal is published after it is done (bulk deals end of day, block deals the same evening). By the time you "
          "can see it the price has usually moved, so it is NEXT-DAY CONTEXT, not a 5-10 minute trigger. The buyer can be a fund, a "
          "trader or an arbitrage desk; a block pair (same quantity, same price, buyer and seller) is often a transfer. Never claim "
          "the 'institution' will keep buying.")
    return 0


def cmd_fii_dii(a):
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "..", "trader-news", "nse_client.py")
    if not os.path.exists(path):
        raise FlowError("trader-news/nse_client.py not found next to this skill")
    spec = importlib.util.spec_from_file_location("nse_client", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        doc = mod.NseClient(offline=a.offline).get_json("/api/fiidiiTradeReact", "fiidiiTradeReact.json")
    except mod.NseError as e:
        raise FlowError("%s\nPaste the latest FII/DII figures from https://www.nseindia.com/reports/fii-dii instead." % e)
    if a.json:
        print(json.dumps(doc, indent=2))
        return 0
    print("NSE provisional FII/FPI and DII cash-market activity (Rs crore). Source: nseindia.com, as published:")
    for r in doc:
        print("  %-8s %s  buy %12s  sell %12s  net %12s" % (r.get("category"), r.get("date"), r.get("buyValue"),
                                                           r.get("sellValue"), r.get("netValue")))
    print("Provisional, end of day, published after the close. Say the date and the source whenever you quote it.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Delivery and participation context (trader-flows, NSE India).")
    sub = ap.add_subparsers(dest="cmd")
    for name, fn, h in (("delivery", cmd_delivery, "delivery % and volume by day for some stocks"),
                        ("screen", cmd_screen, "liquid stocks with unusual volume / delivery"),
                        ("fii-dii", cmd_fii_dii, "FII/FPI and DII net cash-market activity"),
                        ("deals", cmd_deals, "NSE bulk and block deals (published after the trade)")):
        p = sub.add_parser(name, help=h)
        p.set_defaults(fn=fn)
        p.add_argument("--offline", metavar="DIR", help="read saved files from DIR instead of the network")
        p.add_argument("--json", action="store_true")
        p.add_argument("--pause", type=float, default=PAUSE)
        if name == "delivery":
            p.add_argument("symbols", nargs="+")
            p.add_argument("--days", type=int, default=10)
        if name == "deals":
            p.add_argument("symbols", nargs="*")
            p.add_argument("--kind", choices=["bulk", "block", "both"], default="both")
            p.add_argument("--min-value", type=float, default=100.0, help="deal value in lakh rupees (default 100 = Rs 1 crore)")
            p.add_argument("--top", type=int, default=25)
        if name == "screen":
            p.add_argument("--days", type=int, default=10, help="days to average over")
            p.add_argument("--top", type=int, default=20)
            p.add_argument("--min-turnover", type=float, default=100.0, help="lakh rupees traded (default 100 = Rs 1 crore)")
            p.add_argument("--universe", default="trader/universe.txt", help="only these symbols (default trader/universe.txt if it exists; run scan.py universe)")
    a = ap.parse_args(argv)
    if not getattr(a, "fn", None):
        ap.print_help()
        return 1
    try:
        return a.fn(a)
    except FlowError as e:
        print("flows.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):  # the rupee sign on a Windows console
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    sys.exit(main())
