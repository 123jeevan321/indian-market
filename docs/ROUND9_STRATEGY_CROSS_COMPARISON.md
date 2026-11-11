# Round 9: strategies compared on the same dates

Round 9, 2026-11-12. All returns are NET percent per trade (delivery 0.25 %, intraday 0.12 % incl. slippage). Periods: train < 2024-11-11 <= validation < 2025-11-11 <= seen-once (used by rounds 7-8, never used for selection here).

## By NIFTY trend (regime known at the previous close), train + validation, mean net per trade (trades)

| strategy | sideways | strong_bear | strong_bull | weak_bear | weak_bull |
|---|---|---|---|---|---|
| D1_MOM60_10d | +0.69% (7343) | +1.12% (1522) | +1.13% (7077) | -1.27% (1733) | +0.67% (5332) |
| D2_R7CAND_10d | +0.72% (2643) | +1.51% (748) | +1.11% (2287) | +0.70% (612) | +0.56% (1852) |
| D3_R8DELIVBASIS_5d | +0.20% (4967) | +0.34% (1318) | +0.16% (4362) | +0.48% (1266) | -0.17% (3612) |
| D4_REVERSAL_5d | +0.27% (7334) | +0.15% (1648) | +0.06% (6859) | -0.09% (1712) | -0.41% (5346) |
| D5_BREAKOUT_5d | -0.54% (1660) | -2.00% (134) | -0.23% (2487) | -0.50% (251) | -0.67% (1278) |
| D6_SWEEP_5d | +0.63% (1456) | -0.28% (136) | +0.31% (911) | -0.11% (327) | +0.53% (1279) |
| D7_BTST_2d | -0.37% (215) | -0.78% (26) | -0.39% (344) | -1.24% (39) | -0.61% (164) |
| D8_OISHORT_intra | +0.13% (4669) | +0.26% (1241) | +0.20% (4277) | +0.03% (1156) | +0.17% (3450) |
| D9_OILONG_intra | -0.07% (4977) | -0.06% (1324) | +0.03% (4549) | +0.07% (1234) | -0.07% (3677) |
| I1_ORB15L_intra | -0.08% (7791) | -0.12% (2383) | -0.12% (7208) | -0.11% (2559) | -0.10% (5865) |
| I2_ORB15S_intra | -0.05% (9141) | -0.05% (2850) | -0.07% (7885) | -0.09% (2792) | -0.04% (7244) |
| I3_PDLSWEEP_intra | -0.06% (2546) | -0.06% (759) | -0.15% (2303) | -0.10% (864) | -0.12% (2187) |

| condition | best strategy (train+validation) |
|---|---|
| sideways | D2_R7CAND_10d (+0.72%) |
| strong_bear | D2_R7CAND_10d (+1.51%) |
| strong_bull | D1_MOM60_10d (+1.13%) |
| weak_bear | D2_R7CAND_10d (+0.70%) |
| weak_bull | D1_MOM60_10d (+0.67%) |

## By NIFTY volatility (20-day realised vol, terciles fixed on TRAIN)

| strategy | high_vol | low_vol | mid_vol |
|---|---|---|---|
| D1_MOM60_10d | +1.31% (6203) | +0.62% (8589) | +0.33% (8215) |
| D2_R7CAND_10d | +0.78% (2400) | +0.81% (3003) | +1.00% (2739) |
| D3_R8DELIVBASIS_5d | +0.31% (4613) | +0.20% (5557) | -0.08% (5355) |
| D4_REVERSAL_5d | +0.57% (6555) | +0.01% (8313) | -0.43% (8031) |
| D5_BREAKOUT_5d | -0.36% (1570) | -0.37% (2501) | -0.70% (1739) |
| D6_SWEEP_5d | +1.56% (760) | +0.08% (1630) | +0.29% (1719) |
| D7_BTST_2d | -0.13% (168) | -0.57% (385) | -0.62% (235) |
| D8_OISHORT_intra | +0.18% (4419) | +0.19% (5212) | +0.12% (5162) |
| D9_OILONG_intra | +0.00% (4705) | -0.02% (5547) | -0.06% (5509) |
| I1_ORB15L_intra | -0.11% (7895) | -0.10% (8560) | -0.09% (9351) |
| I2_ORB15S_intra | -0.04% (8695) | -0.05% (10209) | -0.08% (11008) |
| I3_PDLSWEEP_intra | -0.11% (2515) | -0.11% (2886) | -0.09% (3258) |

