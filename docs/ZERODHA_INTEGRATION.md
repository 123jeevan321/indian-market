# Zerodha Kite MCP connector: capability report and Round 8 architecture (2026-11-11)

Everything below was verified with read-only calls on 2026-11-11 (after market close), unless marked UNVERIFIED. No order, GTT, alert or
session-changing call was made.

## 1. Connector capability report

| tool | modes | read-only? | research use |
|---|---|---|---|
| `market` | quote, ltp, ohlc, historical, search, option_chain | yes | the only research tool needed |
| `session` | status, logout | status only | session check (expires daily ~06:00 IST for the Kite part) |
| `portfolio` | profile, margins, holdings, positions | yes | not needed for research |
| `mutual_funds` | holdings | yes | not needed |
| `open_kite_view` | interactive widgets | yes | only if you ask for a chart |
| `orders` | list, history, trades, place, modify, cancel, permissions | NO (place/modify/cancel need your approval) | never used; keep "future orders" permission OFF |
| `gtt`, `alerts` | list/get, place/create, modify, delete | NO | never used |
| `help` | workflow docs | yes | reference |

Verified data fields:

| need | available? | evidence |
|---|---|---|
| Live price, OHLC, volume | yes | `quote` NSE:RELIANCE: last_price 1335.4, volume 17,554,310, ohlc |
| Exchange VWAP | yes | `average_price` 1337.54 |
| Last trade qty / time | yes | last_quantity 14, last_trade_time 15:59:55 |
| Total buy / sell quantity | yes | buy_quantity, sell_quantity |
| Market depth | yes, 5 levels each side (price, qty, orders) | `depth.buy/sell` |
| Circuit limits | yes | lower/upper_circuit_limit |
| Open interest | yes for F&O (`oi`, `oi_day_high/low`) | 0 for cash stocks, as expected |
| Instrument master | yes | `search` (BOD master): tokens, lot sizes, expiries |
| Futures contracts | yes | NFO:RELIANCE26NOVFUT, token 15794434, lot 500 |
| Option chain | yes | `option_chain` mode (not pulled here) |
| Historical candles | minute, 3, 5, 10, 15, 30, 60-minute, day | 1-minute RELIANCE bars from 2021-11-15 returned |
| Historical futures OI | yes: DAILY via continuous series back to at least 2022; intraday OI only for currently listed contracts | continuous day 2022-01-03..07 with oi; continuous 15-minute -> "invalid interval for continuous data" |
| Tick-by-tick trades | NO | quote is a snapshot; no trade tape tool |
| Streaming | NO | the MCP has no websocket; every snapshot is one call made by Claude |
| Historical depth / order book | NO | not exposed anywhere |

Practical limits: each MCP call runs inside the chat (it is not callable from our Python scripts), so it is ideal for snapshots, option
chains and spot checks, and poor for bulk downloads (5 years x 100 stocks of minute data would be thousands of calls through the chat).
`quote` takes up to 500 instruments per call, so a whole-universe depth snapshot is ONE call.

## 2. Angel One vs Zerodha

| requirement | Angel One (SmartAPI, scripted) | Zerodha (Kite MCP, in chat) | better for |
|---|---|---|---|
| Historical intraday bars | 15-minute, 5 years, downloaded for 99 stocks; 1-minute in 30-day windows | 1-minute verified back to Nov 2021; all intervals | Angel for bulk (scriptable); Zerodha for spot checks |
| Historical futures OI | UNVERIFIED | daily continuous series verified | Zerodha (or NSE F&O archive for bulk) |
| Live snapshot | `getMarketData FULL`, 50 per call: LTP, avgPrice (VWAP), totBuyQuan/totSellQuan, 5-level depth, circuits, OI | `quote`, 500 per call: same fields | equal content; Angel is scriptable, Zerodha covers 500 at once |
| Live stream | websocket SnapQuote: every update, recorded to disk by our recorder | none | Angel |
| Trade-level data | no (snapshots; trade side must be estimated) | no | neither |
| Option chain | not wired up (UNVERIFIED) | built-in mode | Zerodha |
| Reliability check | same values as Kite on 2026-11-11 (VWAP 1337.54, sell qty 8,156, last qty 14) | same | use both to cross-check |
| Restrictions | rate limits (about 3/s historical); daily TOTP login | Kite session expires daily; calls cost chat context | |

Conclusion: Zerodha does NOT add a new kind of order-flow data. Its depth, VWAP and buy/sell totals are the same fields Angel already gives
(they matched exactly). Keep the Angel recorder as the order-flow source.

## 3. Genuinely new for this project

1. Daily futures open interest history (continuous contract) for F&O stocks: long/short build-up, covering, unwinding (concepts 61-67).
2. Option-chain snapshots (OI by strike, put-call OI) for F&O stocks: forward only (concepts 68-70).
3. Whole-universe snapshot in one call (500 instruments): cross-sectional depth imbalance and VWAP deviation at chosen times.
4. 1-minute history back to 2021 for event studies (e.g. what happened in the 30 minutes after a sweep).
5. Independent second source to validate Angel data (data-quality checks).

