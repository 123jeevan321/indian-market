# Debate system: historical validation (stage 5a, swing mode), run 2026-11-12

Script: `trader-debate/validate.py swing --write`. Raw results: `research/results/debate_validation_swing.json`.

## Setup

- Universe: the current Nifty 100 (100 stocks; survivorship bias, results flattered if anything). Data: Yahoo daily bars (adjusted)
  through 2026-11-11, NSE delivery and F&O files through 2026-11-11. 93,408 stock-days, each a full debate (Buyer, Seller, challenges,
  responses, Judge) built from data available at that close only.
- Trades: long plans as the Buyer writes them (buy-stop next session, do-not-chase cap, stop, T1 net 1.5R, time exit after 5 sessions,
  stop first on ambiguous bars, gaps at the open, Zerodha delivery costs + 1 tick slippage each side, Rs 1,500 risk per trade).
- Chronological split by signal date: TRAIN 2022-11-15..2025-04-03, VALIDATION 2025-04-04..2026-01-20, TEST 2026-01-21..2026-11-09.
- Multiple testing: 3 setups compared, Bonferroni z = 2.39 for every confidence interval below.
- Drawdowns are the sum of all signals in date order (no portfolio cap), so they show direction, not account size.

## Results (net Rs per trade after costs; CI = Bonferroni-adjusted)

| strategy | period | trades | win before costs | win after costs | avg win | avg loss | expectancy | CI | profit factor | T1 before stop |
|---|---|---|---|---|---|---|---|---|---|---|
| Buyer alone | TRAIN | 16,060 | 49.3 % | 46.3 % | 1,110 | -997 | **-21** | -45..+3 | 0.96 | 13.7 % |
| Buyer alone | VALIDATION | 5,693 | 44.5 % | 41.1 % | 1,111 | -1,028 | **-148** | -188..-107 | 0.76 | 12.3 % |
| Buyer alone | TEST | 4,598 | 42.5 % | 39.8 % | 1,140 | -1,119 | **-220** | -270..-170 | 0.67 | 12.7 % |
| Simple rule (20-day breakout) | TEST | 595 | 50.6 % | 46.9 % | 678 | -671 | -39 | -126..+48 | 0.89 | 3.9 % |
| Every stock, every day (same plan) | TEST | 7,554 | 40.6 % | 38.2 % | 1,323 | -1,216 | -245 | -286..-204 | 0.67 | 15.8 % |
| **Judge** | TEST | **0** | - | - | - | - | **0 (NO TRADE on every day)** | - | - | - |

Buyer by setup (expectancy, Rs/trade): S_BRK20 -7 / -135 / -39; S_TREND -2 / -210 / -212; multi-factor -71 / -86 / -269
(TRAIN / VALIDATION / TEST). More cited evidence did not help: the "multi-factor" cases were the worst on TEST.

Seller (swing SELL = exit/avoid a long, scored as a direction call within 5 sessions): correct 42.0 % / 40.2 % / 45.8 % of 24,582 /
9,725 / 11,883 cases; the average move after the call was +0.02 % / +0.19 % / -0.06 %. No predictive value.

Buyer by year (trades, Rs/trade): 2022 (619, -363), 2023 (7,336, +115), 2024 (6,794, -57), 2025 (6,705, -186), 2026 (4,897, -240).
By NIFTY regime: bull -54 (CI -77..), bear -170, sideways -108; high-volatility days +37 (n 3,798, all periods mixed, not tested
out of sample).

## What the Judge did

- With setup records taken from TRAIN+VALIDATION only (S_BRK20 -36, S_TREND -46, multi-factor -77, all with negative CIs), no setup
  qualified, so on TEST the Judge chose NO TRADE every day. Against the Buyer acting alone that avoided 4,598 trades averaging
  -Rs 220 (about -Rs 10.1 lakh in total on TEST). The Judge improved expectancy by declining, not by finding winners.
- Its card rules (stretched from VWAP / RSI above 75, plan problems, late entry) are NOT a useful filter in swing mode: on TEST the
  buyer cases those rules rejected averaged +Rs 16 (n 796, CI -48..) while the ones that passed averaged -Rs 269 (n 3,802). Stretched
  stocks kept going for a few days. This is one TEST observation, not a validated rule; changing the rules because of it would be
  fitting to the test period. It is logged for the next pre-registered round.
- Live `stats.json` now holds the TEST records (S_BRK20 -38.8, S_TREND -212.0, multi-factor -268.7, all CIs at or below zero), so the
  live Judge will keep returning NO TRADE on swing debates until a setup earns a positive untouched record.

## Answers to the validation questions (swing)

| question | answer |
|---|---|
| How often was the Buyer right? | 40-46 % of trades won after costs; T1 was reached before the stop only 12-14 % of the time |
| How often was the Seller right? | 40-46 %: below a coin toss |
| How often did the Judge pick the right direction? | It made no directional calls on TEST (NO TRADE 100 %) |
| Did the Judge improve net expectancy? | Yes versus the Buyer alone (0 vs -Rs 220 per signal), only by not trading |
| Did the debate reduce false entries? | It removed all of them, together with every entry |
| Did it improve reward-to-risk? | Not measurable: no trades taken |
| Profitable after costs? | No configuration was profitable on TEST |
| Across regimes? | Negative in bull, bear and sideways regimes |
| vs existing best strategy | Round 2-3 best swing setup (CHoCH, docs/SWING_BACKTEST.md) was -Rs 8/trade out of sample on a different harness; nothing here beats it |

## Not yet validated

- Intraday mode: needs one-minute (opening window) or 15-minute bars replayed through the intraday snapshot. The 15-minute cache
  exists (100 stocks, 5 years); the one-minute fetch is in progress. Stage 5b.
- Correlation-based exposure limits (60-day return correlation) are not in the replay; trades are scored independently.
