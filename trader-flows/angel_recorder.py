#!/usr/bin/env python3
"""READ-ONLY Angel One SmartAPI tick + depth recorder, and an order-flow summary of what it recorded.

THIS FILE NEVER PLACES, MODIFIES OR CANCELS AN ORDER. It only logs in, subscribes to market data and writes files.
The tests check that no order method name appears in it.

    pip install smartapi-python pyotp logzero websocket-client     # once (the rest of the project stays stdlib only)
    # credentials ONLY in environment variables (never in chat, files or Git):
    #   ANGEL_API_KEY, ANGEL_CLIENT_CODE, ANGEL_PIN, ANGEL_TOTP_SECRET  (the TOTP secret is the text behind the QR code)
    python3 angel_recorder.py record RELIANCE AXISBANK MCX           # until 15:31 IST, SnapQuote (LTP + best 5 bids/asks)
    python3 angel_recorder.py tokens RELIANCE "M&M"                  # check symbol -> Angel token mapping
    python3 angel_recorder.py flow --date 2026-11-12 AXISBANK        # per-minute delta estimate and book imbalance

What the data is: Angel One's SnapQuote stream (mode 3): last traded price and quantity, cumulative day volume, total buy and
sell quantity, best 5 bid and ask levels, exchange timestamp. Prices arrive in paise and are stored in rupees.

What it is NOT: it is not the exchange's full trade-by-trade feed. A websocket tick is a snapshot; several trades can happen
between two ticks. The buy/sell side of each trade is ESTIMATED (quote rule: at or above the ask = buy, at or below the bid = sell,
otherwise the tick rule), so the "delta" is an estimate. Resting orders in the book can be cancelled at any time, so book imbalance
is a clue, not proof that an institution is buying.

Files: trader/ticks/YYYY-MM-DD/SYMBOL.jsonl (one JSON object per tick). Static-IP rules apply to ORDER APIs only; data and login
do not need a registered IP (per Angel One's 2026 notices; check your account).
"""

import argparse
import datetime
import json
import os
import sys
import time
import urllib.request

MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
OUT = "trader/ticks"
SNAP_QUOTE = 3
MAX_SYMBOLS = 25


def ist_now():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=5.5)


