"""Round 11 phases 8-9: pre-registered setups, tested ONLY on history before the 30-session discovery window, chronological 60/20/20.

Pre-registered 2026-11-12 (before any backtest was run). Daily setups use t-1 information and trade day t from the open; opening setups
use the first 15-minute bar (09:15-09:30) and trade from the 09:30 bar's open (Nifty 100 only: 5 years of Angel 15-minute bars).
Exit models: (1) close of day t; (2) +2% target / -1% stop, stop first when one bar touches both, else the close.
Costs: 0.12% round trip (Zerodha intraday charges + slippage), deducted from every trade. Shorts are intraday MIS only.
Run: python research/round11_backtest.py
"""
import glob, json, os, sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from round11 import panel, window, OUT          # noqa: E402
from round11_daily import prep                  # noqa: E402

M15 = os.path.join(os.path.dirname(HERE), "trader", "cache", "m15")
COST = 0.0012
TGT, STP = 0.02, 0.01

DAILY_SETUPS = {   # name: (side, description, condition on the panel row)
    "B_sector_leader": ("long", "beats sector (20d) and NIFTY (60d), sector up >2% in 5 days, stock 5-day return 0..5%",
                        lambda x: (x.rs_ind20_p > 0) & (x.rs60_p > 0) & (x.ind_ret5_p > 0.02) & x.ret5_p.between(0, 0.05)),
    "D_breakout_absorb": ("long", "new 20-day closing high at t-1 on volume >= 1.5x, closed in top 30% of range",
                          lambda x: (x.brk_hi20_p == 1) & (x.rvol_p >= 1.5) & (x.clv_p > 0.7)),
    "E_futures_cash": ("long", "long build-up at t-1, delivery % >= 5 points above average, close in upper 40% of range",
                       lambda x: (x.long_build_p == 1) & (x.deliv_z_p > 5) & (x.clv_p > 0.6)),
    "A_quiet_accum_daily": ("long", "contraction (ATR ratio < 0.8), sideways 10 days, delivery above average, volume rising",
                            lambda x: (x.atr_comp_p < 0.8) & (x.ret10_p.abs() < 0.03) & (x.deliv_z_p > 5) & (x.rvol5_p > 1.1)),
    "F_gap_up_daily": ("long", "day-t gap >= +3% (proxy for an overnight catalyst); buy the open", lambda x: x.gap >= 0.03),
    "F_gap_down_short": ("short", "day-t gap <= -3%; short the open (MIS)", lambda x: x.gap <= -0.03),
    "V_volume_spike_long": ("long", "previous-day volume >= 2x and previous day up (Round 11 discovery: lifts move size)",
                            lambda x: (x.rvol_p >= 2) & (x.ret5_p > 0)),
}
OPEN_SETUPS = {
    "C_vol_progress_long": ("long", "09:15-09:30 volume >= 2x usual, price up >= 1%, close above the bar's typical price",
                            lambda x: (x.rvol15 >= 2) & (x.r15 >= 0.01) & (x.c0 > x.tp0)),
    "C_vol_progress_short": ("short", "volume >= 2x, price down >= 1%, close below typical price (MIS short)",
                             lambda x: (x.rvol15 >= 2) & (x.r15 <= -0.01) & (x.c0 < x.tp0)),
    "F_gap_continue_long": ("long", "gap >= +2% and the first 15 minutes keep rising on volume >= 2x", lambda x: (x.gap >= 0.02) & (x.r15 > 0) & (x.rvol15 >= 2)),
    "F_gap_continue_short": ("short", "gap <= -2% and the first 15 minutes keep falling on volume >= 2x", lambda x: (x.gap <= -0.02) & (x.r15 < 0) & (x.rvol15 >= 2)),
    "A_quiet_then_open": ("long", "quiet accumulation (as A) at t-1, then 09:15-09:30 volume >= 2x and price up >= 0.5%",
                          lambda x: (x.atr_comp_p < 0.8) & (x.ret10_p.abs() < 0.03) & (x.deliv_z_p > 0) & (x.rvol15 >= 2) & (x.r15 >= 0.005)),
    "X_absorb_fade": ("short", "volume >= 2x but |price change| < 0.3% in the first 15 minutes (absorption) after a 5-day rise > 5%",
                      lambda x: (x.rvol15 >= 2) & (x.r15.abs() < 0.003) & (x.ret5_p > 0.05)),
}


