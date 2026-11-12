"""Round 11 charts -> docs/img/r11_*.png (from research/results/r11_*.json)."""
import json, os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
IMG = os.path.join(os.path.dirname(HERE), "docs", "img")
os.makedirs(IMG, exist_ok=True)
UP, DN, GREY = "#2a9d8f", "#e76f51", "#8d99ae"
D = json.load(open(os.path.join(RES, "r11_daily.json")))
O = json.load(open(os.path.join(RES, "r11_open.json")))
B = json.load(open(os.path.join(RES, "r11_backtest.json")))


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(IMG, name), dpi=130)
    plt.close(fig)


# 1. how often stocks move 2/3/5/8 % in a day (window)
mc = D["move_counts"]
ks = [2, 3, 5, 8]
fig, ax = plt.subplots(figsize=(7, 3.6))
x = range(len(ks))
ax.bar([i - 0.2 for i in x], [mc["+%d" % k] for k in ks], 0.4, color=UP, label="up")
ax.bar([i + 0.2 for i in x], [mc["-%d" % k] for k in ks], 0.4, color=DN, label="down")
ax.set_xticks(list(x)); ax.set_xticklabels([">= %d%%" % k for k in ks])
ax.set_ylabel("stock-days"); ax.set_title("Daily close-to-close moves, %s to %s (%d stock-days)" % (D["window"][0], D["window"][1], D["stock_days"]))
ax.legend(frameon=False); ax.spines[["top", "right"]].set_visible(False)
save(fig, "r11_move_counts.png")

# 2. lift for up vs down 3% moves (5-year history): magnitude, not direction
lu = {r["feature"]: r for r in D["lift_history"]["up3"]}
ld = {r["feature"]: r for r in D["lift_history"]["dn3"]}
feats = [f for f in lu if lu[f].get("lift") and f not in ("gap_up1", "gap_down1")]
feats.sort(key=lambda f: lu[f]["lift"] + ld[f]["lift"])
fig, ax = plt.subplots(figsize=(7.5, 6))
y = range(len(feats))
ax.barh([i + 0.2 for i in y], [lu[f]["lift"] for f in feats], 0.4, color=UP, label="P(next day >= +3%) vs normal")
ax.barh([i - 0.2 for i in y], [ld[f]["lift"] for f in feats], 0.4, color=DN, label="P(next day <= -3%) vs normal")
ax.axvline(1, color="black", lw=0.8)
ax.set_yticks(list(y)); ax.set_yticklabels(feats, fontsize=8)
ax.set_xlabel("lift (1.0 = no different from an ordinary day)")
ax.set_title("Pre-move conditions raise BOTH up and down moves\n(5-year history before the window, %s stock-days)" % format(D["history"]["rows"], ","))
ax.legend(frameon=False, fontsize=8, loc="lower right"); ax.spines[["top", "right"]].set_visible(False)
save(fig, "r11_lift_up_vs_down.png")

# 3. opening conditions: P(+2%) vs P(-2%) after 09:30 (window)
T = O["table"]
conds = [k for k in T if k != "_base" and T[k].get("p_up2_pct") is not None]
fig, ax = plt.subplots(figsize=(7.5, 4.8))
y = range(len(conds))
ax.barh([i + 0.2 for i in y], [T[k]["p_up2_pct"] for k in conds], 0.4, color=UP, label="09:30 -> close >= +2%")
ax.barh([i - 0.2 for i in y], [T[k]["p_dn2_pct"] for k in conds], 0.4, color=DN, label="09:30 -> close <= -2%")
ax.axvline(T["_base"]["p_up2_pct"], color=UP, ls=":", lw=1); ax.axvline(T["_base"]["p_dn2_pct"], color=DN, ls=":", lw=1)
ax.set_yticks(list(y)); ax.set_yticklabels(conds, fontsize=8); ax.set_xlabel("% of stock-days")
ax.set_title("Opening conditions at 09:30 and what happened next (window, gross)"); ax.legend(frameon=False, fontsize=8)
ax.spines[["top", "right"]].set_visible(False)
save(fig, "r11_opening_conditions.png")

# 4. TEST results for every pre-registered setup (close exit, net of 0.12% costs)
rows = []
for grp in ("daily", "opening"):
    for name, r in B[grp].items():
        t = r["close_exit"]["TEST"]
        if t.get("n", 0) >= 10:
            rows.append((name, t["mean_pct"], t["ci_pct"]))
rows.sort(key=lambda r: r[1])
fig, ax = plt.subplots(figsize=(7.5, 4.8))
for i, (name, m, ci) in enumerate(rows):
    ax.plot(ci, [i, i], color=GREY, lw=2)
    ax.plot(m, i, "o", color=UP if m > 0 else DN)
ax.axvline(0, color="black", lw=0.8)
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows], fontsize=8)
ax.set_xlabel("net return per trade %%, untouched TEST %s..%s (bar = Bonferroni range)" % (B["cuts"][2], B["cuts"][3]))
ax.set_title("No pre-registered setup is reliably positive after costs"); ax.spines[["top", "right"]].set_visible(False)
save(fig, "r11_backtest_test.png")

# 5. by year (close exit) for a few setups
fig, ax = plt.subplots(figsize=(7.5, 3.8))
for name, col in (("B_sector_leader", UP), ("D_breakout_absorb", DN), ("E_futures_cash", "#264653"), ("V_volume_spike_long", GREY)):
    by = B["daily"][name]["by_year_close_exit"]
    yrs = sorted(by)
    ax.plot(yrs, [by[y] for y in yrs], marker="o", color=col, label=name)
ax.axhline(0, color="black", lw=0.8); ax.set_ylabel("net % per trade"); ax.set_title("Daily setups by year (net of costs)")
ax.legend(frameon=False, fontsize=8); ax.spines[["top", "right"]].set_visible(False)
save(fig, "r11_by_year.png")
print("charts written to", IMG)
