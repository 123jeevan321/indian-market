---
name: trader-scanner
description: >-
  Chart Scanner for NSE India. Builds the stock universe from NSE's own Nifty 50, Nifty Next 50 and Nifty 500
  constituent files, runs a pre-open scan of daily closes (20-day closing-high breakout, bull flag, reclaim of the
  20-day average, oversold, oversold bounce) and an intraday opening-range scan on 5-minute bars in BOTH directions
  (breakout for a BUY, breakdown for an intraday SELL), then writes trader/watchlist.json. Free Yahoo data (.NS).
  Use when the user says "scan the market", "find setups", "what is breaking out", "what is breaking down", "opening
  range breakouts", "build my watchlist", "what should I look at today", or at the start of the trading day.
argument-hint: "[universe | daily | orb] [--side buy|sell] [--at HH:MM]"
---

# trader-scanner

Finds charts that match a rule. A hit is a lead, not a recommendation, and a scan is not a tradability check.

```bash
python3 "${CLAUDE_SKILL_DIR}/scan.py" universe                      # NSE Nifty 50 + Next 50 + 500 -> trader/universe.txt
python3 "${CLAUDE_SKILL_DIR}/scan.py" universe --exclude asm.txt    # drop ASM/GSM/blocked names (you maintain the list)
python3 "${CLAUDE_SKILL_DIR}/scan.py" daily                         # before the open or after the close -> trader/watchlist.json
python3 "${CLAUDE_SKILL_DIR}/scan.py" orb --side buy                # after 9:35 IST: closed above the 15-minute range high
python3 "${CLAUDE_SKILL_DIR}/scan.py" orb --side sell --at 10:30    # closed below the range low (intraday short)
python3 "${CLAUDE_SKILL_DIR}/scan.py" daily --symbols RELIANCE,M\&M,TCS
```

Floors: `--min-price 100` (Rs) and `--min-volume` (daily 500,000 shares; orb 0). `--now "2026-11-09 10:30"` pins the IST clock
for a replay. Exit code 0 when something matched, 1 when nothing did or it could not run.

## Universe

`archives.nseindia.com/content/indices/ind_nifty50list.csv`, `ind_niftynext50list.csv`, `ind_nifty500list.csv` (official,
free). Only the EQ series is kept. Index membership does NOT prove a stock is tradable today: confirm ASM/GSM/T2T,
circuit limits and events on nseindia.com before a call. Symbols with `&` or `-` (M&M, BAJAJ-AUTO) are handled.

## Sessions (IST)

Regular session 9:15-15:30; the opening range is the first 15 minutes (9:15, 9:20, 9:25 bars). A hit is the first completed
5-minute bar to CLOSE beyond the range. NSE trading holidays for 2026 are built in (read from nseindia.com on 2026-11-10); other
years need the list updated. Yahoo often omits the last two NSE bars of a session (15:20, 15:25): irrelevant for a 15:15 flat-by.

## Rules

- Say what was scanned: how many symbols, how many charts returned, how many usable, and the time of the data. A partial
  scan is called partial.
- Say "matched a rule", never "a buy" or "a good trade". Never print a P&L.
- A hit is stale once price has moved; re-run before acting. Next step: `/trader-news SYMBOL`, then `/trader-entry SYMBOL`.

## Safety

- Research and tooling, not financial advice. Not a SEBI-registered adviser. A rules check or a PASS is not a recommendation.
- You place every order yourself in Zerodha Kite. Nothing in this pack places, modifies or cancels an order.
- NSE cash-market equity only, intraday (MIS). No options, futures, index trades, delivery or swing trades.
- Say where each number came from and when. Never invent a price, a volume or a headline. Free data is delayed and unofficial.
- Capital protection first: Rs 500 max loss per trade, no averaging down, no revenge trades, never widen a stop.