def m15_frame():
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
        g = df.groupby("d")
        first = df[df.slot == 0].set_index("d")
        rest = df[df.slot >= 1]
        e = rest[rest.slot == 1].set_index("d").o
        day = pd.DataFrame({"o0": first.o, "h0": first.h, "l0": first.l, "c0": first.c, "v0": first.v, "e": e,
                            "close": g.c.last(), "hi_after": rest.groupby("d").h.max(), "lo_after": rest.groupby("d").l.min()}).dropna()
        # target/stop path on 15-minute bars after entry (stop first on a bar touching both)
        res = {}
        for d, grp in rest.groupby("d"):
            if d not in day.index:
                continue
            en = day.at[d, "e"]
            out = {"long": None, "short": None}
            for _, b in grp.sort_values("slot").iterrows():
                if out["long"] is None:
                    if b.l <= en * (1 - STP): out["long"] = -STP
                    elif b.h >= en * (1 + TGT): out["long"] = TGT
                if out["short"] is None:
                    if b.h >= en * (1 + STP): out["short"] = -STP
                    elif b.l <= en * (1 - TGT): out["short"] = TGT
            res[d] = out
        day["ts_long"] = [res.get(d, {}).get("long") for d in day.index]
        day["ts_short"] = [res.get(d, {}).get("short") for d in day.index]
        day["sym"] = sym
        day["rvol15"] = day.v0 / day.v0.rolling(20, min_periods=10).mean().shift()
        day["r15"] = day.c0 / day.o0 - 1
        day["tp0"] = (day.h0 + day.l0 + day.c0) / 3
        rows.append(day.reset_index())
    return pd.concat(rows, ignore_index=True)


def trade_stats(r, label):
    r = r.dropna()
    if len(r) < 2:
        return {"setup": label, "n": int(len(r))}
    m, se = r.mean(), r.std() / np.sqrt(len(r))
    wins, losses = r[r > 0], r[r <= 0]
    streak = cur = 0
    for x in r:
        cur = cur + 1 if x <= 0 else 0
        streak = max(streak, cur)
    eq = r.cumsum()
    return {"setup": label, "n": int(len(r)), "win_pct": round(100 * (r > 0).mean(), 1), "mean_pct": round(100 * m, 3),
            "ci_pct": [round(100 * (m - 2.6 * se), 3), round(100 * (m + 2.6 * se), 3)],          # ~Bonferroni over 13 setups
            "avg_win_pct": round(100 * wins.mean(), 3) if len(wins) else 0, "avg_loss_pct": round(100 * losses.mean(), 3) if len(losses) else 0,
            "profit_factor": round(wins.sum() / -losses.sum(), 2) if losses.sum() else None,
            "max_dd_pct_points": round(100 * float((eq - eq.cummax()).min()), 1), "max_losing_streak": int(streak),
            "rs_per_trade_on_1lakh": round(1e5 * m, 0)}


def evaluate(df, setups, ret_cols, period_col):
    out = {}
    for name, (side, desc, fn) in setups.items():
        m = fn(df).fillna(False).astype(bool)
        s = df[m].sort_values("d")
        res = {"side": side, "desc": desc}
        for model, col in ret_cols[side].items():
            res[model] = {p: trade_stats(s.loc[s[period_col] == p, col], name) for p in ("TRAIN", "VALIDATION", "TEST")}
        res["per_month_TEST"] = round(len(s[s[period_col] == "TEST"]) / max(1, s.loc[s[period_col] == "TEST", "d"].dt.to_period("M").nunique()), 1)
        res["by_year_close_exit"] = {int(y): trade_stats(g[ret_cols[side]["close_exit"]], name).get("mean_pct") for y, g in s.groupby(s.d.dt.year)}
        if "mkt_trend" in s:
            res["by_market_trend_close_exit"] = {str(k): trade_stats(g[ret_cols[side]["close_exit"]], name).get("mean_pct") for k, g in s.groupby(s.mkt_trend)}
        out[name] = res
    return out


