# Round 9: market regime engine

Round 9, 2026-11-12. All returns are NET percent per trade (delivery 0.25 %, intraday 0.12 % incl. slippage). Periods: train < 2024-11-11 <= validation < 2025-11-11 <= seen-once (used by rounds 7-8, never used for selection here).

Inputs, all known at the decision time (the previous close; the opening gap only for intraday use at 9:15):

| dimension | rule | why |
|---|---|---|
| trend | NIFTY 20-day return within +-1.5 % -> sideways; else close > EMA50 > EMA200 and 20-day return > +2 % -> strong bull; close > EMA200 -> weak bull; close < EMA50 < EMA200 and 20-day return < -2 % -> strong bear; else weak bear | one label per day, no contradictions (precedence order) |
| volatility | NIFTY 20-day realised volatility, low / mid / high terciles with thresholds fixed on TRAIN | avoids look-ahead in the cut-offs |
| breadth | share of liquid stocks above their 50-day EMA: < 40 % weak, 40-60 % mixed, > 60 % strong | participation |
| opening gap | NIFTY open vs previous close: > +0.5 % up, < -0.5 % down, else flat | intraday only |

Tested and not kept as separate dimensions: delivery % and futures OI are stock-level signals (Round 8), not market regimes; ADX and
breakout/reversal "environments" duplicated trend and volatility. Code: research/round9.py `regimes()`.

Finding: regimes DO change which strategy looks best (tables in ROUND9_STRATEGY_CROSS_COMPARISON.md: momentum best in strong trends,
reversal and sweep best in high volatility and after gaps, every intraday breakout negative everywhere). The question is whether that
ranking is stable enough to select on: see the selection engine.
