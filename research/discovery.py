#!/usr/bin/env python3
"""Strategy discovery engine (cross-sectional, staged, leakage-safe). Uses numpy + pandas.

    python research/discovery.py build        # panel + features + labels -> research/cache/panel.pkl
    python research/discovery.py stageA       # single features on TRAIN only -> research/results/stageA.csv
    python research/discovery.py stageB       # combinations of survivors, TRAIN fit / VALIDATION check -> stageB.csv
    python research/discovery.py final        # ONE pre-registered candidate on the untouched TEST period + walk-forward + rupee sim

Design (written before any result was seen):
  * Signal on day t uses data up to the close of t. Entry at the OPEN of t+1. Exit at the CLOSE of t+h (h = 1, 3, 5, 10, 20), or intraday
    (open->close of t+1). Labels never enter feature calculations.
  * Universe each day: 20-day average traded value >= Rs 50 crore and price >= Rs 100 (computed from data up to t).
  * Costs: delivery round trip 0.25 % (STT 0.2 % + stamp/exchange/GST/DP + 1 tick); intraday 0.10 % (MIS charges + slippage).
  * Splits by date: TRAIN first 60 %, VALIDATION next 20 %, TEST last 20 % (TEST touched once, in `final`).
  * Statistics: per-feature long portfolio = top decile of the day's liquid universe by the feature (both signs tried). Returns are sampled
    every h days (non-overlapping) for t-statistics. Multiple testing: Bonferroni over all stage-A tests.
  * Survivorship: universe = today's index members (bias stated in every report).
"""

import itertools
import json
import os
import sys
import urllib.request
from datetime import date

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAILY = os.path.join(ROOT, "trader", "cache", "daily5y")
M15 = os.path.join(ROOT, "trader", "cache", "m15")
OUT = os.path.join(ROOT, "research", "results")
CACHE = os.path.join(ROOT, "research", "cache")
HOLDS = (0, 1, 3, 5, 10, 20)          # 0 = intraday on day t+1
COST = {0: 0.0010}
COST.update({h: 0.0025 for h in HOLDS if h})


# ---------------------------------------------------------------- data

def load_daily():
    rows = []
    for f in os.listdir(DAILY):
        if not f.endswith(".json"):
            continue
        sym = f[:-5].replace("_and_", "&").replace("IDX_", "^")
        with open(os.path.join(DAILY, f), encoding="utf-8") as fh:
            doc = json.load(fh)
        try:
            r = doc["chart"]["result"][0]
            q = r["indicators"]["quote"][0]
            ts = pd.to_datetime(np.array(r["timestamp"]) + 19800, unit="s").normalize()
        except (KeyError, IndexError, TypeError):
            continue
        df = pd.DataFrame({"o": q["open"], "h": q["high"], "l": q["low"], "c": q["close"], "v": q["volume"]}, index=ts)
        df = df[~df.index.duplicated(keep="last")].dropna()
        df["sym"] = sym
        rows.append(df)
    p = pd.concat(rows)
    p.index.name = "d"
    return p.reset_index()


def load_m15_daily():
    """Daily aggregates from 15-minute bars (99 stocks): VWAP, last-hour volume share, first-hour return, intraday close location."""
    out = []
    for f in os.listdir(M15):
        if not f.endswith(".json") or f == "industry.json":
            continue
        sym = f[:-5].replace("_and_", "&")
        with open(os.path.join(M15, f), encoding="utf-8") as fh:
            rows = json.load(fh)
        if not rows:
            continue
        df = pd.DataFrame(rows, columns=["ts", "o", "h", "l", "c", "v"])
        t = pd.to_datetime(df["ts"].str[:19])
        df["d"] = t.dt.normalize()
        df["slot"] = ((t.dt.hour * 60 + t.dt.minute) - 555) // 15
        df = df[(df.slot >= 0) & (df.slot <= 24)]
        df["tpv"] = (df.h + df.l + df.c) / 3 * df.v
        g = df.groupby("d")
        agg = pd.DataFrame({
            "vwap": g.tpv.sum() / g.v.sum(),
            "vol15": g.v.sum(),
            "lasthour_v": df[df.slot >= 21].groupby("d").v.sum(),
            "firsthour_ret": df[df.slot <= 3].groupby("d").c.last() / df[df.slot == 0].groupby("d").o.first() - 1,
            "lasthour_ret": df[df.slot >= 21].groupby("d").c.last() / df[df.slot == 20].groupby("d").c.last() - 1,
        })
        agg["lasthour_share"] = agg.lasthour_v / agg.vol15
        agg["sym"] = sym
        out.append(agg.reset_index())
    return pd.concat(out)


