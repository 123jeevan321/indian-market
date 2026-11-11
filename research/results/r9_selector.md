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
