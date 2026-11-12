#!/usr/bin/env python3
"""Strict Priority-Based Scanner for Approved Top 10 Strategies.
Enforces the user's sequential priority cascade across the ~500 NSE universe.
1. Strategy #1 (Gap-up >=2% rising at 09:30 on volume) -> if hits, STOP.
2. Strategy #2 (Heavy volume fall in first 15m) -> if hits, STOP.
3. Strategy #3 (Absorption after rally) -> if hits, STOP.
...
10. Strategy #10 (Sector-leader momentum) -> if hits, STOP.
If none qualify -> NO TRADE.
"""
import os
import sys
import json
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import snapshot as S

APPROVED_STRATEGIES = [
    {
        "priority": 1,
        "name": "Gap-up >=2% still rising at 09:30 on high volume",
        "type": "Intraday",
        "win_rate": "61.3%",
        "tested_expectancy": "+0.29% (n=119, unproven)",
        "verdict": "Unproven / small sample"
    },
    {
        "priority": 2,
        "name": "Heavy-volume fall in first 15 minutes -> Short",
        "type": "Intraday",
        "win_rate": "52.0%",
        "tested_expectancy": "+0.06% (breakeven)",
        "verdict": "Breakeven"
    },
    {
        "priority": 3,
        "name": "Absorption: Heavy volume, flat price after rally -> Short",
        "type": "Intraday",
        "win_rate": "51.2%",
        "tested_expectancy": "-0.32% (-Rs 320/trade)",
        "verdict": "Negative net expectancy"
    },
    {
        "priority": 4,
        "name": "Heavy-volume rise in first 15 minutes -> Buy",
        "type": "Intraday",
        "win_rate": "47.7%",
        "tested_expectancy": "-0.04% (zero edge)",
        "verdict": "Negative net expectancy"
    },
    {
        "priority": 5,
        "name": "20-day breakout",
        "type": "Swing",
        "win_rate": "46.9%",
        "tested_expectancy": "-Rs 39/trade",
        "verdict": "Negative net expectancy"
    },
    {
        "priority": 6,
        "name": "CHoCH (Change of Character / Trend Change)",
        "type": "Swing",
        "win_rate": "46.5%",
        "tested_expectancy": "-Rs 8/trade",
        "verdict": "Closest to breakeven swing"
    },
    {
        "priority": 7,
        "name": "Pullback in an established uptrend",
        "type": "Swing",
        "win_rate": "46.4%",
        "tested_expectancy": "-Rs 84/trade",
        "verdict": "Negative net expectancy"
    },
    {
        "priority": 8,
        "name": "Gap-down still falling on volume -> Short",
        "type": "Intraday",
        "win_rate": "45.3%",
        "tested_expectancy": "-0.19%",
        "verdict": "Negative net expectancy"
    },
    {
        "priority": 9,
        "name": "Squeeze (Tight-range breakout)",
        "type": "Swing",
        "win_rate": "44.4%",
        "tested_expectancy": "-Rs 116/trade",
        "verdict": "Negative net expectancy"
    },
    {
        "priority": 10,
        "name": "Sector-leader momentum",
        "type": "Next Day",
        "win_rate": "43.6%",
        "tested_expectancy": "-0.16% (-Rs 157/trade)",
        "verdict": "Negative in all tested years"
    }
]

def load_universe():
    path = os.path.join(ROOT, "trader", "universe.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return []

def format_scan_table(results):
    if not results:
        return "### Final Result: 🟡 NO TRADE (No stocks satisfied any of the 10 approved strategies)"
    
    lines = [
        "| Rank | Stock | Strategy No. | Strategy Name | Entry | Stop Loss | Target | Risk:Reward | Setup Status |",
        "|---|---|---|---|---|---|---|---|---|"
    ]
    for r in results:
        lines.append(
            f"| {r['rank']} | **{r['symbol']}** | #{r['strat_no']} | {r['strat_name']} | ₹{r['entry']:.2f} | ₹{r['sl']:.2f} | ₹{r['target']:.2f} | {r['rr']} | {r['status']} |"
        )
    return "\n".join(lines)

if __name__ == "__main__":
    print(f"Top 10 Strategy Priority Scanner Loaded. {len(APPROVED_STRATEGIES)} strategies registered.")
    universe = load_universe()
    print(f"Active Universe: {len(universe)} NSE cash equities.")
