# Round 9: why each strategy failed

Round 9, 2026-11-12. All returns are NET percent per trade (delivery 0.25 %, intraday 0.12 % incl. slippage). Periods: train < 2024-11-11 <= validation < 2025-11-11 <= seen-once (used by rounds 7-8, never used for selection here).

| strategy | main cause (A-I) | evidence |
|---|---|---|
| I1 ORB long, I2 ORB short, I3 PDL sweep (intraday) | G insufficient edge, F costs | gross edge about 0 in every regime, period and gap type; 36-41 % win; costs 0.12 % turn ~0 into -0.1 % |
| D5 breakout 5d | A wrong direction / false breakouts, G | negative in ALL trend, volatility and gap regimes; worst in strong bear (-2.0 %); breakouts mean-revert over 5 days in this universe |
| D7 BTST 2d | F costs, A | negative everywhere; delivery STT on both legs (0.2 %) larger than any edge; strong closes do not continue |
| D4 reversal 5d | D regime | positive only in high volatility (+0.57 %) and after gaps (+0.44 / +0.66 %), negative in mid volatility and weak bull |
| D6 sweep 5d | D regime, I changing behaviour | +0.69 % train, -0.25 % validation; works in high volatility (+1.56 %) and after gaps; fails in bear trends |
| D1 momentum 10d | D regime, I | strong in strong trends both ways (+1.1 %), loses in weak bear (-1.27 %); +1.11 % train vs -0.14 % validation |
| D2 R7 candidate 10d | I overfitting / changing behaviour | chosen in Round 7 on train data: +1.11 % train, +0.19 % validation, -0.25 % seen-once |
| D3 R8 delivery+basis 5d | F costs, G | positive relative edge, but +0.16 / +0.09 / -0.07 % net per trade |
| D8 OI-model intraday short | I decay, F slippage | +0.20 % -> +0.07 % -> +0.06 %; the best stream on drawdown (13 pct points) but below 0.05 % extra slippage tolerance |
| D9 OI-model intraday long | G | about 0 before costs |

Patterns across all strategies:
- **Entry timing is not the main problem**: intraday entries at 9:30-10:30 and daily entries at the next open give the same sign.
- **Stops**: tight intraday stops (range mid) produce 36-41 % win rates; the 2 % study (below) shows the 1 % stop is hit first on about a
  third of days even without a signal, so the stop distance is inside normal noise.
- **Targets of 2 % or more are reached by only 9-11 % of 10:00 entries** before the close.
- **Costs** convert every near-zero gross edge into a loss; delivery strategies held 1-2 days are hit hardest.
- **Regime dependence is real but unstable**: the regimes where D1/D2/D6 worked in training did not reproduce in validation.
- Data/implementation (H): no material problems found; known limits are survivorship bias and 15-minute bar granularity.
