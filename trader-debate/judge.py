"""INDEPENDENT JUDGE. Debate STEPS 8-9.

The Judge does not count arguments and does not trust either agent. For each side that made a case it re-derives everything:
  1. every cited evidence item is recomputed from the snapshot; items that do not reproduce are struck out;
  2. the plan arithmetic (size, costs, targets) is rebuilt and re-checked;
  3. the opponent's FATAL challenges are re-checked by the Judge itself (a concession is not needed, a denial is not enough);
  4. the setup's untouched-test record is looked up in stats.json (written by validate.py in stage 5);
  5. the risk gate is applied (time window, card rules, open exposure, daily loss).
BUY or SELL only when one side passes all five; if both pass, the larger untouched-test expectancy wins; otherwise NO TRADE.
"""
import datetime, json, os

import common as C
import evidence as E

NAME, VERSION = "JUDGE", "judge-1"
STATS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stats.json")


def load_stats(path=STATS):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _verify_evidence(snapshot, side, case):
    kept, struck = [], []
    for e in case.get("evidence_cited", []):
        r = E.recompute(snapshot, side, e["id"])
        if r and r["status"] == "PASS" and r.get("observed") == e.get("observed"):
            kept.append(r)
        else:
            struck.append({"id": e["id"], "why": "does not reproduce on the snapshot (%s)" % (r["status"] if r else "unknown item")})
    return kept, struck


def _verify_plan(snapshot, case):
    p = case.get("plan")
    if not p or p["direction"] == "exit_long":
        return [], p
    rebuilt = C.build_plan(snapshot["mode"], p["direction"], p["entry"], p["stop"], p["entry_kind"])
    lv = C.val(snapshot, "levels") or {}
    probs = C.plan_problems(snapshot["mode"], rebuilt, lv.get("day_high"), lv.get("day_low"))
    for k in ("qty", "target1", "target2", "max_loss_incl_costs"):
        if rebuilt[k] != p[k]:
            probs.append("agent's %s %s differs from the recomputed %s" % (k, p[k], rebuilt[k]))
    return probs, rebuilt


def _record(stats, mode, setup):
    return ((stats.get(mode) or {}).get(setup)) if setup else None


def _validated(rec):
    return bool(rec) and rec.get("n", 0) >= 30 and rec.get("ci_low", -1) > 0 and rec.get("expectancy", -1) > 0


def _risk_gate(snapshot, side, case, state):
    out = []
    mode = snapshot["mode"]
    flags = [e for e in E.evaluate(snapshot, side) if e["status"] == "FLAG"]
    for f in flags:
        out.append("risk flag %s: %s (%s)" % (f["id"], f["observed"], f["threshold"]))
    if mode == "intraday":
        t = datetime.datetime.fromisoformat(snapshot["snapshot_time_ist"]).time()
        if not datetime.time(9, 30) <= t <= datetime.time(14, 45):
            out.append("outside the 09:30-14:45 entry window (%s)" % t.strftime("%H:%M"))
        rv = C.val(snapshot, "relative_volume") or {}
        if t > datetime.time(11, 0) and (rv.get("cumulative_x") or 0) <= 1.0:
            out.append("after 11:00 with relative volume %.2fx (needs above 1.0x)" % (rv.get("cumulative_x") or 0))
    state = state or {}
    if state.get("day_pnl", 0) <= -abs(state.get("daily_loss_limit", 2000)):
        out.append("daily loss limit reached (%s)" % state.get("day_pnl"))
    if state.get("drawdown", 0) <= -abs(state.get("max_drawdown", 10000)):
        out.append("account drawdown stop reached (%s)" % state.get("drawdown"))
    sector = (C.val(snapshot, "sector") or {}).get("sector")
    for pos in state.get("open_positions", []):
        if pos.get("symbol") == snapshot["symbol"]:
            out.append("already holding %s" % pos["symbol"])
        elif sector and pos.get("sector") == sector:
            out.append("correlated exposure: already holding %s in %s" % (pos["symbol"], sector))
    return out


