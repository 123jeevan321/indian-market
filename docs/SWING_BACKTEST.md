# Swing strategy: findings (2026-11-11)

**Verdict: none of the six coded swing setups has an edge.** Over 5 years of daily NSE data (477 liquid Nifty 500 stocks, Nov 2021 - Nov 2026),
after Zerodha delivery costs, every setup lost money in both the in-sample and the out-of-sample period, and none beat a RANDOM long entry
with the same stops and exits (random: about -Rs 26/trade; setups: -Rs 41 to -Rs 138/trade in Scenario A). The 95 % confidence intervals of the
best two (choch, pullback) include zero, so they are "no better than chance", not "proven losers". Regime filters known in advance do not rescue
them: the only positive cells (sweep and choch in sideways markets, about 100 trades each) have intervals far wider than the effect.

**Your weekly targets vs the data.** With Rs 1,500 risk, Rs 5,000 a week needs about +3.3R net every week. The tested setups average about -0.05R
per trade and reached Rs 5,000 in 0-5 % of weeks. A 5 % gain on Rs 1 lakh from one trade needs a 3.3R winner with a full-capital position, which
the Rs 1,500 cap only allows when the stop is about 1.5 % away - tighter than most daily structure stops. Scenario B's 2.5 % on Rs 2 lakh has the
same problem: sizing comes from the stop, so most of the capital sits idle unless several positions run at once.

**Flaws in the specification (to decide):**
1. Bearish 1-5 day swings are impossible in the cash market (no overnight shorts). The module is long only.
2. 15-minute and 4-hour confirmation cannot be backtested over 3-5 years with free data (Yahoo keeps 60 days of 15m, about 2 years of 1h).
   Multi-timeframe rules here are daily (+ weekly levels); intraday timing stays a manual, untested refinement.
3. Order blocks, "institutional accumulation" and premium/discount zones have no single objective definition. They are represented by
   testable proxies (sweep/reclaim, CHoCH, FVG retrace, compression with relative volume); delivery-% accumulation needs a multi-year bhavcopy
   download (possible, not done yet).
4. A 90 %+ win rate does not appear anywhere in the data; win rates are 37-52 %.

**What would be worth testing next** (each must beat the random baseline out of sample before any live use): a sector/NIFTY relative-strength
ranking (top decile only), delivery-% accumulation from bhavcopy history, results-day exclusion, a 10-day holding window, and exits on a
trailing 10-day low instead of fixed R targets.

Until a setup passes, the trading rule is: swing setups from this scanner are REJECT / paper-trade only.

# Swing backtest (NSE, daily bars, long only, 1-5 days)

Run 2026-11-11. Data: Yahoo daily bars 2021-11-11 to 2026-11-11 for 477 of 496 Nifty 500 symbols (missing or short history: 19). Liquidity filter at signal time: 20-day average traded value >= Rs 25 crore, price >= Rs 100. In-sample (IS) = before 2024-11-11, out-of-sample (OOS) = from 2024-11-11. Costs: Zerodha delivery (STT 0.1% both sides, stamp 0.015% buy, exchange, SEBI, GST, DP Rs 15.34 per sell) + 1 tick slippage each side.

## Scenario A: capital Rs 100,000, risk Rs 1500 per trade, max 3 open positions