def tokens_for(symbols, cache="trader/cache/angel_master.json"):
    """NSE equity symbols -> {SYMBOL: token} from Angel's public instrument master (cached for a day)."""
    fresh = os.path.exists(cache) and time.time() - os.path.getmtime(cache) < 86400
    if not fresh:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        req = urllib.request.Request(MASTER_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r, open(cache, "wb") as fh:
            fh.write(r.read())
    with open(cache, encoding="utf-8") as fh:
        master = json.load(fh)
    want = {s.upper(): s.upper() + "-EQ" for s in symbols}
    found = {}
    for row in master:
        if row.get("exch_seg") == "NSE" and row.get("symbol") in want.values():
            found[row["symbol"][:-3]] = str(row["token"])
    return found


def split_book(tick):
    """Return (bids, asks) as [(price_rupees, qty, orders)] sorted best first. Side is decided by price (bids below asks),
    because the SDK's buy/sell labels for SnapQuote depth have been inconsistent across versions."""
    a = [(d["price"] / 100.0, d["quantity"], d.get("no of orders", 0)) for d in tick.get("best_5_buy_data") or [] if d.get("price")]
    b = [(d["price"] / 100.0, d["quantity"], d.get("no of orders", 0)) for d in tick.get("best_5_sell_data") or [] if d.get("price")]
    if a and b and sum(p for p, _, _ in a) / len(a) > sum(p for p, _, _ in b) / len(b):
        a, b = b, a                     # a = the lower-priced side = bids
    bids = sorted(a, key=lambda x: -x[0])
    asks = sorted(b, key=lambda x: x[0])
    return bids, asks


def normalise(tick, symbol):
    bids, asks = split_book(tick)
    ts = tick.get("exchange_timestamp")
    return {"symbol": symbol, "recv": ist_now().isoformat(timespec="milliseconds"),
            "exch_ts": ts, "ltp": (tick.get("last_traded_price") or 0) / 100.0, "ltq": tick.get("last_traded_quantity"),
            "ltt": tick.get("last_traded_timestamp"), "volume": tick.get("volume_trade_for_the_day"),
            "tbq": tick.get("total_buy_quantity"), "tsq": tick.get("total_sell_quantity"),
            "bids": bids, "asks": asks, "seq": tick.get("sequence_number")}


def credentials():
    """The four ANGEL_* values from the environment, or (Windows) from the user's saved environment variables when this
    process started before they were set. Values are never printed."""
    keys = ("ANGEL_API_KEY", "ANGEL_CLIENT_CODE", "ANGEL_PIN", "ANGEL_TOTP_SECRET")
    env = {k: os.environ.get(k) for k in keys}
    if not all(env.values()) and sys.platform.startswith("win"):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as reg:
                for k in keys:
                    if not env[k]:
                        try:
                            env[k] = winreg.QueryValueEx(reg, k)[0]
                        except OSError:
                            pass
        except OSError:
            pass
    missing = [k for k, v in env.items() if not v]
    if missing:
        raise SystemExit("set these environment variables first (never paste them in chat): " + ", ".join(missing))
    return env


def session(env):
    import pyotp
    from SmartApi import SmartConnect
    api = SmartConnect(env["ANGEL_API_KEY"])
    sess = api.generateSession(env["ANGEL_CLIENT_CODE"], env["ANGEL_PIN"], pyotp.TOTP(env["ANGEL_TOTP_SECRET"].replace(" ", "")).now())
    if not sess or not sess.get("status"):
        raise SystemExit("Angel One login FAILED: %s (errorcode %s)" % ((sess or {}).get("message") or "no answer",
                                                                    (sess or {}).get("errorcode")))
    return api, sess


def cmd_login(a):
    """Read-only check: log in, read the profile and one LTP, then log out."""
    try:
        import pyotp  # noqa: F401
        from SmartApi import SmartConnect  # noqa: F401
    except ImportError:
        raise SystemExit("install first: pip install smartapi-python pyotp logzero websocket-client")
    env = credentials()
    api, sess = session(env)
    feed = api.getfeedToken()
    name = ""
    try:
        prof = api.getProfile(sess["data"]["refreshToken"])
        name = (prof.get("data") or {}).get("name") or ""
    except Exception:
        pass
    print("LOGIN OK for client %s%s; feed token %s." % (env["ANGEL_CLIENT_CODE"][:2] + "***", (" (" + name.split()[0] + ")") if name else "",
                                                       "received" if feed else "MISSING"))
    try:
        q = api.ltpData("NSE", "RELIANCE-EQ", tokens_for(["RELIANCE"]).get("RELIANCE", "2885"))
        if q and q.get("status"):
            print("Market data OK: RELIANCE LTP %s (Angel One, %s IST)." % (q["data"].get("ltp"), ist_now().strftime("%Y-%m-%d %H:%M")))
        else:
            print("Market data call answered: %s" % (q or {}).get("message"))
    except Exception as e:
        print("Market data call failed: %s" % e)
    try:
        api.terminateSession(env["ANGEL_CLIENT_CODE"])
        print("Logged out. Nothing was ordered (this tool has no order calls).")
    except Exception:
        pass
    return 0


def cmd_record(a):
    try:
        import pyotp
        from SmartApi import SmartConnect
        from SmartApi.smartWebSocketV2 import SmartWebSocketV2
    except ImportError:
        raise SystemExit("install first: pip install smartapi-python pyotp logzero websocket-client")
    env = credentials()
    syms = [s.upper() for s in a.symbols][:MAX_SYMBOLS]
    toks = tokens_for(syms)
    unknown = [s for s in syms if s not in toks]
    if unknown:
        print("not found in Angel's NSE equity master, skipped: " + ", ".join(unknown))
    if not toks:
        raise SystemExit("no symbols to record")
    by_token = {v: k for k, v in toks.items()}

    api, sess = session(env)
    jwt = sess["data"]["jwtToken"]
    feed = api.getfeedToken()
    day = ist_now().date().isoformat()
    folder = os.path.join(a.out, day)
    os.makedirs(folder, exist_ok=True)
    files = {s: open(os.path.join(folder, s + ".jsonl"), "a", encoding="utf-8") for s in toks}
    stop_at = datetime.datetime.combine(ist_now().date(), datetime.time(15, 31))
    count = {"n": 0}
    ws = SmartWebSocketV2(jwt, env["ANGEL_API_KEY"], env["ANGEL_CLIENT_CODE"], feed)

    def on_open(wsapp):
        ws.subscribe("rec1", SNAP_QUOTE, [{"exchangeType": 1, "tokens": list(toks.values())}])
        print("recording %d symbols (SnapQuote) to %s until 15:31 IST: %s" % (len(toks), folder, ", ".join(toks)))

    def on_data(wsapp, msg):
        sym = by_token.get(str(msg.get("token")))
        if not sym:
            return
        files[sym].write(json.dumps(normalise(msg, sym)) + "\n")
        count["n"] += 1
        if count["n"] % 500 == 0:
            for f in files.values():
                f.flush()
        if ist_now() >= stop_at:
            ws.close_connection()

    def on_error(wsapp, err):
        print("websocket error: %s" % err, file=sys.stderr)

    def on_close(wsapp):
        for f in files.values():
            f.close()
        print("closed after %d ticks" % count["n"])

    ws.on_open, ws.on_data, ws.on_error, ws.on_close = on_open, on_data, on_error, on_close
    ws.connect()
    return 0


def side_of(t, prev):
    """Estimated aggressor side of the volume traded since the previous tick: +1 buy, -1 sell, 0 unknown."""
    if t["bids"] and t["asks"] and prev and prev["bids"] and prev["asks"]:
        bid, ask = prev["bids"][0][0], prev["asks"][0][0]        # the quote standing BEFORE the trade
        if t["ltp"] >= ask:
            return 1
        if t["ltp"] <= bid:
            return -1
    if prev and t["ltp"] > prev["ltp"]:
        return 1
    if prev and t["ltp"] < prev["ltp"]:
        return -1
    return 0


def flow(ticks):
    """Per-minute summary: traded volume, estimated buy/sell volume, estimated delta and cumulative delta, top-5 book imbalance."""
    rows, prev, cum, last_side = {}, None, 0, 0
    for t in ticks:
        if prev is None or t["volume"] is None or prev["volume"] is None:
            prev = t
            continue
        dv = max(0, t["volume"] - prev["volume"])
        s = side_of(t, prev) or last_side
        last_side = s or last_side
        minute = t["recv"][11:16]
        r = rows.setdefault(minute, {"minute": minute, "vol": 0, "buy": 0, "sell": 0, "unknown": 0, "imb": [], "close": t["ltp"]})
        r["vol"] += dv
        r["close"] = t["ltp"]
        if s > 0:
            r["buy"] += dv
        elif s < 0:
            r["sell"] += dv
        else:
            r["unknown"] += dv
        bq, aq = sum(q for _, q, _ in t["bids"]), sum(q for _, q, _ in t["asks"])
        if bq + aq:
            r["imb"].append((bq - aq) / float(bq + aq))
        prev = t
    out = []
    for m in sorted(rows):
        r = rows[m]
        cum += r["buy"] - r["sell"]
        out.append({"minute": m, "close": r["close"], "volume": r["vol"], "est_buy": r["buy"], "est_sell": r["sell"],
                    "unclassified": r["unknown"], "est_delta": r["buy"] - r["sell"], "est_cum_delta": cum,
                    "book_imbalance_top5": round(sum(r["imb"]) / len(r["imb"]), 3) if r["imb"] else None})
    return out


def cmd_flow(a):
    path = os.path.join(a.out, a.date, a.symbol.upper() + ".jsonl")
    if not os.path.exists(path):
        raise SystemExit("no recording at %s (run: angel_recorder.py record %s)" % (path, a.symbol.upper()))
    with open(path, encoding="utf-8") as fh:
        ticks = [json.loads(ln) for ln in fh if ln.strip()]
    rows = flow(ticks)
    if a.json:
        print(json.dumps(rows, indent=2))
        return 0
    print("%s %s: %d ticks. ESTIMATED aggressor side (quote rule, then tick rule); imbalance = (bid qty - ask qty) / total, top 5 levels." % (
        a.symbol.upper(), a.date, len(ticks)))
    print("  time   close     volume   est buy  est sell   est delta  cum delta  book imb")
    for r in rows[-a.last:]:
        print("  %s %9.2f %10s %9s %9s %11s %10s %9s" % (r["minute"], r["close"], "{:,}".format(r["volume"]), "{:,}".format(r["est_buy"]),
                                                         "{:,}".format(r["est_sell"]), "{:+,}".format(r["est_delta"]),
                                                         "{:+,}".format(r["est_cum_delta"]),
                                                         r["book_imbalance_top5"] if r["book_imbalance_top5"] is not None else "-"))
    print("Estimates from websocket snapshots, not the exchange's trade-by-trade tape. Resting orders can be cancelled.")
    return 0


def cmd_tokens(a):
    toks = tokens_for(a.symbols)
    for s in a.symbols:
        print("%-12s %s" % (s.upper(), toks.get(s.upper(), "NOT FOUND")))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Read-only Angel One tick/depth recorder (never places orders).")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("record"); p.set_defaults(fn=cmd_record); p.add_argument("symbols", nargs="+"); p.add_argument("--out", default=OUT)
    p = sub.add_parser("login"); p.set_defaults(fn=cmd_login)
    p = sub.add_parser("tokens"); p.set_defaults(fn=cmd_tokens); p.add_argument("symbols", nargs="+")
    p = sub.add_parser("flow"); p.set_defaults(fn=cmd_flow); p.add_argument("symbol"); p.add_argument("--date", default=ist_now().date().isoformat())
    p.add_argument("--out", default=OUT); p.add_argument("--last", type=int, default=30); p.add_argument("--json", action="store_true")
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
