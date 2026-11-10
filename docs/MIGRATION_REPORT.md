# Migration report: US Day Trader skill -> India Equity Intraday Analyst

Date of this report: 2026-11-10 (IST). Source: `C:\Users\jeeva\claude-projects\day-trader-skill` (commit 3d0f4ef, "The Trader skill v2:
11 day-trading skills", MIT, Jake Schincariol). **The source folder was copied, never modified** (verified with `git status`: only
pre-existing `__pycache__` entries, nothing changed). The Forex project (`forex-market`) was not used.

## 1. The 11 original agents and what each became

| # | original | original job | India version | status |
| --- | --- | --- | --- | --- |
| 1 | trader-scanner | Nasdaq Trader universe; daily + ORB scans (Yahoo) | NSE Nifty 50/Next 50/500 universe, `.NS` symbols, ORB BUY **and SELL** | adapted, tested live |
| 2 | trader-news | Yahoo RSS + SEC 8-K | NSE announcements (confirmed) + Yahoo IN headlines (reported) | adapted; NSE API may 403 |
| 3 | trader-entry | ORB trigger, long only | IST/NSE hours, BUY and SELL triggers | adapted, tested |
| 4 | trader-exit | stop + 1 target, long only | tick-aware, BUY/SELL, T1/T2/T3, management ladder | adapted, tested |
| 5 | trader-timemachine | 10,000-run replay | IST, 72-bar sessions (Yahoo omits last 2 NSE bars), `.NS` | adapted, tested live |
| 6 | trader-risk | US limits, PDT, Alpaca order shape | Rs limits, 2 positions, open risk, costs gate, tick, MIS only, no index/F&O | adapted, tested |
| 7 | trader-budget | USD sizing, Alpaca bracket | Rs 500-risk sizing, capital cap, Zerodha costs, net P&L, refuse if costs > 25% of reward | adapted, tested |
| 8 | trader-broker | tickets + Alpaca MCP calls | manual Kite tickets (3 orders), records the user's yes, never places | adapted |
| 9 | trader-alerts | quotes (Yahoo/Stooq), NYSE clock | NSE clock, side-aware alerts incl. T2/T3, Yahoo only | adapted |
| 10 | trader-analyst | SEC XBRL earnings facts | **procedure only** (no equivalent free structured API): NSE/BSE filings + IR | replaced |
| 11 | trader-pelosi | US Congress trade disclosures | **trader-flows**: NSE bhavcopy delivery %/volume, screen, FII/DII | replaced |
| + | (none) | | **trader-desk** conductor + project `CLAUDE.md` rules | new |

## 2. US-specific components found (and their fate)

New York timezone/DST helper (all 9 scripts) -> IST constant +5:30, no DST. NYSE holidays/early closes 2026-27 -> NSE 2026 list (official `holiday-master`),
no half-days. 9:30-16:00 -> 9:15-15:30. Nasdaq Trader symbol lists -> NSE index CSVs. Yahoo symbols -> `.NS` with `&` encoding. SEC EDGAR (8-K, XBRL) -> NSE
announcements / procedure. House Clerk STOCK Act PTRs -> removed. Alpaca MCP + bracket order shape -> Kite manual tickets. PDT rule -> removed (default off).
USD -> Rs; Stooq quotes -> removed. US-only fixtures and 11 US test files -> replaced with 42 India tests.

## 3. Reusable as-is

Yahoo chart parsing and the polite 429/5xx retry logic; the bar-by-bar trigger engine; the Decimal tick maths in trader-exit; the Time Machine
resampling engine; the fingerprint / yes-parsing / append-only log design in trader-risk and trader-broker; the offline-fixture test approach.

## 4. India adaptation highlights

- Hours 9:15-15:30 IST; pre-open 9:00-9:15 is analysis only; `no_entries_before` 09:30, `no_entries_after` 14:45, `flat_by` 15:15.
- Today (2026-11-10) is an NSE trading holiday (Diwali Balipratipada); 2026-11-08 (Sunday) is the Muhurat session day. Neither is traded by this pack.
- Tick Rs 0.05 enforced in sizing, exit, risk and the Kite ticket. Stops round away from the entry.
- Quantity = floor(Rs 500 / |entry - stop|), capped by capital with **no leverage assumed**. Example: RELIANCE at Rs 1,330 with a Rs 7.60 stop caps at 56 shares by capital (65 by risk).
- Costs: brokerage min(0.03%, Rs 20) per executed order, STT 0.025% sell side, NSE 0.00307%, SEBI Rs 10/crore, stamp 0.003% buy side, GST 18%, plus 1 tick slippage per side
  (Zerodha page read 2026-11-10; `costs.py verify`). Gross and net are both shown; a trade is refused when costs exceed 25% of the gross reward.