| setup | trades | win | avg win / loss Rs | expectancy Rs (95% CI) | avg R | PF | total Rs | max DD Rs | worst losing streak | avg week Rs | Sharpe (weekly) | weeks >=5k / >=10k / <0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| squeeze IS | 250 | 44.8% | 956 / -864 | -48 (-183..+88) | -0.05 | 0.90 | -12065 | 27772 | 9 | -106 | -0.43 | 0% / 0% / 52% |
| squeeze OOS | 214 | 44.4% | 891 / -919 | -116 (-266..+28) | -0.12 | 0.77 | -24801 | 30384 | 6 | -236 | -1.11 | 0% / 0% / 51% |
| **squeeze all** | 464 | 44.6% | 926 / -889 | -79 (-177..+18) | -0.08 | 0.84 | -36866 | 42979 | 9 | -169 | -0.73 | 0% / 0% / 52% |
| sweep IS | 201 | 48.3% | 895 / -1012 | -92 (-250..+62) | -0.07 | 0.82 | -18504 | 31023 | 7 | -164 | -0.66 | 0% / 0% / 42% |
| sweep OOS | 181 | 39.8% | 843 / -743 | -112 (-270..+38) | -0.21 | 0.75 | -20236 | 22188 | 10 | -193 | -0.94 | 0% / 0% / 45% |
| **sweep all** | 382 | 44.2% | 873 / -874 | -101 (-208..+15) | -0.14 | 0.79 | -38740 | 52607 | 10 | -179 | -0.78 | 0% / 0% / 44% |
| choch IS | 254 | 47.2% | 732 / -792 | -72 (-184..+57) | -0.05 | 0.83 | -18304 | 19020 | 7 | -161 | -0.76 | 0% / 0% / 48% |
| choch OOS | 241 | 46.5% | 896 / -793 | -8 (-129..+118) | -0.00 | 0.98 | -1985 | 27782 | 11 | -19 | -0.08 | 0% / 0% / 50% |
| **choch all** | 495 | 46.9% | 811 / -793 | -41 (-129..+51) | -0.03 | 0.90 | -20289 | 27782 | 11 | -93 | -0.41 | 0% / 0% / 50% |
| pullback IS | 284 | 47.2% | 795 / -792 | -43 (-157..+68) | -0.03 | 0.90 | -12278 | 19294 | 13 | -107 | -0.46 | 0% / 0% / 47% |
| pullback OOS | 263 | 46.4% | 901 / -937 | -84 (-281..+83) | -0.06 | 0.83 | -22190 | 31460 | 10 | -213 | -0.59 | 0% / 0% / 52% |
| **pullback all** | 547 | 46.8% | 846 / -862 | -63 (-171..+41) | -0.04 | 0.86 | -34468 | 38616 | 13 | -158 | -0.53 | 0% / 0% / 50% |
| weekhigh IS | 291 | 44.3% | 879 / -863 | -91 (-204..+34) | -0.07 | 0.81 | -26408 | 41179 | 9 | -230 | -0.88 | 0% / 0% / 57% |
| weekhigh OOS | 270 | 37.0% | 742 / -640 | -128 (-236..-24) | -0.19 | 0.68 | -34647 | 46698 | 11 | -330 | -1.65 | 0% / 0% / 65% |
| **weekhigh all** | 561 | 40.8% | 819 / -749 | -109 (-186..-23) | -0.13 | 0.75 | -61055 | 68191 | 11 | -280 | -1.20 | 0% / 0% / 61% |
| fvg IS | 302 | 39.7% | 953 / -914 | -172 (-413..+8) | -0.21 | 0.69 | -51934 | 51934 | 14 | -456 | -1.08 | 0% / 0% / 55% |
| fvg OOS | 258 | 37.6% | 450 / -428 | -98 (-171..-20) | -0.32 | 0.63 | -25314 | 26940 | 7 | -243 | -1.62 | 0% / 0% / 59% |
| **fvg all** | 560 | 38.8% | 728 / -686 | -138 (-266..-27) | -0.26 | 0.67 | -77248 | 78873 | 14 | -354 | -1.10 | 0% / 0% / 57% |
| random IS | 285 | 48.4% | 883 / -832 | -1 (-124..+118) | -0.01 | 1.00 | -384 | 28737 | 7 | -3 | -0.01 | 0% / 0% / 48% |
| random OOS | 265 | 46.8% | 876 / -870 | -53 (-182..+62) | -0.05 | 0.89 | -14019 | 27889 | 13 | -134 | -0.47 | 0% / 0% / 52% |
| **random all** | 550 | 47.6% | 880 / -850 | -26 (-111..+55) | -0.03 | 0.94 | -14403 | 28737 | 13 | -66 | -0.25 | 0% / 0% / 50% |

