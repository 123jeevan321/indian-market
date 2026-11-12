#!/usr/bin/env python3
"""Debate STAGE 5: historical validation of the deterministic agents (swing mode, daily bars). Paper research only.

    python trader-debate/validate.py swing [--limit N] [--write]

For every Nifty 100 stock and every completed session from warm-up to five sessions before the data ends, it builds the same swing
snapshot a live debate would see (bars through that close only; delivery and futures files dated on or before it, all published after
the close), runs the real Buyer, Seller and Judge, and simulates the plans on the FOLLOWING sessions:
  long plans   buy-stop next session at the plan entry (no fill if the open is past the do-not-chase price); exit at the stop, at
               T1, or at the close of session 5; a bar touching both stop and T1 counts as the stop; gaps fill at the open;
               Zerodha delivery costs + one tick of slippage each side.
  SELL (swing) means exit/avoid a long, so it is scored as a direction call: did price reach the plan's downside T1 before the
               invalidation level within 5 sessions, and how much did it move from the next open (gross, % of price).
Chronological split by signal date: TRAIN first 60 %, VALIDATION next 20 %, TEST last 20 % (untouched).
The Judge experiment uses setup records from TRAIN+VALIDATION only and is scored on TEST. Live stats.json gets the TEST records.
"""
import argparse, bisect, datetime, json, math, os, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import buyer, common as C, debate, evidence as E, snapshot as S    # noqa: E402

ROOT = os.path.dirname(HERE)
DAILY = os.path.join(ROOT, "trader", "cache", "daily5y")
HOLD = 5


def load(sym):
    path = os.path.join(DAILY, sym.replace("&", "_and_").replace("^", "IDX_") + ".json")
    with open(path, encoding="utf-8") as fh:
        return S.SW.enrich(S.SW.bars_from(json.load(fh)))


def sector_table(data, industry):
    """{(date, sym): sector field} using only that date's closes (peers' change vs their previous close, self excluded)."""
    chg = {}
    for sym, b in data.items():
        for i in range(1, len(b)):
            chg.setdefault(b[i]["d"], {})[sym] = 100 * (b[i]["c"] / b[i - 1]["c"] - 1)
    return chg


