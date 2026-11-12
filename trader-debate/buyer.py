"""BUYER AGENT (bullish analyst). Debate STEP 2.

Job: build the strongest HONEST case for a long entry from the shared snapshot alone. It never sees the Seller's case before it has
written its own. It cites only catalogue items that PASS on the snapshot, lists the ones that fail or are unavailable, and reports
its own risk flags instead of hiding them. Confidence comes from earlier research (the catalogue's `prior`), never from optimism.
"""
import copy, datetime

import common as C
import evidence as E

NAME, VERSION = "BUYER", "buyer-1"
SETUP_ORDER = ["I_SWEEP", "I_ORB", "I_PDL", "I_VWAP", "S_BRK20", "S_TREND"]   # which passing item names the setup, in priority order


def _setup(passed):
    for iid in SETUP_ORDER:
        if iid in passed:
            return iid
    return None


def _intraday_levels(s, passed):
    lv, price, vw, atr = C.val(s, "levels"), C.val(s, "price"), C.val(s, "vwap"), C.val(s, "atr_5m")
    if not lv or price is None or not vw or not atr:
        return None
    # entry: retest of the highest broken level below price; otherwise a buy-stop above today's high
    broken = [(lv[k], lab) for k, lab in (("prev_high", "previous-day high"), ("or_high", "opening-range high"))
              if lv.get(k) is not None and price > lv[k]]
    if "I_SWEEP" in passed:
        entry, kind = price, "buy near current price after the previous-day low was swept and reclaimed (%.2f)" % lv["prev_low"]
        stop = min(lv["day_low"], entry - atr) - 0.1 * atr
    elif broken:
        lvl, lab = max(broken)
        entry, kind = lvl, "limit buy on a retest of the %s %.2f" % (lab, lvl)
        stop = min(vw["value"], entry - atr) - 0.1 * atr
    else:
        entry, kind = C.tick(lv["day_high"] + C.TICK, up=True), "buy-stop above today's high %.2f" % lv["day_high"]
        stop = min(vw["value"], entry - atr) - 0.1 * atr
    return entry, stop, kind, lv


def _swing_levels(s):
    d, t = C.val(s, "daily"), C.val(s, "trend")
    if not d or not t:
        return None
    entry = C.tick(d["high"] + C.TICK, up=True)
    stop = min(d["low"], t["ema20"]) - 0.1 * t["atr14"]
    return entry, stop, "buy-stop next session above the signal-day high %.2f" % d["high"], None


def analyse(snapshot):
    s = copy.deepcopy(snapshot)                       # never touch the shared snapshot
    t0 = datetime.datetime.now().isoformat(timespec="seconds")
    ev = E.evaluate(s, "buy")
    passed = {e["id"] for e in ev if e["status"] == "PASS"}
    cited = [e for e in ev if e["status"] == "PASS"]
    against = [e for e in ev if e["status"] in ("FAIL", "FLAG")]
    missing = [e["id"] for e in ev if e["status"] == "UNAVAILABLE"]
    case = {"agent": NAME, "version": VERSION, "created": t0, "snapshot_hash": snapshot.get("hash"), "mode": s["mode"],
            "symbol": s["symbol"], "evidence_cited": cited, "evidence_against": against, "unavailable": missing}
    if len(cited) < 2:
        case.update(stance="NO BUY CASE", reason="only %d bullish item(s) pass; a case needs at least 2" % len(cited), plan=None)
        return case
    lv = _intraday_levels(s, passed) if s["mode"] == "intraday" else _swing_levels(s)
    if lv is None:
        case.update(stance="NO BUY CASE", reason="price, VWAP, ATR or level data unavailable: cannot set entry and stop", plan=None)
        return case
    entry, stop, kind, levels = lv
    plan = C.build_plan(s["mode"], "long", entry, stop, kind)
    problems = C.plan_problems(s["mode"], plan, *(levels["day_high"], levels["day_low"]) if levels else (None, None))
    setup = _setup(passed) or "multi-factor"
    prior = next((e["prior"] for e in ev if e["id"] == setup), "no single prior test for this combination")
    nifty = C.val(s, "nifty") or {}
    nch = nifty.get("day_change_pct", nifty.get("change_pct"))
    weak_mkt = nch is not None and nch < 0
    room = None
    if s["mode"] == "intraday" and levels:
        above = [x for x in (levels.get("prev_high"), levels["day_high"]) if x and x > plan["entry"]]
        room = round(min(above) - plan["entry"], 2) if above else None
    case.update(
        stance="BUY CASE", setup=setup, plan=plan, plan_problems=problems,
        potential_upside_pct=round(100 * (plan["target2"] / plan["entry"] - 1), 2),
        room_to_next_resistance=room,
        weak_market_note=("NIFTY is down %.2f%%: the case rests on relative strength, which matters only if the stock keeps "
                          "outperforming; a market sell-off can still drag it below the stop." % nch) if weak_mkt else None,
        invalidation=_invalidation(s["mode"], plan, levels),
        confidence={"source": "prior research", "setup_reference": prior, "validated_out_of_sample": False,
                    "note": "no long setup has passed an untouched-period test after costs (Rounds 1-9); treat as UNVALIDATED"},
        risk_flags=[e for e in ev if e["status"] == "FLAG"])
    return case


