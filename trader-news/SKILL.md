---
name: trader-news
description: >-
  News and event-risk monitor for NSE stocks. Pulls the exchange's own corporate announcements (results, board-meeting
  outcomes, orders and contracts, credit ratings, insider and SAST disclosures) when NSE allows it, plus Yahoo Finance
  headlines, and each stock's move today. Labels items CONFIRMED (NSE filing) vs REPORTED (media). Use when the user
  says "any news on", "check the news", "why is it moving", "is there a result today", "event risk", before any trade
  call, and for every shortlisted stock.
argument-hint: "[symbols]"
---

# trader-news

```bash
python3 "${CLAUDE_SKILL_DIR}/news.py" --tickers RELIANCE TCS M\&M --hours 72
python3 "${CLAUDE_SKILL_DIR}/news.py"                      # watchlist + plan + portfolio symbols
python3 "${CLAUDE_SKILL_DIR}/news.py" --no-nse             # Yahoo headlines only
```

Sources and honesty:

- **NSE corporate announcements** (primary, CONFIRMED): `nseindia.com/api/corporate-announcements`. This is an unofficial website
  API. NSE sometimes answers 403 to scripts; the tool then prints one plain note and does NOT try to get around it. In that case
  open the NSE/BSE announcements page with the browser tools (or ask the user to paste), or use the company's investor-relations page.
- **Yahoo Finance headlines** (REPORTED): leads only. Open the story. Social-media claims and rumours are not news here.
- The "move" line uses Yahoo's chart for the last price vs the previous close.

What to do with it: for every call write a news/fundamental check: latest filings, results date, board meetings, dividends/splits/
ex-dates, ratings, orders, regulatory or promoter disclosures, sector news. An upcoming results date or a regulator action = event
risk: say so and normally avoid the stock that day. Do not chase a stock that already moved sharply on news.

## Safety

- Research and tooling, not financial advice. Not a SEBI-registered adviser. A rules check or a PASS is not a recommendation.
- You place every order yourself in Zerodha Kite. Nothing in this pack places, modifies or cancels an order.
- NSE cash-market equity only, intraday (MIS). No options, futures, index trades, delivery or swing trades.
- Say where each number came from and when. Never invent a price, a volume or a headline. Free data is delayed and unofficial.
- Capital protection first: Rs 500 max loss per trade, no averaging down, no revenge trades, never widen a stop.
