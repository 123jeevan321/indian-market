#!/usr/bin/env python3
"""Round 9: rebuild every major Round 1-8 strategy as a per-trade return stream on COMMON dates, classify market regimes using only
decision-time information, analyse where each strategy fails, test a walk-forward regime -> strategy selector, and study 2 % intraday moves.

    python research/round9.py streams      # -> research/cache/r9_trades.pkl (trade-level, % net returns) + r9_regimes.pkl
    python research/round9.py analyse      # failure analysis, cross-comparison, correlation, co-failure -> research/results/r9_*.csv/md
    python research/round9.py select       # walk-forward selector vs best single vs equal weight -> research/results/r9_selector.md
    python research/round9.py twopct       # 2 % move study on 15-minute data -> research/results/r9_twopct.md

Conventions: every return is NET percent of the position (delivery 0.25 % round trip; intraday 0.12 % = MIS charges + slippage).
A strategy's daily value = mean net return of the trades it ENTERED that day (signal-date attribution; multi-day holds overlap).
Regime for a trade entered on day d uses only data up to the close of d-1 (daily strategies decide at that close); the opening-gap
regime (known at 9:15 on d) is used only for intraday strategies. Volatility thresholds are fixed from the TRAIN period only.
Periods: TRAIN < 2024-11-11 <= VALIDATION < 2025-11-11 <= SEEN-ONCE (used by rounds 7-8; reported, never used for selection).
"""

import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "research"))
import discovery as R7  # noqa: E402
import round8 as R8  # noqa: E402

CACHE = os.path.join(ROOT, "research", "cache")
OUT = os.path.join(ROOT, "research", "results")
M15 = os.path.join(ROOT, "trader", "cache", "m15")
INTRA_COST = 0.0012
STRATS = {
    "D1_MOM60_10d": "top decile 60-day return, hold 10 days (R7 baseline)",
    "D2_R7CAND_10d": "last-hour volume share + illiquidity, hold 10 days (R7 final candidate)",
    "D3_R8DELIVBASIS_5d": "delivery % + futures basis, hold 5 days (R8 best combo)",
    "D4_REVERSAL_5d": "bottom decile 5-day return, hold 5 days (short-term reversal, R7 feature)",
    "D5_BREAKOUT_5d": "close > 20-day high, RVOL >= 1.5, close in top 30 % of range, hold 5 days (R2 squeeze/week-high family)",
    "D6_SWEEP_5d": "sweep below 20-day low and reclaim, above EMA200, hold 5 days (R2/R3 sweep)",
    "D7_BTST_2d": "day gain +1.5-3.5 %, RVOL >= 2, top-20 % close, above 3-day high, hold 2 days (R4 rotation)",
    "D8_OISHORT_intra": "MIS short of the OI-model bottom decile, next day open->close (R8 follow-up)",
    "D9_OILONG_intra": "long the OI-model top decile, next day open->close (R8)",
    "I1_ORB15L_intra": "15-min ORB long, stop OR mid, exit 15:15 (R1/R5)",
    "I2_ORB15S_intra": "15-min ORB breakdown short, stop OR mid, exit 15:15 (R1 sell side)",
    "I3_PDLSWEEP_intra": "previous-day-low sweep + bullish displacement, stop day low, exit 15:15 (R5/R6)",
}


def periods(d, a, b):
    return np.where(d < a, "train", np.where(d < b, "validation", "seen-once"))


# ---------------------------------------------------------------- streams

