**Verdict (2026-11-11): no combination passed.** 216 combinations on 5 years of Angel One 15-minute data for 99 Nifty 100 stocks: none positive in both
periods, none with > 55 % wins in both, and the in-sample leaders collapsed out of sample (FVG + RVOL: +Rs 19 -> -Rs 209 per trade). Same-day beat
2-day holding (OOS mean -Rs 111 vs -Rs 213 per trade), mainly because delivery STT is charged on both sides. Results sit inside the random-entry range.

# Multi-factor matrix backtest (NSE 15-minute bars, Angel One history, long only, morning entries)

Run 2026-11-11. 99 Nifty 100 stocks, 2021-11-12 to 2026-11-11 (1233 sessions). IS = before 2024-11-11, OOS = from 2024-11-11. 216 combinations. Max loss Rs 1,500 per leg incl. costs and slippage; leg <= Rs 1 lakh; max 2 legs, different industries. Same-day = MIS costs; 2-day = delivery costs.

## Top 10 by IN-SAMPLE expectancy (min 60 IS trades), with their OUT-OF-SAMPLE result

| combo | trades | win | expectancy Rs/trade (95% CI) | PF | total Rs | max DD Rs | costs Rs |
|---|---|---|---|---|---|---|---|
| FVG+RVOL | +2.0% | same-day MIS **IS** | 170 | 41.8% | +19 (-132..+166) | 1.05 | +3244 | 12931 | 13740 |
| FVG+RVOL | +2.0% | same-day MIS OOS | 122 | 23.8% | -209 (-365..-47) | 0.59 | -25545 | 28808 | 9899 |
| FVG+RVOL | +3.0% | same-day MIS **IS** | 170 | 40.0% | -0 (-153..+157) | 1.00 | -25 | 12678 | 13738 |
| FVG+RVOL | +3.0% | same-day MIS OOS | 122 | 23.8% | -171 (-343..+7) | 0.67 | -20897 | 25958 | 9900 |
| ORB30+RVOL+FVGp | +2.0% | same-day MIS **IS** | 316 | 46.8% | -11 (-124..+103) | 0.98 | -3408 | 25375 | 23317 |
| ORB30+RVOL+FVGp | +2.0% | same-day MIS OOS | 207 | 40.1% | -189 (-320..-55) | 0.63 | -39116 | 40575 | 15383 |
| FVG+RVOL | +1.5% | same-day MIS **IS** | 170 | 41.8% | -22 (-158..+115) | 0.95 | -3747 | 16101 | 13738 |
| FVG+RVOL | +1.5% | same-day MIS OOS | 122 | 26.2% | -211 (-356..-63) | 0.57 | -25742 | 28531 | 9899 |
| ORB30+POC+FVGp | +1.5% | same-day MIS **IS** | 458 | 46.1% | -25 (-109..+61) | 0.94 | -11388 | 21540 | 36262 |
| ORB30+POC+FVGp | +1.5% | same-day MIS OOS | 354 | 43.2% | -84 (-175..+10) | 0.80 | -29620 | 50119 | 28167 |
| ORB30+POC+FVGp | +2.0% | same-day MIS **IS** | 458 | 44.8% | -27 (-112..+62) | 0.94 | -12390 | 23752 | 36261 |
| ORB30+POC+FVGp | +2.0% | same-day MIS OOS | 354 | 42.9% | -62 (-160..+34) | 0.85 | -22038 | 42305 | 28169 |
| ORB30+RVOL+FVGp | +3.0% | same-day MIS **IS** | 316 | 44.3% | -27 (-146..+89) | 0.94 | -8635 | 23621 | 23312 |
| ORB30+RVOL+FVGp | +3.0% | same-day MIS OOS | 207 | 39.1% | -184 (-326..-45) | 0.64 | -38169 | 40259 | 15384 |
| FVG+RVOL | +3.0% | 2-day CNC **IS** | 166 | 31.9% | -34 (-256..+203) | 0.95 | -5568 | 13572 | 37285 |
| FVG+RVOL | +3.0% | 2-day CNC OOS | 117 | 23.1% | -249 (-467..-16) | 0.63 | -29184 | 35622 | 26733 |
| FVG+RVOL | +2.0% | 2-day CNC **IS** | 167 | 37.1% | -39 (-218..+158) | 0.93 | -6449 | 15155 | 37457 |
| FVG+RVOL | +2.0% | 2-day CNC OOS | 117 | 25.6% | -298 (-490..-100) | 0.55 | -34873 | 38377 | 26727 |
| ORB30+RVOL+FVGp | +1.5% | same-day MIS **IS** | 316 | 48.4% | -39 (-140..+66) | 0.91 | -12247 | 25579 | 23314 |
| ORB30+RVOL+FVGp | +1.5% | same-day MIS OOS | 207 | 42.5% | -182 (-314..-58) | 0.63 | -37700 | 38847 | 15384 |