## 4. Still missing (no retail source provides it)

Trade-by-trade tape with aggressor flags; order-level messages (adds, cancels, modifications); hidden/iceberg quantities; client or
participant IDs; historical order book; pre-open auction order book history; per-stock FII/DII flows. Market depth is a snapshot of
resting orders that can be cancelled: it is NOT institutional order flow.

## 5. What each institutional footprint question needs

| footprint | observable now? | how |
|---|---|---|
| Aggressive buying/selling | estimated only | Angel recorder: quote rule on consecutive snapshots |
| Bid/ask and depth imbalance | yes (snapshots) | Angel recorder stream; Zerodha/Angel snapshots |
| Absorption | estimated | big volume change with small price change while the same side's depth refills (recorder) |
| Large trades | partially | last_quantity jumps in the recorder (misses trades between snapshots) |
| Order-book replenishment | partially | depth at the best price refilling after trades (recorder) |
| Price response to pressure | yes, forward | recorder estimated delta vs next 5-15 minute returns |
| VWAP deviation / reclaim | yes | exchange VWAP (average_price / avgPrice) live; 15-minute approximation historically |
| Liquidity sweeps | yes | price history (all sources) |
| Accumulation / distribution (multi-day) | proxies | delivery % (NSE bhavcopy), futures OI change (Zerodha / NSE F&O archive), closing-hour volume |

## 6. Combined architecture for Round 8

| layer | source | how it is collected | stored in |
|---|---|---|---|
| Daily history | Yahoo daily (existing, 495 stocks) | scripts | trader/cache/daily5y |
| Intraday history | Angel 15-minute (existing, 99 stocks) | scripts | trader/cache/m15 |
| Delivery % history | NSE sec_bhavdata_full archive | scripts (flows.py fetch_day) | trader/cache/bhav |
| Futures OI history | NSE F&O bhavcopy archive (bulk); Zerodha continuous daily OI to cross-check | scripts + a few MCP checks | trader/cache/fo |
| Live order-flow | Angel recorder (websocket SnapQuote) | script, 9:10-15:31 | trader/ticks |
| Cross-sectional snapshots | Angel getMarketData FULL (scripted, 50/call) at 9:20, 10:00, 12:00, 14:45, 15:25; Zerodha quote for spot checks | script | trader/snapshots |
| Options positioning | Zerodha option_chain | Claude in chat, once a day | trader/snapshots/options |

Keys everywhere: NSE tradingsymbol + IST timestamp; a token map (Angel token <-> Kite instrument_token) built from both instrument masters;
quality checks: duplicate timestamps, zero-volume bars, prices outside circuit limits, split/bonus adjustment (both sources serve adjusted
prices; OI history is NOT adjusted, so use percentage changes), and cross-source agreement on close and VWAP.

## 7. Proposed Round 8 features (hypotheses, not strategies)

1. Futures OI change x price change quadrant (daily), and its 3-day persistence.
2. Cash-futures divergence: delivery % rising while futures OI falls (real money vs leverage).
3. Delivery % expansion (vs 20-day average) + close in the top of the range + above the prior high (breakout acceptance).
4. Futures basis change (futures close - spot close).
5. Live: exchange-VWAP deviation at 14:45 + depth imbalance (cross-section of 100-500 stocks), next-day return.
6. Recorder: estimated delta vs price change (absorption = strong delta, small move) and the next 15/30-minute response.
7. Recorder: best-level refill rate after trades at the bid (support being defended).
8. Option-chain put/call OI shifts for F&O stocks (forward only).

## 8. Data acquisition limits

- History is bars only. Depth, buy/sell totals and options OI by strike exist only from the day we start collecting.
- MCP calls run in chat: fine for daily snapshots and checks, not for bulk history.
- Kite session expires daily (about 06:00 IST); Angel needs a daily TOTP login (automated in the recorder).
- Survivorship bias remains for history (current index members only).

## 9. Implementation plan (Round 8, in order)

1. Download 5 years of NSE delivery bhavcopy and F&O bhavcopy (scripts, no MCP); cross-check a sample of OI against Zerodha.
2. Add features 1-4 to `research/discovery.py`; run stage A/B on TRAIN and VALIDATION only (the old TEST window is used up).
3. Start the Angel recorder daily (10-25 stocks) and a scripted snapshot logger at 5 fixed times (whole Nifty 100 / 200).
4. After 4-8 weeks of live data: test features 5-8 forward.
5. Any surviving candidate goes to forward paper-tracking as its final test.

Safety: research uses `market` and `session status` only. No `orders`, `gtt` or `alerts` mutation, no logout, no holdings/positions changes.
Credentials stay in environment variables and the connector; nothing sensitive is written to the repository.
