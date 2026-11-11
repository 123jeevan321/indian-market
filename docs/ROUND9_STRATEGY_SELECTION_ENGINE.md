# Round 9: regime -> strategy selection engine

Round 9, 2026-11-12. All returns are NET percent per trade (delivery 0.25 %, intraday 0.12 % incl. slippage). Periods: train < 2024-11-11 <= validation < 2025-11-11 <= seen-once (used by rounds 7-8, never used for selection here).

Design (fixed before running, no tuning):
1. Each month, look only at history ending 30 calendar days before the month starts (embargo for overlapping holds).
2. For today's regime (trend x volatility; if fewer than 30 past days in that cell, trend only), compute each strategy's past mean daily
   return and t-statistic in that regime.
3. Trade the strategy with the highest past mean among those with t > 2 and mean > 0. Otherwise NO TRADE.
4. Compare with the equal-weight mix of all 12 strategies and with the best single strategy chosen on TRAIN.

Results (mean net return per trade on days the method traded; "pct points" = sum of daily mean returns):

| method | period | days traded | mean net per day traded | t | share of days positive | cum. sum (pct pts) | max drawdown (pct pts) |
|---|---|---|---|---|---|---|---|
| regime selector (walk-forward) | train (walk-forward from Nov 2022) | 373 | +0.422% | 2.26 | 55% | +157.6 | 104.6 |
| regime selector (walk-forward) | validation | 133 | -0.326% | -1.04 | 48% | -43.4 | 151.4 |
| regime selector (walk-forward) | seen-once 2025-26 | 163 | -0.069% | -0.26 | 45% | -11.2 | 93.9 |
| equal weight, all 12 strategies | train (walk-forward from Nov 2022) | 501 | +0.232% | 3.96 | 59% | +116.1 | 48.2 |
| equal weight, all 12 strategies | validation | 247 | -0.107% | -1.19 | 46% | -26.5 | 75.3 |
| equal weight, all 12 strategies | seen-once 2025-26 | 249 | -0.109% | -1.29 | 41% | -27.1 | 52.6 |
| best single on TRAIN: D2_R7CAND_10d | train (walk-forward from Nov 2022) | 479 | +1.229% | 7.46 | 66% | +588.7 | 96.2 |
| best single on TRAIN: D2_R7CAND_10d | validation | 232 | +0.340% | 1.61 | 53% | +78.8 | 145.4 |
| best single on TRAIN: D2_R7CAND_10d | seen-once 2025-26 | 236 | -0.046% | -0.18 | 40% | -10.9 | 109.0 |

Selector picks (all walk-forward days): D2_R7CAND_10d 285, D1_MOM60_10d 201, D8_OISHORT_intra 138, D3_R8DELIVBASIS_5d 34, D4_REVERSAL_5d 14
No-trade days (no strategy with t > 2 in the current regime): 564 of 1236


Reading:
- The selector looked good in its own walk-forward training years (+0.42 % per traded day, t 2.3) and then LOST in validation (-0.33 %,
  t -1.0) and in 2025-26 (-0.07 %). The regime->strategy ranking did not persist.
- It spent most days in D2 (the Round 7 candidate) and D1 (momentum), the two strategies whose edges decayed; switching added drawdown.
- Equal weighting smoothed drawdown (48-75 pct points vs 95-150) but every out-of-sample period was negative.
- No-trade was chosen on 46 % of days, so the rule was already strict.
Risk policy used: one strategy per day, no stacking, positions sized per strategy rules; this did not change the sign of the result.
