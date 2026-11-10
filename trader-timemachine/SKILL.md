---
name: trader-timemachine
description: >-
  Time Machine. Replays the rest of the session 10,000 times for a planned NSE trade, drawing each 5-minute bar from the stock's own
  last ~60 sessions at the same time of day, and re-runs the same rule on every real past session. Reports target-first, stop-first and
  still-open odds, the average R, and an honest verdict. A simulation of the stock's recent behaviour, not a backtest of an edge and not
  a prediction. Use when the user says "replay it", "what are the odds", "has this setup worked", "simulate this trade", "time machine".
argument-hint: "[--plan trader/plan.json] [--seed N]"
---

# trader-timemachine

```bash
python3 "${CLAUDE_SKILL_DIR}/timemachine.py" run                      # the plan in trader/plan.json
python3 "${CLAUDE_SKILL_DIR}/timemachine.py" run --symbol M\&M --side sell --date 2026-11-09 --entry 3249.70 \
    --stop 3276.10 --target 3210.10 --entry-time "10:40 AM" --now "2026-11-09 10:45" --seed 7
python3 "${CLAUDE_SKILL_DIR}/timemachine.py" chart --help
```

- Data: one Yahoo request for 60 days of 5-minute `.NS` bars. Only complete sessions up to 15:15 are used (Yahoo often lacks the last two
  NSE bars); sessions with gaps are listed as left out. Needs at least 20 full sessions.
- Costs are NOT in the replay's R. Run `size.py` for net reward after Zerodha charges.
- Read the verdict honestly: if the history is negative or the replay leans to the stop, say so; do not oversell a marginal setup. A high
  win rate on 30-40 historical firings is not evidence of an edge; there is no confidence-interval magic here.
- This is not walk-forward or out-of-sample validation. Strategy claims need the backtest rules in `docs/MIGRATION_REPORT.md` (section 7).

## Safety

- Research and tooling, not financial advice. Not a SEBI-registered adviser. A rules check or a PASS is not a recommendation.
- You place every order yourself in Zerodha Kite. Nothing in this pack places, modifies or cancels an order.
- NSE cash-market equity only, intraday (MIS). No options, futures, index trades, delivery or swing trades.
- Say where each number came from and when. Never invent a price, a volume or a headline. Free data is delayed and unofficial.
- Capital protection first: Rs 500 max loss per trade, no averaging down, no revenge trades, never widen a stop.
