---
name: trader-alerts
description: >-
  Price alerts and the NSE market clock. Says whether NSE is open, the next open, and the holiday; rings when a stock crosses a stop, a target
  (side-aware: a short's stop is above, its target below), a percent move, the opening bell, or the flat-by time (15:15 IST). Builds alerts from
  trader/plan.json including T2 and T3. Quotes are free Yahoo .NS data, delayed and unofficial: for alerts only, never for timing an order.
  Use when the user says "is the market open", "alert me at", "ring on the stop", "remind me to square off", "check my alerts".
argument-hint: "[clock | quote | add | check | list | reset]"
---

# trader-alerts

```bash
python3 "${CLAUDE_SKILL_DIR}/alerts.py" clock                      # IST, NSE open/closed, holiday, next open
python3 "${CLAUDE_SKILL_DIR}/alerts.py" quote RELIANCE TCS --write # -> trader/prices.json
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --from-plan            # stop, T1/T2/T3 and flat-by from trader/plan.json
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --symbol INFY --above 1190
python3 "${CLAUDE_SKILL_DIR}/alerts.py" check                      # rings what hit, once
python3 "${CLAUDE_SKILL_DIR}/alerts.py" list
```

Run `check` every few minutes while a trade is open (a scheduled task or `/loop`). The alert is a prompt for the user to act in Kite; the stop order in Kite is
what actually protects the trade. The clock covers the 2026 NSE holiday list; other years are flagged as unknown.

## Safety

- Research and tooling, not financial advice. Not a SEBI-registered adviser. A rules check or a PASS is not a recommendation.
- You place every order yourself in Zerodha Kite. Nothing in this pack places, modifies or cancels an order.
- NSE cash-market equity only, intraday (MIS). No options, futures, index trades, delivery or swing trades.
- Say where each number came from and when. Never invent a price, a volume or a headline. Free data is delayed and unofficial.
- Capital protection first: Rs 500 max loss per trade, no averaging down, no revenge trades, never widen a stop.