- Short selling: BUY/SELL symmetric in scanner, entry, exit, budget, risk, alerts, ticket; flatten supports covering a short.

## 5. Data requirements and what is genuinely possible

| need | source here | quality | order-flow-grade? |
| --- | --- | --- | --- |
| Universe | NSE archives index CSVs | official, free | n/a |
| Intraday OHLCV | Yahoo `.NS` 5m | unofficial, delayed, last bars often missing | no bid/ask |
| Previous-day levels, volume, delivery % | NSE bhavcopy (archives) | official, free, EOD | context only |
| Announcements, results | NSE website API / BSE / IR | unofficial; may 403 scripts | n/a |
| FII/DII | NSE website API | unofficial; may 403 | n/a |
| GIFT Nifty, global cues, India VIX, news | web search / browser tools | varies; cite and timestamp | n/a |
| ASM/GSM/T2T, circuit bands | nseindia.com lists | **not automated**; maintain `--exclude` file | n/a |

Genuinely possible with free data: VWAP (from bars), relative volume (vs own history), ATR/RSI/MACD/BB/MAs, opening range, previous-day high/low, session highs/lows,
swing structure, FVG / order-block / BOS / CHoCH / equal-high-low *as price-action descriptions on OHLC bars*, volume-profile **approximations from 5-minute bars**
(label them as approximations), delivery-% context.

## 6. Features that need paid or additional data

- **True order flow** (bid/ask volume, footprint, delta, CVD, stacked imbalance, absorption with aggressor classification, depth, time & sales): requires a tick + depth feed.
  Options: Zerodha Kite Connect (paid API; websocket gives ticks and 5/20-level depth on subscription) with a local recorder; or a vendor feed. Even then, depth shows resting orders
  (which can be cancelled), not institutions. Until this exists the order-flow score is 0 and the system says so.
- **Real-time quotes without lag**: Kite Connect websocket or a vendor.
- **True volume profile (tick-based POC/VAH/VAL)**: tick data; 1-minute bars give a better approximation than 5-minute.
- **Historical intraday data for proper backtests**: Yahoo gives only ~60 days of 5m. A multi-year Indian 1-minute/5-minute set needs a vendor or Kite historical API.
- **Automated ASM/GSM and corporate-action calendars**: NSE files exist but need a reliable fetcher; pending.
- **Pre-open indicative prices / imbalance (9:00-9:15)**: NSE pre-open market data is a website API; collect via the browser tools or a paid feed.

## 7. Validation roadmap (not done yet; every setup is UNVALIDATED)

1. Get >= 2-3 years of Indian 1m/5m data for the Nifty 500 universe, including delisted names (survivorship), with corporate-action adjustments.
2. Implement the setups as rules; costs and slippage from `costs.py`; no look-ahead (signals on completed bars, fills on the next bar's open/limit logic).
3. Chronological train / validation / test split; walk-forward; compare each setup to a simple baseline (e.g. buy at 09:30 and sell at 15:15; random-entry with the same stops).
4. Report trade count, expectancy (R and Rs), profit factor, max drawdown, average win/loss, bootstrap confidence intervals, by regime (trending / ranging / high-VIX).
5. Add an indicator only if it adds out-of-sample value beyond price and volume.
6. Until then the Time Machine's per-stock replay is a sanity check, not evidence of an edge (its own history for M&M's ORB short on 58 sessions was R -0.096).

## 8. Implemented now vs open items

Implemented and tested offline (42 tests) plus live smoke-tests on real NSE data: calendar, IST, universe, scanner both sides, entry both sides, exit/targets/management, Time Machine,
sizing with costs, risk gate, Kite tickets, alerts, flows (bhavcopy), delivery logic, news with graceful NSE fallback.

Open items for the user's decisions or a follow-up:
1. **Confirm the Rs 1,000 daily max loss** (config default, not yet confirmed) and `max_trades_per_day` (3 by default; the brief did not say).
2. **Zerodha MIS rules** (leverage per stock, auto-square-off time and fee, SL-M availability, short-sell eligibility list) must be checked in Kite; nothing here assumes them.
3. **ASM/GSM list automation** and the 2027 holiday list (NSE publishes next year's in December).
4. **VWAP / relative-volume / SMC / volume-profile calculators** over bar data (the framework is in `CLAUDE.md`; the scripts for these indicators are not written yet).
5. **Order-flow data source** (Kite Connect depth recorder or a vendor), if you want that evidence criterion to count.
6. **Backtesting engine** (section 7).
7. A fully live end-to-end paper day on a trading session; today was a holiday, so the live checks used 2026-11-09 data and replays.
