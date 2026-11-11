## How often does a liquid Nifty 100 stock move 2 % in a day? (open-based, all stock-days)

| period | stock-days | high >= open +2 % | low <= open -2 % | either |
|---|---|---|---|---|
| seen-once | 24648 | 17.2% | 18.3% | 34.6% |
| train | 69672 | 19.2% | 21.1% | 38.8% |
| validation | 23724 | 17.7% | 18.7% | 35.5% |

## Can a trade entered at 10:00 capture it? Long at the 10:00 close, stop 1 %, target T, exit 15:15; net of 0.12 %

| entry filter | period | trades | target | hit target first | hit stop first | neither | net expectancy | median MAE |
|---|---|---|---|---|---|---|---|---|
| every stock-day | train | 69672 | 0.5% | 46% | 37% | 17% | -0.300% | -0.73% |
| every stock-day | train | 69672 | 1.0% | 28% | 37% | 34% | -0.216% | -0.73% |
| every stock-day | train | 69672 | 1.5% | 17% | 37% | 46% | -0.176% | -0.73% |
| every stock-day | train | 69672 | 2.0% | 10% | 37% | 53% | -0.159% | -0.73% |
| every stock-day | train | 69672 | 2.5% | 6% | 37% | 57% | -0.149% | -0.73% |
| every stock-day | validation | 23724 | 0.5% | 48% | 34% | 17% | -0.262% | -0.69% |
| every stock-day | validation | 23724 | 1.0% | 28% | 34% | 37% | -0.187% | -0.69% |
| every stock-day | validation | 23724 | 1.5% | 16% | 34% | 50% | -0.156% | -0.69% |
| every stock-day | validation | 23724 | 2.0% | 9% | 34% | 57% | -0.142% | -0.69% |
| every stock-day | validation | 23724 | 2.5% | 5% | 34% | 61% | -0.135% | -0.69% |
| every stock-day | seen-once | 24648 | 0.5% | 50% | 33% | 17% | -0.244% | -0.68% |
| every stock-day | seen-once | 24648 | 1.0% | 29% | 33% | 37% | -0.171% | -0.68% |
| every stock-day | seen-once | 24648 | 1.5% | 16% | 33% | 51% | -0.144% | -0.68% |
| every stock-day | seen-once | 24648 | 2.0% | 9% | 33% | 58% | -0.132% | -0.68% |
| every stock-day | seen-once | 24648 | 2.5% | 5% | 33% | 62% | -0.125% | -0.68% |
| above 30-min range high | train | 6875 | 0.5% | 48% | 39% | 13% | -0.303% | -0.77% |
| above 30-min range high | train | 6875 | 1.0% | 31% | 39% | 30% | -0.205% | -0.77% |
| above 30-min range high | train | 6875 | 1.5% | 19% | 39% | 42% | -0.155% | -0.77% |
| above 30-min range high | train | 6875 | 2.0% | 12% | 39% | 49% | -0.129% | -0.77% |
| above 30-min range high | train | 6875 | 2.5% | 7% | 39% | 54% | -0.120% | -0.77% |
| above 30-min range high | validation | 2312 | 0.5% | 48% | 36% | 16% | -0.279% | -0.71% |
| above 30-min range high | validation | 2312 | 1.0% | 30% | 36% | 34% | -0.193% | -0.71% |
| above 30-min range high | validation | 2312 | 1.5% | 17% | 36% | 46% | -0.149% | -0.71% |
| above 30-min range high | validation | 2312 | 2.0% | 11% | 36% | 53% | -0.122% | -0.71% |
| above 30-min range high | validation | 2312 | 2.5% | 6% | 36% | 58% | -0.109% | -0.71% |
| above 30-min range high | seen-once | 2319 | 0.5% | 50% | 35% | 15% | -0.250% | -0.71% |
| above 30-min range high | seen-once | 2319 | 1.0% | 33% | 35% | 32% | -0.148% | -0.71% |
| above 30-min range high | seen-once | 2319 | 1.5% | 19% | 35% | 47% | -0.112% | -0.71% |
| above 30-min range high | seen-once | 2319 | 2.0% | 11% | 35% | 55% | -0.092% | -0.71% |
| above 30-min range high | seen-once | 2319 | 2.5% | 6% | 35% | 59% | -0.080% | -0.71% |
