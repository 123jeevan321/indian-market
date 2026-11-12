# Open items (updated 12 Nov 2026, 17:45 IST)

| item | status | what it waits for |
|---|---|---|
| Round 10: order-flow recording | day 1 recorded (opening lost to a feed stall; watchdog added). Now automatic: Windows Task Scheduler, weekdays 09:05-15:31 (`scripts/run_recorder.bat`) | 40 sessions for the main test (about mid-January 2027) |
| Round 10B: 09:15-09:18 opening study (5 years, Nifty 100, 1-minute) | data fetch restarts automatically tonight after the Round 11 fetch; pauses 08:45-15:35 on weekdays; 1 of 100 stocks done so far | the fetch (Angel throttles hard: possibly several nights), then the 7 Round 10B reports. The placeholder for order-flow results is now `ROUND10_ORDER_FLOW_BACKTEST_RESULTS.md`, so `ROUND10_BACKTEST_RESULTS.md` is free for 10B |
| Debate system stage 5b: intraday validation | not started | the Round 10B 1-minute data (replayed through the same intraday snapshot) |
| Debate system stage 6: Claude (LLM) layer | not started (user chose engines first) | `ANTHROPIC_API_KEY` and a go-ahead |
| Round 11 1-minute data for all 461 stocks | 131 of 461 fetched; continues tonight | optional: the 37 top movers (needed for the reports) are done |
| Paper trading | day 1 logged (BAJFINANCE paper +Rs 99, real -Rs 29); day 2 is 13 Nov | user decision: live from Mon 16 Nov |
| Intraday scan universe | DONE: Nifty 500 via `debate.py morning` (about 2-4 minutes per run) | - |

Completed today: Round 10 recorder v3 (watchdog), debate system stages 1-5a (`docs/DEBATE_SYSTEM_PLAN.md`, `docs/DEBATE_VALIDATION.md`),
Three-Agent Trading Report format, Round 11 (10 reports, `docs/ROUND11_FINAL_CONCLUSION.md`).
