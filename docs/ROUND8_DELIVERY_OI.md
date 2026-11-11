# Round 8: historical delivery % and futures open interest (2026-11-12)

**Verdict: the new data carries real information, but not enough to beat Indian transaction costs. Nothing is ready for real money.**
Raw outputs: research/results/round8_*.{csv,md,json}. Code: research/fetch_nse.py, research/round8.py.

## Data sources, quality and coverage

| source | coverage | quality |
|---|---|---|
| NSE `sec_bhavdata_full` (delivery) | 1,233 trading days, Nov 2021 - Nov 2026, all 495 research stocks | 96.8 % of liquid stock-days have delivery %; holiday files that repeat the previous session are detected and dropped |
| NSE F&O bhavcopy, old format (to 2024-07-05) and UDiFF (from 2024-07-08) | 1,234 days, 305 stock-futures symbols, 275 in our universe | 63.7 % of liquid stock-days (only F&O stocks have futures) |

Contract handling: OI is summed over all expiries (rollover-neutral); basis uses the nearest contract with at least 3 days to expiry;
prices and OI are unadjusted for splits/bonuses, so only same-day ratios and % changes are used; daily OI changes beyond +-100 %
(lot-size changes, data errors) are discarded.

## Your hypothesis: delivery > 65 % AND futures long build-up

Pre-specified event test, entry next open, delivery costs (0.25 %), all F&O stock-days as the baseline:

| hold | train net | validation net | 2025-26 (seen once) net | excess vs F&O universe (train / val / 2025-26) |
|---|---|---|---|---|
| 1 day | -0.31 % (1,690 events) | -0.25 % | -0.41 % | +0.07 / +0.08 / -0.05 % |
| 3 days | -0.09 % | -0.09 % | -0.46 % | +0.12 / +0.16 / -0.03 % |
| 5 days | +0.02 % | +0.05 % | -0.52 % | +0.07 / +0.19 / 0.00 % |
| 10 days | +0.54 % | +0.19 % | -0.77 % | +0.18 / +0.33 / +0.01 % |

**Answer: no.** It lost money after costs at every holding period up to 5 days, and its small edge over the average F&O stock vanished in
2025-26. Adding "OI up more than 2 %" did not help. The parts separately:
- **High delivery alone** has a small, real relative edge (+0.07 to +0.15 % vs the universe, consistent in all three periods) but it is
  far smaller than the 0.25 % delivery cost.
- **Long build-up alone** is slightly NEGATIVE relative to other stocks (t = -4.3 at 1 day in train): buying where leveraged longs just
  piled in does not pay.

## Single features (288 tests, TRAIN)

26 tests pass |t excess| > 3.4 (Bonferroni), unlike round 7 where none did. The strongest: delivery % (+0.09 % per day vs the universe,
t 4.6), change in futures basis (t 4.1), delivery-vs-OI divergence (t 3.4), long unwinding (t 3.0), OI falling (t 2.7). All are RELATIVE
edges; every one is negative in absolute terms at 1-3 day holds once 0.25 % delivery costs are paid.

## Incremental value (ridge model on ranked features, fitted on TRAIN, scored on VALIDATION)

| universe | hold | 36 base IC | + delivery | + futures OI | + both |
|---|---|---|---|---|---|
| F&O stocks | 1 day | 0.043 | 0.048 | **0.062 (t 8.7)** | 0.065 |
| F&O stocks | 5 days | 0.019 | 0.022 | 0.038 | 0.038 |
| F&O stocks | 10 / 20 days | -0.018 / -0.056 | -0.013 / -0.052 | 0.006 / -0.037 | 0.008 / -0.035 |
| all liquid | 5 days | n/a | 0.018 | n/a | 0.028 |

Futures OI is the most useful new input: it raises next-day predictive power by about 45 % (IC 0.043 -> 0.062, highly significant).
Delivery adds a little. Neither rescues the 10-20 day horizon, which turned negative in validation.

## The one follow-up worth noting: intraday short of the model's bottom decile

The 1-day label is next-open to next-close, i.e. an intraday trade, so it was re-scored with intraday costs (0.10 %) and an MIS short of
the bottom decile (stocks the model expects to fall: mostly yesterday's breakouts and failed breakouts):

| period | short net/day | with +0.05 % extra slippage | t | winning days |
|---|---|---|---|---|
| train | +0.22 % | +0.17 % | 4.65 | 56 % |
| validation | +0.06 % | +0.01 % | 0.89 | 53 % |
| 2025-26 (seen once) | +0.05 % | -0.01 % | 0.76 | 52 % |

It decays from strong in training to break-even after realistic slippage. Not tradable; worth forward paper-tracking only.

## Combinations (299 with at least one new feature, 2-4 factors, 5/10/20-day holds)

12 were stable in train and validation, all at a 5-day hold, built from **high futures basis (futures premium), high delivery %, low
range and long unwinding**. Best simple one, `delivery % + annualised basis`, 5-day hold, top decile:

| period | net per trade | excess vs universe |
|---|---|---|
| train | +0.20 % | +0.26 % (t 3.2) |
| validation | +0.07 % | +0.31 % (t 2.8) |
| 2025-26 (seen once) | -0.02 % | +0.19 % (t 1.5) |

It keeps beating the average stock, but the absolute gain after costs is about zero: on Rs 2 lakh roughly Rs 0-400 per 5-day cycle.

## Comparison with round 7 and why it still fails

- Round 7: no single feature significant; best combo failed out of sample.
- Round 8: delivery % and futures OI ARE significant relative signals (first genuine institutional-footprint evidence in this project),
  and the OI-enhanced model predicts next-day moves materially better. But the edges are 0.05-0.3 % per trade, while a delivery round
  trip costs 0.25 % and an intraday one 0.10 %+, and much of the edge sits in RELATIVE performance that a long-only cash account cannot
  capture (it would need a short or hedge leg).
- Your Rs 5,000-10,000 weekly target remains far beyond any measured edge.

## Best candidates for forward paper-tracking (not real money)

1. 5-day `delivery % + futures basis` top-decile basket (F&O stocks), only when NIFTY is above its 200-day EMA.
2. Intraday MIS short of the OI-model bottom decile, recorded with real fills from Angel One quotes to measure true slippage.
Both need 8-12 weeks of forward results before any decision.
