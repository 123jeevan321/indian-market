"""Round 11 phase 3: opening minutes for every tradable stock-day in the 30-session window (Yahoo 5-minute bars, 60-day range).

Decision time is 09:30 (after the first three 5-minute bars). Features use only bars that ended by 09:30; outcomes start at the 09:30
bar's open. Relative opening volume compares 09:15-09:30 volume with the same slots over the previous 20 sessions.
Run: python research/round11_open.py [--fetch]
"""
import datetime, importlib.util, json, os, sys, time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(HERE, "cache", "r11_y5m")
OUT = os.path.join(HERE, "results")
spec = importlib.util.spec_from_file_location("lv", os.path.join(ROOT, "trader-entry", "levels.py"))
LV = importlib.util.module_from_spec(spec); spec.loader.exec_module(LV)


def fetch_all(syms):
    os.makedirs(CACHE, exist_ok=True)
    for i, s in enumerate(syms):
        path = os.path.join(CACHE, s.replace("&", "_and_") + ".json")
        if os.path.exists(path):
            continue
        try:
            doc = LV.fetch(s)
            json.dump(doc, open(path, "w"))
        except Exception as e:
            print("fail", s, e)
        time.sleep(0.25)
        if i % 50 == 0:
            print(i, s, flush=True)


def days_of(sym):
    """{date: {slot: (o,h,l,c,v)}} for one stock from the cached Yahoo 5-minute chart (slot 0 = 09:15)."""
    doc = json.load(open(os.path.join(CACHE, sym.replace("&", "_and_") + ".json")))
    r = doc["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    out = {}
    for i, t in enumerate(r.get("timestamp") or []):
        o, h, l, c, v = (q[k][i] for k in ("open", "high", "low", "close", "volume"))
        if None in (o, h, l, c):
            continue
        ts = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=t + 19800)
        slot = ((ts.hour * 60 + ts.minute) - (9 * 60 + 15)) // 5
        if 0 <= slot < 75:
            out.setdefault(pd.Timestamp(ts.date()), {})[slot] = (o, h, l, c, v or 0)
    return out


def features(W):
    rows = []
    for sym, grp in W.groupby("sym"):
        try:
            D = days_of(sym)
        except (OSError, KeyError, IndexError, ValueError):
            continue
        dates = sorted(D)
        for _, r in grp.iterrows():
            d = r.d
            if d not in D or not all(k in D[d] for k in range(4)):
                continue
            b = D[d]
            prior = [x for x in dates if x < d][-20:]
            hist = [sum(D[x][k][4] for k in range(3)) for x in prior if all(k in D[x] for k in range(3))]
            v15 = sum(b[k][4] for k in range(3))
            o0 = b[0][0]
            h15, l15 = max(b[k][1] for k in range(3)), min(b[k][2] for k in range(3))
            c15 = b[2][3]
            pv = sum(((b[k][1] + b[k][2] + b[k][3]) / 3) * b[k][4] for k in range(3))
            vwap15 = pv / v15 if v15 else c15
            rng = h15 - l15
            e = b[3][0]                                                   # entry: 09:30 bar open
            later = [b[k] for k in sorted(b) if k >= 3]
            close = later[-1][3]
            rows.append({"sym": sym, "d": d, "cc": r.cc, "gap": o0 / r.prev_c - 1, "r_first5": b[0][3] / o0 - 1,
                         "r15": c15 / o0 - 1, "rvol15": v15 / np.mean(hist) if hist and np.mean(hist) else np.nan,
                         "upper_wick15": (h15 - max(o0, c15)) / rng if rng else 0.0, "lower_wick15": (min(o0, c15) - l15) / rng if rng else 0.0,
                         "above_vwap15": float(c15 > vwap15), "close_pos15": (c15 - l15) / rng if rng else 0.5,
                         "ret_930_close": close / e - 1, "mfe": max(x[1] for x in later) / e - 1, "mae": min(x[2] for x in later) / e - 1,
                         "move_before_930": c15 / r.prev_c - 1})
    return pd.DataFrame(rows)


