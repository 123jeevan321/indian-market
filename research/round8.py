#!/usr/bin/env python3
"""Round 8: delivery-% and futures-open-interest features, single-feature screening, incremental-value models, combinations.

    python research/round8.py features     # trader/cache/nse -> research/cache/panel8.pkl (+ data-quality report)
    python research/round8.py stageA       # new features, TRAIN only, same protocol as round 7
    python research/round8.py incremental  # ridge model on ranked features: 36 vs +delivery vs +OI vs both (TRAIN fit, VALIDATION score)
    python research/round8.py stageB       # 2-4 factor and conditional combinations of surviving features
    python research/round8.py report       # docs/ROUND8_DELIVERY_OI.md

Protocol (unchanged from round 7): signal at the close of t, entry at the next open, exit at the close of t+h; costs 0.25 % delivery,
0.10 % intraday; TRAIN = first 60 % of dates, VALIDATION = next 20 %. The last 20 % (Nov 2025 - Nov 2026) was already used once in round 7,
so it is reported only as "previously seen", never used for selection. A candidate's true final test is forward paper-tracking.
Futures prices and OI are unadjusted for splits/bonuses, so only same-day ratios and percentage changes are used; OI is summed across all
expiries of a stock (rollover-neutral); the near month is replaced by the next month inside the last 3 calendar days before expiry.
"""

import glob
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "research"))
import discovery as R7  # noqa: E402

NSE = os.path.join(ROOT, "trader", "cache", "nse")
CACHE = os.path.join(ROOT, "research", "cache")
OUT = os.path.join(ROOT, "research", "results")

DELIV_FEATS = ["deliv_pct", "deliv_z", "deliv_qty_ratio", "deliv_5d", "deliv_trend", "deliv_up", "deliv_down", "deliv_consol",
               "deliv_near_hi", "deliv_brk", "deliv_failbrk"]
OI_FEATS = ["oi_chg1", "oi_chg5", "long_build", "short_build", "short_cover", "long_unwind", "lb5", "sc5", "basis_ann", "basis_chg",
            "fut_act", "oi_deliv_div", "oi_brk"]


def load_dir(kind):
    parts = []
    for f in sorted(glob.glob(os.path.join(NSE, kind, "*.csv"))):
        if os.path.getsize(f) < 10:
            continue
        df = pd.read_csv(f)
        if df.empty:
            continue
        df["d"] = pd.Timestamp(os.path.basename(f)[:8])
        parts.append(df)
    return pd.concat(parts, ignore_index=True)


