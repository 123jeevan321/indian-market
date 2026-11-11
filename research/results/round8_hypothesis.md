# Hypothesis: delivery > 65 % + futures long build-up

| condition | hold | period | events | mean net | t | excess vs F&O universe | t excess | win |
|---|---|---|---|---|---|---|---|---|
| deliv>65 AND long build-up | 1 | train | 1690 | -0.31% | -5.72 | +0.07% | 1.44 | 38% |
| deliv>65 AND long build-up | 1 | validation | 1256 | -0.25% | -3.79 | +0.08% | 0.97 | 39% |
| deliv>65 AND long build-up | 1 | seen-once 2025-26 | 842 | -0.41% | -3.97 | -0.05% | -0.30 | 34% |
| deliv>65 alone | 1 | train | 8389 | -0.27% | -10.50 | +0.08% | 2.62 | 40% |
| deliv>65 alone | 1 | validation | 5704 | -0.24% | -4.71 | +0.08% | 2.78 | 40% |
| deliv>65 alone | 1 | seen-once 2025-26 | 4291 | -0.29% | -4.67 | +0.07% | 2.23 | 38% |
| long build-up alone | 1 | train | 24051 | -0.40% | -11.87 | -0.04% | -4.28 | 37% |
| long build-up alone | 1 | validation | 11718 | -0.37% | -6.31 | -0.01% | -1.23 | 38% |
| long build-up alone | 1 | seen-once 2025-26 | 11089 | -0.36% | -6.72 | -0.04% | -3.16 | 38% |
| deliv>65 AND long build-up AND OI +2% | 1 | train | 784 | -0.28% | -3.73 | +0.07% | 1.15 | 40% |
| deliv>65 AND long build-up AND OI +2% | 1 | validation | 502 | -0.20% | -2.89 | +0.10% | 1.16 | 42% |
| deliv>65 AND long build-up AND OI +2% | 1 | seen-once 2025-26 | 295 | -0.27% | -3.23 | -0.01% | -0.30 | 37% |
| all F&O stock-days (baseline) | 1 | train | 102707 | -0.34% | -10.55 | +0.00% | 2.14 | 39% |
| all F&O stock-days (baseline) | 1 | validation | 47859 | -0.32% | -5.22 | +0.00% | 0.91 | 40% |
| all F&O stock-days (baseline) | 1 | seen-once 2025-26 | 48219 | -0.30% | -5.85 | +0.00% | 0.04 | 40% |
| deliv>65 AND long build-up | 3 | train | 1690 | -0.09% | 0.59 | +0.12% | 1.49 | 47% |
| deliv>65 AND long build-up | 3 | validation | 1256 | -0.09% | 0.98 | +0.16% | 2.47 | 47% |
| deliv>65 AND long build-up | 3 | seen-once 2025-26 | 837 | -0.46% | -2.90 | -0.03% | -1.11 | 39% |
| deliv>65 alone | 3 | train | 8389 | -0.12% | -0.89 | +0.09% | 2.02 | 47% |
| deliv>65 alone | 3 | validation | 5704 | -0.07% | -0.70 | +0.13% | 2.34 | 47% |
| deliv>65 alone | 3 | seen-once 2025-26 | 4280 | -0.25% | -0.73 | +0.12% | 1.38 | 43% |
| long build-up alone | 3 | train | 24051 | -0.29% | -3.02 | -0.05% | -1.88 | 45% |
| long build-up alone | 3 | validation | 11718 | -0.30% | -1.91 | -0.04% | -1.35 | 44% |
| long build-up alone | 3 | seen-once 2025-26 | 10959 | -0.40% | -0.95 | -0.04% | -0.02 | 41% |
| deliv>65 AND long build-up AND OI +2% | 3 | train | 784 | +0.01% | -0.74 | +0.11% | 0.33 | 49% |
| deliv>65 AND long build-up AND OI +2% | 3 | validation | 502 | -0.08% | 0.41 | +0.11% | 1.97 | 49% |
| deliv>65 AND long build-up AND OI +2% | 3 | seen-once 2025-26 | 294 | -0.30% | -0.67 | -0.04% | 1.04 | 41% |
| all F&O stock-days (baseline) | 3 | train | 102707 | -0.21% | -1.83 | -0.00% | -0.99 | 47% |
| all F&O stock-days (baseline) | 3 | validation | 47859 | -0.25% | -1.03 | +0.00% | 0.62 | 45% |
| all F&O stock-days (baseline) | 3 | seen-once 2025-26 | 47820 | -0.26% | -0.85 | +0.00% | 0.47 | 44% |
| deliv>65 AND long build-up | 5 | train | 1690 | +0.02% | -0.69 | +0.07% | -0.12 | 50% |
| deliv>65 AND long build-up | 5 | validation | 1256 | +0.05% | 0.19 | +0.19% | 0.66 | 49% |
| deliv>65 AND long build-up | 5 | seen-once 2025-26 | 832 | -0.52% | -0.74 | +0.00% | -0.54 | 41% |
| deliv>65 alone | 5 | train | 8389 | +0.04% | 0.84 | +0.10% | 2.02 | 50% |
| deliv>65 alone | 5 | validation | 5704 | +0.02% | -0.73 | +0.15% | 0.07 | 49% |
| deliv>65 alone | 5 | seen-once 2025-26 | 4261 | -0.36% | -0.39 | +0.15% | 0.64 | 43% |
| long build-up alone | 5 | train | 24051 | -0.16% | -1.86 | -0.06% | -2.17 | 48% |
| long build-up alone | 5 | validation | 11718 | -0.29% | -1.16 | -0.04% | -1.41 | 46% |
| long build-up alone | 5 | seen-once 2025-26 | 10836 | -0.43% | -0.02 | -0.04% | 1.56 | 42% |
| deliv>65 AND long build-up AND OI +2% | 5 | train | 784 | +0.22% | -0.73 | +0.10% | -0.52 | 52% |
| deliv>65 AND long build-up AND OI +2% | 5 | validation | 502 | +0.12% | -1.43 | +0.20% | -1.10 | 51% |
| deliv>65 AND long build-up AND OI +2% | 5 | seen-once 2025-26 | 293 | -0.24% | -1.79 | +0.08% | -0.81 | 42% |
| all F&O stock-days (baseline) | 5 | train | 102707 | -0.08% | -0.34 | +0.00% | -0.06 | 49% |
| all F&O stock-days (baseline) | 5 | validation | 47859 | -0.17% | -0.67 | +0.00% | 0.15 | 47% |
| all F&O stock-days (baseline) | 5 | seen-once 2025-26 | 47423 | -0.25% | -0.82 | -0.00% | -0.68 | 44% |
| deliv>65 AND long build-up | 10 | train | 1690 | +0.54% | 0.77 | +0.18% | 1.25 | 54% |
| deliv>65 AND long build-up | 10 | validation | 1256 | +0.19% | 0.98 | +0.33% | 1.42 | 50% |
| deliv>65 AND long build-up | 10 | seen-once 2025-26 | 825 | -0.77% | 0.34 | +0.01% | 0.02 | 40% |
| deliv>65 alone | 10 | train | 8389 | +0.48% | 1.41 | +0.12% | 1.48 | 54% |
| deliv>65 alone | 10 | validation | 5704 | +0.16% | 0.21 | +0.22% | 0.52 | 50% |
| deliv>65 alone | 10 | seen-once 2025-26 | 4213 | -0.70% | -0.82 | +0.14% | -0.29 | 42% |
| long build-up alone | 10 | train | 24051 | +0.20% | -0.50 | -0.04% | -1.91 | 51% |
| long build-up alone | 10 | validation | 11718 | -0.23% | -0.87 | +0.02% | -0.81 | 48% |
| long build-up alone | 10 | seen-once 2025-26 | 10632 | -0.47% | -0.67 | -0.01% | 0.85 | 43% |
| deliv>65 AND long build-up AND OI +2% | 10 | train | 784 | +0.80% | 0.73 | +0.24% | 0.20 | 54% |
| deliv>65 AND long build-up AND OI +2% | 10 | validation | 502 | +0.39% | 0.13 | +0.46% | 0.48 | 54% |
| deliv>65 AND long build-up AND OI +2% | 10 | seen-once 2025-26 | 290 | -0.55% | -1.05 | +0.04% | -0.15 | 42% |
| all F&O stock-days (baseline) | 10 | train | 102707 | +0.28% | 0.88 | +0.00% | 0.34 | 52% |
| all F&O stock-days (baseline) | 10 | validation | 47859 | -0.03% | -0.34 | +0.00% | 1.65 | 49% |
| all F&O stock-days (baseline) | 10 | seen-once 2025-26 | 46428 | -0.32% | -1.11 | -0.00% | -0.38 | 44% |
