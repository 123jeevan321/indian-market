# Strategy comparison: all research rounds (2026-11-11)

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

## Round 7, stage A: 432 single-feature tests on TRAIN (Nov 2021 to Nov 2024)

Bonferroni threshold |t| > 3.48: 0 passed. 28 had t > 2, all at 10- or 20-day holds.

Top 15 overall:

| id | feature (sign) | hold | mean net/trade | t | excess vs universe | t excess |
|---|---|---|---|---|---|---|
| A0102 | atr_comp | 20 | +2.92% | 3.28 | +1.31% | 3.37 |
| A0432 | -lasthour_ret | 20 | +2.42% | 2.92 | +0.68% | 1.49 |
| A0078 | voladj_mom | 20 | +2.84% | 2.67 | +0.84% | 1.52 |
| A0054 | ret120 | 20 | +3.32% | 2.66 | +1.31% | 1.88 |
| A0342 | rs60 | 20 | +2.82% | 2.64 | +1.21% | 2.29 |
| A0042 | ret60 | 20 | +2.82% | 2.64 | +1.21% | 2.29 |
| A0414 | firsthour_ret | 20 | +2.01% | 2.62 | +0.27% | 0.40 |
| A0390 | close_vs_vwap | 20 | +2.62% | 2.48 | +0.88% | 1.76 |
| A0318 | amihud | 20 | +2.51% | 2.43 | +1.11% | 1.88 |
| A0234 | dist_ema50 | 20 | +2.50% | 2.40 | +1.12% | 1.98 |
| A0132 | -rvol5 | 20 | +1.91% | 2.32 | +0.53% | 1.46 |
| A0131 | -rvol5 | 10 | +1.06% | 2.27 | +0.60% | 2.86 |
| A0246 | dist_ema200 | 20 | +2.46% | 2.26 | +1.08% | 1.69 |
| A0180 | -gap | 20 | +2.04% | 2.25 | +0.66% | 1.63 |
| A0120 | -rvol | 20 | +2.10% | 2.23 | +0.72% | 1.42 |

Best short-horizon results (hold 0-5 days), none significant:

| id | feature (sign) | hold | mean net/trade | t | excess vs universe | t excess |
|---|---|---|---|---|---|---|
| A0430 | -lasthour_ret | 5 | +0.20% | 0.90 | +0.10% | 0.88 |
| A0052 | ret120 | 5 | +0.26% | 0.81 | +0.17% | 0.98 |
| A0076 | voladj_mom | 5 | +0.20% | 0.74 | +0.11% | 0.81 |
| A0394 | -close_vs_vwap | 5 | +0.16% | 0.71 | +0.07% | 0.51 |
| A0064 | mom12_1 | 5 | +0.24% | 0.68 | +0.13% | 0.67 |
| A0424 | lasthour_ret | 5 | +0.13% | 0.65 | +0.04% | 0.30 |
| A0388 | close_vs_vwap | 5 | +0.14% | 0.63 | +0.05% | 0.40 |
| A0364 | ind_ret20 | 5 | +0.14% | 0.61 | +0.15% | 1.15 |
| A0130 | -rvol5 | 5 | +0.13% | 0.55 | +0.13% | 1.50 |
| A0316 | amihud | 5 | +0.14% | 0.55 | +0.15% | 1.06 |

Several long-hold features look significant in BOTH signs (first-hour return up or down), which shows the raw t-statistic mostly reflects
the 2021-2024 bull market. The excess-vs-universe column is the honest measure.

## Round 7, stage B: 1246 combinations (2-3 features), TRAIN fit, VALIDATION check (Nov 2024 to Nov 2025)

Stable in both (train net t > 2, train excess t > 1.5, validation net and excess > 0): 98. Top 15 by validation excess t:

| id | train net | train t | train excess t | validation net | validation excess | validation excess t |
|---|---|---|---|---|---|---|
| B10-lasthour_ret+-firsthour_ret+amihud | +0.98% | 2.05 | 1.57 | +0.93% | +1.11% | 3.78 |
| B10-lasthour_share_z+amihud | +1.25% | 2.48 | 2.53 | +0.76% | +0.74% | 3.44 |
| B10--rvol5+lasthour_share_z+amihud | +1.57% | 3.03 | 3.39 | +1.03% | +1.01% | 3.12 |
| B10--rvol5+-firsthour_ret+amihud | +1.37% | 2.87 | 2.59 | +0.56% | +0.74% | 2.55 |
| B10-lasthour_ret+ret20+-rvol | +1.32% | 3.00 | 2.90 | +0.50% | +0.61% | 2.55 |
| B10-lasthour_ret+-rvol+amihud | +1.21% | 2.55 | 2.25 | +0.60% | +0.81% | 2.54 |
| B10--rvol5+lasthour_ret+ret20 | +1.35% | 2.65 | 2.61 | +0.53% | +0.63% | 2.35 |
| B20-firsthour_ret+amihud+-rvol | +3.62% | 3.37 | 2.64 | +1.09% | +1.40% | 2.30 |
| B10-lasthour_share_z+-rvol+amihud | +1.48% | 2.67 | 2.80 | +0.82% | +0.80% | 2.27 |
| B10--rvol5+lasthour_share_z | +1.08% | 2.60 | 2.27 | +0.75% | +0.63% | 2.23 |
| B10-close_vs_vwap+-rvol+amihud | +1.52% | 3.13 | 2.94 | +0.24% | +0.45% | 2.15 |
| B10-atr_comp+close_vs_vwap+-rvol | +1.19% | 2.54 | 2.09 | +0.36% | +0.47% | 2.06 |
| B10-lasthour_ret+-rvol | +1.24% | 2.63 | 2.75 | +0.45% | +0.55% | 1.96 |
| B10-lasthour_share_z+close_vs_vwap+amihud | +1.15% | 2.67 | 2.30 | +0.56% | +0.54% | 1.92 |
| B10-ret120+lasthour_share_z+amihud | +1.38% | 2.54 | 2.19 | +0.72% | +0.70% | 1.87 |

Recurring ingredients of the stable combinations: late-day volume concentration (lasthour_share_z, concept 17), relative illiquidity
within the Nifty 100 (amihud), quiet recent volume (-rvol, -rvol5) and a strong last hour (lasthour_ret), all with a 10-day hold. With
1,246 combinations, a validation t of about 3.4 is still within what chance produces (Bonferroni needs about 3.9), so ONE candidate was
pre-registered and tested once on the untouched TEST period (docs/FINAL_STRATEGY.md).