def daily_trades(p, a, b):
    q = p[p.liquid].copy()
    g = q.groupby("sym", group_keys=False)
    q["y2"] = g.c.shift(-2) / g.o.shift(-1) - 1 - 0.0025
    q["intra_gross"] = g.c.shift(-1) / g.o.shift(-1) - 1
    q["entry_d"] = g.d.shift(-1)
    rk = lambda f: q.groupby("d")[f].rank(pct=True)
    rows = []

    def add(name, mask, ycol, sign=1):
        s = q[mask & q[ycol].notna() & q.entry_d.notna()]
        rows.append(pd.DataFrame({"strategy": name, "signal_d": s.d.values, "entry_d": s.entry_d.values, "sym": s.sym.values,
                                  "ret": (s[ycol].values if sign > 0 else s[ycol].values)}))
    add("D1_MOM60_10d", rk("ret60") >= 0.9, "y10")
    sc2 = (rk("lasthour_share_z") + rk("amihud")) / 2
    add("D2_R7CAND_10d", (sc2.groupby(q.d).rank(pct=True) >= 0.9) & q.lasthour_share_z.notna(), "y10")
    sc3 = (rk("deliv_pct") + rk("basis_ann")) / 2
    add("D3_R8DELIVBASIS_5d", (sc3.groupby(q.d).rank(pct=True) >= 0.9) & q.basis_ann.notna(), "y5")
    add("D4_REVERSAL_5d", rk("ret5") <= 0.1, "y5")
    add("D5_BREAKOUT_5d", (q.brk_hi20 == 1) & (q.rvol >= 1.5) & (q.clv >= 0.7), "y5")
    add("D6_SWEEP_5d", (q.sweep_low20 == 1) & (q.dist_ema200 > 0), "y5")
    hi3 = g.h.transform(lambda s: s.rolling(3).max().shift(1))
    add("D7_BTST_2d", q.ret1.between(0.015, 0.035) & (q.rvol >= 2) & (q.clv >= 0.8) & (q.c > hi3) & (q.avgval20 >= 50e7), "y2")
    # R8 OI model (ridge fitted on TRAIN only)
    fo = q.groupby("sym").oi_tot.transform(lambda s: s.notna().mean()) > 0.5
    m = q[fo & q.intra_gross.notna()].copy()
    m["yx"] = m.intra_gross - m.groupby("d").intra_gross.transform("mean")
    feats = list(R7.FEATURES) + R8.DELIV_FEATS + R8.OI_FEATS
    X = R8.ranked(m, feats)
    tr = (m.d < a).values
    w = np.linalg.solve(X.values[tr].T @ X.values[tr] + 10 * np.eye(len(feats)), X.values[tr].T @ m.yx.values[tr])
    m["pred"] = X.values @ w
    pr = m.groupby("d").pred.rank(pct=True)
    m["short_ret"] = -m.intra_gross - INTRA_COST
    m["long_ret"] = m.intra_gross - INTRA_COST
    for name, mask, col in (("D8_OISHORT_intra", pr <= 0.1, "short_ret"), ("D9_OILONG_intra", pr >= 0.9, "long_ret")):
        s = m[mask & m.entry_d.notna()]
        rows.append(pd.DataFrame({"strategy": name, "signal_d": s.d.values, "entry_d": s.entry_d.values, "sym": s.sym.values, "ret": s[col].values}))
    return pd.concat(rows, ignore_index=True)


def m15_days(path):
    rows = json.load(open(path, encoding="utf-8"))
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=["ts", "o", "h", "l", "c", "v"])
    t = pd.to_datetime(df.ts.str[:19])
    df["d"] = t.dt.normalize()
    df["slot"] = ((t.dt.hour * 60 + t.dt.minute) - 555) // 15
    df = df[(df.slot >= 0) & (df.slot <= 23)]
    full = df.groupby("d").slot.transform("count") == 24
    return df[full].sort_values(["d", "slot"])