def _fatal_checks(snapshot, side, case, opp_challenges, stats):
    """Re-derive the opponent's fatal challenges instead of trusting either agent's answer."""
    stand = []
    for ch in opp_challenges:
        if not ch.get("fatal"):
            continue
        cid = ch["id"]
        if cid[1] == "5":                                    # validation question
            if not _validated(_record(stats, snapshot["mode"], case.get("setup"))):
                stand.append({"id": cid, "text": ch["text"], "judge": "upheld: no untouched-test record shows a positive edge"})
        elif cid[1] == "4":                                  # plan arithmetic
            if case.get("plan_problems"):
                stand.append({"id": cid, "text": ch["text"], "judge": "upheld: the recomputed plan has the same problems"})
        elif cid[1] == "2":                                  # late / extended entry
            ext = E.recompute(snapshot, side, "X_EXTENDED")
            mov = E.recompute(snapshot, side, "X_MOVED")
            flag = mov if cid.endswith("b") else ext            # S2b/B2b = move already done; S2/B2 = stretched from VWAP
            if flag and flag["status"] == "FLAG":
                stand.append({"id": cid, "text": ch["text"], "judge": "upheld: %s reproduces (%s)" % (flag["id"], flag["observed"])})
    return stand


def _assess(snapshot, side, case, opp_challenges, stats, state):
    a = {"side": side, "case": case.get("stance"), "setup": case.get("setup")}
    if case.get("stance") not in ("BUY CASE", "SELL CASE"):
        a.update(passed=False, reasons=[case.get("reason") or case.get("error") or "no case made"], kept=[], struck=[])
        return a
    if case.get("snapshot_hash") != snapshot.get("hash"):
        a.update(passed=False, reasons=["case was built on snapshot %s, not the debate's snapshot %s" % (
            case.get("snapshot_hash"), snapshot.get("hash"))], kept=[], struck=[])
        return a
    kept, struck = _verify_evidence(snapshot, side, case)
    plan_probs, plan = _verify_plan(snapshot, case)
    fatal = _fatal_checks(snapshot, side, case, opp_challenges, stats)
    rec = _record(stats, snapshot["mode"], case.get("setup"))
    risk = _risk_gate(snapshot, side, case, state)
    reasons = []
    if len(kept) < 2:
        reasons.append("only %d cited item(s) reproduce" % len(kept))
    reasons += ["plan: " + p for p in plan_probs]
    reasons += ["challenge %s %s" % (f["id"], f["judge"]) for f in fatal]
    if not _validated(rec):
        reasons.append("setup %s has no validated untouched-test edge (%s)" % (
            case.get("setup"), "record: %s" % rec if rec else "no record in stats.json; prior: %s" % case.get("confidence", {}).get("setup_reference")))
    reasons += ["risk: " + r for r in risk]
    a.update(passed=not reasons, reasons=reasons, kept=kept, struck=struck, plan=plan, record=rec, fatal_upheld=fatal)
    return a


def _change_triggers(snapshot, ab, asl):
    out = []
    vw = C.val(snapshot, "vwap") or {}
    atr = C.val(snapshot, "atr_5m")
    for a in (ab, asl):
        for r in a["reasons"]:
            if "X_EXTENDED" in r and vw.get("value") and atr:
                lvl = vw["value"] + (1.5 if a["side"] == "buy" else -1.5) * atr
                out.append("%s side: price returns to within 1.5 ATR(5m) of VWAP (about %.2f) while its evidence still holds" % (a["side"], lvl))
            if "no validated untouched-test edge" in r:
                out.append("%s side: setup %s earns a positive untouched-test record in validate.py" % (a["side"], a["setup"]))
            if "only" in r and "reproduce" in r:
                out.append("%s side: at least two cited items reproduce" % a["side"])
    if not out:
        out.append("a new snapshot in which the opposing side's evidence starts to pass")
    return sorted(set(out))


MAX_AGE_MIN = 10