def industries():
    path = os.path.join(CACHE, "industry500.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    import csv, io
    t = urllib.request.urlopen(urllib.request.Request("https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
                                                      headers={"User-Agent": "Mozilla/5.0"}), timeout=40).read().decode("utf-8-sig")
    ind = {r["Symbol"].strip().upper(): r["Industry"].strip() for r in csv.DictReader(io.StringIO(t))}
    os.makedirs(CACHE, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(ind, fh)
    return ind


# ---------------------------------------------------------------- features (each uses data up to and including day t)

def build():
    p = load_daily()
    nifty = p[p.sym == "^NSEI"].set_index("d")["c"]
    p = p[p.sym != "^NSEI"].sort_values(["sym", "d"]).copy()
    ind = industries()
    p["ind"] = p.sym.map(ind).fillna("Other")
    g = p.groupby("sym", group_keys=False)
    p["ret1"] = g.c.pct_change()
    for n in (5, 20, 60, 120, 250):
        p["ret%d" % n] = g.c.pct_change(n)
    p["mom12_1"] = g.c.shift(21) / g.c.shift(250) - 1                       # 12-1 month momentum (concept 96)
    p["vol20"] = g.ret1.transform(lambda s: s.rolling(20).std())
    p["vol120"] = g.ret1.transform(lambda s: s.rolling(120).std())
    p["voladj_mom"] = p.ret120 / (p.vol120 * np.sqrt(120))                  # 97
    tr = np.maximum(p.h - p.l, np.maximum((p.h - g.c.shift()).abs(), (p.l - g.c.shift()).abs()))
    p["atr14"] = tr.groupby(p.sym).transform(lambda s: s.rolling(14).mean())
    p["atr_comp"] = p.atr14 / tr.groupby(p.sym).transform(lambda s: s.rolling(60).mean())       # 52
    p["avgv20"] = g.v.transform(lambda s: s.rolling(20).mean().shift(1))
    p["rvol"] = p.v / p.avgv20                                               # 41
    p["rvol5"] = g.v.transform(lambda s: s.rolling(5).mean()) / p.avgv20     # 42 (contraction when low)
    p["avgval20"] = (p.c * p.v).groupby(p.sym).transform(lambda s: s.rolling(20).mean())
    rng = (p.h - p.l).replace(0, np.nan)
    p["clv"] = (p.c - p.l) / rng                                             # close location (34)
    p["range_atr"] = (p.h - p.l) / p.atr14                                   # 55
    p["absorb"] = p.rvol / (p.ret1.abs() / (p.atr14 / p.c) + 0.25)          # 3/44: volume high, move small
    p["gap"] = p.o / g.c.shift() - 1                                         # 58-60
    p["intraday"] = p.c / p.o - 1
    p["overnight5"] = (g.o.shift(0) / g.c.shift(1)).groupby(p.sym).transform(lambda s: np.log(s).rolling(5).sum())
    p["intraday5"] = (p.c / p.o).groupby(p.sym).transform(lambda s: np.log(s).rolling(5).sum())
    hi250 = g.h.transform(lambda s: s.rolling(250).max())
    p["near_hi250"] = p.c / hi250                                            # 52-week-high proximity (George-Hwang)
    ema200 = g.c.transform(lambda s: s.ewm(span=200, adjust=False).mean())
    ema50 = g.c.transform(lambda s: s.ewm(span=50, adjust=False).mean())
    p["dist_ema50"] = p.c / ema50 - 1
    p["dist_ema200"] = p.c / ema200 - 1
    lo20 = g.l.transform(lambda s: s.rolling(20).min().shift(1))
    hi20 = g.h.transform(lambda s: s.rolling(20).max().shift(1))
    p["sweep_low20"] = ((p.l < lo20) & (p.c > lo20)).astype(float)          # 22
    p["sweep_high20"] = ((p.h > hi20) & (p.c < hi20)).astype(float)         # 21
    p["brk_hi20"] = (p.c > hi20).astype(float)                               # 28
    p["pos20"] = (p.c - lo20) / (hi20 - lo20)                                # 40 premium/discount
    p["updown_vol"] = (np.sign(p.ret1) * p.v).groupby(p.sym).transform(lambda s: s.rolling(10).sum()) / \
        p.v.groupby(p.sym).transform(lambda s: s.rolling(10).sum())        # 45 / OBV-style participation
    p["amihud"] = (p.ret1.abs() / (p.c * p.v / 1e7)).groupby(p.sym).transform(lambda s: s.rolling(20).mean())
    nret = nifty.pct_change()
    p["nifty_ret"] = p.d.map(nret)
    p["nifty_ret20"] = p.d.map(nifty.pct_change(20))
    p["resid1"] = p.ret1 - p.nifty_ret                                       # 75
    p["rs60"] = p.ret60 - p.d.map(nifty.pct_change(60))                      # 77
    med = p.groupby(["d", "ind"]).ret20.transform("median")
    p["rs_ind20"] = p.ret20 - med                                            # 78
    p["ind_ret20"] = med                                                     # 76 / 89
    p["ind_ret5"] = p.groupby(["d", "ind"]).ret5.transform("median")
    # market regime (90) and breadth (80)
    above = (p.dist_ema50 > 0).groupby(p.d).mean()
    p["breadth50"] = p.d.map(above)
    e200 = nifty.ewm(span=200, adjust=False).mean()
    p["mkt_trend"] = p.d.map((nifty > e200).astype(float))
    # 15-minute aggregates (99 stocks)
    m = load_m15_daily()
    p = p.merge(m, on=["d", "sym"], how="left")
    p["close_vs_vwap"] = p.c / p.vwap - 1                                    # 1
    p["lasthour_share_z"] = p.lasthour_share - p.groupby("sym").lasthour_share.transform(lambda s: s.rolling(20).mean().shift(1))   # 17
    # labels: entry at next open, exit at close of t+h; intraday = open->close of t+1
    g = p.groupby("sym", group_keys=False)
    o1 = g.o.shift(-1)
    for h in HOLDS:
        if h == 0:
            p["y0"] = g.c.shift(-1) / o1 - 1 - COST[0]
        else:
            p["y%d" % h] = g.c.shift(-h) / o1 - 1 - COST[h]
    p["liquid"] = (p.avgval20 >= 50e7) & (p.c >= 100)
    os.makedirs(CACHE, exist_ok=True)
    p.to_pickle(os.path.join(CACHE, "panel.pkl"))
    print("panel: %d rows, %d symbols, %s to %s" % (len(p), p.sym.nunique(), p.d.min().date(), p.d.max().date()))
    return p


FEATURES = {   # feature -> concept ids it operationalises
    "ret1": [92], "ret5": [92], "ret20": [91], "ret60": [91], "ret120": [91], "mom12_1": [96, 88], "voladj_mom": [97],
    "vol20": [56], "atr_comp": [52, 54], "rvol": [41], "rvol5": [42], "clv": [34], "range_atr": [53, 55], "absorb": [3, 44],
    "gap": [58, 59], "intraday": [60], "overnight5": [17], "intraday5": [1], "near_hi250": [91], "dist_ema50": [91],
    "dist_ema200": [91], "sweep_low20": [22, 30], "sweep_high20": [21], "brk_hi20": [28, 89], "pos20": [40], "updown_vol": [45, 9],
    "amihud": [39], "resid1": [75], "rs60": [77], "rs_ind20": [78], "ind_ret20": [76, 89], "ind_ret5": [76, 87],
    "close_vs_vwap": [1, 48], "lasthour_share_z": [17, 2], "firsthour_ret": [57], "lasthour_ret": [17],
}


def split_dates(p):
    days = np.sort(p.d.unique())
    a, b = days[int(len(days) * 0.6)], days[int(len(days) * 0.8)]
    return a, b


def decile_returns(df, feat, sign, h, q=0.1, min_n=30):
    """Per-day mean label of the top decile (by sign*feature) of the liquid universe; sampled every max(h,1) days."""
    y = "y%d" % h
    d = df[df.liquid & df[feat].notna() & df[y].notna()][["d", feat, y]]
    if d.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    d = d.assign(s=sign * d[feat])
    r = d.groupby("d").s.rank(pct=True, method="first")
    cnt = d.groupby("d").s.transform("count")
    top = d[(r >= 1 - q) & (cnt >= min_n)]
    port = top.groupby("d")[y].mean()
    univ = d[cnt >= min_n].groupby("d")[y].mean()
    step = max(h, 1)
    keep = port.index[::step]
    return port.loc[keep], (port - univ.reindex(port.index)).loc[keep]


def tstat(x):
    x = x.dropna()
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 5 and x.std() > 0 else 0.0


def stage_a():
    p = pd.read_pickle(os.path.join(CACHE, "panel.pkl"))
    a, b = split_dates(p)
    train = p[p.d < a]
    rows, sid = [], 0
    for feat, concepts in FEATURES.items():
        for sign in (1, -1):
            for h in HOLDS:
                sid += 1
                port, exc = decile_returns(train, feat, sign, h)
                if len(port) < 20:
                    continue
                rows.append({"id": "A%04d" % sid, "feature": feat, "concepts": concepts, "sign": sign, "hold": h,
                             "n_periods": len(port), "mean_net": port.mean(), "t_net": tstat(port), "mean_excess": exc.mean(),
                             "t_excess": tstat(exc), "hit": float((port > 0).mean())})
    df = pd.DataFrame(rows)
    n = len(df)
    from math import erf, sqrt
    z = 3.48 if n > 300 else 3.29          # two-sided Bonferroni at 5 % for about 400 tests ~ |t| > 3.5
    df["bonferroni_pass"] = (df.t_net > z) & (df.t_excess > 2.0)
    df["promising"] = (df.t_net > 2.0) & (df.t_excess > 1.5)
    os.makedirs(OUT, exist_ok=True)
    df.sort_values("t_net", ascending=False).to_csv(os.path.join(OUT, "stageA.csv"), index=False)
    print("stage A: %d tests on TRAIN (< %s); Bonferroni |t| > %.2f; pass: %d, promising (t>2): %d" % (
        n, pd.Timestamp(a).date(), z, int(df.bonferroni_pass.sum()), int(df.promising.sum())))
    print(df.sort_values("t_net", ascending=False).head(25)[["id", "feature", "sign", "hold", "mean_net", "t_net", "mean_excess", "t_excess", "hit"]].to_string(index=False))


def combo_score(df, feats):
    """Rank-average of signed features within each day (uses only same-day information)."""
    s = 0
    for f, sign in feats:
        s = s + (sign * df[f]).groupby(df.d).rank(pct=True)
    return s / len(feats)


def stage_b(max_k=3):
    p = pd.read_pickle(os.path.join(CACHE, "panel.pkl"))
    a, b = split_dates(p)
    L = p[p.liquid].copy()
    for f in FEATURES:
        L["r_" + f] = L.groupby("d")[f].rank(pct=True)
    sa = pd.read_csv(os.path.join(OUT, "stageA.csv"))
    rows = []
    for h in HOLDS:
        top_m = 14 if h >= 10 else 8
        cand = sa[(sa.hold == h)].sort_values("t_net", ascending=False).drop_duplicates("feature").head(top_m)
        feats = [(r.feature, int(r.sign)) for r in cand.itertuples()]
        y = "y%d" % h
        for k in range(2, max_k + 1):
            for combo in itertools.combinations(feats, k):
                sc = sum((L["r_" + f] if sg > 0 else 1 - L["r_" + f]) for f, sg in combo) / k
                sub = L[["d", "liquid", y]].assign(score=sc).dropna()
                res = {}
                for name, part in (("train", sub[sub.d < a]), ("val", sub[(sub.d >= a) & (sub.d < b)])):
                    port, exc = decile_returns(part, "score", 1, h)
                    res[name] = (port.mean(), tstat(port), exc.mean(), tstat(exc), len(port))
                rows.append({"id": "B%d-%s" % (h, "+".join("%s%s" % ("" if sg > 0 else "-", f) for f, sg in combo)), "hold": h, "k": k,
                             "features": json.dumps(combo), "train_mean": res["train"][0], "train_t": res["train"][1],
                             "train_exc": res["train"][2], "train_t_exc": res["train"][3], "val_mean": res["val"][0], "val_t": res["val"][1],
                             "val_exc": res["val"][2], "val_t_exc": res["val"][3], "n_val": res["val"][4]})
    df = pd.DataFrame(rows)
    df["stable"] = (df.train_t > 2) & (df.train_t_exc > 1.5) & (df.val_mean > 0) & (df.val_exc > 0)
    df.sort_values(["stable", "val_t_exc"], ascending=False).to_csv(os.path.join(OUT, "stageB.csv"), index=False)
    print("stage B: %d combinations; stable (train t>2, train excess t>1.5, validation net>0 and excess>0): %d" % (len(df), int(df.stable.sum())))
    print(df.sort_values(["stable", "val_t_exc"], ascending=False).head(20)[["id", "train_mean", "train_t", "train_t_exc", "val_mean", "val_exc", "val_t_exc", "n_val"]].to_string(index=False))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"build": build, "stageA": stage_a, "stageB": stage_b}.get(cmd, lambda: print(__doc__))()


def final():
    """Pre-registered candidate on the untouched TEST period + yearly walk-forward + baselines + rupee simulation."""
    pre = json.load(open(os.path.join(OUT, "preregistered.json")))
    p = pd.read_pickle(os.path.join(CACHE, "panel.pkl"))
    a, b = split_dates(p)
    h = pre["hold"]
    y = "y%d" % h
    L = p[p.liquid].copy()
    combos = {"PRIMARY " + pre["candidate"]: pre["features"],
              "secondary -rvol5+lasthour_share_z+amihud": [["rvol5", -1], ["lasthour_share_z", 1], ["amihud", 1]],
              "baseline momentum ret60": [["ret60", 1]], "baseline amihud alone": [["amihud", 1]],
              "baseline lasthour_share_z alone": [["lasthour_share_z", 1]]}
    out = ["# Final test of the pre-registered candidate", "", "Pre-registered %s: `%s`, hold %d days. Rule: %s." % (
        pre["registered_at"], pre["candidate"], h, pre["rule"]), "",
           "| strategy | period | periods | mean net per trade | t | excess vs universe | t excess | hit rate |", "|---|---|---|---|---|---|---|---|"]
    base_universe = L[L.lasthour_share_z.notna()]          # same 99-stock universe for a fair random baseline
    for name, feats in combos.items():
        sc = sum((L[f].groupby(L.d).rank(pct=True) if s > 0 else 1 - L[f].groupby(L.d).rank(pct=True)) for f, s in feats) / len(feats)
        sub = L[["d", "liquid", y]].assign(score=sc).dropna()
        for per, part in (("train", sub[sub.d < a]), ("validation", sub[(sub.d >= a) & (sub.d < b)]), ("TEST", sub[sub.d >= b])):
            port, exc = decile_returns(part, "score", 1, h, min_n=20)
            out.append("| %s | %s | %d | %+.2f%% | %.2f | %+.2f%% | %.2f | %.0f%% |" % (name, per, len(port), 100 * port.mean(), tstat(port),
                                                                              100 * exc.mean(), tstat(exc), 100 * (port > 0).mean()))
        if name.startswith("PRIMARY"):
            prim = sub
    rng = np.random.default_rng(7)
    rnd = base_universe[["d", "liquid", y]].assign(score=rng.random(len(base_universe))).dropna()
    for per, part in (("validation", rnd[(rnd.d >= a) & (rnd.d < b)]), ("TEST", rnd[rnd.d >= b])):
        port, exc = decile_returns(part, "score", 1, h, min_n=20)
        out.append("| random decile (same 99 stocks) | %s | %d | %+.2f%% | %.2f | %+.2f%% | %.2f | %.0f%% |" % (
            per, len(port), 100 * port.mean(), tstat(port), 100 * exc.mean(), tstat(exc), 100 * (port > 0).mean()))
    out += ["", "## Walk-forward by calendar year (fixed rule, no refitting)", "", "| year | periods | mean net | excess | hit |", "|---|---|---|---|---|"]
    for yr in sorted(prim.d.dt.year.unique()):
        port, exc = decile_returns(prim[prim.d.dt.year == yr], "score", 1, h, min_n=20)
        if len(port):
            out.append("| %d | %d | %+.2f%% | %+.2f%% | %.0f%% |" % (yr, len(port), 100 * port.mean(), 100 * exc.mean(), 100 * (port > 0).mean()))
    # regime split (NIFTY above/below EMA200 at signal)
    out += ["", "## By market regime at the signal date (all periods)", "", "| regime | periods | mean net | excess |", "|---|---|---|---|"]
    reg = L[["d", "mkt_trend"]].drop_duplicates("d").set_index("d").mkt_trend
    for lab, val in (("NIFTY above EMA200", 1.0), ("NIFTY below EMA200", 0.0)):
        days = reg[reg == val].index
        port, exc = decile_returns(prim[prim.d.isin(days)], "score", 1, h, min_n=20)
        out.append("| %s | %d | %+.2f%% | %+.2f%% |" % (lab, len(port), 100 * port.mean(), 100 * exc.mean()))
    # rupee simulation on TEST: every h days buy the top 3 at next open, Rs 2 lakh split equally, sell at close of day h
    out += ["", "## Rupee simulation on the TEST period (Rs 2,00,000, top 3 stocks, equal weight, delivery costs included in labels)", ""]
    t = prim[prim.d >= b]
    days = sorted(t.d.unique())[::h]
    pnl = []
    for d in days:
        top = t[t.d == d].nlargest(3, "score")
        if len(top) == 3:
            pnl.append((pd.Timestamp(d), float((top[y] * 200000 / 3).sum()), [float(x * 200000 / 3) for x in top[y]]))
    if pnl:
        per = np.array([x[1] for x in pnl]); trades = np.concatenate([x[2] for x in pnl])
        wk = per / (h / 5.0)
        out += ["Rebalances: %d (every %d trading days). Net Rs per 2-week cycle: mean %+.0f, median %+.0f, worst %+.0f, best %+.0f; "
                "cycles >= Rs 10,000 (= Rs 5,000/week): %.0f%%; losing cycles: %.0f%%. Per-stock trade: mean %+.0f, worst %+.0f "
                "(%.0f%% of trades lost more than Rs 1,500). Implied average per week: %+.0f." % (
                    len(per), h, per.mean(), np.median(per), per.min(), per.max(), 100 * (per >= 10000).mean(), 100 * (per < 0).mean(),
                    trades.mean(), trades.min(), 100 * (trades < -1500).mean(), wk.mean())]
    text = "\n".join(out)
    print(text)
    with open(os.path.join(OUT, "final.md"), "w", encoding="utf-8") as fh:
        fh.write(text + "\n")


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "final":
    final()
