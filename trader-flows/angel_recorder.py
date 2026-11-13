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


STALL_S = 60  # seconds without any packet in market hours before a forced reconnect


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


def quiet_sdk_logs():
    """The SmartApi SDK logs FULL request headers (API key + bearer token) on any request error, to stderr and to logs/<date>/app.log.
    Silence it: our own code reports errors without secrets."""
    import logging
    try:
        import logzero
        logzero.logfile(None)
        logzero.loglevel(logging.CRITICAL + 10)
        logzero.logger.disabled = True
    except ImportError:
        pass
    for name in ("SmartApi", "SmartApi.smartConnect", "SmartApi.smartWebSocketV2"):
        logging.getLogger(name).setLevel(logging.CRITICAL + 10)


def session(env):
    import pyotp
    from SmartApi import SmartConnect
    api = SmartConnect(env["ANGEL_API_KEY"])
    quiet_sdk_logs()                                   # after construction: SmartConnect() re-attaches its log file
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
    """Round 10 recorder (v2): token + exchange on every row, exchange timestamp and local receive time, de-duplication of repeated
    packets, flush every 2 seconds, automatic re-login and re-subscribe after a disconnect, and a session log of every connect,
    disconnect and gap so missing data is visible. Writes only market data; never touches orders."""
    try:
        import pyotp  # noqa: F401
        from SmartApi.smartWebSocketV2 import SmartWebSocketV2
    except ImportError:
        raise SystemExit("install first: pip install smartapi-python pyotp logzero websocket-client")
    import threading
    env = credentials()
    syms = [s.upper() for s in a.symbols][:MAX_SYMBOLS]
    toks = tokens_for(syms)
    unknown = [s for s in syms if s not in toks]
    if unknown:
        print("not found in Angel's NSE equity master, skipped: " + ", ".join(unknown), flush=True)
    if not toks:
        raise SystemExit("no symbols to record")
    by_token = {v: k for k, v in toks.items()}
    day = ist_now().date()
    folder = os.path.join(a.out, day.isoformat())
    os.makedirs(folder, exist_ok=True)
    files = {s: open(os.path.join(folder, s + ".jsonl"), "a", encoding="utf-8") for s in toks}
    log = open(os.path.join(folder, "_session.log"), "a", encoding="utf-8")
    stop_at = datetime.datetime.combine(day, datetime.time(*map(int, a.until.split(":"))))
    state = {"n": 0, "dupes": 0, "last": {}, "last_flush": time.time(), "last_tick": None, "stop": False}
    lock = threading.Lock()

    def note(msg):
        line = "%s %s" % (ist_now().isoformat(timespec="milliseconds"), msg)
        log.write(line + "\n"); log.flush()
        print(line, flush=True)

    def on_data(wsapp, msg):
        sym = by_token.get(str(msg.get("token")))
        if not sym:
            return
        key = (msg.get("exchange_timestamp"), msg.get("last_traded_price"), msg.get("volume_trade_for_the_day"),
               msg.get("total_buy_quantity"), msg.get("total_sell_quantity"))
        with lock:
            if state["last"].get(sym) == key:
                state["dupes"] += 1
                return
            state["last"][sym] = key
            row = normalise(msg, sym)
            row.update(token=str(msg.get("token")), exchange="NSE", mode=msg.get("subscription_mode"))
            files[sym].write(json.dumps(row) + "\n")
            state["n"] += 1
            now = time.time()
            if gap_check(now):
                pass
            state["last_tick"] = now
            if now - state["last_flush"] >= 2.0:
                for f in files.values():
                    f.flush()
                state["last_flush"] = now

    def gap_check(now):
        if state["last_tick"] and now - state["last_tick"] > 30:
            note("GAP: no packets for %.0f s" % (now - state["last_tick"]))
        return False

    attempts = 0
    while ist_now() < stop_at and attempts < a.max_reconnects:
        attempts += 1
        try:
            api, sess = session(env)
            ws = SmartWebSocketV2(sess["data"]["jwtToken"], env["ANGEL_API_KEY"], env["ANGEL_CLIENT_CODE"], api.getfeedToken(),
                                  max_retry_attempt=3, retry_delay=5)
        except (SystemExit, Exception) as e:            # network errors too: never let a failed re-login end the day's recording
            note("LOGIN FAILED (attempt %d): %s: %s" % (attempts, type(e).__name__, str(e)[:120]))
            time.sleep(20)
            continue

        def on_open(wsapp, ws=ws):
            ws.subscribe("r10", SNAP_QUOTE, [{"exchangeType": 1, "tokens": list(toks.values())}])
            note("CONNECTED (attempt %d), subscribed %d symbols SnapQuote: %s" % (attempts, len(toks), ",".join(toks)))

        def on_error(wsapp, err):
            note("ERROR %s" % err)

        def on_close(wsapp):
            note("DISCONNECTED after %d rows" % state["n"])

        ws.on_open, ws.on_data, ws.on_error, ws.on_close = on_open, on_data, on_error, on_close
        t = threading.Thread(target=ws.connect, daemon=True)
        t.start()
        stalled = False
        while t.is_alive() and ist_now() < stop_at:
            time.sleep(1)
            n_ = ist_now().time()
            # Watchdog: in market hours a silent socket (no packets for STALL_S seconds) is torn down and rebuilt with a fresh
            # login. On 2026-11-12 the SDK kept a dead socket open from 09:13 to 09:52 without raising any error.
            if datetime.time(9, 16) <= n_ <= datetime.time(15, 29) and state["last_tick"] and time.time() - state["last_tick"] > STALL_S:
                note("STALL: no packets for %.0f s in market hours; forcing a fresh login" % (time.time() - state["last_tick"]))
                stalled = True
                try:
                    ws.close_connection()
                except Exception:
                    pass
                state["last_tick"] = time.time()
                break
        if ist_now() >= stop_at:
            try:
                ws.close_connection()
            except Exception:
                pass
            break
        note("%s; reconnecting in 5 s" % ("stalled socket closed" if stalled else "connection thread ended"))
        time.sleep(5)
    with lock:
        for f in files.values():
            f.flush(); f.close()
    note("STOPPED: %d rows written, %d duplicate packets skipped, %d connection attempts" % (state["n"], state["dupes"], attempts))
    log.close()
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



