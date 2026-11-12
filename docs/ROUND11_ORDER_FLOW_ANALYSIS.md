# Round 11 · Phase 4: order flow (tick and second level)

## What exists

| data | exists? |
|---|---|
| Historical tick-by-tick trades for NSE stocks | No. Not available from Angel, Zerodha or Yahoo for past dates. |
| Historical order-book (depth) snapshots | No. |
| Our own recordings (Round 10) | 25 large stocks, ONE session (12 Nov 2026), from 09:52 (the feed was silent 09:13-09:52). |
| One-minute candles | Yes (Phase 3). Executed volume only; no side, no depth. |

None of the 40 top movers in the window (Phase 1) was being recorded, and the recordings start after the window. **No order-flow
analysis of the top movers is possible.** Nothing here is reconstructed from one-minute candles.

## The one worked example: BAJFINANCE, 12 Nov 2026 (+3.2 %)

Signed volume was estimated from the recorded snapshots (quote rule, then tick rule); "resting buy share" is total bid quantity /
(bid + ask quantity), which are orders that can be cancelled at any time.

| minute | price | est. buy | est. sell | net | resting buy share |
|---|---|---|---|---|---|
| 10:07 | 1100.85 -> 1101.05 | 57,960 | 124,841 | -66,881 | 0.35 |
| 10:11 | 1100.40 -> 1100.00 | 78,334 | 67,494 | +10,840 | 0.36 |
| 10:12 | 1100.00 -> 1103.10 | 40,450 | 10,887 | +29,563 | 0.38 |
| 10:18 | 1103.80 -> 1106.00 | 58,941 | 6,162 | +52,779 | 0.38 |
| 10:19 | 1105.95 -> 1109.50 | 200,278 | 21,335 | +178,943 | 0.40 |
| 10:20 | 1109.45 -> 1112.15 | 120,375 | 27,576 | +92,799 | 0.46 |
| 10:24 | 1112.00 -> 1113.25 | 33,199 | 112,515 | -79,316 | 0.45 |

- Aggressive buying arrived IN the same minutes as the price jump (10:18-10:20), not before it.
- Resting bids grew AFTER the move (0.38 -> 0.46), i.e. the book followed price.
- Over the whole recorded day (328 minutes): correlation of one minute's net flow with the SAME minute's return 0.07, with the NEXT
  minute's return 0.03; resting buy share vs next-minute return -0.00.

One stock on one day proves nothing either way. It illustrates why order flow is usually coincident with price at this granularity.
The pre-registered Round 10 tests (40 sessions, `docs/ROUND10_ORDER_FLOW_RESEARCH.md`) remain the proper test; collection continues.
