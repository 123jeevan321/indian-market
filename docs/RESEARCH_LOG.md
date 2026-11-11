# Research log

## 2026-11-11: round 7 complete (stages 0-3)

- Stage 0: data inventory (docs/INSTITUTIONAL_RESEARCH.md section 2). Local caches (git-ignored): trader/cache/daily5y and trader/cache/m15.
- Stage 1: 100-concept library in research/concepts.py, rendered in docs/INSTITUTIONAL_RESEARCH.md.
- Stage 2: engine research/discovery.py with build, stageA (432 tests), stageB (1,246 combinations), final (pre-registered test).
- Stage 3: the final test failed (docs/FINAL_STRATEGY.md). The Nov 2025 to Nov 2026 window is now USED; new candidates need forward
  paper data or new recordings for their final test.

## Next stages (resume here)

1. Delivery-percent history: 5 years of NSE sec_bhavdata_full files (trader-flows/flows.py fetch_day); add concepts 84-85; rerun stages
   A-B on TRAIN and VALIDATION only.
2. F&O OI history from the NSE F&O bhavcopy archive for concepts 61-67 and 73-74.
3. Order flow: record 10 stocks daily for 4-8 weeks (trader-flows/angel_recorder.py record ...), then test concepts 4-13 with
   angel_recorder.py flow. This is the only route to genuine absorption and aggression evidence.
4. Machine learning (concept 98): pip install scikit-learn; gradient boosting on the stage-A features with the same splits; accept only if it
   beats the rank-average combinations on VALIDATION.
5. Final tests from now on are forward paper-tracking (spec in docs/FINAL_STRATEGY.md).

Resume:
    python research/discovery.py build
    python research/discovery.py stageA
    python research/discovery.py stageB
    python research/write_reports.py

## 2026-11-11: Zerodha Kite MCP assessment (before Round 8)

See docs/ZERODHA_INTEGRATION.md. Verified read-only: quote (5-level depth, VWAP, buy/sell totals, OI), 1-minute history back to 2021,
continuous futures DAILY OI history, option chain. Not available: trade tape, historical depth, streaming. Its live fields matched Angel One
exactly, so the Angel recorder stays the order-flow source; Zerodha adds futures OI history, option chains and cross-checks.
Round 8 starts with step 1 of the plan in that document.

## 2026-11-12: Round 8 complete (delivery % and futures OI)

Data: research/fetch_nse.py downloaded 1,233 delivery days and 1,234 F&O days (trader/cache/nse, git-ignored). Features and tests in
research/round8.py (features, stageA, incremental, stageB, hypothesis, intraday). Report: docs/ROUND8_DELIVERY_OI.md.
Findings: delivery % and futures OI are significant RELATIVE signals (26 Bonferroni passes; OI lifts next-day IC 0.043 -> 0.062), but no
long-only trade beats costs. User hypothesis (delivery > 65 % + long build-up): negative net at 1-5 days, edge gone in 2025-26.
Next: forward paper-track the two candidates in the report; start the Angel recorder for order-flow features; consider a
market-neutral design only if F&O hedging is ever allowed (currently excluded).

## 2026-11-12: Round 9 complete (cross-strategy failure analysis, regimes, selector, 2 % study)

Code: research/round9.py (streams, analyse, select, twopct), research/write_round9_docs.py. Docs: docs/ROUND9_*.md (7 files).
12 strategies from rounds 1-8 rebuilt trade by trade on common dates. Regimes (trend, volatility, breadth, gap) use decision-time data
only. Walk-forward selector: +0.42 % per traded day in its training years, -0.33 % validation, -0.07 % 2025-26 -> rejected.
2 % study: 35-39 % of stock-days touch +-2 %, but a 10:00 entry hits +2 % first on ~10 % of days; all targets negative after costs.
Answer to the Round 9 question: not with the current strategy set. Next: forward data (Angel recorder, Round 8 paper-tracking).
