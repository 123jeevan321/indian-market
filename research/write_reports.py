"""Render docs/STRATEGY_COMPARISON.md, FINAL_STRATEGY.md, BACKTEST_RESULTS.md and RESEARCH_LOG.md from research/results/."""

import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(ROOT, "research", "results")
D = os.path.join(ROOT, "docs")


def fa(df):
    return "\n".join("| %s | %s%s | %d | %+.2f%% | %.2f | %+.2f%% | %.2f |" % (
        r.id, "" if r.sign > 0 else "-", r.feature, r.hold, 100 * r.mean_net, r.t_net, 100 * r.mean_excess, r.t_excess) for r in df.itertuples())


def fb(df):
    return "\n".join("| %s | %+.2f%% | %.2f | %.2f | %+.2f%% | %+.2f%% | %.2f |" % (
        r.id, 100 * r.train_mean, r.train_t, r.train_t_exc, 100 * r.val_mean, 100 * r.val_exc, r.val_t_exc) for r in df.itertuples())


sa = pd.read_csv(os.path.join(R, "stageA.csv"))
sb = pd.read_csv(os.path.join(R, "stageB.csv"))
final_md = open(os.path.join(R, "final.md"), encoding="utf-8").read()

A_HEAD = "| id | feature (sign) | hold | mean net/trade | t | excess vs universe | t excess |\n|---|---|---|---|---|---|---|\n"
comparison = """# Strategy comparison: all research rounds (2026-11-11)

## Earlier rounds (reports preserved)

| round | report | idea | data | result |
|---|---|---|---|---|
| 1 | docs/BACKTEST_2026-11-11.md | opening-range breakout/breakdown, intraday | 50 stocks, 59 days, 5m | lost Rs 56-90 per trade |
| 2 | docs/SWING_BACKTEST.md | 6 swing setups, 1-5 days | 477 stocks, 5y daily | all negative, none beat random |
| 3 | docs/SWING_BACKTEST.md | relative strength filter, 10-day hold, entry timing | same | only sweep+RS 10d positive, CI includes 0 |
| 4 | docs/MOMENTUM_BACKTEST.md | 2-stock sector-split rotation (BTST) | 200 stocks, 5y daily | 24 of 24 variants negative |
| 5-6 | docs/MATRIX_BACKTEST.md | ORB/FVG/RVOL/sweep/POC grid, same-day vs 2-day | 99 stocks, 5y 15-min | 216 combos: none positive in both periods |
| 7 | this document | cross-sectional discovery engine, 36 features, staged | 495 + 99 stocks | see below |

Why rounds 1-6 failed: all were fixed-target, fixed-stop event trades over 1-5 days. Over such short holds the costs (about 0.25 percent
round trip for delivery, 0.10 percent intraday) are a large share of the typical move, and the signals carried no measurable information
beyond noise. Stage A below confirms it: no feature reaches significance at 0, 1, 3 or 5-day holds.

## Round 7, stage A: %d single-feature tests on TRAIN (Nov 2021 to Nov 2024)

Bonferroni threshold |t| > 3.48: %d passed. %d had t > 2, all at 10- or 20-day holds.

Top 15 overall:

""" % (len(sa), int(sa.bonferroni_pass.sum()), int((sa.t_net > 2).sum())) + A_HEAD + fa(sa.sort_values("t_net", ascending=False).head(15)) + """

Best short-horizon results (hold 0-5 days), none significant:

""" + A_HEAD + fa(sa[sa.hold <= 5].sort_values("t_net", ascending=False).head(10)) + """

Several long-hold features look significant in BOTH signs (first-hour return up or down), which shows the raw t-statistic mostly reflects
the 2021-2024 bull market. The excess-vs-universe column is the honest measure.

## Round 7, stage B: %d combinations (2-3 features), TRAIN fit, VALIDATION check (Nov 2024 to Nov 2025)

Stable in both (train net t > 2, train excess t > 1.5, validation net and excess > 0): %d. Top 15 by validation excess t:

| id | train net | train t | train excess t | validation net | validation excess | validation excess t |
|---|---|---|---|---|---|---|
""" % (len(sb), int(sb.stable.sum())) + fb(sb.sort_values(["stable", "val_t_exc"], ascending=False).head(15)) + """

Recurring ingredients of the stable combinations: late-day volume concentration (lasthour_share_z, concept 17), relative illiquidity
within the Nifty 100 (amihud), quiet recent volume (-rvol, -rvol5) and a strong last hour (lasthour_ret), all with a 10-day hold. With
1,246 combinations, a validation t of about 3.4 is still within what chance produces (Bonferroni needs about 3.9), so ONE candidate was
pre-registered and tested once on the untouched TEST period (docs/FINAL_STRATEGY.md).
"""
open(os.path.join(D, "STRATEGY_COMPARISON.md"), "w", encoding="utf-8").write(comparison)

