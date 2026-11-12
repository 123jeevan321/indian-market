---
name: trader-debate
description: Three-agent debate (Buyer vs Seller vs independent Judge) on one NSE cash stock, intraday or swing. Use when the user asks for a debate, a buy-vs-sell analysis, or "should I buy or sell X". Paper mode only.
---

# trader-debate

Run from the project root. Every debate is stored in `trader/debates/YYYY-MM-DD/` and is never edited afterwards.

    python trader-debate/debate.py run intraday SYMBOL [--now "YYYY-MM-DD HH:MM"] [--no-angel] [--state state.json] [--columns]
    python trader-debate/debate.py run swing SYMBOL [--now YYYY-MM-DD]
    python trader-debate/debate.py show trader/debates/<day>/<record>.json [--columns]
    python trader-debate/debate.py history [--date YYYY-MM-DD] [--symbol SYMBOL]
    python trader-debate/debate.py reassess trader/debates/<day>/<record>.json [--now ...]

How it works (docs/DEBATE_SYSTEM_PLAN.md):
1. `snapshot.py` builds ONE timestamped snapshot; every field is REALTIME, DELAYED, HISTORICAL or UNAVAILABLE.
2. `buyer.py` and `seller.py` each write a case from their own copy of the snapshot, without seeing the other's case.
3. Each challenges the other; each answers or concedes.
4. `judge.py` re-verifies every cited item, the plan arithmetic, the fatal challenges, the setup's untouched-test record
   (`stats.json`, filled by stage 5 validation) and the risk gate. It decides BUY, SELL or NO TRADE.

    python trader-debate/debate.py run intraday|swing SYMBOL --report      # Three-Agent Trading Report (Markdown)
    python trader-debate/debate.py best intraday|swing SYM1,SYM2,SYM3       # debate each, report ONE stock
    python trader-debate/debate.py morning [--at HH:MM] [--top 5]            # Nifty 500 scan -> skip >2.5% movers -> debate top 5
    python trader-debate/debate.py report trader/debates/<day>/<record>.json

STANDING FORMAT (CLAUDE.md): any Indian trading question gets ONE stock in the Three-Agent Trading Report produced by `--report`
or `best`: 🟢 Buyer, 🔴 Seller, ⚖️ Judge, 📊 Final Trade Report, in one response.

Rules for presenting a debate in chat:
- Show the timeline, the three panels and the Judge's reasons. Do not add a verdict of your own.
- SELL intraday = MIS short squared off by 15:15. SELL swing = exit or avoid a long; never an overnight short.
- While `stats.json` has no validated setups, every decision is NO TRADE. Say so; do not present a rejected case as a trade.
- Live mode skips the Angel login while the Round 10 recorder is running (depth and opening candles show UNAVAILABLE).
- Never place, modify or cancel orders. The user executes manually.