def sector_field(chg, industry, sym, d):
    sec = industry.get(sym)
    day = chg.get(d, {})
    vals = sorted(v for s, v in day.items() if s != sym and industry.get(s) == sec)
    if not sec or not vals:
        return S.NA("no peers with a close on %s" % d)
    return S.F({"sector": sec, "peers": len(vals), "median_change_pct": round(vals[len(vals) // 2], 2),
                "peers_up": sum(1 for v in vals if v > 0)}, "daily closes (replay)", d.isoformat(), "HISTORICAL")


def simulate_long(b, i, plan):
    """Plan made at the close of bar i; orders live from bar i+1. Returns a trade dict or None (no fill)."""
    if not plan or not plan.get("qty") or i + 1 >= len(b):
        return None
    e, cap, stop, t1, qty = plan["entry"], plan["do_not_enter_past"], plan["stop"], plan["target1"], plan["qty"]
    x = b[i + 1]
    if x["o"] > cap or x["h"] < e:
        return None
    fill = max(x["o"], e)
    r = plan["risk_per_share"] or (fill - stop)
    mfe = mae = 0.0
    exit_px, why, k = None, None, i + 1
    for k in range(i + 1, min(len(b), i + 1 + HOLD)):
        y = b[k]
        if k > i + 1 and y["o"] <= stop:
            exit_px, why = y["o"], "stop (gap)"; break
        if k > i + 1 and y["o"] >= t1:
            exit_px, why = y["o"], "T1 (gap)"; break
        mfe, mae = max(mfe, y["h"] - fill), min(mae, y["l"] - fill)
        if y["l"] <= stop:
            exit_px, why = stop, "stop"; break
        if y["h"] >= t1:
            exit_px, why = t1, "T1"; break
    if exit_px is None:
        exit_px, why = b[k]["c"], "time"
    gross = (exit_px - fill) * qty
    net = gross - C.round_trip("swing", qty, fill, exit_px)
    return {"fill": round(fill, 2), "exit": round(exit_px, 2), "why": why, "qty": qty, "gross": round(gross, 2), "net": round(net, 2),
            "mfe_r": round(mfe / r, 2) if r else None, "mae_r": round(mae / r, 2) if r else None, "days": k - i}


def score_exit(b, i, plan):
    """SELL (exit/avoid long): did price reach the downside T1 before the invalidation level within 5 sessions?"""
    if not plan or i + 1 >= len(b):
        return None
    ref = b[i + 1]["o"]
    for k in range(i + 1, min(len(b), i + 1 + HOLD)):
        y = b[k]
        if y["h"] >= plan["stop"]:
            return {"correct": False, "move_pct": round(100 * (plan["stop"] / ref - 1), 2), "why": "invalidated"}
        if y["l"] <= plan["target1"]:
            return {"correct": True, "move_pct": round(100 * (plan["target1"] / ref - 1), 2), "why": "T1"}
    return {"correct": b[k]["c"] < ref, "move_pct": round(100 * (b[k]["c"] / ref - 1), 2), "why": "time"}


def stats(trades, z=1.96):
    if not trades:
        return {"n": 0}
    net = [t["net"] for t in trades]
    gross = [t["gross"] for t in trades]
    m = statistics.mean(net)
    sd = statistics.pstdev(net) if len(net) > 1 else 0.0
    wins, losses = [x for x in net if x > 0], [x for x in net if x <= 0]
    eq, peak, dd = 0.0, 0.0, 0.0
    for t in sorted(trades, key=lambda t: t["date"]):
        eq += t["net"]; peak = max(peak, eq); dd = min(dd, eq - peak)
    return {"n": len(net), "win_gross_pct": round(100 * sum(1 for g in gross if g > 0) / len(gross), 1),
            "win_net_pct": round(100 * len(wins) / len(net), 1), "avg_win": round(statistics.mean(wins), 1) if wins else 0,
            "avg_loss": round(statistics.mean(losses), 1) if losses else 0, "expectancy": round(m, 1),
            "ci_low": round(m - z * sd / math.sqrt(len(net)), 1), "ci_high": round(m + z * sd / math.sqrt(len(net)), 1),
            "profit_factor": round(sum(wins) / -sum(losses), 2) if losses and sum(losses) else None,
            "total": round(sum(net)), "max_drawdown": round(dd), "t1_before_stop_pct": round(100 * sum(1 for t in trades if t["why"].startswith("T1")) / len(trades), 1),
            "stop_pct": round(100 * sum(1 for t in trades if t["why"].startswith("stop")) / len(trades), 1),
            "mfe_r_avg": round(statistics.mean(t["mfe_r"] for t in trades if t["mfe_r"] is not None), 2),
            "mae_r_avg": round(statistics.mean(t["mae_r"] for t in trades if t["mae_r"] is not None), 2)}


def run_swing(limit=None):
    industry = json.load(open(os.path.join(ROOT, "trader", "cache", "m15", "industry.json"), encoding="utf-8"))
    syms = sorted(industry)[:limit] if limit else sorted(industry)
    data = {s: load(s) for s in syms}
    nifty = load("^NSEI")
    regime = S.SW.regime_map(nifty)
    nd = [x["d"] for x in nifty]
    natr = {x["d"]: x["atr"] / x["c"] for x in nifty}
    q75 = sorted(natr.values())[int(0.75 * len(natr))]
    chg = sector_table(data, industry)
    debate.TIMEOUT_S = None
    rows = []
    for n_sym, sym in enumerate(syms, 1):
        b = data[sym]
        for i in range(250, len(b) - 1):
            d = b[i]["d"]
            j = bisect.bisect_right(nd, d) - 1
            if j < 250 or nd[j] != d:
                continue
            snap = S.swing_from_bars(sym, b[i - 259:i + 1], nifty[j - 259:j + 1], d, d.isoformat() + "T15:35:00", "daily cache (replay)",
                                     sector_field(chg, industry, sym, d), regime)
            rec = debate.run(snap, stats={})                                  # Judge with no records -> its rejections are logged
            msgs = {(m["agent"], m["kind"]): m["content"] for m in rec["messages"]}
            bc, sc, v = msgs[("BUYER", "initial_case")], msgs[("SELLER", "initial_case")], msgs[("JUDGE", "verdict")]
            base = buyer._swing_levels(snap)
            uncond = C.build_plan("swing", "long", base[0], base[1], base[2]) if base else None
            brk = E.recompute(snap, "buy", "S_BRK20")
            rows.append({"sym": sym, "date": d, "i": i, "regime": regime.get(d, "n/a"), "highvol": natr.get(d, 0) >= q75,
                         "buyer": bc["stance"], "setup": bc.get("setup"), "seller": sc["stance"],
                         "buyer_trade": simulate_long(b, i, bc.get("plan")) if bc["stance"] == "BUY CASE" else None,
                         "seller_score": score_exit(b, i, sc.get("plan")) if sc["stance"] == "SELL CASE" else None,
                         "rule_trade": simulate_long(b, i, uncond) if brk and brk["status"] == "PASS" else None,
                         "all_trade": simulate_long(b, i, uncond),
                         "buyer_reasons": v["buyer_assessment"]["reasons"], "judge_live": v["decision"]})
        print("%3d/%d %-12s rows so far %d" % (n_sym, len(syms), sym, len(rows)), flush=True)
    return rows


def split(rows):
    dates = sorted({r["date"] for r in rows})
    c1, c2 = dates[int(0.6 * len(dates))], dates[int(0.8 * len(dates))]
    for r in rows:
        r["period"] = "TRAIN" if r["date"] < c1 else "VALIDATION" if r["date"] < c2 else "TEST"
    return {"train_start": dates[0], "validation_start": c1, "test_start": c2, "end": dates[-1]}


def tr(rows, key, period=None, **filt):
    out = []
    for r in rows:
        if period and r["period"] not in (period if isinstance(period, tuple) else (period,)):
            continue
        if any(r.get(k) != v for k, v in filt.items()):
            continue
        t = r.get(key)
        if t:
            out.append(dict(t, date=r["date"], sym=r["sym"], setup=r.get("setup")))
    return out


def judge_replay(rows, records):
    """Judge decisions on rows using `records` as stats (re-runs only the parts that depend on stats: the edge check)."""
    zero = []
    for r in rows:
        if r["buyer"] != "BUY CASE" or not r["buyer_trade"]:
            continue
        other = [x for x in r["buyer_reasons"] if "untouched-test" not in x and not x.startswith("challenge S5")]
        rec = records.get(r["setup"])
        ok = not other and rec and rec["n"] >= 30 and rec["ci_low"] > 0 and rec["expectancy"] > 0
        if ok:
            zero.append(dict(r["buyer_trade"], date=r["date"], sym=r["sym"], setup=r["setup"]))
    return zero


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["swing"]); p.add_argument("--limit", type=int); p.add_argument("--write", action="store_true")
    a = p.parse_args(argv)
    t0 = datetime.datetime.now()
    rows = run_swing(a.limit)
    cut = split(rows)
    setups = sorted({r["setup"] for r in rows if r["buyer"] == "BUY CASE"})
    z = statistics.NormalDist().inv_cdf(1 - 0.05 / (2 * max(1, len(setups))))     # Bonferroni over the setups compared
    res = {"cut": {k: str(v) for k, v in cut.items()}, "rows": len(rows), "setups": setups, "z": round(z, 3), "minutes": None}
    per = ("TRAIN", "VALIDATION", "TEST")
    res["buyer"] = {p_: stats(tr(rows, "buyer_trade", p_), z) for p_ in per}
    res["rule_brk20"] = {p_: stats(tr(rows, "rule_trade", p_), z) for p_ in per}
    res["all_days"] = {p_: stats(tr(rows, "all_trade", p_), z) for p_ in per}
    res["buyer_by_setup"] = {s: {p_: stats(tr(rows, "buyer_trade", p_, setup=s), z) for p_ in per} for s in setups}
    # Judge experiment: records from TRAIN+VALIDATION, decisions scored on TEST
    pre = {s: stats(tr(rows, "buyer_trade", ("TRAIN", "VALIDATION"), setup=s), z) for s in setups}
    test_rows = [r for r in rows if r["period"] == "TEST"]
    jt = judge_replay(test_rows, pre)
    res["judge_test"] = stats(jt, z)
    res["judge_records_used"] = pre
    bc_test = [r for r in test_rows if r["buyer"] == "BUY CASE"]
    rej = [dict(r["buyer_trade"], date=r["date"]) for r in bc_test if r["buyer_trade"] and
           any("risk:" in x or x.startswith("plan:") or "challenge S2" in x or "challenge S4" in x for x in r["buyer_reasons"])]
    acc = [dict(r["buyer_trade"], date=r["date"]) for r in bc_test if r["buyer_trade"] and not
           any("risk:" in x or x.startswith("plan:") or "challenge S2" in x or "challenge S4" in x for x in r["buyer_reasons"])]
    res["judge_filter_test"] = {"rejected_by_rules": stats(rej, z), "passed_rules": stats(acc, z)}
    res["no_trade_rate_test"] = round(100 * (1 - len(jt) / max(1, len(test_rows))), 2)
    res["judge_trades_test"] = len(jt)
    res["seller"] = {p_: {"n": len([r for r in rows if r["period"] == p_ and r["seller_score"]]),
                          "correct_pct": round(100 * statistics.mean([1 if r["seller_score"]["correct"] else 0 for r in rows if r["period"] == p_ and r["seller_score"]]), 1) if any(r["period"] == p_ and r["seller_score"] for r in rows) else None,
                          "avg_move_pct": round(statistics.mean([r["seller_score"]["move_pct"] for r in rows if r["period"] == p_ and r["seller_score"]]), 2) if any(r["period"] == p_ and r["seller_score"] for r in rows) else None}
                     for p_ in per}
    res["buyer_by_year"] = {y: stats([t for t in tr(rows, "buyer_trade") if t["date"].year == y], z) for y in sorted({r["date"].year for r in rows})}
    res["all_by_year"] = {y: stats([t for t in tr(rows, "all_trade") if t["date"].year == y], z) for y in sorted({r["date"].year for r in rows})}
    res["buyer_by_regime"] = {g: stats(tr(rows, "buyer_trade", regime=g), z) for g in ("bull", "bear", "sideways")}
    res["buyer_highvol"] = stats(tr(rows, "buyer_trade", highvol=True), z)
    res["case_rates"] = {"buy_case_pct": round(100 * sum(1 for r in rows if r["buyer"] == "BUY CASE") / len(rows), 1),
                         "sell_case_pct": round(100 * sum(1 for r in rows if r["seller"] == "SELL CASE") / len(rows), 1),
                         "both_pct": round(100 * sum(1 for r in rows if r["buyer"] == "BUY CASE" and r["seller"] == "SELL CASE") / len(rows), 1)}
    res["minutes"] = round((datetime.datetime.now() - t0).total_seconds() / 60, 1)
    out = os.path.join(ROOT, "research", "results", "debate_validation_swing.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=str)
    print(json.dumps({k: res[k] for k in ("cut", "rows", "case_rates", "buyer", "all_days", "judge_test", "judge_trades_test", "seller", "minutes")}, indent=1, default=str))
    if a.write:
        test_records = {s: v["TEST"] for s, v in res["buyer_by_setup"].items()}
        path = os.path.join(HERE, "stats.json")
        cur = json.load(open(path, encoding="utf-8"))
        cur["swing"] = {s: {k: r.get(k) for k in ("n", "expectancy", "ci_low", "ci_high", "win_net_pct")} for s, r in test_records.items() if r.get("n")}
        cur["swing_note"] = "TEST period %s..%s, Bonferroni z=%.2f over %d setups; written %s" % (
            cut["test_start"], cut["end"], z, len(setups), datetime.date.today())
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(cur, fh, indent=1)
        print("stats.json updated (swing):", cur["swing"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
