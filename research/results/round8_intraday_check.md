# Intraday re-score of the F&O 36+delivery+OI model

| period | days | universe gross | top-decile gross | LONG net (0.10%) | stress (0.15%) | bottom-decile gross | SHORT net (0.10%) | stress (0.15%) | short t | short win days |
|---|---|---|---|---|---|---|---|---|---|---|
| train | 722 | -0.085% | +0.097% | -0.003% | -0.053% | -0.317% | +0.217% | +0.167% | 4.65 | 56% |
| validation | 247 | -0.047% | +0.058% | -0.042% | -0.092% | -0.162% | +0.062% | +0.012% | 0.89 | 53% |
| seen-once 2025-26 | 247 | -0.037% | +0.022% | -0.078% | -0.128% | -0.145% | +0.045% | -0.005% | 0.76 | 52% |

Largest model weights (ranked features): brk_hi20 -0.0030, sweep_high20 -0.0027, rvol5 -0.0021, deliv_5d +0.0016, clv +0.0016, oi_chg1 -0.0014, long_build +0.0014, deliv_qty_ratio -0.0014, deliv_z +0.0012, oi_chg5 -0.0012
