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
