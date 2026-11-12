# Round 11 · Phase 8: candidate setups (pre-registered 12 Nov 2026, before any backtest)

Defined in `research/round11_backtest.py` from the discovery window (Phases 1-7) and the user's hypotheses A-F. Tested only on data
BEFORE the window. Shorts are intraday MIS only.

| id | hypothesis | conditions (all known at decision time) | entry | exits |
|---|---|---|---|---|
| A_quiet_accum_daily | A: quiet accumulation | ATR ratio < 0.8, 10-day return within +/-3 %, delivery 5+ points above average, 5-day volume > 1.1x | buy day t open | close of day t; or +2 % target / -1 % stop |
| A_quiet_then_open | A + opening expansion | as A (delivery above average) then 09:15-09:30 volume >= 2x and price +0.5 % | buy 09:30 | same |
| B_sector_leader | B: sector-leading momentum | beats sector (20d) and NIFTY (60d), sector +2 % in 5 days, stock 5-day return 0-5 % | buy day t open | same |
| C_vol_progress_long | C: opening volume with price progress | 09:15-09:30 volume >= 2x, price +1 %, close above the bar's typical price | buy 09:30 | same |
| C_vol_progress_short | C, bearish mirror | volume >= 2x, price -1 %, close below typical price | short 09:30 | same |
| D_breakout_absorb | D: resistance absorption and breakout | new 20-day closing high at t-1 on 1.5x volume, closed in top 30 % of range | buy day t open | same |
| E_futures_cash | E: futures positioning + cash confirmation | long build-up at t-1, delivery 5+ points above average, close in upper 40 % | buy day t open | same |
| F_gap_up_daily | F: news (proxy) | gap >= +3 % (overnight catalyst proxy) | buy day t open | same |
| F_gap_down_short | F, bearish | gap <= -3 % | short day t open | same |
| F_gap_continue_long | F + technical confirmation | gap >= +2 %, rising through 09:15-09:30 on 2x volume | buy 09:30 | same |
| F_gap_continue_short | F + confirmation, bearish | gap <= -2 %, falling on 2x volume | short 09:30 | same |
| V_volume_spike_long | discovery: volume lifts move size | previous-day volume >= 2x with 5-day return > 0 | buy day t open | same |
| X_absorb_fade | discovery: absorption | 2x opening volume, price flat, after a 5-day rise > 5 % | short 09:30 | same |

Rejection conditions common to all: not tradable (average value < Rs 10 cr, price < Rs 50, < 250 sessions of history).
Maximum holding: same day (intraday). Costs: 0.12 % round trip on every trade.
Hypothesis F uses the gap as a stand-in for news because no historical filings feed is available; a real news-plus-confirmation test
needs exchange announcement timestamps.

Not pre-registered (seen only in the window, kept for a future test): long-lower-wick reversal on heavy opening volume; gap-down still
falling at 09:30 (bounce); first 5 minutes up 1 % and above VWAP.
