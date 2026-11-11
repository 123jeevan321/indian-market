# Institutional footprint research (NSE) — 2026-11-11

## 1. How large participants trade, and what retail data can see

These are well-documented mechanics from market-microstructure research and exchange practice, not secret desk methods.

- **Mutual funds, insurers, pension money (DII) and long-only FIIs** trade large parent orders over hours or days to limit market impact
  (the square-root impact law; Almgren-Chriss style optimal execution). They benchmark to **VWAP**, **TWAP**, arrival price, or the
  **closing price** (index funds and rebalancing trade near the close; NSE's closing price is the volume-weighted average of the last
  30 minutes, not an auction). Footprints that survive in public data: abnormal **volume concentration late in the day**, unusual **volume
  with small price change** (passive absorption), and higher **delivery %** (positions taken home).
- **Hedge funds and quant desks** run cross-sectional momentum, short-term reversal, statistical arbitrage and event strategies with short
  legs, futures and low costs; most need shorting, F&O, or sub-millisecond infrastructure.
- **Proprietary/HFT desks and market makers** earn the spread and short-horizon order-flow imbalance with co-location and order-level data.
  A retail account with snapshot data and 0.1 %+ costs cannot compete there.
- **FII/DII category flows** are published daily for the whole market (provisional, after the close); they are not per-stock signals.
- **Bulk/block deals** are disclosed after the trade; many are arbitrage or transfers.
- **Derivatives positioning** (futures OI, options OI) shows where leveraged participants add or remove risk; history is in NSE's F&O
  bhavcopy archive (not downloaded yet).
- **Opening auction** (NSE pre-open 9:00-9:08) order imbalance is visible live on the NSE site but not archived for retail history.

What retail data CANNOT reveal: who traded (no client IDs), cancelled orders, hidden quantity, the full trade tape. Angel One's SnapQuote
gives last trade, day volume, total buy/sell quantity and best-5 depth as **snapshots**; trade direction must be **estimated**.

## 2. Data actually available to this project

| dataset | coverage | what it contains | what it does NOT contain |
|---|---|---|---|
| Daily OHLCV (Yahoo) | 495 Nifty 500 stocks, Nov 2021-Nov 2026 | open, high, low, close, volume | intraday path, trade side |
| 15-minute OHLCV (Angel One) | 99 Nifty 100 stocks, 5 years | intraday bars, volume | trade side, depth, ticks |
| Angel recorder (SnapQuote) | forward only, from first recording | LTP, last qty, day volume, total buy/sell qty, best-5 bids/asks, exchange time | every trade, order IDs, cancellations |
| NSE bhavcopy with delivery | public, downloadable for 5 years | delivery qty and %, trades | intraday timing |
| NSE F&O bhavcopy | public, downloadable | futures/options OI, prices | intraday OI |

## 3. The 100-concept library and status

Data codes: D daily, M 15-minute, B bhavcopy/deals, T recorder ticks, F F&O history, X not available. Test results are TRAIN-period
statistics (first 60 % of dates, top-decile portfolio, net of costs); none passed the Bonferroni threshold (|t| > 3.48 for 432 tests).