## Scenario B: capital Rs 200,000, risk Rs 2000 per trade, max 3 open positions

| setup | trades | win | avg win / loss Rs | expectancy Rs (95% CI) | avg R | PF | total Rs | max DD Rs | worst losing streak | avg week Rs | Sharpe (weekly) | weeks >=5k / >=10k / <0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| squeeze IS | 252 | 45.6% | 1364 / -1229 | -46 (-227..+151) | -0.02 | 0.93 | -11512 | 32235 | 9 | -101 | -0.28 | 3% / 0% / 47% |
| squeeze OOS | 218 | 45.0% | 1352 / -1405 | -165 (-362..+46) | -0.10 | 0.79 | -36049 | 43781 | 6 | -343 | -1.06 | 1% / 0% / 50% |
| **squeeze all** | 470 | 45.3% | 1358 / -1311 | -101 (-239..+40) | -0.06 | 0.86 | -47561 | 56829 | 9 | -218 | -0.64 | 2% / 0% / 49% |
| sweep IS | 202 | 48.0% | 1371 / -1494 | -118 (-347..+128) | -0.07 | 0.85 | -23811 | 40214 | 7 | -211 | -0.57 | 2% / 0% / 42% |
| sweep OOS | 186 | 39.2% | 1506 / -1290 | -192 (-419..+33) | -0.14 | 0.75 | -35780 | 37164 | 9 | -341 | -1.03 | 1% / 0% / 47% |
| **sweep all** | 388 | 43.8% | 1429 / -1388 | -154 (-321..+12) | -0.10 | 0.80 | -59591 | 76206 | 9 | -275 | -0.78 | 1% / 0% / 44% |
| choch IS | 254 | 47.6% | 990 / -1072 | -90 (-246..+91) | -0.05 | 0.84 | -22831 | 25115 | 7 | -200 | -0.70 | 1% / 0% / 47% |
| choch OOS | 241 | 46.1% | 1272 / -1078 | +5 (-165..+183) | -0.00 | 1.01 | 1126 | 33777 | 11 | +11 | 0.03 | 5% / 0% / 50% |
| **choch all** | 495 | 46.9% | 1125 / -1075 | -44 (-164..+83) | -0.03 | 0.92 | -21705 | 33777 | 11 | -100 | -0.31 | 3% / 0% / 49% |
| pullback IS | 284 | 46.8% | 1089 / -1082 | -65 (-218..+88) | -0.04 | 0.89 | -18440 | 26314 | 13 | -160 | -0.51 | 0% / 0% / 49% |
| pullback OOS | 263 | 46.8% | 1281 / -1291 | -88 (-347..+137) | -0.04 | 0.87 | -23161 | 35961 | 10 | -223 | -0.46 | 3% / 0% / 51% |
| **pullback all** | 547 | 46.8% | 1181 / -1182 | -76 (-220..+66) | -0.04 | 0.88 | -41602 | 47404 | 13 | -191 | -0.47 | 1% / 0% / 50% |
| weekhigh IS | 291 | 45.7% | 1319 / -1273 | -88 (-273..+88) | -0.05 | 0.87 | -25724 | 50669 | 9 | -224 | -0.57 | 5% / 0% / 54% |
| weekhigh OOS | 273 | 42.1% | 1524 / -1300 | -110 (-321..+88) | -0.06 | 0.85 | -30082 | 61177 | 10 | -286 | -0.70 | 5% / 1% / 55% |
| **weekhigh all** | 564 | 44.0% | 1414 / -1286 | -99 (-222..+38) | -0.05 | 0.86 | -55807 | 79685 | 10 | -256 | -0.64 | 5% / 0% / 55% |
| fvg IS | 303 | 42.2% | 1619 / -1555 | -214 (-521..+49) | -0.10 | 0.76 | -64788 | 64788 | 9 | -568 | -0.90 | 4% / 0% / 52% |
| fvg OOS | 287 | 38.7% | 1305 / -1131 | -189 (-351..-6) | -0.16 | 0.73 | -54198 | 59696 | 8 | -521 | -1.29 | 4% / 0% / 59% |
| **fvg all** | 590 | 40.5% | 1473 / -1342 | -202 (-387..-27) | -0.13 | 0.75 | -118987 | 119923 | 9 | -546 | -1.02 | 4% / 0% / 55% |
| random IS | 286 | 46.9% | 1374 / -1208 | +2 (-184..+179) | -0.00 | 1.00 | 479 | 44191 | 7 | +4 | 0.01 | 1% / 0% / 45% |
| random OOS | 265 | 46.4% | 1323 / -1282 | -73 (-265..+92) | -0.04 | 0.89 | -19261 | 39077 | 13 | -183 | -0.43 | 6% / 0% / 52% |
| **random all** | 551 | 46.6% | 1350 / -1244 | -34 (-165..+84) | -0.02 | 0.95 | -18781 | 44191 | 13 | -86 | -0.22 | 3% / 0% / 48% |