def intraday_trades():
    rows, mfe = [], []
    for f in sorted(os.listdir(M15)):
        if not f.endswith(".json") or f == "industry.json":
            continue
        sym = f[:-5].replace("_and_", "&")
        df = m15_days(os.path.join(M15, f))
        if df is None or df.empty:
            continue
        days = sorted(df.d.unique())
        arr = {d: g[["o", "h", "l", "c", "v"]].values for d, g in df.groupby("d")}
        for i, d in enumerate(days):
            b = arr[d]
            if i == 0:
                continue
            pb = arr[days[i - 1]]
            pdl = pb[:, 2].min()
            orh, orl = b[0, 1], b[0, 2]
            mid = (orh + orl) / 2
            o = b[0, 0]
            # 2 % study: entry at the 10:00 close (end of slot 2); path from slot 3 to 23
            e10 = b[2, 3]
            path = b[3:]
            mfe.append((sym, d, (b[:, 1].max() / o - 1), (b[:, 2].min() / o - 1), e10, path[:, 1].max() / e10 - 1,
                        path[:, 2].min() / e10 - 1, b[23, 3] / e10 - 1, b[:3, 4].sum(), b[2, 3] > max(b[0, 1], b[1, 1]),
                        b[2, 3] < min(b[0, 2], b[1, 2])))
            done = {"L": False, "S": False, "W": False}
            low_so_far, swept = 1e18, False
            for k in range(1, 5):
                hk, lk, ck, ok = b[k, 1], b[k, 2], b[k, 3], b[k, 0]
                low_so_far = min(low_so_far, b[:k + 1, 2].min())
                swept = swept or b[:k + 1, 2].min() < pdl
                for kind, cond, stop, side in (("L", ck > orh, mid, 1), ("S", ck < orl, mid, -1),
                                               ("W", swept and ck > pdl and ck > ok and (hk - lk) > 0 and (ck - ok) / (hk - lk) >= 0.6, low_so_far, 1)):
                    if done[kind] or not cond or not (0.003 * ck <= side * (ck - stop) <= 0.03 * ck):
                        continue
                    done[kind] = True
                    exit_px = b[23, 3]
                    for j in range(k + 1, 24):
                        if (side > 0 and b[j, 2] <= stop) or (side < 0 and b[j, 1] >= stop):
                            exit_px = (min(b[j, 0], stop) if side > 0 else max(b[j, 0], stop))
                            break
                    rows.append({"strategy": {"L": "I1_ORB15L_intra", "S": "I2_ORB15S_intra", "W": "I3_PDLSWEEP_intra"}[kind],
                                 "signal_d": d, "entry_d": d, "sym": sym, "ret": side * (exit_px / ck - 1) - INTRA_COST,
                                 "gap": o / pb[-1, 3] - 1})
    mf = pd.DataFrame(mfe, columns=["sym", "d", "day_up", "day_dn", "e10", "mfe", "mae", "close_ret", "vol_am", "above_or30", "below_or30"])
    return pd.DataFrame(rows), mf


def regimes(p, a):
    n = pd.read_pickle(os.path.join(CACHE, "panel.pkl"))
    p0 = R7.load_daily()
    nf = p0[p0.sym == "^NSEI"].set_index("d").sort_index()
    c = nf.c
    e50, e200 = c.ewm(span=50, adjust=False).mean(), c.ewm(span=200, adjust=False).mean()
    r20 = c.pct_change(20)
    vol = c.pct_change().rolling(20).std() * np.sqrt(252)
    lo, hi = vol[vol.index < a].quantile([1 / 3, 2 / 3])
    trend = np.select([r20.abs() < 0.015, (c > e50) & (e50 > e200) & (r20 > 0.02), c > e200, (c < e50) & (e50 < e200) & (r20 < -0.02)],
                      ["sideways", "strong_bull", "weak_bull", "strong_bear"], "weak_bear")
    breadth = n[n.liquid].groupby("d").dist_ema50.apply(lambda s: (s > 0).mean())
    reg = pd.DataFrame({"trend": trend, "vol": np.where(vol > hi, "high_vol", np.where(vol < lo, "low_vol", "mid_vol")),
                        "breadth": pd.cut(breadth.reindex(c.index), [-1, 0.4, 0.6, 2], labels=["weak_breadth", "mixed_breadth", "strong_breadth"]).astype(str),
                        "nifty_gap_next": (nf.o.shift(-1) / c - 1)}, index=c.index)
    # decision-time: a trade entered on day d uses the regime computed at the close of d-1
    reg_for_entry = reg.shift(1)
    reg_for_entry["gap_today"] = np.select([reg.nifty_gap_next.shift(1) > 0.005, reg.nifty_gap_next.shift(1) < -0.005], ["gap_up", "gap_down"], "flat_open")
    return reg_for_entry.drop(columns="nifty_gap_next")


def streams():
    p = pd.read_pickle(os.path.join(CACHE, "panel8.pkl"))
    a, b = R7.split_dates(p)
    d = daily_trades(p, a, b)
    i, mf = intraday_trades()
    t = pd.concat([d, i.drop(columns="gap")], ignore_index=True)
    t["entry_d"] = pd.to_datetime(t.entry_d)
    reg = regimes(p, a)
    t = t.join(reg, on="entry_d")
    t["period"] = periods(t.entry_d, a, b)
    t.to_pickle(os.path.join(CACHE, "r9_trades.pkl"))
    mf["period"] = periods(mf.d, a, b)
    mf = mf.join(reg, on="d")
    mf.to_pickle(os.path.join(CACHE, "r9_mfe.pkl"))
    reg.to_pickle(os.path.join(CACHE, "r9_regimes.pkl"))
    print(t.groupby(["strategy", "period"]).ret.agg(["count", "mean"]).unstack().round(4).to_string())


