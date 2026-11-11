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

## Daily routine and the trade card

- **After the close (from 15:35 IST):** `swing.py scan --setups sweep --rs-min 0.8 --watch MCX,BEL,...` on the completed daily bar. This is when
  swing signals exist; nothing intraday changes a daily signal.
- **Next session:** the tested entry is the next day's OPEN (or the signal day's close, see the timing table in docs/SWING_BACKTEST.md). Waiting until
  9:45-10:30 to see the open settle, or buying at 14:30-15:15, is a reasonable manual refinement, but it is NOT what was backtested: say so. Skip the
  trade if the price has already moved more than 1 x ATR above the planned entry (chasing).
- **Card (always this shape):**

```
SWING [LONG] SYMBOL | setup: sweep+RS (paper-only lead) | data: Yahoo daily, bar DATE
Entry range: X - Y          Stop-loss: Z (structural: sweep low - 0.1 ATR)
Target 1: A (+a%, 1.5R) - book half, stop to entry     Target 2: B (+b%, 3R)     Time exit: close of day 10
Quantity: N (Rs value)      Max loss incl. costs: Rs <=1,500      Net at T1: Rs ...
Why: <the exact conditions that fired>   Why not: <regime, extension, event risk>
Decision: PAPER / REJECT (until the setup passes out-of-sample)
```

Targets come from R multiples of the structural stop, not a fixed 2.5-5 %. The card shows the percentage each target means; if T1 is under
about 2 % the move is too small for the delivery costs and the trade is skipped.

## 2-Stock Sector-Split Rotation (BTST, 1-2 days)

`momentum_rotator.py scan --angel` (from 14:45 IST, Angel One live snapshot) or `scan` after the close; `momentum_rotator.py backtest --offline`.
Card: symbol + industry, LTP/time/source, day gain, RVOL, close position in range, buy range, stop (-1.5 %), book profit (+3 %), day-2 time exit,
quantity, max loss incl. costs, net at target, decision. Status: FAILED the backtest gate on 2026-11-11 -> PAPER.

## Safety

- Research and tooling. The user places every order in Kite. Nothing here places, modifies or cancels an order.
- No options, futures, index trades or short swings. A stop can gap overnight: the max loss is at the stop price, a gap can lose more.