def _invalidation(mode, plan, levels):
    if mode == "intraday":
        return ["a 5-minute close below VWAP", "price trades at or below the stop %.2f" % plan["stop"],
                "not filled within 30 minutes, or filled above %.2f (do-not-chase price)" % plan["do_not_enter_past"],
                "NIFTY falls below its VWAP while the sector median turns negative", "T1 not reached within 90 minutes (stall exit)"]
    return ["a daily close below the stop %.2f" % plan["stop"], "next session opens above %.2f (too far to chase)" % plan["do_not_enter_past"],
            "NIFTY regime turns bear", "no progress to T1 by the close of session 5"]


def challenge(own_case, other_case, snapshot):
    """STEP 5: the Buyer questions the Seller's case. Returns a list of challenges, each with an id the Seller must answer."""
    out = []
    if other_case.get("stance") != "SELL CASE":
        return out
    s = snapshot
    vw, lv, price = C.val(s, "vwap"), C.val(s, "levels"), C.val(s, "price")
    if s["mode"] == "intraday" and lv and price and lv.get("prev_low") and 0 <= (price - lv["prev_low"]) / price < 0.004:
        out.append({"id": "B1", "fatal": False, "text": "Support is close: the previous-day low %.2f is within 0.4%% below price; "
                    "shorts into support often bounce." % lv["prev_low"]})
    if vw and vw.get("deviation_atr") is not None and vw["deviation_atr"] < -1.5:
        out.append({"id": "B2", "fatal": True, "text": "The short is late: price is already %.2f ATR(5m) below VWAP (rule: no entry "
                    "beyond 1.5)." % vw["deviation_atr"]})
    for e in E.evaluate(s, "buy"):
        if e["id"] in ("I_SWEEP", "I_RS", "S_RS") and e["status"] == "PASS":
            out.append({"id": "B3-" + e["id"], "fatal": False, "text": "Counter-evidence: %s (%s)." % (e["description"], e["observed"])})
    if other_case.get("plan_problems"):
        out.append({"id": "B4", "fatal": True, "text": "The short plan fails the arithmetic checks: " + "; ".join(other_case["plan_problems"])})
    out.append({"id": "B5", "fatal": True, "text": "Has this short setup worked on unseen data? Reference: %s."
                % other_case.get("confidence", {}).get("setup_reference")})
    return out


def respond(own_case, challenges, snapshot):
    """STEP 7: answer each challenge with a recomputed fact, or concede it."""
    out = []
    for ch in challenges:
        cid = ch["id"]
        if cid.startswith("S5"):
            out.append({"to": cid, "concede": True, "text": "Conceded: the long setup is not validated out of sample (%s)."
                        % own_case.get("confidence", {}).get("setup_reference")})
        elif cid.startswith("S4"):
            out.append({"to": cid, "concede": True, "text": "Conceded: the plan arithmetic fails as stated."})
        elif cid.startswith("S2"):
            out.append({"to": cid, "concede": True, "text": "Conceded: the entry is beyond 1.5 ATR(5m) from VWAP; the rule says no entry."})
        elif cid.startswith("S3"):
            item = cid.split("-", 1)[1]
            out.append({"to": cid, "concede": False, "text": "Acknowledged as counter-evidence (%s). It does not reproduce on the buy side; "
                        "the long case stands on %d passing items." % (item, len(own_case.get("evidence_cited", [])))})
        else:
            out.append({"to": cid, "concede": False, "text": "Noted; the stop at %s already allows for it."
                        % (own_case.get("plan") or {}).get("stop")})
    return out
