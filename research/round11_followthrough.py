"""Volume follow-through test (user idea, 12 Nov 2026; rule fixed before running).

Strategies #1 (gap >= +2 %, rising 09:15-09:30, volume >= 2x) and #4 (volume >= 2x, +1 %, close above typical price), Nifty 100,
Angel 15-minute bars, 5 years, same 60/20/20 cut as Round 11.
Follow-through at 09:45: the 09:30-09:45 bar's volume >= its own 20-session average AND its close > the 09:30 entry price.
Compared, net of 0.12 % costs, exit at the close:
  A  original: buy 09:30, every signal
  B  original trades split by follow-through (B_ft / B_fade): does a fade mark the losers?
  C  user's rule: buy at 09:45 (next bar's open) only when follow-through holds; faded setups are dropped
Run: python research/round11_followthrough.py
"""
import glob, json, os, sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from round11 import panel, window, OUT        # noqa: E402

M15 = os.path.join(os.path.dirname(HERE), "trader", "cache", "m15")
COST = 0.0012


def frame():
    rows = []
    for f in glob.glob(os.path.join(M15, "*.json")):
        sym = os.path.basename(f)[:-5].replace("_and_", "&")
        if sym == "industry":
            continue
        data = json.load(open(f))
        if not data:
            continue
        df = pd.DataFrame(data, columns=["ts", "o", "h", "l", "c", "v"])
        df["d"] = pd.to_datetime(df.ts.str[:10])
        df["slot"] = ((pd.to_datetime(df.ts.str[11:16], format="%H:%M") - pd.Timestamp("1900-01-01 09:15")).dt.total_seconds() // 900).astype(int)
        df = df[(df.slot >= 0) & (df.slot <= 24)]
        piv = {k: df[df.slot == k].set_index("d") for k in (0, 1, 2)}
        day = pd.DataFrame({"o0": piv[0].o, "h0": piv[0].h, "l0": piv[0].l, "c0": piv[0].c, "v0": piv[0].v,
                            "o1": piv[1].o, "c1": piv[1].c, "v1": piv[1].v, "o2": piv[2].o, "close": df.groupby("d").c.last()}).dropna()
        day["sym"] = sym
        day["rv0"] = day.v0 / day.v0.rolling(20, min_periods=10).mean().shift()
        day["rv1"] = day.v1 / day.v1.rolling(20, min_periods=10).mean().shift()
        rows.append(day.reset_index())
    return pd.concat(rows, ignore_index=True)


def st(r):
    r = r.dropna()
    if len(r) < 5:
        return {"n": int(len(r))}
    m, se = r.mean(), r.std() / np.sqrt(len(r))
    return {"n": int(len(r)), "win_pct": round(100 * (r > 0).mean(), 1), "mean_pct": round(100 * m, 3),
            "ci_pct": [round(100 * (m - 1.96 * se), 3), round(100 * (m + 1.96 * se), 3)]}


def main():
    p = panel()
    w = window(p)
    H = p[(p.d < w[0]) & p.tradable][["sym", "d", "prev_c"]]
    M = frame().merge(H, on=["sym", "d"])
    days = sorted(M.d.unique())
    c1, c2 = days[int(0.6 * len(days))], days[int(0.8 * len(days))]
    M["period"] = np.where(M.d < c1, "TRAIN", np.where(M.d < c2, "VALIDATION", "TEST"))
    M["gap"], M["r15"], M["tp0"] = M.o0 / M.prev_c - 1, M.c0 / M.o0 - 1, (M.h0 + M.l0 + M.c0) / 3
    M["ft"] = (M.rv1 >= 1.0) & (M.c1 > M.o1)
    M["A"] = M.close / M.o1 - 1 - COST                     # buy 09:30 (slot-1 open)
    M["C"] = M.close / M.o2 - 1 - COST                     # buy 09:45 (slot-2 open)
    sets = {"#1 gap continuation": (M.gap >= 0.02) & (M.r15 > 0) & (M.rv0 >= 2),
            "#4 volume + rise": (M.rv0 >= 2) & (M.r15 >= 0.01) & (M.c0 > M.tp0)}
    res = {"cuts": [str(days[0])[:10], str(c1)[:10], str(c2)[:10], str(days[-1])[:10]]}
    for name, m in sets.items():
        S = M[m]
        res[name] = {}
        for per in ("TRAIN", "VALIDATION", "TEST", "ALL"):
            X = S if per == "ALL" else S[S.period == per]
            res[name][per] = {"A_all_0930": st(X.A), "B_followthrough_0930": st(X[X.ft].A), "B_faded_0930": st(X[~X.ft].A),
                              "C_user_rule_0945": st(X[X.ft].C), "share_faded_pct": round(100 * (~X.ft).mean(), 1) if len(X) else None}
    json.dump(res, open(os.path.join(OUT, "r11_followthrough.json"), "w"), indent=1)
    for name in sets:
        print("\n" + name)
        for per in ("TRAIN", "VALIDATION", "TEST", "ALL"):
            r = res[name][per]
            print("  %-10s faded %5s%% | A all %s | B ft %s | B faded %s | C 09:45 rule %s" % (
                per, r["share_faded_pct"], *[(r[k].get("n"), r[k].get("mean_pct"), r[k].get("win_pct")) for k in
                                              ("A_all_0930", "B_followthrough_0930", "B_faded_0930", "C_user_rule_0945")]))


if __name__ == "__main__":
    main()
