# Round 11 · Phase 7: stocks with the same conditions that did NOT move

The negative comparison is the conditional rates below: of all stock-days that showed the condition, how many moved, and how many
moved the WRONG way. (Window 13,484 stock-days; history 383,438.)

| early condition | days with it (history) | next day +3 % | next day -3 % | did NOT move 3 % either way |
|---|---|---|---|---|
| previous-day volume > 2x | 33,703 | 11.8 % | 9.1 % | about 79 % |
| delivery % +10 points above average | 55,022 | 7.3 % | 5.1 % | about 88 % |
| futures OI +10 % in 5 days | 27,128 | 6.0 % | 5.5 % | about 89 % |
| new 20-day high at t-1 | 23,297 | 10.0 % | 7.0 % | about 83 % |
| sector up > 2 % in 5 days | 84,376 | 8.6 % | 4.9 % | about 87 % |
| any ordinary day | 383,438 | 7.8 % | 5.8 % | about 86 % |

Percentages = base rate x lift from `ROUND11_PREVIOUS_DAYS_ANALYSIS.md`.

Opening-time failures (window, from 09:30):

| condition at 09:30 | days | continued >= +2 % | reversed <= -2 % | in between |
|---|---|---|---|---|
| volume >= 2x and up >= 1 % (looks like buying) | 569 | 17.2 % | 16.9 % | 65.9 % |
| gap >= +2 % and still rising | 173 | 17.3 % | 19.7 % | 63.0 % |
| volume >= 3x | 910 | 18.6 % | 17.0 % | 64.4 % |
| volume >= 2x, price flat | 194 | 13.9 % | 12.4 % | 73.7 % |

## What separates genuine moves from false signals

From the available data: **nothing measurable before the event.** For every stock that showed heavy volume, a delivery jump or a
breakout the day before and then rallied, there were about as many that showed the same thing and fell, and many more that did nothing.
Examples from the window:
- High volume, no follow-through: of 569 opens with 2x volume and +1 % progress by 09:30, 96 (16.9 %) fell 2 % or more by the close.
- Strong gap that reversed: of 173 gap-ups still rising at 09:30, more reversed by 2 % (19.7 %) than added 2 % (17.3 %).
- Positive news without lasting reaction: HBLENGINE (+17.3 % on 16 Oct) gave back 7.5 % the next week; CHENNPETRO (+14.7 % on 07 Oct)
  fell 5 % the next day; FINCABLES fell 5 % the session after its +20 % results day.
- Repeat "gainers" that lost money over the window: AEGISLOG (8 up days of 3 %+, window return -10.1 %), CARTRADE (7, -12.3 %).

The difference between winners and look-alikes was the content of news that was not yet public, which no chart, volume or delivery
pattern in this data revealed in advance.
