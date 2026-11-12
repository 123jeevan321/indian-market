# Round 11: final conclusion (12 Nov 2026)

## The question

"Which stocks are showing the same conditions that appeared BEFORE previous 3-5 % moves?"

## The answer from the data

**Big moves have a common cause, but it is not visible in market data beforehand.** In the 30-session window, 8 of the 12 largest moves
that could be checked followed quarterly results, 1 a major company announcement and 2 sector or commodity news (`ROUND11_NEWS_AND_CATALYSTS.md`).
In the days before, these stocks looked like every other stock: no volume build-up, no compression, no delivery surge, no futures
positioning, no sector leadership (`ROUND11_PREVIOUS_DAYS_ANALYSIS.md`).

**What the data can predict is size, not direction.** High recent volume, wide ranges and large recent moves raise the odds of a 3 %
move by 25-70 %, almost equally up and down (383,438 stock-days). High opening volume does the same for the rest of the day.

**Nothing tested made money after costs.** 13 pre-registered setups covering hypotheses A-F were tested on 4 years of data that played
no part in designing them. Every daily setup lost money in TRAIN, VALIDATION and TEST and in every year; the opening setups were near
zero with ranges spanning both signs (`ROUND11_BACKTEST_RESULTS.md`).

## Phase 10: the scanner

The brief said to build the discovery scanner only if a repeatable edge was found. None was, so no BUY/SELL scanner was built and the
debate system's `stats.json` gets no new validated setups. Building one anyway would rank stocks on conditions shown to be coin flips
after costs.

What the research supports instead (not built; a possible next step):
- A **volatility watchlist**: stocks most likely to move 3 % either way today (recent volume, ranges, a results date). This is
  useful for deciding WHERE to watch, not WHAT to buy, and fits the debate system as context, not as a signal.
- A **results calendar** (board-meeting dates are filed in advance). It flags event risk on positions already held, e.g. avoid holding
  an intraday or swing position into a results announcement by accident.

## Limitations

- Window of 30 sessions in a results season; one market regime.
- Survivorship: current Nifty 500 members only.
- News checked for 12 moves by web search (no exchange filings feed; NSE and BSE APIs refuse automated access); times are approximate.
- No historical tick or order-book data; one recorded session illustrates order flow.
- 1-minute data limited to about 20 sessions per Angel request; five early-window movers lack it.
- Special sessions (Muhurat) are missing from daily data.
- Signals that fire on many stocks the same day are correlated; confidence ranges treat trades as independent and are too narrow on
  market-wide days.

## Not tested, for a future pre-registered round

1. Gap-down still falling at 09:30 (window: +0.56 % bounce) and long lower wick on heavy opening volume (+0.17 %).
2. F_gap_continue_long on more data (TEST +0.29 %, n 119, inconclusive).
3. Results-day trading with real announcement timestamps: enter only after the filing, on confirmation. Needs a filings feed.
