---
name: trader-budget
description: >-
  Position sizing and costs for NSE intraday trades. Turns a plan (entry, stop, target) into a whole-share quantity from the Rs 500 max
  loss (quantity = floor(risk / |entry - stop|)), capped by the Rs 75,000 capital with no leverage assumed, then itemises Zerodha's
  brokerage, STT, exchange charges, SEBI fee, stamp duty, GST and slippage at the target and at the stop, shows gross and net P&L, and
  refuses trades whose costs eat too much of the reward. Writes a proposed order to trader/orders.json. Use when the user says "how many
  shares", "size this", "what will it cost", "net profit after charges", "position size", "is the target worth it".
argument-hint: "[--limit PRICE] [--write]"
---

# trader-budget

```bash
python3 "${CLAUDE_SKILL_DIR}/size.py"                       # sizes trader/plan.json with a limit order at the plan's entry
python3 "${CLAUDE_SKILL_DIR}/size.py" --write               # -> trader/orders.json (entry + stop + target legs)
python3 "${CLAUDE_SKILL_DIR}/size.py" --limit 1329.50 --json
python3 "${CLAUDE_SKILL_DIR}/costs.py" 50 1500 1510         # a round trip's charges
python3 "${CLAUDE_SKILL_DIR}/costs.py" verify               # compare the built-in rates with zerodha.com/charges
```

Config (`trader/config.json`, example in this folder): `budget` 75000, `max_loss_per_trade_inr` 500, `max_daily_loss_inr` 2000 (you allow 1,000 to 3,000), `max_trades_per_day` 0 (no cap), `max_open_positions` 2,
`max_open_risk_inr` 1000, `min_reward_risk` 1.5, `max_cost_pct_of_reward` 25, `slippage_ticks` 1, `mis_leverage` 5.

- Zerodha intraday (read from zerodha.com/charges on 2026-11-10): brokerage min(0.03%, Rs 20) per executed order; STT 0.025% on the sell side; NSE
  transaction charge 0.00307%; SEBI Rs 10 per crore; stamp duty 0.003% on the buy side; GST 18% on brokerage + SEBI + exchange. Rates change:
  run `costs.py verify` and re-read the page before quoting a net number to the user.
- MIS (Margin Intraday Square-off) is Zerodha's INTRADAY product; delivery is CNC. Zerodha's margin page lists the MIS leverage per stock (large caps 5x, others lower,
  e.g. 4.27x): `python3 costs.py leverage RELIANCE` reads it into `trader/leverage.json`, and the LOWER of that and `mis_leverage` applies. Leverage raises buying power, not
  the rupee risk: quantity still comes from the Rs 500 stop distance. Margins can change during the day. Zerodha charges Rs 50 + 18% GST per order if it auto-squares-off your MIS position.
- Always present BOTH gross and net. A target whose costs exceed ~25% of the gross reward is refused: that is the "5-10 point scalp is not worth it" rule.
- Quantity is a whole number rounded down. The max loss shown is at the stop price; a gap can lose more.

## Safety

- Research and tooling, not financial advice. Not a SEBI-registered adviser. A rules check or a PASS is not a recommendation.
- You place every order yourself in Zerodha Kite. Nothing in this pack places, modifies or cancels an order.
- NSE cash-market equity only, intraday (MIS). No options, futures, index trades, delivery or swing trades.
- Say where each number came from and when. Never invent a price, a volume or a headline. Free data is delayed and unofficial.
- Capital protection first: Rs 500 max loss per trade, no averaging down, no revenge trades, never widen a stop.