def cmd_quality(a):
    """Per-day data-quality report for a recording folder: rows, update rate, gaps, clock offset, crossed books, session events."""
    folder = os.path.join(a.out, a.date)
    if not os.path.isdir(folder):
        raise SystemExit("no recording folder %s" % folder)
    print("Recording %s" % folder)
    print("  %-11s %8s %9s %10s %12s %14s %8s %12s" % ("symbol", "rows", "rows/min", "gaps>30s", "max gap s", "clock offs ms", "crossed", "missing min"))
    for f in sorted(os.listdir(folder)):
        if not f.endswith(".jsonl"):
            continue
        ticks = [json.loads(ln) for ln in open(os.path.join(folder, f), encoding="utf-8") if ln.strip()]
        if not ticks:
            continue
        recv = [datetime.datetime.fromisoformat(t["recv"]) for t in ticks]
        mkt = [r for r in recv if datetime.time(9, 15) <= r.time() <= datetime.time(15, 30)]
        day = recv[0].date()
        # Count the session edges too: a late first packet or an early last one is a gap (missed in v2 of this report).
        edges = [datetime.datetime.combine(day, datetime.time(9, 15))] + mkt + [datetime.datetime.combine(day, datetime.time(15, 30))]
        gaps = [(b - a_).total_seconds() for a_, b in zip(edges, edges[1:])]
        missing = sum(g for g in gaps if g > 60)
        offs = []
        for t, r in zip(ticks, recv):
            if t.get("exch_ts"):
                ex = datetime.datetime(1970, 1, 1) + datetime.timedelta(milliseconds=t["exch_ts"]) + datetime.timedelta(hours=5.5)
                offs.append((r - ex).total_seconds() * 1000)
        crossed = sum(1 for t in ticks if t["bids"] and t["asks"] and t["bids"][0][0] >= t["asks"][0][0])
        mins = 375.0 - missing / 60
        print("  %-11s %8d %9.1f %10d %12.0f %14.0f %8d %12.1f" % (f[:-6], len(ticks), len(mkt) / max(1.0, mins),
              sum(1 for g in gaps if g > 30), max(gaps) if gaps else 0, sorted(offs)[len(offs) // 2] if offs else 0, crossed, missing / 60))
    log = os.path.join(folder, "_session.log")
    if os.path.exists(log):
        print("Session log:")
        for ln in open(log, encoding="utf-8"):
            print("  " + ln.rstrip())
    return 0



def main(argv=None):
    ap = argparse.ArgumentParser(description="Read-only Angel One tick/depth recorder (never places orders).")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("record"); p.set_defaults(fn=cmd_record); p.add_argument("symbols", nargs="+"); p.add_argument("--out", default=OUT)
    p.add_argument("--until", default="15:31", help="IST stop time HH:MM"); p.add_argument("--max-reconnects", type=int, default=30)
    p = sub.add_parser("login"); p.set_defaults(fn=cmd_login)
    p = sub.add_parser("quality"); p.set_defaults(fn=cmd_quality)
    p.add_argument("--date", default=ist_now().date().isoformat()); p.add_argument("--out", default="trader/ticks_r10")
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