## Scenario A by market regime (NIFTY at the signal date: known in advance, no look-ahead)

| setup | trades | win | avg win / loss Rs | expectancy Rs (95% CI) | avg R | PF | total Rs | max DD Rs | worst losing streak | avg week Rs | Sharpe (weekly) | weeks >=5k / >=10k / <0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| squeeze / bull | 276 | 44.9% | 968 / -860 | -38 (-171..+98) | -0.06 | 0.92 | -10597 | 19362 | 8 | -52 | -0.27 | 0% / 0% / 32% |
| squeeze / sideways | 98 | 43.9% | 851 / -832 | -94 (-291..+92) | -0.08 | 0.80 | -9174 | 12880 | 8 | -43 | -0.45 | 0% / 0% / 12% |
| squeeze / bear | 87 | 44.8% | 896 / -1039 | -171 (-412..+73) | -0.13 | 0.70 | -14896 | 18845 | 6 | -76 | -0.78 | 0% / 0% / 13% |
| sweep / bull | 225 | 43.1% | 839 / -950 | -179 (-328..-51) | -0.18 | 0.67 | -40216 | 43734 | 10 | -198 | -1.09 | 0% / 0% / 31% |
| sweep / sideways | 70 | 50.0% | 782 / -712 | +35 (-198..+285) | -0.01 | 1.10 | 2458 | 9258 | 5 | +12 | 0.14 | 0% / 0% / 9% |
| sweep / bear | 83 | 41.0% | 1103 / -785 | -11 (-258..+236) | -0.14 | 0.98 | -948 | 10153 | 6 | -5 | -0.04 | 0% / 0% / 11% |
| choch / bull | 285 | 45.3% | 793 / -766 | -60 (-183..+47) | -0.04 | 0.86 | -17160 | 25367 | 9 | -85 | -0.48 | 0% / 0% / 33% |
| choch / sideways | 98 | 52.0% | 783 / -770 | +38 (-152..+242) | +0.03 | 1.10 | 3714 | 9335 | 5 | +17 | 0.18 | 0% / 0% / 10% |
| choch / bear | 107 | 44.9% | 928 / -870 | -64 (-278..+156) | -0.04 | 0.87 | -6814 | 23494 | 11 | -34 | -0.28 | 0% / 0% / 14% |
| pullback / bull | 315 | 45.1% | 836 / -790 | -57 (-168..+52) | -0.04 | 0.87 | -17980 | 24594 | 13 | -89 | -0.49 | 0% / 0% / 30% |
| pullback / sideways | 106 | 46.2% | 837 / -731 | -6 (-195..+191) | -0.00 | 0.99 | -624 | 7456 | 8 | -3 | -0.03 | 0% / 0% / 15% |
| pullback / bear | 120 | 50.8% | 908 / -1181 | -119 (-462..+186) | -0.08 | 0.80 | -14268 | 19928 | 10 | -72 | -0.33 | 0% / 0% / 13% |
| weekhigh / bull | 324 | 40.4% | 833 / -814 | -148 (-252..-38) | -0.15 | 0.70 | -47885 | 51645 | 8 | -236 | -1.17 | 0% / 0% / 40% |
| weekhigh / sideways | 111 | 45.9% | 712 / -646 | -22 (-202..+146) | -0.05 | 0.94 | -2477 | 14147 | 8 | -12 | -0.15 | 0% / 0% / 14% |
| weekhigh / bear | 119 | 37.0% | 880 / -639 | -77 (-253..+108) | -0.14 | 0.81 | -9197 | 16579 | 11 | -43 | -0.42 | 0% / 0% / 14% |
| fvg / bull | 330 | 38.2% | 811 / -792 | -180 (-373..-17) | -0.25 | 0.63 | -59419 | 60579 | 9 | -293 | -0.95 | 0% / 0% / 37% |
| fvg / sideways | 109 | 38.5% | 577 / -494 | -81 (-216..+61) | -0.19 | 0.73 | -8823 | 10470 | 12 | -41 | -0.51 | 0% / 0% / 15% |
| fvg / bear | 113 | 40.7% | 612 / -515 | -56 (-203..+109) | -0.34 | 0.82 | -6306 | 12950 | 6 | -32 | -0.34 | 0% / 0% / 15% |
| random / bull | 313 | 46.3% | 867 / -842 | -50 (-166..+69) | -0.04 | 0.89 | -15774 | 19481 | 7 | -78 | -0.39 | 0% / 0% / 32% |
| random / sideways | 110 | 49.1% | 780 / -879 | -65 (-251..+126) | -0.07 | 0.86 | -7101 | 16885 | 7 | -33 | -0.28 | 0% / 0% / 12% |
| random / bear | 118 | 50.0% | 1019 / -829 | +95 (-103..+304) | +0.06 | 1.23 | 11192 | 12292 | 11 | +57 | 0.41 | 0% / 0% / 14% |

