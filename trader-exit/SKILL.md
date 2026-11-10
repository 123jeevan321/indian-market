---
name: trader-exit
description: >-
  Exit Planner for NSE intraday trades. Before entry it sets the stop (opening-range midpoint, range low/high, a price, a
  percent or an ATR multiple), Target 1 plus stretch Targets 2 and 3 in R multiples, all on the Rs 0.05 tick, for a BUY or
  an intraday SELL, plus the exit-management ladder (book half at T1, breakeven plus costs, trail on structure, never widen,
  flat by 15:15). Refuses stops on the wrong side or too tight for the spread. Use when the user says "set my stop",
  "where is the target", "exit plan", "stop loss and targets", "partial profit", "when do I move to breakeven".
argument-hint: "[--stop or-mid|or-low|or-high|price:X|pct:X|atr:K] [--target 1.5R]"
---

# trader-exit

```bash
python3 "${CLAUDE_SKILL_DIR}/exit.py" plan                                  # from trader/entry.json, or-mid stop, 1.5R target
python3 "${CLAUDE_SKILL_DIR}/exit.py" plan --symbol RELIANCE --entry 1330.00 --or-high 1328.50 --or-low 1315.00 --write
python3 "${CLAUDE_SKILL_DIR}/exit.py" plan --symbol RELIANCE --side sell --entry 1313.00 --or-high 1328.50 --or-low 1315.00 --write
python3 "${CLAUDE_SKILL_DIR}/exit.py" plan --stop atr:1.5 --symbol INFY --entry 1180 --offline INFY.json
python3 "${CLAUDE_SKILL_DIR}/exit.py" show
```

- Prices are NSE prices: tick Rs 0.05. A long's stop rounds DOWN and a short's UP (away from the entry); targets to the nearest tick.
- T1 is your target (default 1.5R, matching `min_reward_risk`); T2 = T1 + 1R and T3 = T1 + 2R are stretch targets: move them to real
  structure (previous-day high/low, VWAP, round numbers, volume-profile nodes) when you present a call.
- The plan's `management` ladder is fixed BEFORE entry. Do not move to breakeven early (it turns winners into scratches) and never widen
  a stop. Whether partials help is an empirical question: the Time Machine's history and your own log decide, not a slogan.
- Refused with the reason: stop on the wrong side, target on the wrong side, risk under 0.05% of price or 3 ticks.
- A tight stop is only valid if structure supports it and it survives normal movement. Never pick an arbitrary 1-2 point stop.

## Safety

- Research and tooling, not financial advice. Not a SEBI-registered adviser. A rules check or a PASS is not a recommendation.
- You place every order yourself in Zerodha Kite. Nothing in this pack places, modifies or cancels an order.
- NSE cash-market equity only, intraday (MIS). No options, futures, index trades, delivery or swing trades.
- Say where each number came from and when. Never invent a price, a volume or a headline. Free data is delayed and unofficial.
- Capital protection first: Rs 500 max loss per trade, no averaging down, no revenge trades, never widen a stop.
