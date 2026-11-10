---
name: trader-flows
description: >-
  Delivery and participation context for NSE stocks, replacing the original US Congress-trade tracker. Reads NSE's official end-of-day bhavcopy with delivery
  position to show each stock's delivery %, volume and trades against its own recent days, screens the liquid universe for unusual volume and delivery,
  and reports FII/FPI and DII cash-market net flows when NSE allows it. Context only: it cannot see intraday bid/ask aggression, depth, footprint or
  delta and never claims institutional order flow. Use when the user says "delivery volume", "is there accumulation", "FII DII data", "unusual volume
  yesterday", "institutional activity", "who is buying".
argument-hint: "[delivery SYMBOL... | screen | fii-dii]"
---

# trader-flows

```bash
python3 "${CLAUDE_SKILL_DIR}/flows.py" delivery RELIANCE TCS --days 10     # delivery %, volume, close by day
python3 "${CLAUDE_SKILL_DIR}/flows.py" screen --top 20 --min-turnover 100  # liquid names with unusual volume / delivery (uses trader/universe.txt)
python3 "${CLAUDE_SKILL_DIR}/flows.py" fii-dii                             # FII/FPI and DII net, if NSE answers
```

Source: `archives.nseindia.com/products/content/sec_bhavdata_full_DDMMYYYY.csv` (official; posted in the evening; holiday dates may carry the previous
session's data, which the tool detects and skips). Cached under `trader/cache/`.

How to read it, and what NOT to claim:

- Delivery % = delivered quantity / traded quantity. Higher than the stock's own average with rising price and volume MAY indicate accumulation; with a falling
  price MAY indicate distribution. These are labels for "possible", never "FIIs bought". Use only: possible accumulation, possible distribution, insufficient evidence.
- Intraday delivery % does not exist; this is end-of-day context for tomorrow's watchlist.
- FII/DII figures are provisional end-of-day totals for the whole market, not per stock. Quote the date and source. If the NSE API refuses, ask the user to paste them.
- Real order-flow analysis (bid/ask volume, footprint, CVD, stacked imbalances, depth) needs a tick/depth feed (for example Zerodha Kite Connect market-depth websocket, or a
  paid vendor) and a recorder. Without it, say "no genuine order-flow data" and score that criterion 0.

## Safety

- Research and tooling, not financial advice. Not a SEBI-registered adviser. A rules check or a PASS is not a recommendation.
- You place every order yourself in Zerodha Kite. Nothing in this pack places, modifies or cancels an order.
- NSE cash-market equity only, intraday (MIS). No options, futures, index trades, delivery or swing trades.
- Say where each number came from and when. Never invent a price, a volume or a headline. Free data is delayed and unofficial.
- Capital protection first: Rs 500 max loss per trade, no averaging down, no revenge trades, never widen a stop.