# ---------------------------------------------------------------- analysis

def tt(x):
    x = pd.Series(x).dropna()
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 5 and x.std() > 0 else np.nan


def daily_matrix(t):
    return t.groupby(["entry_d", "strategy"]).ret.mean().unstack()


def analyse():
    t = pd.read_pickle(os.path.join(CACHE, "r9_trades.pkl"))
    out = []
    # inventory per strategy and period
    inv = t.groupby(["strategy", "period"]).ret.agg(trades="count", mean="mean", win=lambda s: (s > 0).mean(),
                                                    avg_win=lambda s: s[s > 0].mean(), avg_loss=lambda s: s[s <= 0].mean())
    dm = daily_matrix(t)
    dd = {}
    for s in dm:
        cum = dm[s].fillna(0).cumsum()
        dd[s] = float((cum.cummax() - cum).max())
    inv.to_csv(os.path.join(OUT, "r9_inventory.csv"))
    # strategy x regime (TRAIN + VALIDATION only for selection-relevant tables; seen-once separately)
    for dim in ("trend", "vol", "breadth", "gap_today"):
        sub = t[t.period != "seen-once"]
        tab = sub.groupby(["strategy", dim]).ret.agg(["mean", "count"]).unstack()
        tab.to_csv(os.path.join(OUT, "r9_regime_%s.csv" % dim))
    # correlation of daily streams and co-failure
    corr = dm[dm.index < pd.Timestamp("2025-11-11")].corr(min_periods=60)
    corr.to_csv(os.path.join(OUT, "r9_corr.csv"))
    both_neg = {}
    cols = list(dm.columns)
    for i, x in enumerate(cols):
        for y in cols[i + 1:]:
            j = dm[[x, y]].dropna()
            if len(j) >= 60:
                xneg = j[x] < 0
                both_neg[(x, y)] = (float((xneg & (j[y] < 0)).mean()), float((j[y][xneg] > 0).mean()), len(j))
    pd.DataFrame([(k[0], k[1], v[0], v[1], v[2]) for k, v in both_neg.items()],
                 columns=["A", "B", "both_negative_share", "B_positive_when_A_negative", "common_days"]).to_csv(os.path.join(OUT, "r9_cofail.csv"), index=False)
    json.dump(dd, open(os.path.join(OUT, "r9_drawdown_pct_points.json"), "w"), indent=1)
    print(inv.round(4).to_string())


# ---------------------------------------------------------------- selector

