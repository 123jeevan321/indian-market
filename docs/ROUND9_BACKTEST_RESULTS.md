# Round 9: backtest results

Round 9, 2026-11-12. All returns are NET percent per trade (delivery 0.25 %, intraday 0.12 % incl. slippage). Periods: train < 2024-11-11 <= validation < 2025-11-11 <= seen-once (used by rounds 7-8, never used for selection here).

## Strategy streams

| strategy | train | validation | seen-once | win rate | max DD |
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

## Selector vs single vs equal weight

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


## The 2 % daily opportunity (15-minute data, 99 Nifty 100 stocks)

## How often does a liquid Nifty 100 stock move 2 % in a day? (open-based, all stock-days)

| period | stock-days | high >= open +2 % | low <= open -2 % | either |
|---|---|---|---|---|
| seen-once | 24648 | 17.2% | 18.3% | 34.6% |
| train | 69672 | 19.2% | 21.1% | 38.8% |
| validation | 23724 | 17.7% | 18.7% | 35.5% |

## Can a trade entered at 10:00 capture it? Long at the 10:00 close, stop 1 %, target T, exit 15:15; net of 0.12 %

| entry filter | period | trades | target | hit target first | hit stop first | neither | net expectancy | median MAE |
|---|---|---|---|---|---|---|---|---|
| every stock-day | train | 69672 | 0.5% | 46% | 37% | 17% | -0.300% | -0.73% |
| every stock-day | train | 69672 | 1.0% | 28% | 37% | 34% | -0.216% | -0.73% |
| every stock-day | train | 69672 | 1.5% | 17% | 37% | 46% | -0.176% | -0.73% |
| every stock-day | train | 69672 | 2.0% | 10% | 37% | 53% | -0.159% | -0.73% |
| every stock-day | train | 69672 | 2.5% | 6% | 37% | 57% | -0.149% | -0.73% |
| every stock-day | validation | 23724 | 0.5% | 48% | 34% | 17% | -0.262% | -0.69% |
| every stock-day | validation | 23724 | 1.0% | 28% | 34% | 37% | -0.187% | -0.69% |
| every stock-day | validation | 23724 | 1.5% | 16% | 34% | 50% | -0.156% | -0.69% |
| every stock-day | validation | 23724 | 2.0% | 9% | 34% | 57% | -0.142% | -0.69% |
| every stock-day | validation | 23724 | 2.5% | 5% | 34% | 61% | -0.135% | -0.69% |
| every stock-day | seen-once | 24648 | 0.5% | 50% | 33% | 17% | -0.244% | -0.68% |
| every stock-day | seen-once | 24648 | 1.0% | 29% | 33% | 37% | -0.171% | -0.68% |
| every stock-day | seen-once | 24648 | 1.5% | 16% | 33% | 51% | -0.144% | -0.68% |
| every stock-day | seen-once | 24648 | 2.0% | 9% | 33% | 58% | -0.132% | -0.68% |
| every stock-day | seen-once | 24648 | 2.5% | 5% | 33% | 62% | -0.125% | -0.68% |
| above 30-min range high | train | 6875 | 0.5% | 48% | 39% | 13% | -0.303% | -0.77% |
| above 30-min range high | train | 6875 | 1.0% | 31% | 39% | 30% | -0.205% | -0.77% |
| above 30-min range high | train | 6875 | 1.5% | 19% | 39% | 42% | -0.155% | -0.77% |
| above 30-min range high | train | 6875 | 2.0% | 12% | 39% | 49% | -0.129% | -0.77% |
| above 30-min range high | train | 6875 | 2.5% | 7% | 39% | 54% | -0.120% | -0.77% |
| above 30-min range high | validation | 2312 | 0.5% | 48% | 36% | 16% | -0.279% | -0.71% |
| above 30-min range high | validation | 2312 | 1.0% | 30% | 36% | 34% | -0.193% | -0.71% |
| above 30-min range high | validation | 2312 | 1.5% | 17% | 36% | 46% | -0.149% | -0.71% |
| above 30-min range high | validation | 2312 | 2.0% | 11% | 36% | 53% | -0.122% | -0.71% |
| above 30-min range high | validation | 2312 | 2.5% | 6% | 36% | 58% | -0.109% | -0.71% |
| above 30-min range high | seen-once | 2319 | 0.5% | 50% | 35% | 15% | -0.250% | -0.71% |
| above 30-min range high | seen-once | 2319 | 1.0% | 33% | 35% | 32% | -0.148% | -0.71% |
| above 30-min range high | seen-once | 2319 | 1.5% | 19% | 35% | 47% | -0.112% | -0.71% |
| above 30-min range high | seen-once | 2319 | 2.0% | 11% | 35% | 55% | -0.092% | -0.71% |
| above 30-min range high | seen-once | 2319 | 2.5% | 6% | 35% | 59% | -0.080% | -0.71% |


Distinctions you asked for:
- A stock moving 2 % in a day: about 35-39 % of stock-days touch +-2 % from the open.
- Our trade capturing 2 %: a long entered at 10:00 with a 1 % stop reaches +2 % first on only 9-11 % of days; the stop is hit first on
  33-36 %; net expectancy -0.09 % to -0.14 % per trade at every target from 0.5 % to 2.5 %, in both validation and 2025-26.
- A 2 % net return on deployed capital needs the trade to capture more than 2.12 % after costs.
- A 2 % return on the whole Rs 2 lakh account (Rs 4,000) needs every rupee deployed and that capture, every day.
Adverse excursion: the median 10:00 entry first moves 0.7 % against you before the close.
