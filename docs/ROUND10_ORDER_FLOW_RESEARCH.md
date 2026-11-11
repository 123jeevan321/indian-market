# Round 10: order-flow research plan (pre-registered 2026-11-12, before any data exists)

Status: COLLECTING. No test is run before 20 sessions; the main test waits for 40.

## Features (computed at time t from rows with exchange time <= t)

| feature | definition | question |
|---|---|---|
| OBI1 | (best bid qty - best ask qty) / (sum) | Q5 |
| OBI5 | same over the best 5 levels | Q5 |
| TOT | tbq / (tbq + tsq) | Q5, Q9 |
| DELTA_k | estimated signed volume over the last k minutes (quote rule, then tick rule) | Q1, Q2 |
| ABSORB_k | abs(DELTA_k) high (top 20 % for that stock) while abs(return over k) is low (bottom 30 %) | Q3 |
| REFILL | best-level quantity restored within 30 s after trades take it | Q3 |
| BRK_FLOW | at a break of the 15-min opening range or previous-day high/low: DELTA and OBI5 change in the 5 minutes around the break | Q4 |
| SPREAD | best ask - best bid in ticks | cost control |

## Tests

1. Predictive (Q1, Q2, Q5): rank IC and decile spreads of each feature vs the mid-price return over the next 1, 5 and 15 minutes, per
   stock and pooled, by session hour. Benchmark: the same horizon predicted by the last 1/5/15-minute price return alone (does order flow
   add anything beyond price?).
2. Absorption (Q3): return over the next 15 and 30 minutes after ABSORB events vs matched non-events with the same past return.
3. False breakouts (Q4): among 15-min ORB and previous-day-level breaks, compare BRK_FLOW for breaks that held 30 minutes vs failed.
4. Trading value (Q6-Q8): the Round 9 intraday streams (ORB long/short, PDL sweep, OI-model short) re-run with an order-flow filter
   (take a signal only when DELTA and OBI5 agree with the direction). Measure net expectancy after 0.12 % costs, stop-hit rate and entry
   price improvement vs the unfiltered versions on the SAME signals.
5. Incremental value (Q9): ridge model with Round 8 daily features + intraday price features, with and without order-flow features,
   trained on the first half of the collected sessions and scored on the second half (chronological, purged by one session).

Multiple testing: about 8 features x 3 horizons x 2 directions; a feature counts only if |t| > 3 pooled AND the sign holds in both halves.
Success criterion for any trading use: positive net expectancy after costs in the second half, better than the unfiltered strategy, and
then 4-8 weeks of forward paper trading.
