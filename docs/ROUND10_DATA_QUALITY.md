# Round 10: data quality

Checked every day with `python trader-flows/angel_recorder.py quality --date YYYY-MM-DD` (rows, rows per minute in market hours, gaps over
30 s, the longest gap, median clock offset between local receive time and exchange time, crossed books) plus `_session.log`.

## Rules applied before any analysis

1. Use the EXCHANGE timestamp (`exch_ts`) for ordering and for every prediction window; the local `recv` time is only for latency checks.
2. A signal computed at time t may use only rows with `exch_ts` <= t. Labels (future price change) start strictly after t.
3. Sessions with a gap > 60 s in market hours are flagged; signals inside a gap are dropped, not filled.
4. Rows with a crossed or empty book (bid >= ask, no bid or no ask) are excluded from imbalance features.
5. Depth and total buy/sell quantity are RESTING ORDERS, which can be cancelled or modified at any time. Executed volume is only the change
   in cumulative `volume`; its direction is ESTIMATED (quote rule, then tick rule). Neither is evidence of who traded.
6. Pre-open (09:00-09:15) packets are analysed separately from the continuous session.

## Day log

| date | symbols | rows | median rows/min | days with gaps > 60 s | reconnects | notes |
|---|---|---|---|---|---|---|
| 2026-11-12 (after-hours test, 00:29) | 3 | 3 | n/a | n/a | 0 | one snapshot per symbol after the close, as expected; `exch_ts` = last feed time (16:08:11 IST on 11 Nov) |
| 2026-11-12 (first session) | 25 | pending | pending | pending | pending | scheduled |