| # | cat | concept | measures | why an institution might create it | data | programmatic proxy | limitation | status / result |
|---|---|---|---|---|---|---|---|---|
| 1 | A | VWAP deviation / reclaim | distance of price from session VWAP; recrossing it | VWAP-benchmarked execution keeps price near VWAP; a reclaim may mean buyers absorbed supply | M | close vs cumulative typical-price*vol / vol | 15m VWAP approximates tick VWAP | TESTED stage A (intraday5, close_vs_vwap); best: + close_vs_vwap h=20, +2.62%/trade, t=2.48 (excess t=1.76) |
| 2 | A | TWAP execution pattern | unusually even volume across the day | time-sliced parent orders spread volume evenly | M | low dispersion of 15m volume shares vs stock's norm | even volume is also the market's normal U-shape residual | TESTED stage A (lasthour_share_z); best: + lasthour_share_z h=20, +1.87%/trade, t=2.18 (excess t=0.91) |
| 3 | A | Volume-weighted absorption | high volume with small price change | a large passive buyer/seller absorbs the other side | M,D | volume z-score high, |return|/ATR low | ambiguous direction without trade side | TESTED stage A (absorb); best: - absorb h=20, +1.93%/trade, t=2.14 (excess t=1.30) |
| 4 | A | Bid-ask imbalance | best bid qty vs best ask qty | large resting interest on one side | T | (bid1q-ask1q)/(bid1q+ask1q) | resting orders can be cancelled; spoofing | NEEDS recorder data (Angel SnapQuote, forward only) |
| 5 | A | Order-book imbalance (5 levels) | depth-weighted imbalance | parent order working passively | T | sum best-5 bid qty vs ask qty | snapshots only, forward data only | NEEDS recorder data (Angel SnapQuote, forward only) |
| 6 | A | Market depth imbalance (total) | total buy qty vs total sell qty in the book | large passive interest | T | tbq/(tbq+tsq) | includes far-from-market orders | NEEDS recorder data (Angel SnapQuote, forward only) |
| 7 | A | Aggressive buyer/seller detection | trades at ask vs at bid | urgent institutional demand crosses the spread | T | quote rule on consecutive snapshots | snapshots miss trades between ticks | NEEDS recorder data (Angel SnapQuote, forward only) |
| 8 | A | Delta divergence | price makes new high while cumulative delta does not | buying exhaustion / hidden selling | T | price HH with CVD LH | estimated delta | NEEDS recorder data (Angel SnapQuote, forward only) |
| 9 | A | Cumulative volume delta | running buy minus sell volume | persistent one-sided aggression | T | sum of signed volume | estimated delta | TESTED stage A (updown_vol); best: + updown_vol h=20, +1.64%/trade, t=2.16 (excess t=0.62) |
| 10 | A | Trade initiation imbalance | share of buyer-initiated volume | informed traders demand liquidity | T | signed volume / volume | estimated sign | NEEDS recorder data (Angel SnapQuote, forward only) |
| 11 | A | Large-trade detection | prints much larger than typical | block-sized child orders | T | last traded qty > 20x median | snapshot LTQ is the last trade only | NEEDS recorder data (Angel SnapQuote, forward only) |
| 12 | A | Iceberg indication | repeated refills at one price | hidden quantity shown in slices | T | same best price, qty replenished after trades | needs many snapshots; not proof | NEEDS recorder data (Angel SnapQuote, forward only) |
| 13 | A | Hidden liquidity | traded volume at a price > displayed depth | non-displayed or refilled orders | T | volume at price vs visible qty | very noisy with snapshots | NEEDS recorder data (Angel SnapQuote, forward only) |
| 14 | A | Absorption at key levels | absorption (3) located at PDL/PDH/round levels | defence of a level by a large participant | M,D | absorption flag within 0.3% of PDL/PDH | level choice is arbitrary | proxy covered by related features / regime variable |
| 15 | A | Failed auction | a move outside value that reverses quickly | no follow-through = no institutional acceptance | M | break of prior VA/high then close back inside within 2 bars | definitions vary | proxy covered by related features / regime variable |
| 16 | A | Opening auction imbalance | pre-open buy/sell imbalance | large market-on-open interest | X | NSE pre-open order book (website only, not archived) | no history available | NOT OBSERVABLE with retail data |
| 17 | A | Closing auction / closing price activity | volume concentration in the final 30 min | funds rebalance near the close (closing price benchmark) | M | last-hour volume share vs norm | NSE close is a 30-min VWAP, not an auction | TESTED stage A (overnight5, lasthour_share_z, lasthour_ret); best: - lasthour_ret h=20, +2.42%/trade, t=2.92 (excess t=1.49) |
| 18 | A | Inventory imbalance | market-maker inventory pressure | dealers lean prices to unload inventory | X | needs dealer positions | not observable | NOT OBSERVABLE with retail data |
| 19 | A | Volume-at-price concentration | volume clustered in a narrow band | accumulation in a range | M | share of 5-day volume within +-0.5% of POC | approximate profile | proxy covered by related features / regime variable |
| 20 | A | POC migration | point of control moving up/down over days | value accepted higher/lower | M | slope of daily POC over 5 days | approximate profile | proxy covered by related features / regime variable |
| 21 | B | Buy-side liquidity sweep | run above prior highs then reversal | stops above highs supply liquidity to sellers | M,D | high > prior N-day high, close < it | common in noise | TESTED stage A (sweep_high20); best: + sweep_high20 h=20, +1.42%/trade, t=1.59 (excess t=0.11) |
| 22 | B | Sell-side liquidity sweep | run below prior lows then reversal | stops below lows supply liquidity to buyers | M,D | low < prior N-day low, close > it | tested in rounds 2 and 6: no edge | TESTED stage A (sweep_low20); best: + sweep_low20 h=20, +1.28%/trade, t=1.41 (excess t=-0.34) |
| 23 | B | Equal highs / lows | two touches of the same level | resting stops cluster there | D | two highs within 0.2% in 20 days | subjective tolerance | proxy covered by related features / regime variable |
| 24 | B | Previous-day high/low reaction | behaviour at PDH/PDL | stops and limit orders cluster at known levels | M | first touch of PDH/PDL and the next-hour return | tested partly in round 6 | TESTED in earlier rounds: tested partly in round 6 |
| 25 | B | Previous-week high/low reaction | behaviour at weekly levels | swing traders' reference levels | D | close above prior week high | round 2: no edge | TESTED in earlier rounds: round 2: no edge |
| 26 | B | Opening-range liquidity | breaks of the first 15/30 minutes | overnight orders resolve at the open | M | close beyond OR | rounds 1 and 6: no edge | TESTED in earlier rounds: rounds 1 and 6: no edge |
| 27 | B | Stop-run reversal | sweep (21/22) + strong reversal bar | stops triggered then large buyer steps in | M | sweep then displacement | round 6: no edge | TESTED in earlier rounds: round 6: no edge |
| 28 | B | Breakout acceptance | price holds above a broken level for N bars | acceptance = participants agree on higher value | M,D | N closes above level | lagging | TESTED stage A (brk_hi20); best: - brk_hi20 h=20, +1.33%/trade, t=1.60 (excess t=-0.18) |
| 29 | B | Breakout rejection | price falls back below a broken level | trapped buyers | M,D | close back below within N bars | short side limited in cash | proxy covered by related features / regime variable |
| 30 | B | Failed breakdown | break below support then reclaim | sellers trapped, short covering | M,D | close below level then reclaim within 2 bars | same as 22 in practice | TESTED stage A (sweep_low20); best: + sweep_low20 h=20, +1.28%/trade, t=1.41 (excess t=-0.34) |
| 31 | B | Market structure shift | swing sequence turns | trend change | D | fractal swing highs/lows | lagging | proxy covered by related features / regime variable |
| 32 | B | Break of structure | close beyond last swing | trend continuation | D | close > last confirmed swing high | round 2 | TESTED in earlier rounds: round 2 |
| 33 | B | Change of character | first BOS against trend | reversal | D | round 2 'choch' setup | round 2: no edge | TESTED in earlier rounds: round 2: no edge |
| 34 | B | Displacement candle | large-bodied range expansion | urgent order flow | M,D | body > 1.5 ATR, close in extreme 20% | also news | TESTED stage A (clv); best: + clv h=20, +0.99%/trade, t=1.33 (excess t=-0.96) |
| 35 | B | Fair value gap | 3-bar gap left by displacement | one-sided order flow left no trades | M,D | low[t] > high[t-2] | rounds 2 and 6: no edge | TESTED in earlier rounds: rounds 2 and 6: no edge |
| 36 | B | Order block | last opposite candle before displacement | where the large order started | D | last down bar before a displacement up | no objective definition | proxy covered by related features / regime variable |
| 37 | B | Breaker block | failed order block flipped | trapped participants | D | order block broken then retested | subjective | proxy covered by related features / regime variable |
| 38 | B | Mitigation block | retest of a failed swing origin | institutions exit losing inventory | D | subjective variant of 36/37 | no objective definition | proxy covered by related features / regime variable |
| 39 | B | Liquidity void | low-volume price area | price moves fast through areas with few resting orders | M | price bins with < 20% of mean profile volume | approximate profile | TESTED stage A (amihud); best: + amihud h=20, +2.51%/trade, t=2.43 (excess t=1.88) |
| 40 | B | Premium / discount zone | position within a swing range | buy below the middle of the range | D | (close - swing low)/(swing high - swing low) | equivalent to a stochastic oscillator | TESTED stage A (pos20); best: + pos20 h=20, +1.23%/trade, t=1.46 (excess t=-0.38) |
| 41 | C | Relative volume expansion | volume vs own average | institutions trade more than usual when they act | D,M | vol / 20-day avg | news drives it too | TESTED stage A (rvol); best: - rvol h=20, +2.10%/trade, t=2.23 (excess t=1.42) |
| 42 | C | Relative volume contraction | unusually quiet volume | absence of urgency before expansion | D | vol / avg < 0.6 for N days | noisy | TESTED stage A (rvol5); best: - rvol5 h=20, +1.91%/trade, t=2.32 (excess t=1.46) |
| 43 | C | Volume climax | extreme volume at extended price | capitulation / blow-off | D | vol > 3x avg after 10-day move > 2 ATR | rare events | proxy covered by related features / regime variable |
| 44 | C | Volume absorption (daily) | high volume, small range day | passive large order | D | vol z > 2 and range < 0.7 ATR | direction unknown | TESTED stage A (absorb); best: - absorb h=20, +1.93%/trade, t=2.14 (excess t=1.30) |
| 45 | C | Volume-price divergence | price up on falling volume | weak participation | D | 5-day price change vs volume trend sign | weak evidence in literature | TESTED stage A (updown_vol); best: + updown_vol h=20, +1.64%/trade, t=2.16 (excess t=0.62) |
| 46 | C | Volume profile (session) | volume by price | where value is accepted | M | 15m approximated profile | approximation | proxy covered by related features / regime variable |
| 47 | C | Fixed-range profile | profile of a chosen range | value of a base | M | profile over last base | range choice subjective | proxy covered by related features / regime variable |
| 48 | C | Anchored VWAP | VWAP from an event (earnings, swing low) | cost basis of participants since the event | D,M | VWAP anchored at 20-day low | anchor choice | TESTED stage A (close_vs_vwap); best: + close_vs_vwap h=20, +2.62%/trade, t=2.48 (excess t=1.76) |
| 49 | C | VWAP bands | standard-deviation bands around VWAP | stretched execution | M | z of price vs VWAP | intraday only | proxy covered by related features / regime variable |
| 50 | C | High-volume node reaction | price at a heavy-volume price | support/resistance from inventory | M | distance to 5-day POC | round 6 POC filter: no edge | TESTED in earlier rounds: round 6 POC filter: no edge |
| 51 | C | Low-volume node rejection | price moving through thin areas | few resting orders | M | see 39 | approximate | proxy covered by related features / regime variable |
| 52 | C | ATR compression | volatility contraction | quiet accumulation before expansion | D | ATR5/ATR50 | round 2 squeeze: no edge | TESTED stage A (atr_comp); best: + atr_comp h=20, +2.92%/trade, t=3.28 (excess t=3.37) |
| 53 | C | Volatility expansion | range expansion after compression | start of a move | D | range > 2 ATR after compression | event-driven | TESTED stage A (range_atr); best: - range_atr h=20, +2.22%/trade, t=2.20 (excess t=2.84) |
| 54 | C | Bollinger squeeze | band width percentile | same as 52 | D | BB width 6-month low | duplicate of 52 | TESTED stage A (atr_comp); best: + atr_comp h=20, +2.92%/trade, t=3.28 (excess t=3.37) |
| 55 | C | Range expansion | today's range vs average | urgency | D | range/ATR | duplicate of 34/53 | TESTED stage A (range_atr); best: - range_atr h=20, +2.22%/trade, t=2.20 (excess t=2.84) |
| 56 | C | Intraday volatility regime | realised 15m volatility state | risk appetite of liquidity providers | M | rolling stdev of 15m returns | regime only | TESTED stage A (vol20); best: + vol20 h=20, +2.63%/trade, t=2.08 (excess t=1.69) |
| 57 | C | Opening volatility | first-30-min range vs norm | overnight information arriving | M | OR30 range / avg | regime only | TESTED stage A (firsthour_ret); best: + firsthour_ret h=20, +2.01%/trade, t=2.62 (excess t=0.40) |
| 58 | C | Gap continuation | gap and go | information shock with institutional follow-through | D,M | gap > 1 ATR & first hour in gap direction | testable | TESTED stage A (gap); best: - gap h=20, +2.04%/trade, t=2.25 (excess t=1.63) |
| 59 | C | Gap fill | gap reverts | liquidity-driven open | D,M | gap then close back toward prior close | testable | TESTED stage A (gap); best: - gap h=20, +2.04%/trade, t=2.25 (excess t=1.63) |
| 60 | C | Failed gap continuation | gap reverses through prior close | trapped participants | M | gap up then close < prior close | testable | TESTED stage A (intraday); best: + intraday h=20, +1.52%/trade, t=1.71 (excess t=0.32) |
| 61 | D | Futures basis change | futures - spot spread | leveraged long/short demand | F | near-month futures close - spot | needs F&O history | NEEDS NSE F&O OI history (public archive, not yet downloaded) |
| 62 | D | Futures OI change | open interest change | new positions vs closing | F | dOI/OI | needs F&O history | NEEDS NSE F&O OI history (public archive, not yet downloaded) |
| 63 | D | Price-OI combination | quadrant of price and OI change | who is adding risk | F | sign(dP), sign(dOI) | needs F&O history | NEEDS NSE F&O OI history (public archive, not yet downloaded) |
| 64 | D | Long buildup | price up, OI up | new longs | F | quadrant | needs F&O history | NEEDS NSE F&O OI history (public archive, not yet downloaded) |
| 65 | D | Short buildup | price down, OI up | new shorts | F | quadrant | needs F&O history | NEEDS NSE F&O OI history (public archive, not yet downloaded) |
| 66 | D | Short covering | price up, OI down | shorts exiting | F | quadrant | needs F&O history | NEEDS NSE F&O OI history (public archive, not yet downloaded) |
| 67 | D | Long unwinding | price down, OI down | longs exiting | F | quadrant | needs F&O history | NEEDS NSE F&O OI history (public archive, not yet downloaded) |
| 68 | D | Option-chain positioning | OI by strike | where writers defend | F | max-OI call/put strikes | needs option history | NEEDS NSE F&O OI history (public archive, not yet downloaded) |
| 69 | D | Put-call OI change | PCR change | hedging demand | F | dPCR | needs option history | NEEDS NSE F&O OI history (public archive, not yet downloaded) |
| 70 | D | Strike OI concentration | OI clustered at strikes | pinning | F | OI share top strike | needs option history | NEEDS NSE F&O OI history (public archive, not yet downloaded) |
| 71 | D | Implied volatility change | IV moves | event pricing | F | ATM IV from option prices | needs option history | NEEDS NSE F&O OI history (public archive, not yet downloaded) |
| 72 | D | Gamma exposure proxy | dealer gamma sign | hedging flows amplify/dampen moves | F | needs OI by strike + assumptions | assumption-heavy | NEEDS NSE F&O OI history (public archive, not yet downloaded) |
| 73 | D | Rollover behaviour | roll % near expiry | conviction to carry positions | F | next-month OI / total | needs F&O history | NEEDS NSE F&O OI history (public archive, not yet downloaded) |
| 74 | D | Cash-futures divergence | futures OI up while cash delivery falls | leveraged vs real-money disagreement | F,B | dOI vs delivery % | needs both histories | NEEDS NSE F&O OI history (public archive, not yet downloaded) |
| 75 | D | Index-stock divergence | stock vs NIFTY move | stock-specific demand | D | stock return - beta*NIFTY return | testable | TESTED stage A (resid1); best: - resid1 h=20, +1.99%/trade, t=1.91 (excess t=1.25) |
| 76 | E | Sector rotation | money moving between sectors | allocation shifts by funds | D | industry median 20-day return rank change | testable | TESTED stage A (ind_ret20, ind_ret5); best: + ind_ret5 h=20, +1.57%/trade, t=1.99 (excess t=0.39) |
| 77 | E | RS vs NIFTY | relative strength | persistent buying by trend followers | D | 60-day excess return rank | round 3: filter only | TESTED stage A (rs60); best: + rs60 h=20, +2.82%/trade, t=2.64 (excess t=2.29) |
| 78 | E | RS vs sector | stock vs its industry | stock-specific demand | D | return - industry median | testable | TESTED stage A (rs_ind20); best: + rs_ind20 h=20, +1.99%/trade, t=1.80 (excess t=1.16) |
| 79 | E | Breadth divergence | index vs advance/decline | narrow leadership | D | index 20d return vs % stocks above 50-EMA | regime only | proxy covered by related features / regime variable |
| 80 | E | Advance-decline | daily A/D ratio | broad participation | D | share of universe up | regime only | proxy covered by related features / regime variable |
| 81 | E | FII / DII flows | net cash buying by category | largest marginal buyers/sellers | X | NSE provisional data (daily, website API; history not archived for us) | market-level, not per stock | NOT OBSERVABLE with retail data |
| 82 | E | Bulk deals | > 0.5% of equity traded by one client | large holder entering/exiting | B | archive bulk.csv (current day only); history via NSE site | history hard to obtain; often arbitrage desks | NEEDS NSE bhavcopy/deals history (next stage) |
| 83 | E | Block deals | negotiated window trades | transfers between institutions | B | archive block.csv | often transfers, not directional | NEEDS NSE bhavcopy/deals history (next stage) |
| 84 | E | Delivery % expansion | delivered share of volume vs norm | positions taken home, not day-traded | B | deliv% - 20-day avg deliv% | needs bhavcopy history | NEEDS NSE bhavcopy/deals history (next stage) |
| 85 | E | Delivery volume concentration | delivered qty vs average delivered qty | real-money accumulation | B | deliv qty / 20-day avg | needs bhavcopy history | NEEDS NSE bhavcopy/deals history (next stage) |
| 86 | E | Correlated stock moves | co-movement with peers | sector-wide flows | D | rolling correlation to industry | regime only | proxy covered by related features / regime variable |
| 87 | E | Lead-lag | large caps leading peers | slow diffusion of information | D | lagged return of industry leaders | testable | TESTED stage A (ind_ret5); best: + ind_ret5 h=20, +1.57%/trade, t=1.99 (excess t=0.39) |
| 88 | E | Index constituent momentum | momentum among index members | benchmark-tracking flows | D | 12-1 month return rank | testable | TESTED stage A (mom12_1); best: + mom12_1 h=20, +2.61%/trade, t=1.95 (excess t=1.17) |
| 89 | E | Sector breakout confirmation | industry index at 20-day high | sector-wide demand | D | industry median at 20-day high | testable | TESTED stage A (brk_hi20, ind_ret20); best: - brk_hi20 h=20, +1.33%/trade, t=1.60 (excess t=-0.18) |
| 90 | E | Market regime classification | trend/volatility state | conditioning variable | D | NIFTY vs EMA200, realised vol tercile | regime only | proxy covered by related features / regime variable |
| 91 | F | Time-series momentum | own past return | trend following, slow information diffusion | D | sign of 60/120-day return | testable | TESTED stage A (ret20, ret60, ret120, near_hi250, dist_ema50, dist_ema200); best: + ret120 h=20, +3.32%/trade, t=2.66 (excess t=1.88) |
| 92 | F | Short-term mean reversion | 1-5 day reversal | liquidity provision earns a premium | D | 5-day return rank (lowest = buy) | testable | TESTED stage A (ret1, ret5); best: - ret1 h=20, +1.99%/trade, t=1.91 (excess t=1.25) |
| 93 | F | Change-point detection | structural break in a series | regime change | D | CUSUM on returns | regime only | proxy covered by related features / regime variable |
| 94 | F | Hidden Markov regimes | latent states | risk-on/off | D | 2-state Gaussian HMM on NIFTY returns | regime only, overfit risk | proxy covered by related features / regime variable |
| 95 | F | Cointegration / pairs | spread mean reversion between peers | stat-arb desks | D | Engle-Granger on industry pairs | needs short leg (not in cash overnight) | proxy covered by related features / regime variable |
| 96 | F | Cross-sectional momentum | rank of 6-12 month return | best-documented equity anomaly globally and in India | D | 12-1 month return decile | testable | TESTED stage A (mom12_1); best: + mom12_1 h=20, +2.61%/trade, t=1.95 (excess t=1.17) |
| 97 | F | Volatility-adjusted momentum | momentum / volatility | risk-parity style ranking | D | 120d return / 120d stdev | testable | TESTED stage A (voladj_mom); best: + voladj_mom h=20, +2.84%/trade, t=2.67 (excess t=1.52) |
| 98 | F | ML classification | learned feature mix | captures interactions | D,M | gradient boosting on the feature set | overfit risk; must beat simple ranks OOS | proxy covered by related features / regime variable |
| 99 | F | Event-driven (results) | post-earnings drift | slow reaction to news | B | needs results dates | results calendar history not yet collected | NEEDS NSE bhavcopy/deals history (next stage) |
| 100 | F | Multi-factor conditional model | combination of the above | diversified signal | D,M | rank-sum of selected features | selection bias | proxy covered by related features / regime variable |