def select():
    t = pd.read_pickle(os.path.join(CACHE, "r9_trades.pkl"))
    reg = pd.read_pickle(os.path.join(CACHE, "r9_regimes.pkl"))
    dm = daily_matrix(t)
    days = dm.index
    key = (reg.trend.astype(str) + "|" + reg.vol.astype(str)).reindex(days)
    trend_only = reg.trend.astype(str).reindex(days)
    a, b = pd.Timestamp("2024-11-11"), pd.Timestamp("2025-11-11")
    months = pd.Series(days).dt.to_period("M").unique()
    picks = pd.Series(index=days, dtype=object)
    log = []
    for mth in months:
        start = mth.to_timestamp()
        if start < pd.Timestamp("2022-11-01"):
            continue                                        # need a year of history first
        hist = dm[dm.index < start - pd.Timedelta(days=30)]  # 30-calendar-day embargo for overlapping holds
        hk, ht = key.reindex(hist.index), trend_only.reindex(hist.index)
        md = days[(days >= start) & (days < (mth + 1).to_timestamp())]
        for d in md:
            best, best_m = None, 0.0
            for s in dm.columns:
                for lab, ser in ((key[d], hk), (trend_only[d], ht)):
                    x = hist[s][ser == lab].dropna()
                    if len(x) >= 30:
                        mu, tv = x.mean(), tt(x)
                        if mu > best_m and tv > 2.0:
                            best, best_m = s, mu
                        break
            picks[d] = best
    sel = pd.Series([dm.at[d, picks[d]] if isinstance(picks[d], str) and pd.notna(dm.at[d, picks[d]]) else np.nan for d in days], index=days)
    ew = dm.mean(axis=1)
    best_single = dm[dm.index < a].mean().idxmax()
    lines = ["| method | period | days traded | mean net per day traded | t | share of days positive | cum. sum (pct pts) | max drawdown (pct pts) |",
             "|---|---|---|---|---|---|---|---|"]
    for name, ser in (("regime selector (walk-forward)", sel), ("equal weight, all 12 strategies", ew),
                      ("best single on TRAIN: " + best_single, dm[best_single])):
        for per, m in (("train (walk-forward from Nov 2022)", (days >= pd.Timestamp("2022-11-01")) & (days < a)), ("validation", (days >= a) & (days < b)),
                       ("seen-once 2025-26", days >= b)):
            x = ser[m].dropna()
            cum = x.cumsum()
            lines.append("| %s | %s | %d | %+.3f%% | %.2f | %.0f%% | %+.1f | %.1f |" % (
                name, per, len(x), 100 * x.mean() if len(x) else 0, tt(x) if len(x) > 5 else 0, 100 * (x > 0).mean() if len(x) else 0,
                100 * x.sum(), 100 * float((cum.cummax() - cum).max()) if len(x) else 0))
    usage = picks.dropna().value_counts()
    lines += ["", "Selector picks (all walk-forward days): " + ", ".join("%s %d" % kv for kv in usage.items()),
              "No-trade days (no strategy with t > 2 in the current regime): %d of %d" % (int(picks.isna().sum()), len(picks))]
    text = "\n".join(lines)
    print(text)
    open(os.path.join(OUT, "r9_selector.md"), "w", encoding="utf-8").write(text + "\n")


# ---------------------------------------------------------------- 2 % study

def twopct():
    mf = pd.read_pickle(os.path.join(CACHE, "r9_mfe.pkl"))
    lines = ["## How often does a liquid Nifty 100 stock move 2 % in a day? (open-based, all stock-days)", "",
             "| period | stock-days | high >= open +2 % | low <= open -2 % | either |", "|---|---|---|---|---|"]
    for per, s in mf.groupby("period"):
        lines.append("| %s | %d | %.1f%% | %.1f%% | %.1f%% |" % (per, len(s), 100 * (s.day_up >= 0.02).mean(), 100 * (s.day_dn <= -0.02).mean(),
                                                         100 * ((s.day_up >= 0.02) | (s.day_dn <= -0.02)).mean()))
    lines += ["", "## Can a trade entered at 10:00 capture it? Long at the 10:00 close, stop 1 %, target T, exit 15:15; net of 0.12 %", "",
              "| entry filter | period | trades | target | hit target first | hit stop first | neither | net expectancy | median MAE |",
              "|---|---|---|---|---|---|---|---|---|"]
    filters = {"every stock-day": mf.e10 > 0, "above 30-min range high": mf.above_or30}
    for fname, fm in filters.items():
        for per in ("train", "validation", "seen-once"):
            s = mf[fm & (mf.period == per)]
            for T in (0.005, 0.01, 0.015, 0.02, 0.025):
                hit = (s.mfe >= T) & (s.mae > -0.01)          # stop-first rule: a day that touched the stop counts as a stop
                stop = s.mae <= -0.01
                neither = ~hit & ~stop
                ret = np.where(stop, -0.01, np.where(hit, T, s.close_ret)) - INTRA_COST
                lines.append("| %s | %s | %d | %.1f%% | %.0f%% | %.0f%% | %.0f%% | %+.3f%% | %+.2f%% |" % (
                    fname, per, len(s), 100 * T, 100 * hit.mean(), 100 * stop.mean(), 100 * neither.mean(), 100 * ret.mean(),
                    100 * s.mae.median()))
    text = "\n".join(lines)
    print(text)
    open(os.path.join(OUT, "r9_twopct.md"), "w", encoding="utf-8").write(text + "\n")


if __name__ == "__main__":
    {"streams": streams, "analyse": analyse, "select": select, "twopct": twopct}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()
