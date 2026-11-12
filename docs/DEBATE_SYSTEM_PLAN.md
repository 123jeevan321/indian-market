# Three-agent debate system (Buyer vs Seller vs Judge): plan, architecture, data flow

Status: PLAN (2026-11-12). Paper mode only. Nothing here places, modifies or cancels orders.

## 1. Two design decisions that everything else follows from

**A. The agents are evidence engines first, writers second.** Each agent is a Python module that computes its evidence from the shared
snapshot and returns a structured case (JSON). An optional LLM layer (Claude) can turn that case into prose and argue in the rebuttal
rounds, but it may only cite evidence IDs that the engine computed. The Judge's decision is computed from verified evidence and historical
statistics; the LLM Judge can explain it but cannot override it. If the LLM output disagrees with the computed decision, or cites evidence
that does not exist, the result is NO TRADE and the mismatch is logged.

Why: the user's own principle ("the side with the strongest independently verified statistical evidence, not the most convincing
AI-generated explanation"). A persuasive language model is exactly the failure mode to guard against.

**B. Historical validation is done on the engines, not on the language model.** An LLM replaying 2021-2026 dates already "knows" much of
what happened (its training data covers those markets), so any LLM backtest over that period has look-ahead bias that cannot be removed.
It would also cost thousands of API calls. So: the deterministic agents are backtested 60/20/20 over five years; the LLM layer is judged
only on forward paper trading, by comparing its explanations with the engine's decisions and outcomes.

## 2. Architecture

```
trader-debate/
  SKILL.md              how to run a debate in chat (intraday / swing)
  snapshot.py           STEP 1: one timestamped, provenance-tagged snapshot shared by all agents
  evidence.py           evidence catalogue: id, side, formula, threshold, data source, historical stat key
  buyer.py              STEP 2: bullish case (sees only the snapshot)
  seller.py             STEP 3: bearish case (sees only the snapshot)
  rebuttal.py           STEPS 5-7: each side challenges the other's evidence with rule-based checks, then responds
  judge.py              STEPS 8-9: re-verifies every cited item, applies stats + risk gates, decides BUY / SELL / NO TRADE
  llm.py                optional: Claude narration and argument layer (structured outputs, evidence-ID citations only)
  debate.py             orchestrator + CLI: run, show, history, reassess
  render.py             STEP 10: terminal view: three labelled panels (BUYER / SELLER / JUDGE) and a chronological timeline
  validate.py           historical replay of the engines, 60/20/20, regimes, comparisons
trader/debates/YYYY-MM-DD/<id>.json     full record (git-ignored): snapshot, every message with timestamp, model versions, decision
```

Reused, not duplicated: `trader-entry/levels.py` (VWAP, RVOL, opening range, profile, impulse), `trader-swing/swing.py` (`enrich`:
EMAs, ATR, RSI, RVOL; `regime_map`; `rs_ranks`), `trader-flows/flows.py` (delivery %), `research/round8.py` (OI and basis features),
`trader-flows/angel_recorder.py` (Angel login, live quote, depth), `trader-budget/costs.py` (all costs), `trader-risk/check.py` (risk
gates, IST time windows), `research/round10_open.py` (1-minute opening data, once fetched).

## 3. Data flow

1. `snapshot.py` builds ONE record for symbol S at time T: every field carries `value`, `source` (Angel live / Kite / Yahoo delayed / NSE
   archive / cache), `as_of` timestamp and `class` = REALTIME | HISTORICAL | UNAVAILABLE. Delivery % and OI are always the previous
   session's (published after the close). Bid/ask depth only from Angel live. A field that cannot be fetched is UNAVAILABLE, never filled.
2. Buyer and Seller each receive a deep copy of the snapshot and run in separate function calls (separate LLM conversations if the LLM
   layer is on). Neither receives the other's output before writing its initial case.
3. Each initial case is a fixed schema: proposed entry, stop, T1, T2, holding period, evidence list (each item: id, observed value,
   threshold, why it matters, historical stat), potential move, reward-to-risk, invalidation conditions, historical confidence (from the
   stats table, never self-assessed).
