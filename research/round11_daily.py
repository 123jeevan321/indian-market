"""Round 11 phases 1, 2, 6, 7 (daily level). Features are measured at the close of t-1 (known before day t opens); the outcome is day t.
Opening-gap features use day t's open (known at 09:15). Run: python research/round11_daily.py"""
import json, os, sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from round11 import panel, window, OUT, CACHE   # noqa: E402

FEATS = {  # name: (description, condition on columns known before the outcome)
    "contraction": ("volatility contraction: ATR ratio < 0.8 (t-1)", lambda x: x.atr_comp_p < 0.8),
    "sideways10": ("sideways: |10-day return| < 3% (t-1)", lambda x: x.ret10_p.abs() < 0.03),
    "vol_rising": ("volume rising: 5-day avg / 20-day avg > 1.3 (t-1)", lambda x: x.rvol5_p > 1.3),
    "rvol_prev": ("previous-day volume > 2x its 20-day average", lambda x: x.rvol_p > 2),
    "deliv_high": ("previous-day delivery % > 20-day avg + 10 points", lambda x: x.deliv_z_p > 10),
    "deliv_low": ("previous-day delivery % < 20-day avg - 10 points", lambda x: x.deliv_z_p < -10),
    "oi_up5": ("futures OI up > 10% over 5 days (t-1)", lambda x: x.oi_chg5_p > 0.10),
    "long_build": ("long build-up at t-1 (price up, OI up)", lambda x: x.long_build_p == 1),
    "short_cover": ("short covering at t-1 (price up, OI down)", lambda x: x.short_cover_p == 1),
    "short_build": ("short build-up at t-1 (price down, OI up)", lambda x: x.short_build_p == 1),
    "rs_nifty": ("beats NIFTY over 60 days (t-1)", lambda x: x.rs60_p > 0),
    "rs_sector": ("beats its sector over 20 days (t-1)", lambda x: x.rs_ind20_p > 0),
    "sector_hot": ("sector up > 2% over 5 days (t-1)", lambda x: x.ind_ret5_p > 0.02),
    "ret5_up": ("up > 5% over the previous 5 days", lambda x: x.ret5_p > 0.05),
    "ret5_down": ("down > 5% over the previous 5 days", lambda x: x.ret5_p < -0.05),
    "strong_close": ("previous day closed in the top 20% of its range", lambda x: x.clv_p > 0.8),
    "weak_close": ("previous day closed in the bottom 20% of its range", lambda x: x.clv_p < 0.2),
    "wide_prev": ("previous-day range > 1.5 ATR", lambda x: x.range_atr_p > 1.5),
    "near_52wk_high": ("within 5% of the 250-day high (t-1)", lambda x: x.near_hi250_p > 0.95),
    "brk20_prev": ("closed at a new 20-day high at t-1", lambda x: x.brk_hi20_p == 1),
    "higher_lows": ("3 rising daily lows into t-1", lambda x: x.hl3_p == 1),
    "gap_up1": ("day-t opening gap > +1% (known at 09:15)", lambda x: x.gap > 0.01),
    "gap_down1": ("day-t opening gap < -1% (known at 09:15)", lambda x: x.gap < -0.01),
}
PRE = ["ret5_p", "ret10_p", "ret20_p", "atr_comp_p", "rvol5_p", "rvol_p", "deliv_pct_p", "deliv_z_p", "oi_chg1_p", "oi_chg5_p",
       "basis_chg_p", "rs60_p", "rs_ind20_p", "ind_ret5_p", "clv_p", "range_atr_p", "near_hi250_p", "brk_hi20_p", "hl3_p", "gap", "nifty_ret"]


def prep(p):
    g = p.groupby("sym")
    p["ret10"] = p.c / g.c.shift(10) - 1
    p["hl3"] = ((p.l > g.l.shift(1)) & (g.l.shift(1) > g.l.shift(2)) & (g.l.shift(2) > g.l.shift(3))).astype(float)
    g = p.groupby("sym")
    for c in ("atr_comp", "ret10", "rvol5", "rvol", "deliv_z", "oi_chg5", "long_build", "short_cover", "short_build", "rs60", "rs_ind20",
              "ind_ret5", "ret5", "clv", "range_atr", "near_hi250", "brk_hi20", "hl3", "deliv_pct", "ret20", "basis_chg", "oi_chg1"):
        p[c + "_p"] = g[c].shift()
    p["avgval_cr_p"] = g.avgval20.shift() / 1e7
    return p


def lift_table(df, ev_col):
    base = df[ev_col].mean()
    rows = []
    for k, (desc, fn) in FEATS.items():
        m = fn(df).fillna(False).astype(bool)
        n = int(m.sum())
        if n < 30 or not base:
            rows.append({"feature": k, "desc": desc, "n": n}); continue
        pr = df.loc[m, ev_col].mean()
        se = np.sqrt(pr * (1 - pr) / n)
        rows.append({"feature": k, "desc": desc, "n": n, "share_of_days_pct": round(100 * n / len(df), 1), "p_event_pct": round(100 * pr, 2),
                     "base_pct": round(100 * base, 2), "lift": round(pr / base, 2), "lift_lo": round((pr - 1.96 * se) / base, 2),
                     "lift_hi": round((pr + 1.96 * se) / base, 2)})
    return rows


