# Round 9: full audit of Rounds 1-8

Round 9, 2026-11-12. All returns are NET percent per trade (delivery 0.25 %, intraday 0.12 % incl. slippage). Periods: train < 2024-11-11 <= validation < 2025-11-11 <= seen-once (used by rounds 7-8, never used for selection here).

## Inventory of what was tested before

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
| D1_MOM60_10d | +1.11% (15439) | -0.14% (7568) | +0.31% (7557) | 52% / 48% / 49% | 238 |
| D2_R7CAND_10d | +1.11% (6011) | +0.19% (2131) | -0.25% (2198) | 54% / 50% / 43% | 237 |
| D3_R8DELIVBASIS_5d | +0.16% (10630) | +0.09% (4895) | -0.07% (4883) | 52% / 50% / 45% | 114 |
| D4_REVERSAL_5d | +0.06% (15532) | -0.07% (7367) | -0.32% (7532) | 48% / 46% / 44% | 229 |
| D5_BREAKOUT_5d | -0.41% (4259) | -0.62% (1551) | -0.35% (1563) | 44% / 44% / 45% | 559 |
| D6_SWEEP_5d | +0.69% (3011) | -0.25% (1098) | -0.01% (1425) | 55% / 48% / 46% | 160 |
| D7_BTST_2d | -0.53% (552) | -0.39% (236) | -0.55% (239) | 40% / 42% / 36% | 345 |
| D8_OISHORT_intra | +0.20% (10619) | +0.07% (4174) | +0.06% (4035) | 55% / 53% / 52% | 13 |
| D9_OILONG_intra | -0.02% (11338) | -0.05% (4423) | -0.09% (4283) | 48% / 48% / 45% | 61 |
| I1_ORB15L_intra | -0.10% (19204) | -0.09% (6615) | -0.11% (6666) | 36% / 37% / 37% | 194 |
| I2_ORB15S_intra | -0.04% (22265) | -0.11% (7700) | -0.10% (7453) | 40% / 38% / 38% | 149 |
| I3_PDLSWEEP_intra | -0.09% (6410) | -0.14% (2253) | -0.09% (2723) | 41% / 39% / 41% | 178 |

Definitions: research/round9.py `STRATS`. Duplicates found: R1 ORB = R5 ORB15 (I1); R2 sweep = R6 SWEEP = R3 sweep+RS (D6/I3);
R2 squeeze, week-high and R4 rotation are the same breakout-on-volume idea (D5/D7); R7 `ret60`, `rs60` and `dist_ema50` are one momentum
feature; R8 `long_build` and `oi_chg1` overlap. Experiments counted so far: Rounds 1-8 about 2,500; Round 9 adds 12 streams, 4 regime
dimensions, 1 pre-specified selector and 20 target/filter cells in the 2 % study.