COND = {
    "C_vol_progress_up": ("09:15-09:30 volume >= 2x usual AND price up >= 1% since the open", lambda x: (x.rvol15 >= 2) & (x.r15 >= 0.01)),
    "C_vol_progress_down": ("volume >= 2x AND price down >= 1% since the open", lambda x: (x.rvol15 >= 2) & (x.r15 <= -0.01)),
    "C_vol_no_progress": ("volume >= 2x AND |price change| < 0.3% (absorption?)", lambda x: (x.rvol15 >= 2) & (x.r15.abs() < 0.003)),
    "C_lowvol_strong_up": ("volume < 1x usual AND price up >= 1%", lambda x: (x.rvol15 < 1) & (x.r15 >= 0.01)),
    "C_vol_upper_wick": ("volume >= 2x AND upper wick > 50% of the 15-min range", lambda x: (x.rvol15 >= 2) & (x.upper_wick15 > 0.5)),
    "C_vol_lower_wick": ("volume >= 2x AND lower wick > 50% of the 15-min range", lambda x: (x.rvol15 >= 2) & (x.lower_wick15 > 0.5)),
    "C_gapup_continue": ("gap >= +2% AND price still rising at 09:30", lambda x: (x.gap >= 0.02) & (x.r15 > 0)),
    "C_gapup_fade": ("gap >= +2% AND price falling by 09:30", lambda x: (x.gap >= 0.02) & (x.r15 < 0)),
    "C_gapdown_continue": ("gap <= -2% AND price still falling at 09:30", lambda x: (x.gap <= -0.02) & (x.r15 < 0)),
    "C_strong_first5": ("first 5-minute bar up >= 1% and closes above VWAP at 09:30", lambda x: (x.r_first5 >= 0.01) & (x.above_vwap15 == 1)),
    "C_top_rvol": ("09:15-09:30 volume >= 3x usual (any direction)", lambda x: x.rvol15 >= 3),
}


def table(F):
    up, dn = (F.ret_930_close >= 0.02).mean(), (F.ret_930_close <= -0.02).mean()
    out = {"_base": {"n": len(F), "p_up2_pct": round(100 * up, 2), "p_dn2_pct": round(100 * dn, 2),
                     "mean_ret_930_close_pct": round(100 * F.ret_930_close.mean(), 3)}}
    for k, (desc, fn) in COND.items():
        m = fn(F).fillna(False).astype(bool)
        s = F[m]
        if len(s) < 20:
            out[k] = {"desc": desc, "n": int(len(s))}; continue
        se = s.ret_930_close.std() / np.sqrt(len(s))
        out[k] = {"desc": desc, "n": int(len(s)), "p_up2_pct": round(100 * (s.ret_930_close >= 0.02).mean(), 1),
                  "p_dn2_pct": round(100 * (s.ret_930_close <= -0.02).mean(), 1), "mean_ret_pct": round(100 * s.ret_930_close.mean(), 3),
                  "ci_pct": [round(100 * (s.ret_930_close.mean() - 1.96 * se), 3), round(100 * (s.ret_930_close.mean() + 1.96 * se), 3)],
                  "mfe_pct": round(100 * s.mfe.mean(), 2), "mae_pct": round(100 * s.mae.mean(), 2),
                  "share_of_cc_ge3_days_pct": round(100 * (s.cc >= 0.03).mean(), 1)}
    return out


def main():
    W = pd.read_pickle(os.path.join(HERE, "cache", "r11_window.pkl"))
    if "--fetch" in sys.argv:
        fetch_all(sorted(W.sym.unique()))
    F = features(W)
    F.to_pickle(os.path.join(HERE, "cache", "r11_open.pkl"))
    res = {"stock_days": len(F), "symbols": int(F.sym.nunique()), "table": table(F)}
    # where were the big movers at 09:30? share of the full-day move already done
    big_up, big_dn = F[F.cc >= 0.05], F[F.cc <= -0.05]
    res["big_up_days"] = {"n": len(big_up), "median_move_by_930_pct": round(100 * big_up.move_before_930.median(), 2),
                          "median_cc_pct": round(100 * big_up.cc.median(), 2), "median_rvol15": round(big_up.rvol15.median(), 2),
                          "share_rvol15_ge2_pct": round(100 * (big_up.rvol15 >= 2).mean(), 1),
                          "share_gap_ge2_pct": round(100 * (big_up.gap >= 0.02).mean(), 1),
                          "median_ret_930_close_pct": round(100 * big_up.ret_930_close.median(), 2)}
    res["big_down_days"] = {"n": len(big_dn), "median_move_by_930_pct": round(100 * big_dn.move_before_930.median(), 2),
                            "median_cc_pct": round(100 * big_dn.cc.median(), 2), "median_rvol15": round(big_dn.rvol15.median(), 2),
                            "share_rvol15_ge2_pct": round(100 * (big_dn.rvol15 >= 2).mean(), 1)}
    res["all_days_rvol15_ge2_pct"] = round(100 * (F.rvol15 >= 2).mean(), 1)
    json.dump(res, open(os.path.join(OUT, "r11_open.json"), "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