final_doc = """# Final strategy decision (round 7, 2026-11-11)

**Decision: NOT suitable for live trading. Paper-track only, as a research signal.** No strategy in seven rounds produced positive net
returns on an untouched out-of-sample period.

## The candidate sent to the final test

- Rule (pre-registered before the test): among liquid Nifty 100 stocks, rank each stock by (a) today's last-hour volume share minus its
  20-day average (closing-period accumulation) and (b) its 20-day Amihud illiquidity; average the two ranks; buy the top decile (about 10
  stocks; top 3 for a Rs 2 lakh account) at the next open; sell at the close of day 10. Long only. Delivery costs included.
- Chosen because it was the simplest combination positive in TRAIN and VALIDATION and beating the universe in both.

## Result on the untouched TEST period (Nov 2025 to Nov 2026)

- Net per trade -0.37 percent (t -0.48), hit rate 41 percent. It still beat the same 99-stock universe by +0.38 percent per 10-day trade
  (t 1.56) and beat random picks (-0.55 percent), but the market fell and the relative edge was too small to make money.
- The 3-feature variant failed outright (-0.91 percent net, excess -0.16 percent).
- Walk-forward by year: excess positive in 2022-2025, negative in 2026, so the edge is shrinking.
- Regime: positive only when NIFTY was above its 200-day EMA.
- Rupee simulation (Rs 2 lakh, top 3, every 10 days, TEST period): about -Rs 162 per week on average, 64 percent losing cycles,
  Rs 10,000 or more in 5 percent of 2-week cycles; 32 percent of single-stock trades lost more than Rs 1,500 (the rule has no stop).

## Full final-test output

""" + final_md.split("\n", 2)[2] + """

## Your weekly target, quantified

- The best edge measured anywhere (train period) is about +1.25 percent per 10-day trade in a rising market: on Rs 2 lakh about
  Rs 2,500 per two weeks (about Rs 1,250 a week), with large swings. Rs 5,000-10,000 a week (2.5-5 percent weekly) needs roughly 4-8 times
  that edge. On the untouched period even the best candidate averaged slightly below zero.
- A Rs 1,500 per-trade cap fits this 10-day signal only with about Rs 30,000 positions and a 5 percent stop, which shrinks the rupee result.

## Paper-tracking specification (no real money)

- Every second Friday after 15:35: rebuild the panel, rank the 99 stocks, list the top 3.
- Only when NIFTY is above its 200-day EMA.
- Paper-buy at the next open, paper-sell at the close of the 10th trading day; log net results after delivery costs.
- Review after 8-12 cycles. Consider small real money only if the paper excess AND net result are both positive.
"""
open(os.path.join(D, "FINAL_STRATEGY.md"), "w", encoding="utf-8").write(final_doc)

open(os.path.join(D, "BACKTEST_RESULTS.md"), "w", encoding="utf-8").write("""# Backtest results index (all rounds preserved)

| round | file | headline |
|---|---|---|
| 1 | docs/BACKTEST_2026-11-11.md | ORB intraday, 59 days: BUY -Rs 90/trade, SELL -Rs 56/trade |
| 2-3 | docs/SWING_BACKTEST.md | 6 swing setups, 5y: all negative; sweep+RS 10d +Rs 120 OOS (CI includes 0) |
| 4 | docs/MOMENTUM_BACKTEST.md | 2-stock rotation: 24 of 24 variants negative |
| 5-6 | docs/MATRIX_BACKTEST.md | 216 intraday combos on 15-min data: none positive in both periods |
| 7 | docs/STRATEGY_COMPARISON.md, docs/FINAL_STRATEGY.md | 432 single + 1,246 combination tests; the best candidate failed the untouched test |

Raw outputs: research/results/stageA.csv, stageB.csv, final.md, preregistered.json. IDs: A#### single features, B<hold>-<features> combos.
""")

open(os.path.join(D, "RESEARCH_LOG.md"), "w", encoding="utf-8").write("""# Research log

## 2026-11-11: round 7 complete (stages 0-3)

- Stage 0: data inventory (docs/INSTITUTIONAL_RESEARCH.md section 2). Local caches (git-ignored): trader/cache/daily5y and trader/cache/m15.
- Stage 1: 100-concept library in research/concepts.py, rendered in docs/INSTITUTIONAL_RESEARCH.md.
- Stage 2: engine research/discovery.py with build, stageA (432 tests), stageB (1,246 combinations), final (pre-registered test).
- Stage 3: the final test failed (docs/FINAL_STRATEGY.md). The Nov 2025 to Nov 2026 window is now USED; new candidates need forward
  paper data or new recordings for their final test.

## Next stages (resume here)

1. Delivery-percent history: 5 years of NSE sec_bhavdata_full files (trader-flows/flows.py fetch_day); add concepts 84-85; rerun stages
   A-B on TRAIN and VALIDATION only.
2. F&O OI history from the NSE F&O bhavcopy archive for concepts 61-67 and 73-74.
3. Order flow: record 10 stocks daily for 4-8 weeks (trader-flows/angel_recorder.py record ...), then test concepts 4-13 with
   angel_recorder.py flow. This is the only route to genuine absorption and aggression evidence.
4. Machine learning (concept 98): pip install scikit-learn; gradient boosting on the stage-A features with the same splits; accept only if it
   beats the rank-average combinations on VALIDATION.
5. Final tests from now on are forward paper-tracking (spec in docs/FINAL_STRATEGY.md).

Resume:
    python research/discovery.py build
    python research/discovery.py stageA
    python research/discovery.py stageB
    python research/write_reports.py
""")
print("reports written")
