---
name: trader-entry
description: >-
  Entry Timer for NSE intraday trades. Watches one stock bar by bar (5-minute or 1-minute, Yahoo .NS data) and says
  waiting, triggered or expired for an opening-range breakout (BUY: first close above the range high) or breakdown (SELL:
  first close below the range low), or a close beyond a level you give. Honours the NSE calendar, 9:15 open, the
  no-entries-before 09:30 and no-entries-after 14:45 windows. Use when the user says "is it time to enter", "has RELIANCE
  triggered", "watch this setup", "entry timing", "can I short this", "ORB on", or after the scanner and news steps.
argument-hint: "SYMBOL [--side buy|sell] [--setup orb|level]"
---

# trader-entry

```bash
python3 "${CLAUDE_SKILL_DIR}/entry.py" check RELIANCE --side buy            # opening-range breakout, 5-minute bars
python3 "${CLAUDE_SKILL_DIR}/entry.py" check RELIANCE --side sell --write   # breakdown -> trader/entry.json
python3 "${CLAUDE_SKILL_DIR}/entry.py" check TCS --setup level --level 3200 --min-volume-x 1.5
python3 "${CLAUDE_SKILL_DIR}/entry.py" watch RELIANCE --every 30 --until 14:45
python3 "${CLAUDE_SKILL_DIR}/entry.py" check RELIANCE --now "2026-11-09 11:00"   # replay a past day
```

Status: **waiting** (not yet), **triggered** (a completed bar closed beyond the level, with its time and price), **expired** (no trigger
before `no_entries_after`, default 14:45). A bar counts only when complete; Yahoo's live tick is dropped. Opening range = the 9:15, 9:20,
9:25 bars. A wick through the level is not a trigger.

How to use a result: "triggered" means the CONDITION happened, not that the trade is good. A trigger that is more than one bar old is a
late entry: recalculate risk and reward or cancel, do not chase. Combine with market and sector context, VWAP side, relative volume and
news before any READY call. A short additionally needs: stock allowed for intraday short in Kite, no circuit lock, liquid, and a stop above.

Limits: free Yahoo bars lag and have no bid/ask, depth or aggressor data. This tool never claims order-flow or institutional activity.

## Safety

- Research and tooling, not financial advice. Not a SEBI-registered adviser. A rules check or a PASS is not a recommendation.
- You place every order yourself in Zerodha Kite. Nothing in this pack places, modifies or cancels an order.
- NSE cash-market equity only, intraday (MIS). No options, futures, index trades, delivery or swing trades.
- Say where each number came from and when. Never invent a price, a volume or a headline. Free data is delayed and unofficial.
- Capital protection first: Rs 500 max loss per trade, no averaging down, no revenge trades, never widen a stop.