def features():
    p = pd.read_pickle(os.path.join(CACHE, "panel.pkl"))
    dv = load_dir("deliv")
    for c in ("close_unadj", "qty", "trades", "deliv_qty", "deliv_pct"):
        dv[c] = pd.to_numeric(dv[c], errors="coerce")
    fu = load_dir("fut")
    for c in ("close", "settle", "oi", "chg_oi", "contracts", "underlying"):
        fu[c] = pd.to_numeric(fu[c], errors="coerce")
    fu["expiry"] = pd.to_datetime(fu["expiry"])
    quality = {"deliv_days": int(dv.d.nunique()), "deliv_rows": int(len(dv)), "deliv_symbols": int(dv.sym.nunique()),
               "deliv_missing_pct": float(dv.deliv_pct.isna().mean() * 100), "fut_days": int(fu.d.nunique()), "fut_rows": int(len(fu)),
               "fut_symbols": int(fu.sym.nunique()), "panel_days": int(p.d.nunique()),
               "panel_symbols_with_delivery": int(p[p.sym.isin(set(dv.sym))].sym.nunique()),
               "panel_symbols_with_futures": int(p[p.sym.isin(set(fu.sym))].sym.nunique())}
    # futures: total OI across expiries; near contract (skip last 3 days before expiry) for basis
    fu["dte"] = (fu.expiry - fu.d).dt.days
    tot = fu.groupby(["d", "sym"]).agg(oi_tot=("oi", "sum"), fut_contracts=("contracts", "sum")).reset_index()
    near = fu[fu.dte >= 3].sort_values("dte").groupby(["d", "sym"]).first().reset_index()[["d", "sym", "close", "dte"]]
    near = near.rename(columns={"close": "fut_close", "dte": "fut_dte"})
    p = p.merge(dv[["d", "sym", "close_unadj", "deliv_qty", "deliv_pct"]], on=["d", "sym"], how="left")
    p = p.merge(tot, on=["d", "sym"], how="left").merge(near, on=["d", "sym"], how="left")
    p = p.sort_values(["sym", "d"])
    g = p.groupby("sym", group_keys=False)
    roll = lambda s, n: s.rolling(n, min_periods=max(5, n // 2)).mean().shift(1)
    # delivery features (concepts 84, 85)
    p["deliv_z"] = p.deliv_pct - g.deliv_pct.transform(lambda s: roll(s, 20))
    p["deliv_qty_ratio"] = p.deliv_qty / g.deliv_qty.transform(lambda s: roll(s, 20))
    p["deliv_5d"] = p.groupby("sym").deliv_qty_ratio.transform(lambda s: s.rolling(5).mean())
    p["deliv_trend"] = g.deliv_pct.transform(lambda s: s.rolling(5).mean()) - g.deliv_pct.transform(lambda s: roll(s, 60))
    up = (p.ret1 > 0).astype(float)
    p["deliv_up"] = p.deliv_qty_ratio * up                                   # delivery expansion on an up day
    p["deliv_down"] = p.deliv_qty_ratio * (1 - up)                           # ... on a down day (distribution?)
    p["deliv_consol"] = p.deliv_5d * (p.atr_comp < 0.9).astype(float)       # accumulation inside a contraction
    p["deliv_near_hi"] = p.deliv_qty_ratio * (p.near_hi250 > 0.95).astype(float)
    p["deliv_brk"] = p.deliv_qty_ratio * p.brk_hi20                          # breakout acceptance with real money
    p["deliv_failbrk"] = p.deliv_qty_ratio * p.sweep_high20                  # failed breakout on heavy delivery (distribution)
    # futures features (concepts 61-67, 73-74)
    p["oi_chg1"] = g.oi_tot.pct_change()
    p["oi_chg5"] = g.oi_tot.pct_change(5)
    p.loc[p.oi_chg1.abs() > 1.0, "oi_chg1"] = np.nan                        # lot-size/contract changes or data errors
    p.loc[p.oi_chg5.abs() > 2.0, "oi_chg5"] = np.nan
    pr, oi = np.sign(p.ret1), np.sign(p.oi_chg1)
    p["long_build"] = ((pr > 0) & (oi > 0)).astype(float).where(p.oi_chg1.notna())
    p["short_build"] = ((pr < 0) & (oi > 0)).astype(float).where(p.oi_chg1.notna())
    p["short_cover"] = ((pr > 0) & (oi < 0)).astype(float).where(p.oi_chg1.notna())
    p["long_unwind"] = ((pr < 0) & (oi < 0)).astype(float).where(p.oi_chg1.notna())
    p["lb5"] = p.ret5.clip(lower=0) * p.oi_chg5.clip(lower=0)               # 5-day long build-up strength
    p["sc5"] = p.ret5.clip(lower=0) * (-p.oi_chg5).clip(lower=0)            # 5-day short covering strength
    basis = (p.fut_close / p.close_unadj - 1)
    p["basis_ann"] = basis / p.fut_dte.clip(lower=3) * 365
    p["basis_chg"] = p.basis_ann - p.groupby("sym").basis_ann.transform(lambda s: roll(s, 20))
    p["fut_act"] = p.fut_contracts / g.fut_contracts.transform(lambda s: roll(s, 20))
    p["oi_deliv_div"] = p.deliv_z.rank(pct=True) - p.oi_chg5.rank(pct=True)   # real money in, leverage out (74)
    p["oi_brk"] = p.oi_chg1 * p.brk_hi20                                     # OI expansion on a breakout
    p.to_pickle(os.path.join(CACHE, "panel8.pkl"))
    cov = {f: float(p.loc[p.liquid, f].notna().mean() * 100) for f in DELIV_FEATS + OI_FEATS}
    quality["feature_coverage_pct_of_liquid_rows"] = cov
    with open(os.path.join(OUT, "round8_quality.json"), "w") as fh:
        json.dump(quality, fh, indent=2)
    print(json.dumps(quality, indent=2))


def stage_a():
    p = pd.read_pickle(os.path.join(CACHE, "panel8.pkl"))
    a, b = R7.split_dates(p)
    train = p[p.d < a]
    rows, sid = [], 0
    for feat in DELIV_FEATS + OI_FEATS:
        for sign in (1, -1):
            for h in R7.HOLDS:
                sid += 1
                port, exc = R7.decile_returns(train, feat, sign, h)
                if len(port) < 20:
                    continue
                rows.append({"id": "A8-%04d" % sid, "feature": feat, "sign": sign, "hold": h, "n_periods": len(port),
                             "mean_net": port.mean(), "t_net": R7.tstat(port), "mean_excess": exc.mean(), "t_excess": R7.tstat(exc),
                             "hit": float((port > 0).mean())})
    df = pd.DataFrame(rows)
    df["bonferroni_pass"] = (df.t_excess.abs() > 3.4)
    df.sort_values("t_excess", ascending=False).to_csv(os.path.join(OUT, "round8_stageA.csv"), index=False)
    print("round 8 stage A: %d tests on TRAIN; |t_excess| > 3.4: %d; t_excess > 2: %d" % (len(df), int(df.bonferroni_pass.sum()),
                                                                                         int((df.t_excess > 2).sum())))
    print(df.sort_values("t_excess", ascending=False).head(25)[["id", "feature", "sign", "hold", "mean_net", "t_net", "mean_excess", "t_excess", "hit"]].to_string(index=False))


def ranked(p, feats):
    X = pd.DataFrame({f: p.groupby("d")[f].rank(pct=True) - 0.5 for f in feats})
    return X.fillna(0.0)


def ridge_eval(p, feats, h, lam=10.0):
    """Fit y_h (excess over the day's mean) on ranked features in TRAIN; score VALIDATION by top-decile net return and rank IC."""
    a, b = R7.split_dates(p)
    y = "y%d" % h
    q = p[p.liquid & p[y].notna()].copy()
    q["yx"] = q[y] - q.groupby("d")[y].transform("mean")
    X = ranked(q, feats)
    tr = (q.d < a).values
    va = ((q.d >= a) & (q.d < b)).values
    A = X.values[tr]
    w = np.linalg.solve(A.T @ A + lam * np.eye(A.shape[1]), A.T @ q.yx.values[tr])
    q["pred"] = X.values @ w
    out = {}
    for name, m in (("train", tr), ("val", va)):
        s = q[m]
        rp, ry = s.groupby("d").pred.rank(), s.groupby("d").yx.rank()
        ic = pd.DataFrame({"d": s.d, "a": rp, "b": ry}).groupby("d").apply(lambda z: z.a.corr(z.b))
        port, exc = R7.decile_returns(s.assign(liquid=True), "pred", 1, h)
        out[name] = {"ic": float(ic.mean()), "ic_t": R7.tstat(ic.iloc[::max(h, 1)]), "top_net": float(port.mean()),
                     "top_exc": float(exc.mean()), "top_t_exc": R7.tstat(exc)}
    return out, dict(zip(feats, map(float, w)))


def incremental():
    p = pd.read_pickle(os.path.join(CACHE, "panel8.pkl"))
    base = list(R7.FEATURES)
    fo = p.groupby("sym").oi_tot.transform(lambda s: s.notna().mean()) > 0.5
    sets = {"36 base": base, "36 + delivery": base + DELIV_FEATS, "36 + futures OI": base + OI_FEATS,
            "36 + both": base + DELIV_FEATS + OI_FEATS}
    rows = []
    for uni_name, uni in (("all liquid stocks", p), ("F&O stocks only", p[fo])):
        for h in (1, 5, 10, 20):
            for name, feats in sets.items():
                if uni_name == "all liquid stocks" and "OI" in name:
                    continue
                res, w = ridge_eval(uni, feats, h)
                rows.append({"universe": uni_name, "hold": h, "model": name, "train_ic": res["train"]["ic"], "val_ic": res["val"]["ic"],
                             "val_ic_t": res["val"]["ic_t"], "val_top_net": res["val"]["top_net"], "val_top_exc": res["val"]["top_exc"],
                             "val_top_t_exc": res["val"]["top_t_exc"]})
                print("%-18s h=%-2d %-16s train IC %+.4f | VAL IC %+.4f (t %.2f) top-decile net %+.2f%% excess %+.2f%% (t %.2f)" % (
                    uni_name, h, name, res["train"]["ic"], res["val"]["ic"], res["val"]["ic_t"], 100 * res["val"]["top_net"],
                    100 * res["val"]["top_exc"], res["val"]["top_t_exc"]), flush=True)
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "round8_incremental.csv"), index=False)