def data_age_minutes(snapshot):
    """Minutes between the snapshot time and the end of the last price bar it used (intraday). None if unknown."""
    f = snapshot["fields"].get("price") or {}
    try:
        asof = datetime.datetime.strptime(f["as_of"][:16], "%Y-%m-%d %H:%M")
        return (datetime.datetime.fromisoformat(snapshot["snapshot_time_ist"]) - asof).total_seconds() / 60
    except (KeyError, TypeError, ValueError):
        return None


def decide(snapshot, buyer_case, seller_case, buyer_challenges, seller_challenges, buyer_responses, seller_responses,
           stats=None, state=None):
    stats = load_stats() if stats is None else stats
    t0 = datetime.datetime.now().isoformat(timespec="seconds")
    failed = [c["agent"] for c in (buyer_case, seller_case) if c.get("stance") == "AGENT FAILED"]
    ab = _assess(snapshot, "buy", buyer_case, seller_challenges, stats, state)
    asl = _assess(snapshot, "sell", seller_case, buyer_challenges, stats, state)
    out = {"agent": NAME, "version": VERSION, "created": t0, "snapshot_hash": snapshot.get("hash"),
           "buyer_assessment": ab, "seller_assessment": asl}
    if failed:
        out.update(decision="NO TRADE", why="debate incomplete: %s failed; a one-sided debate never produces a signal" % ", ".join(failed))
    elif snapshot.get("unavailable") and "price" in snapshot["unavailable"]:
        out.update(decision="NO TRADE", why="price data unavailable")
    elif snapshot["mode"] == "intraday" and (data_age_minutes(snapshot) is None or data_age_minutes(snapshot) > MAX_AGE_MIN):
        out.update(decision="NO TRADE", why="price data is %s minutes old at debate time (limit %d): unreliable for an intraday entry"
                   % ("an unknown number of" if data_age_minutes(snapshot) is None else "%.0f" % data_age_minutes(snapshot), MAX_AGE_MIN))
    else:
        winners = [a for a in (ab, asl) if a["passed"]]
        if len(winners) == 2:
            eb, es = ab["record"]["expectancy"], asl["record"]["expectancy"]
            winners = [ab] if eb > es else [asl] if es > eb else []
        if len(winners) == 1:
            w = winners[0]
            out.update(decision="BUY" if w["side"] == "buy" else "SELL", plan=w["plan"],
                       why="%s case passed verification, plan checks, fatal challenges, untouched-test record and risk gate" % w["side"])
        else:
            out.update(decision="NO TRADE", why="no side passed every check; see each side's reasons")
    out["buyer_right"] = [e["observed"] for e in ab.get("kept", [])]
    out["buyer_wrong"] = [s["id"] + ": " + s["why"] for s in ab.get("struck", [])] + ab["reasons"]
    out["seller_right"] = [e["observed"] for e in asl.get("kept", [])]
    out["seller_wrong"] = [s["id"] + ": " + s["why"] for s in asl.get("struck", [])] + asl["reasons"]
    out["more_reliable_evidence"] = _reliability(ab, asl)
    out["rejected_arguments"] = [{"side": a["side"], "reasons": a["reasons"]} for a in (ab, asl) if not a["passed"]]
    out["what_would_change_it"] = _change_triggers(snapshot, ab, asl)
    return out


def _reliability(ab, asl):
    def score(a):
        hist = sum(1 for e in a.get("kept", []) if e["id"] in ("I_DELIV", "I_OI"))   # the only items with a measured edge (Round 8)
        return len(a.get("kept", [])), hist
    (nb, hb), (ns, hs) = score(ab), score(asl)
    note = ("Item counts are reported, not used to decide. Only delivery and OI items have a measured relative edge (Round 8); "
            "everything else is unvalidated in isolation.")
    return {"buyer_reproducing_items": nb, "buyer_items_with_measured_edge": hb, "seller_reproducing_items": ns,
            "seller_items_with_measured_edge": hs, "note": note}