## Exit variant check (Scenario A, single 3R target instead of the half-at-1.5R ladder)

| setup | trades | win | avg win / loss Rs | expectancy Rs (95% CI) | avg R | PF | total Rs | max DD Rs | worst losing streak | avg week Rs | Sharpe (weekly) | weeks >=5k / >=10k / <0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| squeeze single-3R | 467 | 44.5% | 943 / -884 | -70 (-173..+40) | -0.07 | 0.86 | -32922 | 40951 | 9 | -151 | -0.62 | 1% / 0% / 54% |
| sweep single-3R | 376 | 44.4% | 923 / -905 | -93 (-205..+23) | -0.09 | 0.81 | -35023 | 52602 | 9 | -161 | -0.68 | 0% / 0% / 45% |
| choch single-3R | 495 | 46.3% | 845 / -797 | -37 (-127..+62) | -0.03 | 0.91 | -18501 | 31331 | 11 | -85 | -0.35 | 1% / 0% / 50% |
| pullback single-3R | 545 | 45.9% | 852 / -853 | -71 (-176..+36) | -0.05 | 0.85 | -38644 | 43092 | 13 | -177 | -0.60 | 0% / 0% / 51% |
| weekhigh single-3R | 558 | 40.9% | 814 / -736 | -103 (-189..-19) | -0.11 | 0.76 | -57444 | 63980 | 10 | -264 | -1.11 | 0% / 0% / 60% |
| fvg single-3R | 562 | 35.4% | 787 / -665 | -151 (-288..-51) | -0.30 | 0.65 | -84882 | 84882 | 13 | -389 | -1.20 | 0% / 0% / 59% |

Limits: survivorship bias (today's index members); Yahoo daily bars (split-adjusted, not dividend-adjusted); a bar touching stop and target counts as the stop; signals are ranked by relative volume when more appear than open slots; no news/results filter; the CI assumes independent trades. FAILED/UNTESTED concepts are listed in the strategy document.
