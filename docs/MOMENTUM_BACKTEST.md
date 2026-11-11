# Verdict (2026-11-11): FAILED the go-live gate -> PAPER only

All 24 variants of the 2-Stock Sector-Split Rotation lost money after delivery costs in BOTH periods, and none clearly beat random entries
with the same exits (random OOS: -Rs 112 to -Rs 232 per trade).

- The exact proposal (+1.5-2.0 % day gain, RVOL >= 2, top-20 % close, 1.5 % stop, +3 % target, buy near the close): 45 trades in 5 years
  (about one every 6 weeks, too rare for a weekly goal), win rate 26-27 %, -Rs 331 (IS) and -Rs 717 (OOS) per trade.
- The best variant (+1.5-3.5 % gain, structural stop at the day's low, +3 % target, buy near the close): 330 trades, win 44-48 %,
  -Rs 67 (IS) and -Rs 117 (OOS) per trade, i.e. about the same as random entries.
- A fixed 1.5 % stop did worse than the structural stop in every pairing, and buying near the close beat buying the next open.
- Weeks with >= Rs 5,000 net: 0-6 % of weeks in every variant.

What this means: a strong close on unusual volume, by itself, did not predict the next 1-2 days in liquid NSE stocks over 2021-2026.
Next research ideas (each must pass the same gate): market-regime filter (NIFTY above its 20-day average), news/results catalysts only,
and the Angel One tick recordings (real buy/sell pressure), which the backtests have never had.

# 2-Stock Sector-Split Rotation: backtest (NSE Nifty 200, daily bars, 1-2 days, long only)

Run 2026-11-11. Data: Yahoo daily 2021-11-12 to 2026-11-11, 194 of 200 Nifty 200 symbols. Max loss per leg Rs 1,500 INCLUDING delivery costs and 1 tick slippage each side; leg <= Rs 1 lakh; max 2 legs, different NSE Industry groups. IS = before 2024-11-11, OOS = from 2024-11-11. Survivorship bias: today's members.

| setup | trades | win | avg win / loss Rs | expectancy Rs (95% CI) | avg R | PF | total Rs | max DD Rs | worst losing streak | avg week Rs | Sharpe (weekly) | weeks >=5k / >=10k / <0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| +1.5-2.0% close-entry 1.5%-stop +2.5% | IS | 19 | 26.3% | 1523 / -1084 | -398 (-958..+208) | -0.27 | 0.50 | -7560 | 9238 | 6 | -71 | -0.85 | 0% / 0% / 12% |
| +1.5-2.0% close-entry 1.5%-stop +2.5% | OOS | 26 | 26.9% | 896 / -1354 | -748 (-1179..-277) | -0.50 | 0.24 | -19453 | 19453 | 5 | -201 | -2.16 | 0% / 0% / 18% |
| +1.5-2.0% close-entry 1.5%-stop +3.0% | IS | 19 | 26.3% | 1776 / -1084 | -331 (-932..+345) | -0.22 | 0.59 | -6294 | 8393 | 6 | -59 | -0.66 | 0% / 0% / 12% |
| +1.5-2.0% close-entry 1.5%-stop +3.0% | OOS | 26 | 26.9% | 1011 / -1354 | -717 (-1165..-218) | -0.48 | 0.28 | -18643 | 18643 | 5 | -192 | -2.01 | 0% / 0% / 18% |
| +1.5-2.0% close-entry 1.5%-stop +3.5% | IS | 19 | 26.3% | 1724 / -1084 | -345 (-937..+343) | -0.23 | 0.57 | -6551 | 7913 | 6 | -62 | -0.69 | 0% / 0% / 12% |
| +1.5-2.0% close-entry 1.5%-stop +3.5% | OOS | 26 | 26.9% | 1127 / -1354 | -686 (-1164..-160) | -0.46 | 0.31 | -17834 | 17834 | 5 | -184 | -1.86 | 0% / 0% / 18% |
| +1.5-2.0% close-entry struct-stop +2.5% | IS | 19 | 31.6% | 733 / -881 | -371 (-793..+40) | -0.25 | 0.38 | -7049 | 7592 | 6 | -66 | -1.04 | 0% / 0% / 11% |
| +1.5-2.0% close-entry struct-stop +2.5% | OOS | 26 | 34.6% | 513 / -924 | -426 (-784..-97) | -0.28 | 0.29 | -11086 | 11955 | 4 | -114 | -1.74 | 0% / 0% / 15% |
| +1.5-2.0% close-entry struct-stop +3.0% | IS | 19 | 31.6% | 840 / -881 | -337 (-769..+101) | -0.22 | 0.44 | -6408 | 7115 | 6 | -60 | -0.92 | 0% / 0% / 11% |
| +1.5-2.0% close-entry struct-stop +3.0% | OOS | 26 | 34.6% | 584 / -924 | -402 (-776..-51) | -0.27 | 0.33 | -10441 | 11492 | 4 | -108 | -1.59 | 0% / 0% / 15% |
| +1.5-2.0% close-entry struct-stop +3.5% | IS | 19 | 31.6% | 839 / -881 | -338 (-778..+108) | -0.23 | 0.44 | -6416 | 6838 | 6 | -61 | -0.91 | 0% / 0% / 11% |
| +1.5-2.0% close-entry struct-stop +3.5% | OOS | 26 | 30.8% | 591 / -885 | -431 (-787..-85) | -0.29 | 0.30 | -11197 | 11252 | 4 | -115 | -1.70 | 0% / 0% / 16% |
| +1.5-2.0% open-entry 1.5%-stop +2.5% | IS | 19 | 15.8% | 1924 / -1243 | -743 (-1234..-141) | -0.50 | 0.29 | -14115 | 14115 | 10 | -133 | -1.53 | 0% / 0% / 14% |
| +1.5-2.0% open-entry 1.5%-stop +2.5% | OOS | 26 | 26.9% | 1105 / -1346 | -686 (-1114..-194) | -0.46 | 0.30 | -17835 | 17835 | 4 | -184 | -1.99 | 0% / 0% / 18% |
| +1.5-2.0% open-entry 1.5%-stop +3.0% | IS | 19 | 15.8% | 2221 / -1243 | -696 (-1221..-43) | -0.46 | 0.34 | -13222 | 13222 | 10 | -125 | -1.37 | 0% / 0% / 14% |
| +1.5-2.0% open-entry 1.5%-stop +3.0% | OOS | 26 | 26.9% | 1282 / -1346 | -638 (-1106..-86) | -0.43 | 0.35 | -16597 | 16597 | 4 | -171 | -1.76 | 0% / 0% / 18% |
| +1.5-2.0% open-entry 1.5%-stop +3.5% | IS | 19 | 15.8% | 2364 / -1243 | -673 (-1221..+9) | -0.45 | 0.36 | -12794 | 12794 | 10 | -121 | -1.29 | 0% / 0% / 14% |
| +1.5-2.0% open-entry 1.5%-stop +3.5% | OOS | 26 | 26.9% | 1459 / -1346 | -591 (-1091..+11) | -0.39 | 0.40 | -15359 | 15359 | 4 | -158 | -1.54 | 0% / 0% / 18% |
| +1.5-2.0% open-entry struct-stop +2.5% | IS | 19 | 21.1% | 917 / -840 | -470 (-849..-62) | -0.31 | 0.29 | -8935 | 8956 | 8 | -84 | -1.32 | 0% / 0% / 13% |
| +1.5-2.0% open-entry struct-stop +2.5% | OOS | 24 | 29.2% | 600 / -800 | -391 (-707..-71) | -0.26 | 0.31 | -9391 | 9925 | 4 | -97 | -1.69 | 0% / 0% / 15% |
| +1.5-2.0% open-entry struct-stop +3.0% | IS | 19 | 21.1% | 966 / -840 | -460 (-854..-26) | -0.31 | 0.31 | -8738 | 8738 | 8 | -82 | -1.27 | 0% / 0% / 13% |
| +1.5-2.0% open-entry struct-stop +3.0% | OOS | 24 | 25.0% | 655 / -770 | -414 (-712..-91) | -0.28 | 0.28 | -9932 | 9932 | 6 | -102 | -1.77 | 0% / 0% / 16% |
| +1.5-2.0% open-entry struct-stop +3.5% | IS | 19 | 21.1% | 1019 / -840 | -449 (-854..-5) | -0.30 | 0.32 | -8530 | 8530 | 8 | -80 | -1.23 | 0% / 0% / 13% |
| +1.5-2.0% open-entry struct-stop +3.5% | OOS | 24 | 25.0% | 729 / -770 | -395 (-707..-59) | -0.26 | 0.32 | -9488 | 9488 | 6 | -98 | -1.64 | 0% / 0% / 16% |
| +1.5-3.5% close-entry 1.5%-stop +2.5% | IS | 183 | 42.1% | 1483 / -1302 | -130 (-363..+108) | -0.09 | 0.83 | -23798 | 24922 | 6 | -158 | -0.66 | 1% / 0% / 36% |
| +1.5-3.5% close-entry 1.5%-stop +2.5% | OOS | 159 | 37.7% | 1566 / -1340 | -243 (-491..+16) | -0.16 | 0.71 | -38704 | 44275 | 13 | -372 | -1.34 | 1% / 0% / 45% |
| +1.5-3.5% close-entry 1.5%-stop +3.0% | IS | 181 | 42.5% | 1579 / -1307 | -79 (-331..+141) | -0.05 | 0.89 | -14330 | 16405 | 6 | -95 | -0.39 | 1% / 0% / 36% |
| +1.5-3.5% close-entry 1.5%-stop +3.0% | OOS | 159 | 37.1% | 1713 / -1339 | -206 (-474..+68) | -0.14 | 0.75 | -32818 | 39552 | 13 | -316 | -1.05 | 2% / 0% / 44% |
| +1.5-3.5% close-entry 1.5%-stop +3.5% | IS | 181 | 42.0% | 1646 / -1306 | -66 (-326..+167) | -0.04 | 0.91 | -12006 | 16150 | 6 | -80 | -0.31 | 2% / 0% / 37% |
| +1.5-3.5% close-entry 1.5%-stop +3.5% | OOS | 157 | 35.7% | 1819 / -1334 | -209 (-474..+79) | -0.14 | 0.76 | -32814 | 41468 | 13 | -316 | -1.03 | 4% / 0% / 46% |
| +1.5-3.5% close-entry struct-stop +2.5% | IS | 177 | 48.0% | 676 / -784 | -83 (-212..+53) | -0.06 | 0.80 | -14662 | 17703 | 5 | -97 | -0.71 | 0% / 0% / 36% |
| +1.5-3.5% close-entry struct-stop +2.5% | OOS | 155 | 44.5% | 734 / -832 | -135 (-283..+9) | -0.09 | 0.71 | -20903 | 27989 | 6 | -201 | -1.44 | 0% / 0% / 47% |
| +1.5-3.5% close-entry struct-stop +3.0% | IS | 175 | 48.0% | 705 / -779 | -67 (-207..+73) | -0.04 | 0.83 | -11727 | 15370 | 5 | -78 | -0.56 | 0% / 0% / 37% |
| +1.5-3.5% close-entry struct-stop +3.0% | OOS | 155 | 43.9% | 790 / -826 | -117 (-268..+32) | -0.08 | 0.75 | -18146 | 25754 | 6 | -174 | -1.21 | 0% / 0% / 46% |
| +1.5-3.5% close-entry struct-stop +3.5% | IS | 175 | 47.4% | 725 / -775 | -64 (-203..+84) | -0.04 | 0.84 | -11150 | 15164 | 6 | -74 | -0.52 | 0% / 0% / 38% |
| +1.5-3.5% close-entry struct-stop +3.5% | OOS | 153 | 41.8% | 836 / -824 | -130 (-276..+24) | -0.09 | 0.73 | -19822 | 27430 | 6 | -191 | -1.27 | 0% / 0% / 47% |
| +1.5-3.5% open-entry 1.5%-stop +2.5% | IS | 182 | 35.7% | 1413 / -1317 | -342 (-549..-138) | -0.23 | 0.60 | -62243 | 66601 | 11 | -412 | -1.82 | 0% / 0% / 40% |
| +1.5-3.5% open-entry 1.5%-stop +2.5% | OOS | 159 | 34.6% | 1453 / -1409 | -419 (-650..-165) | -0.28 | 0.55 | -66608 | 67441 | 12 | -647 | -2.61 | 0% / 0% / 50% |
| +1.5-3.5% open-entry 1.5%-stop +3.0% | IS | 182 | 35.2% | 1501 / -1311 | -323 (-530..-99) | -0.22 | 0.62 | -58711 | 60643 | 11 | -389 | -1.67 | 0% / 0% / 40% |
| +1.5-3.5% open-entry 1.5%-stop +3.0% | OOS | 157 | 33.1% | 1556 / -1391 | -415 (-665..-178) | -0.28 | 0.55 | -65214 | 65632 | 12 | -633 | -2.48 | 0% / 0% / 54% |
| +1.5-3.5% open-entry 1.5%-stop +3.5% | IS | 182 | 34.6% | 1571 / -1311 | -313 (-527..-92) | -0.21 | 0.63 | -57019 | 59376 | 11 | -378 | -1.60 | 0% / 0% / 40% |
| +1.5-3.5% open-entry 1.5%-stop +3.5% | OOS | 156 | 32.7% | 1617 / -1398 | -412 (-665..-158) | -0.27 | 0.56 | -64307 | 65145 | 12 | -624 | -2.34 | 0% / 0% / 54% |
| +1.5-3.5% open-entry struct-stop +2.5% | IS | 173 | 40.5% | 608 / -714 | -179 (-301..-57) | -0.12 | 0.58 | -30989 | 35171 | 9 | -205 | -1.63 | 0% / 0% / 41% |
| +1.5-3.5% open-entry struct-stop +2.5% | OOS | 153 | 44.4% | 641 / -882 | -205 (-343..-63) | -0.14 | 0.58 | -31379 | 36240 | 6 | -305 | -2.12 | 0% / 0% / 49% |
| +1.5-3.5% open-entry struct-stop +3.0% | IS | 172 | 39.0% | 636 / -713 | -187 (-305..-64) | -0.12 | 0.57 | -32222 | 35502 | 9 | -213 | -1.69 | 0% / 0% / 42% |
| +1.5-3.5% open-entry struct-stop +3.0% | OOS | 151 | 41.1% | 667 / -856 | -231 (-371..-84) | -0.15 | 0.54 | -34806 | 38126 | 6 | -338 | -2.35 | 0% / 0% / 50% |
| +1.5-3.5% open-entry struct-stop +3.5% | IS | 172 | 38.4% | 677 / -713 | -180 (-296..-51) | -0.12 | 0.59 | -30928 | 34617 | 9 | -205 | -1.59 | 0% / 0% / 42% |
| +1.5-3.5% open-entry struct-stop +3.5% | OOS | 150 | 40.7% | 697 / -842 | -216 (-362..-67) | -0.14 | 0.57 | -32407 | 36288 | 6 | -315 | -2.18 | 0% / 0% / 48% |

## Random baseline (same exits, sizing and costs; 5 seeds; fixed 1.5 % stop, +3 % target, close entry)

| setup | trades | win | avg win / loss Rs | expectancy Rs (95% CI) | avg R | PF | total Rs | max DD Rs | worst losing streak | avg week Rs | Sharpe (weekly) | weeks >=5k / >=10k / <0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| random seed 0 | OOS | 226 | 38.1% | 1660 / -1300 | -173 (-388..+40) | -0.12 | 0.78 | -39211 | 41857 | 13 | -377 | -1.20 | 2% / 0% / 60% |
| random seed 1 | OOS | 233 | 41.2% | 1686 / -1372 | -112 (-340..+101) | -0.07 | 0.86 | -26021 | 39935 | 8 | -248 | -0.66 | 5% / 0% / 55% |
| random seed 2 | OOS | 230 | 40.9% | 1535 / -1312 | -148 (-325..+52) | -0.10 | 0.81 | -34147 | 43915 | 10 | -328 | -0.92 | 4% / 0% / 53% |
| random seed 3 | OOS | 245 | 37.6% | 1753 / -1371 | -198 (-417..+37) | -0.13 | 0.77 | -48459 | 62126 | 18 | -462 | -1.05 | 6% / 0% / 57% |
| random seed 4 | OOS | 232 | 39.2% | 1473 / -1333 | -232 (-425..-25) | -0.15 | 0.71 | -53884 | 55774 | 9 | -513 | -1.48 | 1% / 0% / 58% |

## Ranking by out-of-sample expectancy (Rs per trade)

| variant | OOS exp | IS exp | OOS n | IS n | days both legs stopped |
|---|---|---|---|---|---|
| +1.5-3.5% close-entry struct-stop +3.0% | -117 | -67 | 155 | 175 | 2 |
| +1.5-3.5% close-entry struct-stop +3.5% | -130 | -64 | 153 | 175 | 2 |
| +1.5-3.5% close-entry struct-stop +2.5% | -135 | -83 | 155 | 177 | 3 |
| +1.5-3.5% open-entry struct-stop +2.5% | -205 | -179 | 153 | 173 | 1 |
| +1.5-3.5% close-entry 1.5%-stop +3.0% | -206 | -79 | 159 | 181 | 9 |
| +1.5-3.5% close-entry 1.5%-stop +3.5% | -209 | -66 | 157 | 181 | 9 |
| +1.5-3.5% open-entry struct-stop +3.5% | -216 | -180 | 150 | 172 | 1 |
| +1.5-3.5% open-entry struct-stop +3.0% | -231 | -187 | 151 | 172 | 1 |
| +1.5-3.5% close-entry 1.5%-stop +2.5% | -243 | -130 | 159 | 183 | 10 |
| +1.5-2.0% open-entry struct-stop +2.5% | -391 | -470 | 24 | 19 | 0 |
| +1.5-2.0% open-entry struct-stop +3.5% | -395 | -449 | 24 | 19 | 0 |
| +1.5-2.0% close-entry struct-stop +3.0% | -402 | -337 | 26 | 19 | 0 |
| +1.5-3.5% open-entry 1.5%-stop +3.5% | -412 | -313 | 156 | 182 | 10 |
| +1.5-2.0% open-entry struct-stop +3.0% | -414 | -460 | 24 | 19 | 0 |
| +1.5-3.5% open-entry 1.5%-stop +3.0% | -415 | -323 | 157 | 182 | 9 |
| +1.5-3.5% open-entry 1.5%-stop +2.5% | -419 | -342 | 159 | 182 | 9 |
| +1.5-2.0% close-entry struct-stop +2.5% | -426 | -371 | 26 | 19 | 0 |
| +1.5-2.0% close-entry struct-stop +3.5% | -431 | -338 | 26 | 19 | 0 |
| +1.5-2.0% open-entry 1.5%-stop +3.5% | -591 | -673 | 26 | 19 | 1 |
| +1.5-2.0% open-entry 1.5%-stop +3.0% | -638 | -696 | 26 | 19 | 1 |
| +1.5-2.0% close-entry 1.5%-stop +3.5% | -686 | -345 | 26 | 19 | 2 |
| +1.5-2.0% open-entry 1.5%-stop +2.5% | -686 | -743 | 26 | 19 | 1 |
| +1.5-2.0% close-entry 1.5%-stop +3.0% | -717 | -331 | 26 | 19 | 2 |
| +1.5-2.0% close-entry 1.5%-stop +2.5% | -748 | -398 | 26 | 19 | 2 |

Reading guide: a variant is usable only if BOTH IS and OOS expectancy are positive, the OOS confidence interval is mostly above zero, and it beats the random rows. Picking the best of 24 variants by OOS alone overfits; prefer variants positive in both periods.
