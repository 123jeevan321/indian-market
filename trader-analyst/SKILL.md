---
name: trader-analyst
description: >-
  Results and fundamentals check for NSE stocks. For a shortlisted stock, reads the company's latest quarterly results and filings from primary
  sources (NSE/BSE announcements, the company's investor-relations page, the results PDF) and sums up what changed: revenue, EBITDA, net profit
  and margins, year on year and quarter on quarter, debt and cash, orders, guidance, promoter pledging, and when the next results date is. Flags
  event risk for the day. Use when the user says "how were the results", "fundamental check", "is it reporting this week", "is the company
  healthy", "why is it up", or before any call on a stock with results or a board meeting near.
argument-hint: "SYMBOL"
---

# trader-analyst

This skill is a procedure, not a script (the original US version read SEC XBRL, which does not exist for India). Use primary sources in this order:

1. NSE corporate announcements for the symbol (financial results, outcome of board meeting, investor presentation, credit rating, orders, regulatory):
   `python3 trader-news/news.py --tickers SYMBOL --hours 720`. If NSE refuses scripted access, use the browser tools on
   nseindia.com/get-quotes/equity?symbol=SYMBOL (Corporate Filings), bseindia.com, or the company's investor-relations page; or ask the user to paste.
2. Quarterly results: pull revenue, EBITDA, PAT and margins for the last 4-5 quarters (standalone and consolidated: say which). Compare YoY and QoQ.
   Cross-check against the exchange filing, not only a media summary.
3. Balance-sheet and governance flags: debt, interest cover, promoter pledge, auditor remarks, litigation, regulatory actions.
4. The calendar: next results date, board meeting date, ex-dividend / record dates, corporate actions. Any of these on the trade day = event risk = avoid.

Write: what changed, what the market may be reacting to, what remains uncertain, and the trade implication (usually: avoid or reduce risk around an
event; a good result already priced in is not a reason to buy). Separate CONFIRMED (filings) from REPORTED (media) from rumour. Never trade on rumours.
Fundamentals rarely justify an intraday entry by themselves; they exist to keep you out of traps.

## Safety

- Research and tooling, not financial advice. Not a SEBI-registered adviser. A rules check or a PASS is not a recommendation.
- You place every order yourself in Zerodha Kite. Nothing in this pack places, modifies or cancels an order.
- NSE cash-market equity only, intraday (MIS). No options, futures, index trades, delivery or swing trades.
- Say where each number came from and when. Never invent a price, a volume or a headline. Free data is delayed and unofficial.
- Capital protection first: Rs 500 max loss per trade, no averaging down, no revenge trades, never widen a stop.
