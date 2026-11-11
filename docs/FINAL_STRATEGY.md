# Final strategy decision (round 7, 2026-11-11)

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