4. Rebuttal: each side receives the other's case and runs its challenge checks (examples: "your volume is the 09:15 auction print",
   "entry is 2.2 ATR(5m) above VWAP", "support at previous-day low is 0.3 % below your short entry", "this setup's untouched-test
   expectancy is negative"). Each side then answers the two strongest challenges with evidence or concedes them.
5. Judge receives the snapshot, both cases and the full exchange. It recomputes every cited evidence item from the snapshot (an item that
   does not reproduce is struck out), looks up the untouched-test statistics for the proposed setup, applies the risk gate, and decides.
6. Every message is appended to the debate record with its timestamp, the snapshot hash it used and the model/engine version. Records are
   append-only: a reassessment (new data later in the day) adds a new round linked to the original and never edits it.

## 4. Judge decision rule (fixed before validation)

BUY or SELL only if ALL hold, otherwise NO TRADE:
- the setup's untouched-test net expectancy after costs is positive and its 95 % confidence interval excludes zero;
- at least two cited evidence items reproduce and none of the opponent's challenges marked "fatal" stands;
- reward-to-risk to T1 is at least 1.5 after costs, T1 lies inside the day's range or the case says it needs a new high/low;
- the CLAUDE.md card rules hold (not more than 1.5 ATR(5m) beyond VWAP in the trade direction, not already more than 2.5 % moved, hard
  "do not enter past" price, stall exit, time windows 09:30-14:45 intraday, no new cards after 11:00 unless RVOL > 1.0);
- risk gate: size from stop distance; Rs 2,00,000 test capital; per-trade risk and daily loss limit from CLAUDE.md; no second position in
  the same sector or with 60-day return correlation above 0.7; account drawdown stop (proposed: pause at -Rs 10,000 from the peak).
If both sides pass (rare), the side with the larger untouched-test expectancy wins; ties go to NO TRADE.

Known consequence: on current evidence (Rounds 1-9: no setup has positive untouched-test expectancy after costs) the Judge will choose
NO TRADE on almost every debate. That is the correct output until a setup passes, not a bug to tune away.

## 5. Mode rules

| | Intraday | Swing (1-5 days) |
|---|---|---|
| Data | 1-min (opening), 5-min, VWAP, opening range, prev-day H/L, RVOL, breadth, sector, Angel depth when live | daily + weekly structure, EMAs, ATR, RS vs Nifty, delivery %, futures OI and premium |
| SELL means | intraday short (MIS), flat by 15:15; never carried overnight | exit or avoid an existing long only. No overnight cash shorts (would need F&O, which is out of scope) |
| Windows | entries 09:30-14:45 (09:19 earliest in the opening study) | entry near the close or next open |
| Costs | intraday | delivery |

## 6. Stages (each one reviewed before the next)

1. Snapshot builder + evidence catalogue + tests (no agents yet). Output: a snapshot JSON for any symbol, intraday and swing.
2. Buyer and Seller engines + initial cases + tests for independence (neither module imports the other; no shared mutable state).
3. Rebuttal round + Judge + risk gate + tests (failed agent, missing data, timeouts -> NO TRADE; never a default BUY/SELL).
4. Debate record + terminal view (three panels + timeline) + history and reassess commands. (User choice 2026-11-12: terminal only.)
5. Historical validation of the engines (swing on 5y daily; intraday on 15-min now and 1-min after the fetch): Buyer alone, Seller alone,
   simple rule (ORB), best existing strategy (Round 8 delivery + basis basket), and the Judge; win rates before and after costs,
   expectancy, profit factor, drawdown, NO TRADE rate, false entries avoided, by year and regime. Reports in docs/DEBATE_VALIDATION.md.
6. LLM layer (user choice 2026-11-12: engines first, Claude added at this stage) (Claude Opus 5.5 via the official `anthropic` Python SDK, structured outputs, adaptive thinking). Needs an API key;
   rough cost about $0.20-0.30 per stock debate (six calls), so about $4-6 a day for 20 stocks. Logged prompts, inputs, outputs, model id.
7. Forward paper trading: every Judge decision logged and scored; LIVE use only after it beats the comparisons in forward data too.
