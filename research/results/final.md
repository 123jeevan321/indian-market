# Final test of the pre-registered candidate

Pre-registered 2026-11-11T23:18:59: `B10-lasthour_share_z+amihud`, hold 10 days. Rule: each rebalance day: liquid Nifty-100 stocks with 15-minute data; rank-average of (last-hour volume share minus its 20-day mean) and (20-day Amihud illiquidity); buy the top decile at next open, sell at the close of day 10.

| strategy | period | periods | mean net per trade | t | excess vs universe | t excess | hit rate |
|---|---|---|---|---|---|---|---|
| PRIMARY B10-lasthour_share_z+amihud | train | 70 | +1.25% | 2.48 | +0.71% | 2.53 | 61% |
| PRIMARY B10-lasthour_share_z+amihud | validation | 22 | +0.76% | 1.38 | +0.74% | 3.44 | 55% |
| PRIMARY B10-lasthour_share_z+amihud | TEST | 22 | -0.37% | -0.48 | +0.38% | 1.56 | 41% |
| secondary -rvol5+lasthour_share_z+amihud | train | 70 | +1.57% | 3.03 | +1.03% | 3.39 | 63% |
| secondary -rvol5+lasthour_share_z+amihud | validation | 22 | +1.03% | 1.86 | +1.01% | 3.12 | 59% |
| secondary -rvol5+lasthour_share_z+amihud | TEST | 22 | -0.91% | -1.25 | -0.16% | -0.64 | 41% |
| baseline momentum ret60 | train | 69 | +1.03% | 2.00 | +0.49% | 1.92 | 65% |
| baseline momentum ret60 | validation | 25 | -0.53% | -0.56 | -0.22% | -0.57 | 52% |
| baseline momentum ret60 | TEST | 24 | +0.26% | 0.35 | +0.50% | 1.20 | 54% |
| baseline amihud alone | train | 73 | +0.79% | 1.58 | +0.33% | 1.34 | 63% |
| baseline amihud alone | validation | 23 | -0.67% | -0.74 | -0.26% | -0.87 | 52% |
| baseline amihud alone | TEST | 22 | -0.37% | -0.45 | +0.02% | 0.06 | 36% |
| baseline lasthour_share_z alone | train | 70 | +0.74% | 1.69 | +0.20% | 0.78 | 57% |
| baseline lasthour_share_z alone | validation | 24 | +0.20% | 0.37 | +0.08% | 0.24 | 54% |
| baseline lasthour_share_z alone | TEST | 22 | -0.81% | -1.22 | -0.06% | -0.21 | 50% |
| random decile (same 99 stocks) | validation | 24 | -0.47% | -0.84 | -0.59% | -2.26 | 42% |
| random decile (same 99 stocks) | TEST | 22 | -0.55% | -0.69 | +0.21% | 0.68 | 41% |

## Walk-forward by calendar year (fixed rule, no refitting)

| year | periods | mean net | excess | hit |
|---|---|---|---|---|
| 2021 | 2 | +0.52% | -0.21% | 50% |
| 2022 | 23 | +0.41% | +0.66% | 65% |
| 2023 | 25 | +1.68% | +0.75% | 64% |
| 2024 | 23 | +0.67% | +0.52% | 52% |
| 2025 | 23 | +0.44% | +0.28% | 52% |
| 2026 | 19 | -0.20% | -0.22% | 37% |

## By market regime at the signal date (all periods)

| regime | periods | mean net | excess |
|---|---|---|---|
| NIFTY above EMA200 | 76 | +0.75% | +0.47% |
| NIFTY below EMA200 | 38 | +0.12% | -0.18% |

## Rupee simulation on the TEST period (Rs 2,00,000, top 3 stocks, equal weight, delivery costs included in labels)

Rebalances: 22 (every 10 trading days). Net Rs per 2-week cycle: mean -324, median -1324, worst -16005, best +25117; cycles >= Rs 10,000 (= Rs 5,000/week): 5%; losing cycles: 64%. Per-stock trade: mean -108, worst -7753 (32% of trades lost more than Rs 1,500). Implied average per week: -162.