| condition | best strategy (train+validation) |
|---|---|
| high_vol | D6_SWEEP_5d (+1.56%) |
| low_vol | D2_R7CAND_10d (+0.81%) |
| mid_vol | D2_R7CAND_10d (+1.00%) |

## By market breadth (share of liquid stocks above their 50-day EMA)

| strategy | mixed_breadth | strong_breadth | weak_breadth |
|---|---|---|---|
| D1_MOM60_10d | +0.73% (4604) | +0.94% (13777) | -0.03% (4626) |
| D2_R7CAND_10d | +1.00% (1672) | +0.96% (4744) | +0.47% (1726) |
| D3_R8DELIVBASIS_5d | +0.10% (3332) | +0.11% (8808) | +0.26% (3385) |
| D4_REVERSAL_5d | -0.07% (4687) | -0.11% (13487) | +0.46% (4725) |
| D5_BREAKOUT_5d | -0.62% (826) | -0.39% (4616) | -1.09% (368) |
| D6_SWEEP_5d | +0.39% (1110) | +0.14% (1822) | +0.95% (1177) |
| D7_BTST_2d | -0.90% (151) | -0.35% (573) | -0.80% (64) |
| D8_OISHORT_intra | +0.18% (3087) | +0.18% (8525) | +0.09% (3181) |
| D9_OILONG_intra | -0.13% (3292) | -0.00% (9082) | -0.01% (3387) |
| I1_ORB15L_intra | -0.11% (5360) | -0.11% (14259) | -0.06% (5697) |
| I2_ORB15S_intra | +0.06% (6423) | -0.07% (16207) | -0.17% (6752) |
| I3_PDLSWEEP_intra | -0.15% (1819) | -0.12% (4642) | -0.01% (2038) |

| condition | best strategy (train+validation) |
|---|---|
| mixed_breadth | D2_R7CAND_10d (+1.00%) |
| strong_breadth | D2_R7CAND_10d (+0.96%) |
| weak_breadth | D6_SWEEP_5d (+0.95%) |

## By today's NIFTY opening gap (intraday strategies can use it; daily strategies enter at this open)

| strategy | flat_open | gap_down | gap_up |
|---|---|---|---|
| D1_MOM60_10d | +0.48% (18471) | +1.76% (1936) | +1.51% (2600) |
| D2_R7CAND_10d | +0.78% (6397) | +1.03% (753) | +1.31% (992) |
| D3_R8DELIVBASIS_5d | +0.07% (12187) | +0.30% (1405) | +0.44% (1933) |
| D4_REVERSAL_5d | -0.13% (18243) | +0.44% (1949) | +0.66% (2707) |
| D5_BREAKOUT_5d | -0.47% (4806) | +0.13% (321) | -0.71% (683) |
| D6_SWEEP_5d | +0.18% (3394) | +1.09% (225) | +1.93% (490) |
| D7_BTST_2d | -0.50% (649) | -0.65% (55) | -0.26% (84) |
| D8_OISHORT_intra | +0.23% (11592) | -0.17% (1335) | -0.01% (1866) |
| D9_OILONG_intra | -0.08% (12349) | +0.18% (1421) | +0.13% (1991) |
| I1_ORB15L_intra | -0.11% (19512) | -0.10% (2740) | -0.05% (3554) |
| I2_ORB15S_intra | -0.05% (24054) | -0.09% (2132) | -0.11% (3726) |
| I3_PDLSWEEP_intra | -0.12% (6735) | -0.05% (1526) | +0.05% (398) |

| condition | best strategy (train+validation) |
|---|---|
| flat_open | D2_R7CAND_10d (+0.78%) |
| gap_down | D1_MOM60_10d (+1.76%) |
| gap_up | D6_SWEEP_5d (+1.93%) |