## Combos positive in BOTH periods (min 40 trades each), ranked by the weaker period

| combo | trades | win | expectancy Rs/trade (95% CI) | PF | total Rs | max DD Rs | costs Rs |
|---|---|---|---|---|---|---|---|
| none | | | | | | | |

Combos with win rate > 55 % in both periods: 0

## Same-day vs 2-day (average over all combos with >= 40 trades in a period)

| hold | period | combos | mean expectancy Rs | share of combos > 0 |
|---|---|---|---|---|
| sameday | IS | 96 | -135 | 1% |
| sameday | OOS | 93 | -111 | 2% |
| 2day | IS | 96 | -217 | 0% |
| 2day | OOS | 93 | -213 | 0% |

## Random baseline (random entry bar 9:30-10:30, 0.75 % stop, same exits/sizing/costs)

| combo | trades | win | expectancy Rs/trade (95% CI) | PF | total Rs | max DD Rs | costs Rs |
|---|---|---|---|---|---|---|---|
| random +1.5% 2day IS | 827 | 38.3% | -168 (-251..-89) | 0.73 | -138589 | 140750 | 193289 |
| random +1.5% 2day OOS | 562 | 30.4% | -330 (-409..-247) | 0.51 | -185271 | 197034 | 131656 |
| random +1.5% sameday IS | 1027 | 37.6% | -149 (-198..-96) | 0.68 | -153232 | 156630 | 84306 |
| random +1.5% sameday OOS | 692 | 39.6% | -103 (-167..-42) | 0.76 | -71615 | 73215 | 56497 |
| random +2.0% 2day IS | 796 | 30.9% | -221 (-307..-128) | 0.68 | -175614 | 181302 | 186491 |
| random +2.0% 2day OOS | 556 | 26.3% | -386 (-475..-297) | 0.47 | -214584 | 221922 | 129728 |
| random +2.0% sameday IS | 1011 | 34.3% | -159 (-212..-106) | 0.67 | -160404 | 164712 | 82833 |
| random +2.0% sameday OOS | 716 | 38.8% | -55 (-121..+21) | 0.87 | -39411 | 49451 | 58696 |
| random +3.0% 2day IS | 792 | 30.8% | -192 (-282..-102) | 0.72 | -151774 | 165436 | 186003 |
| random +3.0% 2day OOS | 535 | 30.7% | -164 (-270..-42) | 0.76 | -87672 | 90338 | 124714 |
| random +3.0% sameday IS | 1006 | 35.9% | -126 (-183..-65) | 0.73 | -126921 | 129749 | 82343 |
| random +3.0% sameday OOS | 716 | 38.5% | -62 (-133..+7) | 0.86 | -44582 | 55471 | 58499 |

## Weekly net Rs distribution for: FVG+RVOL | +2.0% | same-day MIS

| period | weeks | mean | p10 | p25 | median | p75 | p90 | worst | best | weeks >= 5k | >= 10k | < 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 262 | -85 | -1322 | -637 | +0 | +0 | +1295 | -2805 | +3826 | 0% | 0% | 39% |
| OOS | 105 | -243 | -1861 | -822 | +0 | +0 | +1262 | -2805 | +3826 | 0% | 0% | 46% |

Limits: today's index members (survivorship); 15-minute bars hide the order of moves inside a bar (stop assumed first); entry at the trigger bar's close + 1 tick; no news filter; multiple testing across 216 combos inflates the best in-sample numbers.
