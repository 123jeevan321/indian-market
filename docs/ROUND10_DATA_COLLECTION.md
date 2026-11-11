# Round 10: Angel One order-flow data collection (started 2026-11-12)

## Recorder capability audit (verified from the code, the installed SmartAPI SDK and a live connection test)

| item | status | evidence |
|---|---|---|
| Feed | Angel SmartAPI WebSocket V2, mode 3 (SnapQuote) | SDK constants LTP_MODE=1, QUOTE=2, SNAP_QUOTE=3, DEPTH=4 |
| Last traded price, quantity, time | recorded (`ltp`, `ltq`, `ltt` epoch seconds) | test row: ltp 1335.4, ltq 14, ltt = 15:59:55 IST (matches Zerodha) |
| Cumulative day volume | recorded (`volume`) | 17,554,310 (matches Zerodha) |
| Total buy / sell quantity in the book | recorded (`tbq`, `tsq`) | 0 / 8,156 after the close |
| Best 5 bids and asks (price, quantity, number of orders) | recorded (`bids`, `asks`); side decided by price because the SDK swaps its buy/sell labels | test row asks [[1335.4, 8156, 43]] |
| Exchange timestamp | recorded (`exch_ts`, epoch milliseconds) | decodes to the exchange's last feed time |
| Local receive time | recorded (`recv`, IST, milliseconds, PC clock) | |
| Sequence number, token, exchange, mode | recorded (`seq`, `token`, `exchange`, `mode`) | added in v2 |
| Trade-by-trade tape | NOT available | SnapQuote is a snapshot per update; trades between updates are invisible |
| Order-level adds / cancels / modifications | NOT available | only aggregated depth |
| 20-level depth | available in the SDK as mode 4 (DEPTH), NOT used | UNVERIFIED for equity cash on this account; can be tested later |
| Update frequency | measured per day by `angel_recorder.py quality` | not assumed |
| Subscription limit | 25 symbols in this recorder (MAX_SYMBOLS); Angel's own per-connection limit UNVERIFIED (third-party sources say ~1,000 tokens) | |

### What v1 lacked and v2 fixes (trader-flows/angel_recorder.py)

| issue in v1 | v2 behaviour |
|---|---|
| no reconnect: one disconnect lost the rest of the day | SDK retries (3), then the recorder logs in again and re-subscribes, up to 30 times a day |
| flush every 500 ticks: up to 500 ticks lost in a crash | flush every 2 seconds |
| duplicate packets written | consecutive identical packets (same exchange time, price, volume, totals) skipped and counted |
| no record of gaps | `_session.log`: every connect, disconnect, error and any gap > 30 s |
| no token / exchange on rows | added |

Live test after hours (2026-11-12 00:29 IST, 3 symbols): connected, subscribed, wrote one row per symbol, stopped cleanly at the set time.

## Collection plan

- Dataset: `trader/ticks_r10/YYYY-MM-DD/SYMBOL.jsonl` + `_session.log` (git-ignored, local only; historical datasets untouched).
- Symbols (25): RELIANCE, HDFCBANK, ICICIBANK, SBIN, AXISBANK, KOTAKBANK, INFY, TCS, HCLTECH, LT, M&M, MARUTI, BHARTIARTL, ITC,
  HINDUNILVR, SUNPHARMA, TATASTEEL, BAJFINANCE, BEL, MCX, ADANIENT, NTPC, TITAN, ETERNAL, BSE (liquid, 9 sectors, all F&O).
- Hours: start 09:08 IST (subscription ready before the 09:15 open; pre-open packets are kept and labelled by time), stop 15:31.
- Duration: at least 4-8 weeks (20-40 sessions) before any test.
- Daily check: `python trader-flows/angel_recorder.py quality --date YYYY-MM-DD`.

## Running it each day

Today's session (2026-11-12) is scheduled as a background job in this Claude session (waits until 09:08, records until 15:31). It needs
the PC awake and the Claude app open. For later days, run this before 09:10 (or ask me to schedule it):

    python trader-flows/angel_recorder.py record RELIANCE HDFCBANK ICICIBANK SBIN AXISBANK KOTAKBANK INFY TCS HCLTECH LT M&M MARUTI BHARTIARTL ITC HINDUNILVR SUNPHARMA TATASTEEL BAJFINANCE BEL MCX ADANIENT NTPC TITAN ETERNAL BSE --out trader/ticks_r10

The recorder never imports or calls an order function (enforced by tests/test_recorder.py).