## Do strategies make money when others lose? (daily streams, train + validation)

Median correlation between strategy daily returns: 0.20. The median share of days where B was positive when A was negative is only
34 %: **most strategies lose on the same days**, because they are all long cash equities exposed to the same market move. The only strongly
negative correlations are mechanical (the OI model's long and short ends, ORB long vs ORB short).

Pairs where B most often made money on A's losing days:

| A | B | days both negative | B positive when A negative | common days |
|---|---|---|---|---|
| D8_OISHORT_intra | D9_OILONG_intra | 13% | 73% | 1216 |
| D4_REVERSAL_5d | D8_OISHORT_intra | 19% | 63% | 1214 |
| D7_BTST_2d | D8_OISHORT_intra | 22% | 63% | 606 |
| D6_SWEEP_5d | D8_OISHORT_intra | 19% | 62% | 911 |
| D3_R8DELIVBASIS_5d | D8_OISHORT_intra | 18% | 62% | 1210 |
| D5_BREAKOUT_5d | D8_OISHORT_intra | 21% | 61% | 1093 |
| D1_MOM60_10d | D8_OISHORT_intra | 16% | 60% | 1168 |
| D2_R7CAND_10d | D8_OISHORT_intra | 19% | 56% | 1163 |

Full correlation matrix:

| | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | I1 | I2 | I3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1_MOM60_10d | 1.00 | 0.66 | 0.49 | 0.52 | 0.38 | 0.40 | 0.17 | -0.17 | 0.22 | 0.13 | -0.15 | 0.11 |
| D2_R7CAND_10d | 0.66 | 1.00 | 0.51 | 0.47 | 0.26 | 0.37 | 0.16 | -0.14 | 0.21 | 0.14 | -0.14 | 0.11 |
| D3_R8DELIVBASIS_5d | 0.49 | 0.51 | 1.00 | 0.77 | 0.44 | 0.61 | 0.27 | -0.24 | 0.36 | 0.29 | -0.25 | 0.24 |
| D4_REVERSAL_5d | 0.52 | 0.47 | 0.77 | 1.00 | 0.44 | 0.63 | 0.29 | -0.32 | 0.36 | 0.31 | -0.25 | 0.23 |
| D5_BREAKOUT_5d | 0.38 | 0.26 | 0.44 | 0.44 | 1.00 | 0.32 | 0.31 | -0.23 | 0.19 | 0.17 | -0.12 | 0.09 |
| D6_SWEEP_5d | 0.40 | 0.37 | 0.61 | 0.63 | 0.32 | 1.00 | 0.26 | -0.24 | 0.28 | 0.18 | -0.21 | 0.17 |
| D7_BTST_2d | 0.17 | 0.16 | 0.27 | 0.29 | 0.31 | 0.26 | 1.00 | -0.33 | 0.29 | 0.19 | -0.21 | 0.13 |
| D8_OISHORT_intra | -0.17 | -0.14 | -0.24 | -0.32 | -0.23 | -0.24 | -0.33 | 1.00 | -0.68 | -0.55 | 0.58 | -0.44 |
| D9_OILONG_intra | 0.22 | 0.21 | 0.36 | 0.36 | 0.19 | 0.28 | 0.29 | -0.68 | 1.00 | 0.61 | -0.62 | 0.51 |
| I1_ORB15L_intra | 0.13 | 0.14 | 0.29 | 0.31 | 0.17 | 0.18 | 0.19 | -0.55 | 0.61 | 1.00 | -0.55 | 0.59 |
| I2_ORB15S_intra | -0.15 | -0.14 | -0.25 | -0.25 | -0.12 | -0.21 | -0.21 | 0.58 | -0.62 | -0.55 | 1.00 | -0.53 |
| I3_PDLSWEEP_intra | 0.11 | 0.11 | 0.24 | 0.23 | 0.09 | 0.17 | 0.13 | -0.44 | 0.51 | 0.59 | -0.53 | 1.00 |
