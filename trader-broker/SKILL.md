---
name: trader-broker
description: >-
  Manual order tickets for Zerodha Kite. Never places an order. Shows the entry, stop-loss (SL with trigger and limit) and target as the exact
  Kite fields to enter by hand, marks an order READY only if trader-risk passed that exact order today, records the user's explicit "yes" for ONE
  order, logs what the user placed, records fills, and builds the flatten ticket to close an intraday position by 15:15. Use when the user says
  "give me the ticket", "what do I enter in Kite", "I placed it", "I got filled", "flatten", "square off", "log my trades".
argument-hint: "[show | approve | result | fill | flatten | log]"
---

# trader-broker

```bash
python3 "${CLAUDE_SKILL_DIR}/ticket.py" show                          # each order as plain words + Kite fields, READY or not
python3 "${CLAUDE_SKILL_DIR}/ticket.py" approve --index 1 --reply "yes"
python3 "${CLAUDE_SKILL_DIR}/ticket.py" result --index 1 --status placed --broker-id 2611110012345
python3 "${CLAUDE_SKILL_DIR}/ticket.py" fill --symbol RELIANCE --side buy --qty 8 --price 1330.00
python3 "${CLAUDE_SKILL_DIR}/ticket.py" flatten --symbol RELIANCE --qty 8 [--side buy]   # --side buy closes a short
python3 "${CLAUDE_SKILL_DIR}/ticket.py" log
```

Zerodha has no bracket order, so a trade is three Kite orders: (1) ENTRY, LIMIT, product MIS, validity DAY; (2) after the fill, STOP-LOSS: type SL with a
trigger price and a limit price a little beyond it; (3) TARGET: LIMIT. An SL-limit may not fill in a gap or a fast market, and a stop can fill beyond its
trigger: tell the user to watch it, and never promise an exit price. Check current Kite rules for SL-M and MIS before relying on them; MIS positions are
squared off by Zerodha late in the session with a charge, so be flat by `flat_by` yourself.

A "yes" counts for ONE order and must start with "yes"; "yes to all", "sure", "ok", or a yes naming another stock or amount is refused. READY needs a
trader-risk PASS for that exact order today. The log is append-only (`trader/state/broker.json`) and feeds the open-position and daily-loss limits.

## Safety

- Research and tooling, not financial advice. Not a SEBI-registered adviser. A rules check or a PASS is not a recommendation.
- You place every order yourself in Zerodha Kite. Nothing in this pack places, modifies or cancels an order.
- NSE cash-market equity only, intraday (MIS). No options, futures, index trades, delivery or swing trades.
- Say where each number came from and when. Never invent a price, a volume or a headline. Free data is delayed and unofficial.
- Capital protection first: Rs 500 max loss per trade, no averaging down, no revenge trades, never widen a stop.
