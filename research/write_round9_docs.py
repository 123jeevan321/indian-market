"""Write the seven Round 9 documents from research/results/r9_* outputs."""

import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(ROOT, "research", "results")
D = os.path.join(ROOT, "docs")
inv = open(os.path.join(R, "r9_inventory_table.md"), encoding="utf-8").read()
sel = open(os.path.join(R, "r9_selector.md"), encoding="utf-8").read()
two = open(os.path.join(R, "r9_twopct.md"), encoding="utf-8").read()


def regime_md(dim):
    t = pd.read_csv(os.path.join(R, "r9_regime_%s.csv" % dim), header=[0, 1], index_col=0)
    m, n = t["mean"] * 100, t["count"]
    cols = list(m.columns)
    out = ["| strategy | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for s in m.index:
        out.append("| %s | " % s + " | ".join("%+.2f%% (%d)" % (m.at[s, c], n.at[s, c]) if pd.notna(m.at[s, c]) else "-" for c in cols) + " |")
    best = ["| %s | %s (%+.2f%%) |" % (c, m[c].idxmax(), m[c].max()) for c in cols]
    return "\n".join(out), "\n".join(["| condition | best strategy (train+validation) |", "|---|---|"] + best)


c = pd.read_csv(os.path.join(R, "r9_corr.csv"), index_col=0)
corr_md = "| | " + " | ".join(x.split("_")[0] for x in c.columns) + " |\n|---|" + "---|" * len(c.columns) + "\n" + "\n".join(
    "| %s | " % i + " | ".join("%.2f" % v if pd.notna(v) else "-" for v in c.loc[i]) + " |" for i in c.index)
cf = pd.read_csv(os.path.join(R, "r9_cofail.csv"))
cf_top = cf.sort_values("B_positive_when_A_negative", ascending=False).head(8)
cf_md = "| A | B | days both negative | B positive when A negative | common days |\n|---|---|---|---|---|\n" + "\n".join(
    "| %s | %s | %.0f%% | %.0f%% | %d |" % (r.A, r.B, 100 * r.both_negative_share, 100 * r.B_positive_when_A_negative, r.common_days) for r in cf_top.itertuples())

HDR = "Round 9, 2026-11-12. All returns are NET percent per trade (delivery 0.25 %, intraday 0.12 % incl. slippage). Periods: train < 2024-11-11 <= validation < 2025-11-11 <= seen-once (used by rounds 7-8, never used for selection here).\n\n"

docs = {}
docs["ROUND9_FULL_AUDIT.md"] = "# Round 9: full audit of Rounds 1-8\n\n" + HDR + """## Inventory of what was tested before

| round | strategy family | entry | exit / stop / target | hold | data | trades | result |
|---|---|---|---|---|---|---|---|
| 1 | opening-range breakout, BUY and SELL | 5-min close beyond 15-min range | stop range mid, target 1.5R, flat 15:15 | intraday | 50 stocks, 59 days | 3,416 | -Rs 90 / -Rs 56 per trade |
| 2 | squeeze, sweep, CHoCH, EMA pullback, week-high, FVG | daily signals, next open | half at 1.5R, stop to entry, rest 3R, day 5 | 1-5 days | 477 stocks, 5y | ~3,000 | all negative, none beat random |
| 3 | + relative strength, 10-day hold, entry timing | same | same | 5-10 days | same | ~1,000 | only sweep+RS 10d positive (CI incl. 0) |
| 4 | 2-stock sector-split rotation (BTST) | +1.5-3.5 % day, RVOL > 2, strong close | +2.5-3.5 % target, 1.5 % / structural stop, day 2 | 1-2 days | 200 stocks, 5y | 24 variants | all negative |
| 5-6 | ORB/FVG/RVOL/sweep/POC matrix | 15-min triggers to 10:30 | structural stop, 1.5-3 % target, same day or 2 days | 0-2 days | 99 stocks, 5y 15-min | 216 combos | none positive in both periods |
| 7 | 36-feature cross-sectional discovery | decile ranks | fixed holds 0-20 days | 0-20 days | 495 stocks | 432 + 1,246 tests | final candidate failed (-0.37 %) |
| 8 | delivery % and futures OI | decile ranks, events | fixed holds | 0-20 days | 495 + 275 F&O | 288 + 299 tests | real relative signals, no long trade beats costs |

Raw trade lists were NOT saved by earlier rounds (only summary tables), so Round 9 rebuilt the twelve representative strategies below on
ONE common dataset and calendar, trade by trade, so they can be compared on the same dates.

## Rebuilt strategies (trade-level, common dates)

| strategy | train mean (trades) | validation | seen-once | win rate train / val / seen | max drawdown (sum of daily mean returns, pct points) |
|---|---|---|---|---|---|
""" + inv + """

Definitions: research/round9.py `STRATS`. Duplicates found: R1 ORB = R5 ORB15 (I1); R2 sweep = R6 SWEEP = R3 sweep+RS (D6/I3);
R2 squeeze, week-high and R4 rotation are the same breakout-on-volume idea (D5/D7); R7 `ret60`, `rs60` and `dist_ema50` are one momentum
feature; R8 `long_build` and `oi_chg1` overlap. Experiments counted so far: Rounds 1-8 about 2,500; Round 9 adds 12 streams, 4 regime
dimensions, 1 pre-specified selector and 20 target/filter cells in the 2 % study.
"""

docs["ROUND9_FAILURE_ANALYSIS.md"] = "# Round 9: why each strategy failed\n\n" + HDR + """| strategy | main cause (A-I) | evidence |
|---|---|---|
| I1 ORB long, I2 ORB short, I3 PDL sweep (intraday) | G insufficient edge, F costs | gross edge about 0 in every regime, period and gap type; 36-41 % win; costs 0.12 % turn ~0 into -0.1 % |
| D5 breakout 5d | A wrong direction / false breakouts, G | negative in ALL trend, volatility and gap regimes; worst in strong bear (-2.0 %); breakouts mean-revert over 5 days in this universe |
| D7 BTST 2d | F costs, A | negative everywhere; delivery STT on both legs (0.2 %) larger than any edge; strong closes do not continue |
| D4 reversal 5d | D regime | positive only in high volatility (+0.57 %) and after gaps (+0.44 / +0.66 %), negative in mid volatility and weak bull |
| D6 sweep 5d | D regime, I changing behaviour | +0.69 % train, -0.25 % validation; works in high volatility (+1.56 %) and after gaps; fails in bear trends |
| D1 momentum 10d | D regime, I | strong in strong trends both ways (+1.1 %), loses in weak bear (-1.27 %); +1.11 % train vs -0.14 % validation |
| D2 R7 candidate 10d | I overfitting / changing behaviour | chosen in Round 7 on train data: +1.11 % train, +0.19 % validation, -0.25 % seen-once |
| D3 R8 delivery+basis 5d | F costs, G | positive relative edge, but +0.16 / +0.09 / -0.07 % net per trade |
| D8 OI-model intraday short | I decay, F slippage | +0.20 % -> +0.07 % -> +0.06 %; the best stream on drawdown (13 pct points) but below 0.05 % extra slippage tolerance |
| D9 OI-model intraday long | G | about 0 before costs |

Patterns across all strategies:
- **Entry timing is not the main problem**: intraday entries at 9:30-10:30 and daily entries at the next open give the same sign.
- **Stops**: tight intraday stops (range mid) produce 36-41 % win rates; the 2 % study (below) shows the 1 % stop is hit first on about a
  third of days even without a signal, so the stop distance is inside normal noise.
- **Targets of 2 % or more are reached by only 9-11 % of 10:00 entries** before the close.
- **Costs** convert every near-zero gross edge into a loss; delivery strategies held 1-2 days are hit hardest.
- **Regime dependence is real but unstable**: the regimes where D1/D2/D6 worked in training did not reproduce in validation.
- Data/implementation (H): no material problems found; known limits are survivorship bias and 15-minute bar granularity.
"""

trend_md, trend_best = regime_md("trend")
vol_md, vol_best = regime_md("vol")
gap_md, gap_best = regime_md("gap_today")
br_md, br_best = regime_md("breadth")
docs["ROUND9_STRATEGY_CROSS_COMPARISON.md"] = "# Round 9: strategies compared on the same dates\n\n" + HDR + """## By NIFTY trend (regime known at the previous close), train + validation, mean net per trade (trades)

""" + trend_md + "\n\n" + trend_best + """

## By NIFTY volatility (20-day realised vol, terciles fixed on TRAIN)

""" + vol_md + "\n\n" + vol_best + """

## By market breadth (share of liquid stocks above their 50-day EMA)

""" + br_md + "\n\n" + br_best + """

## By today's NIFTY opening gap (intraday strategies can use it; daily strategies enter at this open)

""" + gap_md + "\n\n" + gap_best + """

## Do strategies make money when others lose? (daily streams, train + validation)

Median correlation between strategy daily returns: %.2f. The median share of days where B was positive when A was negative is only
%.0f %%: **most strategies lose on the same days**, because they are all long cash equities exposed to the same market move. The only strongly
negative correlations are mechanical (the OI model's long and short ends, ORB long vs ORB short).

Pairs where B most often made money on A's losing days:

""" % (np.nanmedian(c.where(~np.eye(len(c), dtype=bool)).values), 100 * cf.B_positive_when_A_negative.median()) + cf_md + """

Full correlation matrix:

""" + corr_md + "\n"

docs["ROUND9_MARKET_REGIMES.md"] = "# Round 9: market regime engine\n\n" + HDR + """Inputs, all known at the decision time (the previous close; the opening gap only for intraday use at 9:15):

| dimension | rule | why |
|---|---|---|
| trend | NIFTY 20-day return within +-1.5 % -> sideways; else close > EMA50 > EMA200 and 20-day return > +2 % -> strong bull; close > EMA200 -> weak bull; close < EMA50 < EMA200 and 20-day return < -2 % -> strong bear; else weak bear | one label per day, no contradictions (precedence order) |
| volatility | NIFTY 20-day realised volatility, low / mid / high terciles with thresholds fixed on TRAIN | avoids look-ahead in the cut-offs |
| breadth | share of liquid stocks above their 50-day EMA: < 40 % weak, 40-60 % mixed, > 60 % strong | participation |
| opening gap | NIFTY open vs previous close: > +0.5 % up, < -0.5 % down, else flat | intraday only |

Tested and not kept as separate dimensions: delivery % and futures OI are stock-level signals (Round 8), not market regimes; ADX and
breakout/reversal "environments" duplicated trend and volatility. Code: research/round9.py `regimes()`.

Finding: regimes DO change which strategy looks best (tables in ROUND9_STRATEGY_CROSS_COMPARISON.md: momentum best in strong trends,
reversal and sweep best in high volatility and after gaps, every intraday breakout negative everywhere). The question is whether that
ranking is stable enough to select on: see the selection engine.
"""

docs["ROUND9_STRATEGY_SELECTION_ENGINE.md"] = "# Round 9: regime -> strategy selection engine\n\n" + HDR + """Design (fixed before running, no tuning):
1. Each month, look only at history ending 30 calendar days before the month starts (embargo for overlapping holds).
2. For today's regime (trend x volatility; if fewer than 30 past days in that cell, trend only), compute each strategy's past mean daily
   return and t-statistic in that regime.
3. Trade the strategy with the highest past mean among those with t > 2 and mean > 0. Otherwise NO TRADE.
4. Compare with the equal-weight mix of all 12 strategies and with the best single strategy chosen on TRAIN.

Results (mean net return per trade on days the method traded; "pct points" = sum of daily mean returns):

""" + sel + """

Reading:
- The selector looked good in its own walk-forward training years (+0.42 % per traded day, t 2.3) and then LOST in validation (-0.33 %,
  t -1.0) and in 2025-26 (-0.07 %). The regime->strategy ranking did not persist.
- It spent most days in D2 (the Round 7 candidate) and D1 (momentum), the two strategies whose edges decayed; switching added drawdown.
- Equal weighting smoothed drawdown (48-75 pct points vs 95-150) but every out-of-sample period was negative.
- No-trade was chosen on 46 % of days, so the rule was already strict.
Risk policy used: one strategy per day, no stacking, positions sized per strategy rules; this did not change the sign of the result.
"""

docs["ROUND9_BACKTEST_RESULTS.md"] = "# Round 9: backtest results\n\n" + HDR + "## Strategy streams\n\n| strategy | train | validation | seen-once | win rate | max DD |\n|---|---|---|---|---|---|\n" + inv + "\n\n## Selector vs single vs equal weight\n\n" + sel + "\n\n## The 2 % daily opportunity (15-minute data, 99 Nifty 100 stocks)\n\n" + two + """

Distinctions you asked for:
- A stock moving 2 % in a day: about 35-39 % of stock-days touch +-2 % from the open.
- Our trade capturing 2 %: a long entered at 10:00 with a 1 % stop reaches +2 % first on only 9-11 % of days; the stop is hit first on
  33-36 %; net expectancy -0.09 % to -0.14 % per trade at every target from 0.5 % to 2.5 %, in both validation and 2025-26.
- A 2 % net return on deployed capital needs the trade to capture more than 2.12 % after costs.
- A 2 % return on the whole Rs 2 lakh account (Rs 4,000) needs every rupee deployed and that capture, every day.
Adverse excursion: the median 10:00 entry first moves 0.7 % against you before the close.
"""

docs["ROUND9_FINAL_CONCLUSION.md"] = "# Round 9: final conclusion\n\n" + HDR + """## Can we select, for each market condition, the strategy with the strongest independently validated performance?

**Not with the strategies we have.** The data supports half of your hypothesis and rejects the other half.

What holds:
- Market conditions DO change which strategy works: momentum in strong trends, reversal and sweep-reclaim in high volatility and after
  gaps, and the intraday breakout family fails in every condition.

What fails:
1. **The rankings are not stable out of sample.** A walk-forward selector that only used past data earned +0.42 % per traded day in its
   training years, then -0.33 % in validation and -0.07 % in 2025-26.
2. **Strategies lose together.** Median correlation 0.20; on a typical strategy's losing days, the other strategies were positive only
   about a third of the time, because all long cash strategies share the market move.
3. **No component has a durable positive edge after costs.** A selector can only choose among components; it cannot create an edge
   that none of them has. The best component (the Round 8 intraday OI short) decays to break-even after realistic slippage.
4. **The 2 % day is common for stocks (35-39 % of days touch +-2 %) but not capturable**: from a 10:00 entry, the target is hit first on
   about 10 % of days and every target from 0.5 % to 2.5 % loses after costs.

What would have to change for a "yes":
- At least two components with positive out-of-sample net expectancy and low correlation (for example, a genuine short or hedged leg:
  intraday shorts are allowed, F&O hedges are excluded by your rules).
- Order-flow evidence from the Angel recorder (still not collected) as a new, non-price input.
- Forward paper results, because every historical window has now been used for selection at least once.

Recommendation: keep capital out of these rules. Continue the Round 8 paper-tracking separately, start the Angel recorder, and re-run
this Round 9 engine (`python research/round9.py streams && ... select`) when 3-6 months of forward data exist.
"""

for name, text in docs.items():
    with open(os.path.join(D, name), "w", encoding="utf-8") as fh:
        fh.write(text)
print("wrote", len(docs), "docs")