def stage_b():
    p = pd.read_pickle(os.path.join(CACHE, "panel8.pkl"))
    a, b = R7.split_dates(p)
    sa8 = pd.read_csv(os.path.join(OUT, "round8_stageA.csv"))
    sa7 = pd.read_csv(os.path.join(OUT, "stageA.csv"))
    L = p[p.liquid].copy()
    rows = []
    for h in (5, 10, 20):
        new = sa8[(sa8.hold == h) & (sa8.t_excess > 1.5)].sort_values("t_excess", ascending=False).drop_duplicates("feature").head(6)
        old = sa7[(sa7.hold == h) & (sa7.t_excess > 1.5)].sort_values("t_excess", ascending=False).drop_duplicates("feature").head(6)
        pool = [(r.feature, int(r.sign)) for r in new.itertuples()] + [(r.feature, int(r.sign)) for r in old.itertuples()]
        for f, _ in pool:
            if "r_" + f not in L:
                L["r_" + f] = L.groupby("d")[f].rank(pct=True)
        y = "y%d" % h
        for k in (2, 3, 4):
            for combo in itertools.combinations(pool, k):
                if not any(f in DELIV_FEATS + OI_FEATS for f, _ in combo):
                    continue                                  # round 7 already covered old-only combinations
                if len({f for f, _ in combo}) < k:
                    continue
                sc = sum((L["r_" + f] if s > 0 else 1 - L["r_" + f]) for f, s in combo) / k
                sub = L[["d", "liquid", y, "mkt_trend"]].assign(score=sc).dropna()
                res = {}
                for name, part in (("train", sub[sub.d < a]), ("val", sub[(sub.d >= a) & (sub.d < b)])):
                    port, exc = R7.decile_returns(part, "score", 1, h)
                    res[name] = (port.mean(), R7.tstat(port), exc.mean(), R7.tstat(exc), len(port))
                rows.append({"id": "B8-%d-%s" % (h, "+".join("%s%s" % ("" if s > 0 else "-", f) for f, s in combo)), "hold": h, "k": k,
                             "train_net": res["train"][0], "train_t": res["train"][1], "train_exc": res["train"][2], "train_t_exc": res["train"][3],
                             "val_net": res["val"][0], "val_t": res["val"][1], "val_exc": res["val"][2], "val_t_exc": res["val"][3],
                             "n_val": res["val"][4]})
    df = pd.DataFrame(rows)
    df["stable"] = (df.train_t_exc > 2) & (df.val_t_exc > 2) & (df.val_net > 0)
    df.sort_values(["stable", "val_t_exc"], ascending=False).to_csv(os.path.join(OUT, "round8_stageB.csv"), index=False)
    print("round 8 stage B: %d combinations with >= 1 new feature; stable (train and validation excess t > 2, validation net > 0): %d" % (
        len(df), int(df.stable.sum())))
    print(df.sort_values(["stable", "val_t_exc"], ascending=False).head(20)[["id", "train_net", "train_t_exc", "val_net", "val_exc", "val_t_exc", "n_val"]].to_string(index=False))


