#!/usr/bin/env python3
"""Round 10B: NSE opening-window (09:15-09:18) research. Read-only data access; no orders.

    python research/round10_open.py fetch      # Angel One ONE_MINUTE candles, Nifty 100, 5 years -> trader/cache/m1/
    python research/round10_open.py coverage   # exact per-stock / per-year coverage report

Storage per stock (gzip CSV): 1-minute bars 09:15-11:14, then 5-minute bars 11:15-15:29 built from the same 1-minute data
(keeps 171 rows a day instead of 375; exits after 11:15 are resolved on 5-minute bars with the stop-first rule).
"""
import csv, datetime, gzip, importlib.util, io, json, os, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "trader", "cache", "m1")
UNIVERSE = os.path.join(ROOT, "trader", "cache", "m15", "industry.json")


def _rec():
    spec = importlib.util.spec_from_file_location("rec", os.path.join(ROOT, "trader-flows", "angel_recorder.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def ist_now():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=5, minutes=30)


def compress(rows):
    """1-minute rows [ts,o,h,l,c,v] -> 1-minute until 11:14, 5-minute buckets from 11:15."""
    out, bucket = [], None
    for ts, o, h, l, c, v in rows:
        t = ts[11:16]
        if t < "11:15":
            out.append([ts[:16], o, h, l, c, v]); continue
        hh, mm = int(t[:2]), int(t[3:])
        key = ts[:11] + "%02d:%02d" % (hh, mm - mm % 5)
        if bucket and bucket[0] == key:
            bucket[2] = max(bucket[2], h); bucket[3] = min(bucket[3], l); bucket[4] = c; bucket[5] += v
        else:
            if bucket:
                out.append(bucket)
            bucket = [key, o, h, l, c, v]
    if bucket:
        out.append(bucket)
    return out


def cmd_fetch():
    rec = _rec()
    syms = sorted(json.load(open(UNIVERSE, encoding="utf-8")))
    toks = rec.tokens_for(syms)
    os.makedirs(CACHE, exist_ok=True)
    env = rec.credentials()
    api, _ = rec.session(env)
    end = datetime.date(2026, 11, 12)
    start = datetime.date(2021, 11, 1)
    pause, n_req = 2.5, 0
    log = open(os.path.join(CACHE, "_fetch.log"), "a", encoding="utf-8")
    for s in syms:
        path = os.path.join(CACHE, s.replace("&", "_and_") + ".csv.gz")
        if os.path.exists(path) or s not in toks:
            if s not in toks:
                log.write("%s NO TOKEN\n" % s); log.flush()
            continue
        rows, d = [], start
        while d <= end:
            # keep clear of tomorrow's live recorder session
            if datetime.time(8, 45) <= ist_now().time() <= datetime.time(15, 35) and ist_now().weekday() < 5:
                log.write("%s paused for market hours\n" % ist_now()); log.flush()
                print("paused for market hours; rerun fetch after 15:35 (finished stocks are kept)", flush=True)
                return 0
            e = min(end, d + datetime.timedelta(days=27))
            for attempt in range(8):
                try:
                    time.sleep(pause)
                    r = api.getCandleData({"exchange": "NSE", "symboltoken": toks[s], "interval": "ONE_MINUTE",
                                           "fromdate": d.strftime("%Y-%m-%d 09:15"), "todate": e.strftime("%Y-%m-%d 15:30")})
                    n_req += 1
                    if not r or not r.get("status", True) and "rate" in str(r.get("message", "")).lower():
                        raise RuntimeError(str(r))
                    rows += r.get("data") or []
                    pause = max(2.5, pause * 0.95)
                    break
                except Exception as ex:
                    msg = str(ex)
                    log.write("%s %s %s attempt %d pause %.1f: %s\n" % (ist_now().isoformat(timespec="seconds"), s, d, attempt + 1,
                                                                       pause, msg[-90:])); log.flush()
                    if "rate" in msg.lower():
                        pause = min(10.0, pause * 1.5)
                        time.sleep(20 * (attempt + 1))
                    elif "token" in msg.lower() or "session" in msg.lower():
                        api, _ = rec.session(env); time.sleep(5)
                    else:
                        time.sleep(5)
            else:
                log.write("%s %s..%s FAILED after 8 attempts\n" % (s, d, e)); log.flush()
            d = e + datetime.timedelta(days=1)
        rows.sort(key=lambda x: x[0])
        comp = compress(rows)
        with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh); w.writerows(comp)
        log.write("%s %s rows1m=%d stored=%d first=%s last=%s requests=%d pause=%.2f\n" % (
            ist_now().isoformat(timespec="seconds"), s, len(rows), len(comp), rows[0][0][:10] if rows else "-",
            rows[-1][0][:10] if rows else "-", n_req, pause)); log.flush()
        print("%-12s %7d 1m bars  %s..%s" % (s, len(rows), rows[0][0][:10] if rows else "-", rows[-1][0][:10] if rows else "-"), flush=True)
    try:
        api.terminateSession(env["ANGEL_CLIENT_CODE"])
    except Exception:
        pass
    return 0


def load(sym):
    path = os.path.join(CACHE, sym.replace("&", "_and_") + ".csv.gz")
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return [(r[0], float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])) for r in csv.reader(fh)]


def cmd_coverage():
    syms = sorted(json.load(open(UNIVERSE, encoding="utf-8")))
    have = 0
    print("%-12s %5s %5s %5s %5s %5s %5s %6s  first..last" % ("symbol", "2021", "2022", "2023", "2024", "2025", "2026", "open4"))
    for s in syms:
        try:
            rows = load(s)
        except FileNotFoundError:
            print("%-12s MISSING" % s); continue
        have += 1
        days = {}
        for r in rows:
            days.setdefault(r[0][:10], set()).add(r[0][11:16])
        full = {d for d, m in days.items() if {"09:15", "09:16", "09:17", "09:18"} <= m}
        by = {y: sum(1 for d in days if d.startswith(y)) for y in ("2021", "2022", "2023", "2024", "2025", "2026")}
        print("%-12s %5d %5d %5d %5d %5d %5d %6d  %s..%s" % (s, by["2021"], by["2022"], by["2023"], by["2024"], by["2025"], by["2026"],
                                                            len(full), min(days), max(days)))
    print("stocks with data: %d of %d" % (have, len(syms)))
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit({"fetch": cmd_fetch, "coverage": cmd_coverage}.get(cmd, lambda: print(__doc__) or 0)())
