# India Equity Intraday Analyst

Claude skills for **NSE India cash-market intraday trade research**: a scanner, news and event-risk checks, an entry timer, an
exit planner, a Time Machine replay, a risk gate, position sizing with real Zerodha costs, manual Kite tickets, alerts, a
results/fundamentals procedure and a delivery/FII-DII context tool. **A research aid: you place every order yourself.**
NO TRADE is a valid, often preferred, answer.

Adapted from the US-market [day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill) (MIT, Jake Schincariol); the original is
untouched. Not affiliated with NSE, Zerodha or Anthropic. **Not financial advice.** Most intraday traders lose money; this pack
does not change that. Nothing here guarantees profit, and every setup is **unvalidated** until backtested on Indian data (see
`docs/MIGRATION_REPORT.md`).

## Scope

- NSE cash-market equity, intraday (MIS), liquid stocks from Nifty 50 / Next 50 / 500. BUY, or intraday SELL (short) where permitted.
- Not allowed (blocked by the risk gate): options, futures, index trades, commodities, forex, crypto, delivery/swing trades.
- Capital Rs 75,000. Max loss per trade Rs 500. Proposed Rs 1,000 daily loss (confirm it), 2 positions, Rs 1,000 total open risk.
- All times IST. Session 9:15-15:30, no entries before 09:30 or after 14:45, flat by 15:15.

## Install

```bash
git clone https://github.com/123jeevan321/india-equity-intraday-skill.git
cd india-equity-intraday-skill
python -m unittest discover -s tests        # offline tests
mkdir trader && cp trader-budget/config.example.json trader/config.json   # your rules
```

As Claude Code skills: copy the `trader-*` folders into `~/.claude/skills/` (or your project's `.claude/skills/`), or add this repo as a
plugin marketplace. Working inside this folder, `CLAUDE.md` is loaded automatically and holds the standing rules. Python 3.8+, standard library only.

## The twelve

| skill | job |
| --- | --- |
| `/trader-desk` | the conductor: runs the day in order and writes the TRADE PLAN |
| `/trader-scanner` | NSE universe; daily setups; opening-range breakout (BUY) and breakdown (SELL) scans |
| `/trader-news` | NSE announcements (confirmed) + Yahoo headlines (reported) + event risk |
| `/trader-entry` | bar-by-bar trigger for a BUY or SELL |
| `/trader-exit` | stop, T1/T2/T3 on the 0.05 tick, exit-management ladder |
| `/trader-timemachine` | 10,000 replays from the stock's own recent bars + real history |
| `/trader-budget` | quantity from Rs 500 risk, Zerodha costs, gross vs net, refuses poor-value targets |
| `/trader-risk` | PASS/BLOCK against your limits, MIS only, no index/F&O symbols |
| `/trader-broker` | the exact Kite orders to enter by hand; records your yes; never places anything |
| `/trader-alerts` | NSE clock and side-aware stop/target/flat-by alerts |
| `/trader-analyst` | results and fundamentals procedure from primary sources |
| `/trader-flows` | official delivery %/volume context and FII/DII (not order flow) |

## One trade, end to end

```bash
python trader-scanner/scan.py universe && python trader-scanner/scan.py orb --side buy
python trader-news/news.py --tickers RELIANCE              # filings, event risk
python trader-entry/entry.py check RELIANCE --side buy --write
python trader-exit/exit.py plan --write                    # stop, T1-T3, management
python trader-timemachine/timemachine.py run               # honest odds
python trader-budget/size.py --write                       # shares, costs, net
python trader-risk/check.py                                # PASS / BLOCK
python trader-broker/ticket.py show                        # Kite fields; you type them in
```

## Data honesty

- **Yahoo `.NS` charts**: free, unofficial, 5-minute bars, delayed, last two NSE bars often missing. Good for structure, not for tick timing.
- **NSE archives** (index lists, bhavcopy with delivery %): official, end of day, scriptable.
- **NSE website APIs** (announcements, FII/DII): unofficial; they may answer 403 to scripts. The tools say so and fall back to the browser or a paste; they do not try to evade the block.
- **Order flow** (bid/ask, footprint, delta/CVD, depth): *not available* in any free source here. Without a tick/depth feed the evidence score for it is 0. Nothing is fabricated.
- **Costs**: Zerodha rates read from zerodha.com/charges on 2026-11-10 (`costs.py verify` re-checks). STT/exchange/SEBI/stamp/GST all change; re-verify.

See `docs/MIGRATION_REPORT.md` for the architecture, what changed from the US pack, the data requirements, what needs paid data, and the validation roadmap.

MIT. Original work (c) 2026 Jake Schincariol; India adaptation (c) 2026 Maghil-Jeevan.
