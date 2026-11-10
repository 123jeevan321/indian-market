---
name: trader-risk
description: >-
  Risk Manager for NSE intraday orders. Checks every proposed order against the user's limits and says PASS or BLOCK with reasons:
  Rs 500 max loss per trade, Rs 1,000 daily loss, 2 open positions, Rs 1,000 total open risk, reward:risk, costs vs reward, capital,
  the 0.05 tick, the 09:30-14:45 entry window and NSE holidays, MIS only, no index, futures or options symbols. Exits are never
  blocked. Use when the user says "check this trade", "is this within my limits", "risk check", or before every ticket.
argument-hint: "[--orders trader/orders.json]"
---

# trader-risk

```bash
python3 "${CLAUDE_SKILL_DIR}/check.py"                      # trader/orders.json + trader/config.json -> trader/state/risk.json
python3 "${CLAUDE_SKILL_DIR}/check.py" --now "2026-11-11 10:05" --no-write
python3 "${CLAUDE_SKILL_DIR}/check.py" --json
```

What blocks an ENTRY: format, an index/futures/option-looking symbol, a product other than MIS, a price off the Rs 0.05 tick, a blocked
symbol, size, capital, a missing or wrong-sided stop, `loss` over `max_loss_per_trade_inr` (500), reward:risk under `min_reward_risk` (1.5),
costs over `max_cost_pct_of_reward` (25%), `daily loss` over `max_daily_loss_inr` (1,000), more than `max_open_positions` (2), total open risk
over `max_open_risk_inr` (1,000), `max_trades_per_day`, a duplicate, and the entry window (09:30-14:45 IST, trading days only).
Exits (a flatten) only get warnings: getting out is always possible.

Each verdict carries a fingerprint of the exact order; trader-broker shows READY only for the order that passed today. A PASS is a rules check, not a
recommendation, and it knows nothing about news, event risk, circuit limits or ASM/GSM status.

## Safety

- Research and tooling, not financial advice. Not a SEBI-registered adviser. A rules check or a PASS is not a recommendation.
- You place every order yourself in Zerodha Kite. Nothing in this pack places, modifies or cancels an order.
- NSE cash-market equity only, intraday (MIS). No options, futures, index trades, delivery or swing trades.
- Say where each number came from and when. Never invent a price, a volume or a headline. Free data is delayed and unofficial.
- Capital protection first: Rs 500 max loss per trade, no averaging down, no revenge trades, never widen a stop.
