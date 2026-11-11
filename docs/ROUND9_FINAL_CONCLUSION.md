# Round 9: final conclusion

Round 9, 2026-11-12. All returns are NET percent per trade (delivery 0.25 %, intraday 0.12 % incl. slippage). Periods: train < 2024-11-11 <= validation < 2025-11-11 <= seen-once (used by rounds 7-8, never used for selection here).

## Can we select, for each market condition, the strategy with the strongest independently validated performance?

**Not with the strategies we have.** The data supports half of your hypothesis and rejects the other half.

What holds:
- Market conditions DO change which strategy works: momentum in strong trends, reversal and sweep-reclaim in high volatility and after
  gaps, and the intraday breakout family fails in every condition.

What fails:
1. **The rankings are not stable out of sample.** A walk-forward selector that only used past data earned +0.42 % per traded day in its
   training years, then -0.33 % in validation and -0.07 % in 2025-26.
2. **Strategies lose together.** Median correlation 0.20; on a typical strategy's losing days, the other strategies were positive only
   about a third of the time, because all long cash strategies share the market move.
3. **No component has a durable positive edge after costs.** A selector can only choose among components; it cannot create an edge
   that none of them has. The best component (the Round 8 intraday OI short) decays to break-even after realistic slippage.
4. **The 2 % day is common for stocks (35-39 % of days touch +-2 %) but not capturable**: from a 10:00 entry, the target is hit first on
   about 10 % of days and every target from 0.5 % to 2.5 % loses after costs.

What would have to change for a "yes":
- At least two components with positive out-of-sample net expectancy and low correlation (for example, a genuine short or hedged leg:
  intraday shorts are allowed, F&O hedges are excluded by your rules).
- Order-flow evidence from the Angel recorder (still not collected) as a new, non-price input.
- Forward paper results, because every historical window has now been used for selection at least once.

Recommendation: keep capital out of these rules. Continue the Round 8 paper-tracking separately, start the Angel recorder, and re-run
this Round 9 engine (`python research/round9.py streams && ... select`) when 3-6 months of forward data exist.