def split(df):
    days = sorted(df.d.unique())
    c1, c2 = days[int(0.6 * len(days))], days[int(0.8 * len(days))]
    df["period"] = np.where(df.d < c1, "TRAIN", np.where(df.d < c2, "VALIDATION", "TEST"))
    return [str(days[0])[:10], str(c1)[:10], str(c2)[:10], str(days[-1])[:10]]


def main():
    p = prep(panel())
    w = window(p)
    H = p[(p.d < w[0]) & p.tradable].copy()
    cuts = split(H)
    # daily setups: enter at the open of day t
    H["L_close"] = H.c / H.o - 1 - COST
    H["S_close"] = H.o / H.c - 1 - COST
    tl = np.where(H.l <= H.o * (1 - STP), -STP, np.where(H.h >= H.o * (1 + TGT), TGT, H.c / H.o - 1))
    ts = np.where(H.h >= H.o * (1 + STP), -STP, np.where(H.l <= H.o * (1 - TGT), TGT, H.o / H.c - 1))
    H["L_ts"], H["S_ts"] = tl - COST, ts - COST
    daily = evaluate(H, DAILY_SETUPS, {"long": {"close_exit": "L_close", "target_stop": "L_ts"},
                                       "short": {"close_exit": "S_close", "target_stop": "S_ts"}}, "period")
    base = {p_: trade_stats(H.loc[H.period == p_, "L_close"], "all_days_long") for p_ in ("TRAIN", "VALIDATION", "TEST")}
    # opening setups on Nifty 100 (15-minute bars)
    M = m15_frame()
    M = M.merge(H[["sym", "d", "prev_c", "atr_comp_p", "ret10_p", "deliv_z_p", "ret5_p", "mkt_trend", "period"]], on=["sym", "d"], how="inner")
    M["gap"] = M.o0 / M.prev_c - 1
    M["L_close"] = M.close / M.e - 1 - COST
    M["S_close"] = M.e / M.close - 1 - COST
    M["L_ts"] = M.ts_long.fillna(M.close / M.e - 1) - COST
    M["S_ts"] = M.ts_short.fillna(M.e / M.close - 1) - COST
    opening = evaluate(M, OPEN_SETUPS, {"long": {"close_exit": "L_close", "target_stop": "L_ts"},
                                        "short": {"close_exit": "S_close", "target_stop": "S_ts"}}, "period")
    obase = {p_: trade_stats(M.loc[M.period == p_, "L_close"], "nifty100_all_days_long_0930") for p_ in ("TRAIN", "VALIDATION", "TEST")}
    res = {"cuts": cuts, "history_rows": len(H), "opening_rows": len(M), "cost_round_trip_pct": 100 * COST,
           "baseline_daily_long_open_to_close": base, "baseline_nifty100_0930_to_close": obase, "daily": daily, "opening": opening}
    json.dump(res, open(os.path.join(OUT, "r11_backtest.json"), "w"), indent=1, default=str)
    print("cuts", cuts, "rows", len(H), "opening rows", len(M))
    for grp, R in (("DAILY", daily), ("OPENING", opening)):
        for name, r in R.items():
            for model in ("close_exit", "target_stop"):
                print("%-8s %-22s %-5s %-11s" % (grp, name, r["side"], model),
                      " | ".join("%s n=%s mean=%s%% win=%s%% ci=%s" % (p_[:3], r[model][p_].get("n"), r[model][p_].get("mean_pct"),
                                                                    r[model][p_].get("win_pct"), r[model][p_].get("ci_pct")) for p_ in ("TRAIN", "VALIDATION", "TEST")))
    print("baseline daily", {k: (v.get("n"), v.get("mean_pct")) for k, v in base.items()})
    print("baseline 09:30", {k: (v.get("n"), v.get("mean_pct")) for k, v in obase.items()})


if __name__ == "__main__":
    main()