if __name__ == "__main__":
    {"features": features, "stageA": stage_a, "incremental": incremental, "stageB": stage_b}.get(
        sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()


def hypothesis():
    """User hypothesis (pre-specified 2026-11-11): delivery % > 65 AND futures long build-up (price up, total OI up) on day t.
    Event study: every qualifying liquid stock-day, entry next open, net of costs, vs the same day's universe and vs each condition alone."""
    p = pd.read_pickle(os.path.join(CACHE, "panel8.pkl"))
    a, b = R7.split_dates(p)
    q = p[p.liquid & p.oi_tot.notna()].copy()
    conds = {"deliv>65 AND long build-up": (q.deliv_pct > 65) & (q.long_build == 1),
             "deliv>65 alone": (q.deliv_pct > 65), "long build-up alone": (q.long_build == 1),
             "deliv>65 AND long build-up AND OI +2%": (q.deliv_pct > 65) & (q.long_build == 1) & (q.oi_chg1 > 0.02),
             "all F&O stock-days (baseline)": pd.Series(True, index=q.index)}
    lines = ["| condition | hold | period | events | mean net | t | excess vs F&O universe | t excess | win |", "|---|---|---|---|---|---|---|---|---|"]
    for h in (1, 3, 5, 10):
        y = "y%d" % h
        q["ex"] = q[y] - q.groupby("d")[y].transform("mean")
        for name, m in conds.items():
            for per, pm in (("train", q.d < a), ("validation", (q.d >= a) & (q.d < b)), ("seen-once 2025-26", q.d >= b)):
                s = q[m & pm & q[y].notna()]
                daily = s.groupby("d")[y].mean().iloc[::max(h, 1)]
                dex = s.groupby("d").ex.mean().iloc[::max(h, 1)]
                lines.append("| %s | %d | %s | %d | %+.2f%% | %.2f | %+.2f%% | %.2f | %.0f%% |" % (
                    name, h, per, len(s), 100 * s[y].mean(), R7.tstat(daily), 100 * s.ex.mean(), R7.tstat(dex), 100 * (s[y] > 0).mean()))
    text = "\n".join(lines)
    print(text)
    with open(os.path.join(OUT, "round8_hypothesis.md"), "w", encoding="utf-8") as fh:
        fh.write("# Hypothesis: delivery > 65 % + futures long build-up\n\n" + text + "\n")


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "hypothesis":
    hypothesis()


def intraday_check():
    """Follow-up found in `incremental`: the h=1 label is next-open -> next-close, i.e. an INTRADAY trade. Re-score the F&O
    '36 + both' ridge model with intraday costs (0.10 %, plus a 0.05 % extra-slippage stress) for the top decile (long) and the bottom
    decile (MIS short, allowed intraday). Model fitted on TRAIN only."""
    p = pd.read_pickle(os.path.join(CACHE, "panel8.pkl"))
    a, b = R7.split_dates(p)
    fo = p.groupby("sym").oi_tot.transform(lambda s: s.notna().mean()) > 0.5
    q = p[fo & p.liquid].copy()
    g = q.groupby("sym", group_keys=False)
    q["gross"] = g.c.shift(-1) / g.o.shift(-1) - 1                    # open->close of t+1, before costs
    q = q[q.gross.notna()]
    q["yx"] = q.gross - q.groupby("d").gross.transform("mean")
    feats = list(R7.FEATURES) + DELIV_FEATS + OI_FEATS
    X = ranked(q, feats)
    tr = (q.d < a).values
    A = X.values[tr]
    w = np.linalg.solve(A.T @ A + 10 * np.eye(A.shape[1]), A.T @ q.yx.values[tr])
    q["pred"] = X.values @ w
    r = q.groupby("d").pred.rank(pct=True)
    lines = ["| period | days | universe gross | top-decile gross | LONG net (0.10%) | stress (0.15%) | bottom-decile gross | SHORT net (0.10%) | stress (0.15%) | short t | short win days |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for per, m in (("train", q.d < a), ("validation", (q.d >= a) & (q.d < b)), ("seen-once 2025-26", q.d >= b)):
        s = q[m]
        rr = r[m]
        top = s[rr >= 0.9].groupby("d").gross.mean()
        bot = s[rr <= 0.1].groupby("d").gross.mean()
        uni = s.groupby("d").gross.mean()
        short = -bot - 0.001
        lines.append("| %s | %d | %+.3f%% | %+.3f%% | %+.3f%% | %+.3f%% | %+.3f%% | %+.3f%% | %+.3f%% | %.2f | %.0f%% |" % (
            per, len(uni), 100 * uni.mean(), 100 * top.mean(), 100 * (top.mean() - 0.001), 100 * (top.mean() - 0.0015),
            100 * bot.mean(), 100 * short.mean(), 100 * (short.mean() - 0.0005), R7.tstat(short), 100 * (short > 0).mean()))
    top_w = sorted(zip(feats, w), key=lambda z: -abs(z[1]))[:10]
    text = "\n".join(lines) + "\n\nLargest model weights (ranked features): " + ", ".join("%s %+.4f" % (f, x) for f, x in top_w)
    print(text)
    with open(os.path.join(OUT, "round8_intraday_check.md"), "w", encoding="utf-8") as fh:
        fh.write("# Intraday re-score of the F&O 36+delivery+OI model\n\n" + text + "\n")


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "intraday":
    intraday_check()