def rec(r, cols):
    return {k: (str(r[k])[:10] if k == "d" else round(float(r[k]), 4) if isinstance(r[k], (float, np.floating)) else r[k]) for k in cols}


def main():
    p = prep(panel())
    w = window(p)
    W = p[p.d.isin(w) & p.tradable].copy()
    H = p[(p.d < w[0]) & p.tradable].copy()
    res = {"window": [str(w[0])[:10], str(w[-1])[:10]], "stock_days": len(W), "symbols": int(W.sym.nunique())}
    cols = ["sym", "d", "ind", "cc", "oc", "to_high", "to_low", "hl", "avgval_cr_p", "prev_c", "c"]

    def top(df, col, asc=False):
        return [rec(r, cols) for _, r in df.sort_values(col, ascending=asc).drop_duplicates("sym").head(20).iterrows()]
    res["top_gainers_cc"] = top(W, "cc")
    res["top_losers_cc"] = top(W, "cc", True)
    res["top_open_to_close"] = top(W, "oc")
    res["top_to_high"] = top(W, "to_high")
    res["top_to_low"] = top(W, "to_low", True)
    res["top_range_small_close"] = top(W[W.cc.abs() < 0.01], "hl")
    rep = W[W.cc >= 0.03].groupby("sym").size().sort_values(ascending=False)
    res["repeat_gainers"] = []
    for s, n in rep.head(20).items():
        x = W[W.sym == s]
        res["repeat_gainers"].append({"sym": s, "days_up_3pct": int(n), "window_return_pct": round(100 * float(x.c.iloc[-1] / x.prev_c.iloc[0] - 1), 1)})
    res["move_counts"] = {("+" if s > 0 else "-") + str(k): int(((W.cc >= k / 100) if s > 0 else (W.cc <= -k / 100)).sum())
                          for k in (2, 3, 5, 8) for s in (1, -1)}
    res["range_counts"] = {"hl>=3%": int((W.hl >= 0.03).sum()), "hl>=5%": int((W.hl >= 0.05).sum()),
                           "to_high>=3%": int((W.to_high >= 0.03).sum()), "to_low<=-3%": int((W.to_low <= -0.03).sum()),
                           "big_range_small_close (hl>=4%, |cc|<1%)": int(((W.hl >= 0.04) & (W.cc.abs() < 0.01)).sum())}
    res["closed_at_high_ge_4.5pct"] = int(((W.cc >= 0.045) & ((W.c - W.h).abs() < 1e-6)).sum())

    def profile(events):
        out = []
        for e in events:
            r = W[(W.sym == e["sym"]) & (W.d == pd.Timestamp(e["d"]))].iloc[0]
            out.append(dict({"sym": e["sym"], "d": e["d"], "cc": e["cc"]}, **{k: (None if pd.isna(r[k]) else round(float(r[k]), 4)) for k in PRE}))
        return out
    res["pre_gainers"] = profile(res["top_gainers_cc"])
    res["pre_losers"] = profile(res["top_losers_cc"])
    med = lambda df: {k: (None if df[k].dropna().empty else round(float(df[k].median()), 4)) for k in PRE}
    res["median_pre"] = {"top20_gainers": med(pd.DataFrame(res["pre_gainers"])), "top20_losers": med(pd.DataFrame(res["pre_losers"])),
                         "all_up3_days": med(W[W.cc >= 0.03]), "all_down3_days": med(W[W.cc <= -0.03]), "all_stock_days": med(W)}
    for D in (W, H):
        D["up3"], D["dn3"], D["abs3"] = (D.cc >= 0.03).astype(float), (D.cc <= -0.03).astype(float), (D.cc.abs() >= 0.03).astype(float)
    W["up3_hi"] = (W.to_high >= 0.03).astype(float)
    res["lift_window"] = {k: lift_table(W, k) for k in ("up3", "dn3", "abs3", "up3_hi")}
    res["lift_history"] = {k: lift_table(H, k) for k in ("up3", "dn3", "abs3")}
    res["history"] = {"rows": len(H), "start": str(H.d.min())[:10], "end": str(H.d.max())[:10],
                      "up3_pct": round(100 * H.up3.mean(), 2), "dn3_pct": round(100 * H.dn3.mean(), 2)}
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, "r11_daily.json"), "w"), indent=1, default=str)
    W[["sym", "d", "ind", "cc", "oc", "to_high", "to_low", "hl", "o", "h", "l", "c", "prev_c"] + PRE].to_pickle(os.path.join(CACHE, "r11_window.pkl"))
    print(json.dumps({k: res[k] for k in ("window", "stock_days", "symbols", "move_counts", "range_counts", "closed_at_high_ge_4.5pct", "history")}, indent=1))
    for k in ("up3", "dn3", "abs3"):
        print("\nLIFT", k, "| window vs 5-year history before it")
        hw = {r["feature"]: r for r in res["lift_history"][k]}
        for r in res["lift_window"][k]:
            h = hw[r["feature"]]
            print("  %-15s win n=%5s lift %5s [%5s..%5s] | hist n=%7s lift %5s [%5s..%5s]" % (
                r["feature"], r["n"], r.get("lift"), r.get("lift_lo"), r.get("lift_hi"), h["n"], h.get("lift"), h.get("lift_lo"), h.get("lift_hi")))


if __name__ == "__main__":
    main()
