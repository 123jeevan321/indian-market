---
name: trader-swing
description: >-
  Swing module for NSE cash stocks held 1-5 trading days in delivery (CNC), LONG ONLY. Six objectively coded setups
  (compression squeeze breakout, liquidity sweep and reclaim, change of character, EMA pullback, previous-week-high breakout,
  bullish fair value gap retrace) plus a random baseline, a 5-year daily backtest with Zerodha delivery costs, a live scanner from
  the last completed daily bar, and a sizing calculator that keeps the loss at the stop (including costs) within Rs 1,500-2,000.
  Use when the user says "swing trade", "hold for a few days", "1-5 day trade", "delivery trade", "which stock for a week",
  "swing scan", "swing backtest", or asks to size a CNC position.
argument-hint: "[scan | backtest | size --entry X --stop Y]"
---

# trader-swing

```bash
python3 "${CLAUDE_SKILL_DIR}/swing.py" scan                                  # candidates from the last COMPLETED daily bar
python3 "${CLAUDE_SKILL_DIR}/swing.py" scan --setups squeeze,sweep --risk 1500 --capital 100000
python3 "${CLAUDE_SKILL_DIR}/swing.py" backtest --write docs/SWING_BACKTEST.md   # 5y daily, Nifty 500 liquid names, costs, IS/OOS
python3 "${CLAUDE_SKILL_DIR}/swing.py" size --entry 1356 --stop 1331 --risk 1500
```

Rules this skill enforces:

- **Long only.** An Indian cash short cannot be held overnight; bearish swings need F&O or SLB, which this project excludes.
- **Risk per trade Rs 1,500** (Scenario A, Rs 1 lakh) or **Rs 2,000** (Scenario B, Rs 2 lakh) INCLUDING delivery costs and slippage.
  Quantity = floor((risk - Rs 16) / (stop distance + ~0.22 % of price + 2 ticks)). Capital does not change the rupee risk.
- **Stops are structural** (signal-bar low, sweep low, last swing low, 3-bar low, gap bottom) minus 0.1 ATR, never closer than 1 ATR,
  never wider than 3 ATR (skip the trade instead).
- **Exits fixed before entry:** half at T1 = 1.5R, stop to entry, rest at T2 = 3R, everything out at the close of day 5. T3 = 4.5R is a
  stretch level, not part of the tested rule.
- **Delivery costs** (zerodha.com/charges, read 2026-11-10): no brokerage, STT 0.1 % on buy AND sell, stamp 0.015 % on buy, exchange,
  SEBI, GST, DP Rs 15.34 per sell. Swing costs are about 0.22 % of the position per round trip: a 2.5 % move keeps about 2.3 %.

How to present a swing call: use the TRADE PLAN format in `CLAUDE.md` with the setup's backtest row (win rate, expectancy, OOS) quoted next to
it. If the setup's out-of-sample expectancy is not positive, the answer is REJECT, whatever the chart looks like. Before any call check
results/board-meeting dates (`trader-news`), NIFTY regime and sector, and say if the stock already moved more than 6 % in 5 days (chasing).

## Safety

- Research and tooling. The user places every order in Kite. Nothing here places, modifies or cancels an order.
- No options, futures, index trades or short swings. A stop can gap overnight: the max loss is at the stop price, a gap can lose more.
