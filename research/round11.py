#!/usr/bin/env python3
"""Round 11: reverse-engineering large NSE moves. Read-only data access; no orders.

    python research/round11.py universe      # liquid universe + the 30-session discovery window
    python research/round11.py fetch1m       # Angel ONE_MINUTE candles for the window, one request per stock -> research/cache/r11_m1/
    python research/round11.py analyse       # phases 1-7 tables -> research/results/r11_*.json
    python research/round11.py backtest      # phases 8-9 on the 5-year panel (discovery window excluded), 60/20/20

Discovery window = the last 30 completed sessions in the Round 8 panel (delivery + futures data complete). Everything learned there is
TESTED only on earlier data, split chronologically (TRAIN 60 % / VALIDATION 20 % / TEST 20 %).
"""
import datetime, json, os, sys, time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "research", "cache")
M1 = os.path.join(CACHE, "r11_m1")
OUT = os.path.join(ROOT, "research", "results")
MIN_VAL = 10e7          # Rs 10 crore average daily traded value (20 days, known at t-1)
MIN_PX = 50.0


def panel():
    p = pd.read_pickle(os.path.join(CACHE, "panel8.pkl"))
    p = p.sort_values(["sym", "d"]).reset_index(drop=True)
    g = p.groupby("sym")
    p["prev_c"] = g.c.shift()
    p["cc"] = p.c / p.prev_c - 1                     # close-to-close
    p["oc"] = p.c / p.o - 1                          # open-to-close
    p["to_high"] = p.h / p.prev_c - 1                # previous close -> day high
    p["to_low"] = p.l / p.prev_c - 1                 # previous close -> day low
    p["hl"] = p.h / p.l - 1                          # intraday high-low range
    p["tradable"] = (g.avgval20.shift() >= MIN_VAL) & (p.prev_c >= MIN_PX) & (g.cumcount() >= 250)
    return p


def window(p, n=30):
    days = sorted(p.d.unique())
    return days[-n:]


def cmd_universe():
    p = panel()
    w = window(p)
    sub = p[p.d.isin(w) & p.tradable]
    syms = sorted(sub.sym.unique())
    os.makedirs(OUT, exist_ok=True)
    info = {"window_start": str(w[0])[:10], "window_end": str(w[-1])[:10], "sessions": len(w), "tradable_symbols": len(syms),
            "stock_days": int(len(sub))}
    json.dump({"info": info, "symbols": syms}, open(os.path.join(OUT, "r11_universe.json"), "w"), indent=1)
    print(info)


def cmd_fetch1m():
    import importlib.util
    spec = importlib.util.spec_from_file_location("rec", os.path.join(ROOT, "trader-flows", "angel_recorder.py"))
    rec = importlib.util.module_from_spec(spec); spec.loader.exec_module(rec)
    u = json.load(open(os.path.join(OUT, "r11_universe.json")))
    start = (pd.Timestamp(u["info"]["window_start"]) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    end = "2026-11-12"
    os.makedirs(M1, exist_ok=True)
    toks = rec.tokens_for(u["symbols"])
    env = rec.credentials()
    api, _ = rec.session(env)
    pause, log = 3.0, open(os.path.join(M1, "_fetch.log"), "a", encoding="utf-8")
    order = u["symbols"]
    pri = os.path.join(OUT, "r11_priority.json")
    if os.path.exists(pri):                          # biggest movers first; the rest only if time allows
        first = [x for x in json.load(open(pri)) if x in order]
        order = first + [x for x in order if x not in first]
    for s in order:
        path = os.path.join(M1, s.replace("&", "_and_") + ".json")
        if os.path.exists(path) or s not in toks:
            continue
        for attempt in range(8):
            now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
            if now.weekday() < 5 and datetime.time(8, 45) <= now.time() <= datetime.time(15, 35):
                print("paused for market hours", flush=True); return 0
            time.sleep(pause)
            try:
                r = api.getCandleData({"exchange": "NSE", "symboltoken": toks[s], "interval": "ONE_MINUTE",
                                       "fromdate": start + " 09:15", "todate": end + " 15:30"})
                rows = (r or {}).get("data") or []
                json.dump(rows, open(path, "w"))
                log.write("%s %s %d rows\n" % (now.isoformat(timespec="seconds"), s, len(rows))); log.flush()
                pause = max(3.0, pause * 0.9)
                break
            except Exception as e:
                msg = str(e)
                log.write("%s %s attempt %d: %s\n" % (now.isoformat(timespec="seconds"), s, attempt + 1, msg[-70:])); log.flush()
                if "rate" in msg.lower():
                    pause = min(15.0, pause * 1.5); time.sleep(15 * (attempt + 1))
                elif "token" in msg.lower() or "session" in msg.lower():
                    api, _ = rec.session(env)
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    fn = {"universe": cmd_universe, "fetch1m": cmd_fetch1m}.get(cmd)
    sys.exit(fn() if fn else print(__doc__))
