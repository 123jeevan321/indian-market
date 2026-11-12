# Round 11 · Phase 6: common patterns across the movers

## Feature comparison: top gainers before their big day

Values at t-1 unless marked. "-" = no futures contract or not available. Full table for all 40 movers: `research/results/r11_daily.json`
(`pre_gainers`, `pre_losers`).

| feature | HBLENGINE | PPLPHARMA | ENGINERSIN | TARIL | ATHERENERG | ONESOURCE | median top 20 | median all days |
|---|---|---|---|---|---|---|---|---|
| catalyst | not confirmed | results | results | results | results | results | 8 of 12 results | - |
| opening gap (day t) | +0.2 % | +7.7 % | +3.3 % | +9.5 % | -1.0 % | +0.4 % | +0.7 % | 0.0 % |
| 09:15-09:18 move | -0.5 % | +2.0 % | +5.1 % | +2.3 % | +0.1 % | -0.2 % | mixed | - |
| first 3 min volume, % of day | 0.2 % | 3.8 % | 2.7 % | 8.1 % | 0.6 % | 0.0 % | mixed | - |
| 5-day return | see JSON | | | | | | +0.1 % | -0.8 % |
| previous-day volume vs average | | | | | | | 1.10x | 0.83x |
| delivery vs average (points) | | | | | | | +1.7 | -0.7 |
| futures OI, 5 days | | | | | | | -5.1 % | -1.0 % |
| sector-relative 20 days | | | | | | | +0.3 % | 0.0 % |
| volatility ratio | | | | | | | 1.01 | 1.06 |

## How often each pattern appears (frequency vs ordinary days)

| pattern | among top-20 gainers | among all +3 % days | among ordinary days | conclusion |
|---|---|---|---|---|
| company news / results on the day | 8 of 12 checked | not measurable (no filings feed) | rare | the dominant cause |
| gap >= +2 % at the open | 7 of 17 with 1-min data | 23 % of +5 % days | about 3 % | common, but the move is already in the price |
| opening volume >= 2x | about half | 45 % of +5 % days | 12 % | raises odds of a big move either way |
| volatility contraction before the move | rare (median ratio 1.01) | median 1.08 | median 1.06 | not a precursor |
| delivery surge the day before | no (median +1.7 points) | median 0.0 | -0.7 | not a precursor |
| futures long build-up before | no (OI median -5 %) | - | - | lift 0.70 (history): calmer days follow |
| sector leadership before | no (median +0.3 %) | median -0.1 % | 0.0 % | not a precursor |
| strong close the day before | no (median close location 0.38) | 0.50 | 0.48 | slight tilt in history (1.12), too weak |

## Common pattern, stated plainly

The one thing the big movers share is **an event** (results or a major announcement) on or just before the day. The price, volume,
delivery and futures data in the preceding 10 days, 5 days and the previous day looked ordinary. The conditions that DO precede big
days (recent high volume, wide ranges, big recent moves) precede big DOWN days just as often as big up days, so they identify
volatile stocks, not winners.

## Hidden relationships checked

- Combination effects were tested as the pre-registered setups A-F and V in `ROUND11_BACKTEST_RESULTS.md`: combining conditions did
  not create direction.
- Market-wide days dominate the opening results: on 07 Apr 2025, 387 stocks gapped down 3 % or more and recovered about 5.6 % intraday
  on average. Any rule that fires on many stocks on the same day is really one bet on the market, not many independent trades.
