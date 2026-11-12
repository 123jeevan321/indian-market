"""SELLER AGENT (bearish analyst). Debate STEP 3.

Job: build the strongest HONEST bearish case from the shared snapshot alone, written before it sees the Buyer's case.
What SELL means depends on the mode and the rules of NSE cash equity:
  intraday  an intraday short (MIS), squared off by 15:15 the same day. Never carried overnight (a cash short held to settlement
            fails delivery and goes to auction).
  swing     EXIT or AVOID a long position. No overnight short is proposed: that would need F&O, which is out of scope.
It also looks for weakness hidden by a strong market (stock lagging NIFTY on an up day).
"""
import copy, datetime

import common as C
import evidence as E

NAME, VERSION = "SELLER", "seller-1"
SETUP_ORDER = ["I_FAILBRK", "I_ORB", "I_PDL", "I_VWAP", "S_BRK20", "S_CLOSE", "S_TREND"]


def _intraday_levels(s, passed):
    lv, price, vw, atr = C.val(s, "levels"), C.val(s, "price"), C.val(s, "vwap"), C.val(s, "atr_5m")
    if not lv or price is None or not vw or not atr:
        return None
    broken = [(lv[k], lab) for k, lab in (("prev_low", "previous-day low"), ("or_low", "opening-range low"))
              if lv.get(k) is not None and price < lv[k]]
    if "I_FAILBRK" in passed:
        entry, kind = price, "short near current price after the failed break of the previous-day high %.2f" % lv["prev_high"]
        stop = max(lv["day_high"], entry + atr) + 0.1 * atr
    elif broken:
        lvl, lab = min(broken)
        entry, kind = lvl, "limit short on a retest of the %s %.2f from below" % (lab, lvl)
        stop = max(vw["value"], entry + atr) + 0.1 * atr
    else:
        entry, kind = C.tick(lv["day_low"] - C.TICK), "sell-stop below today's low %.2f" % lv["day_low"]
        stop = max(vw["value"], entry + atr) + 0.1 * atr
    return entry, stop, kind, lv


def analyse(snapshot):
    s = copy.deepcopy(snapshot)
    t0 = datetime.datetime.now().isoformat(timespec="seconds")
    ev = E.evaluate(s, "sell")
    passed = {e["id"] for e in ev if e["status"] == "PASS"}
    cited = [e for e in ev if e["status"] == "PASS"]
    against = [e for e in ev if e["status"] in ("FAIL", "FLAG")]
    missing = [e["id"] for e in ev if e["status"] == "UNAVAILABLE"]
    case = {"agent": NAME, "version": VERSION, "created": t0, "snapshot_hash": snapshot.get("hash"), "mode": s["mode"],
            "symbol": s["symbol"], "evidence_cited": cited, "evidence_against": against, "unavailable": missing,
            "sell_type": "INTRADAY SHORT (MIS), square off by 15:15" if s["mode"] == "intraday"
            else "EXIT / AVOID LONG (no overnight cash short)"}
    if len(cited) < 2:
        case.update(stance="NO SELL CASE", reason="only %d bearish item(s) pass; a case needs at least 2" % len(cited), plan=None)
        return case
    setup = next((i for i in SETUP_ORDER if i in passed), "multi-factor")
    prior = next((e["prior"] for e in ev if e["id"] == setup), "no single prior test for this combination")
    nifty = C.val(s, "nifty") or {}
    nch = nifty.get("day_change_pct", nifty.get("change_pct"))
    hidden = ("NIFTY is up %.2f%% but this stock is not participating: weakness hidden by a strong market." % nch
              if nch is not None and nch > 0 and ("I_RS" in passed or "S_RS" in passed) else None)
    if s["mode"] == "intraday":
        lv = _intraday_levels(s, passed)
        if lv is None:
            case.update(stance="NO SELL CASE", reason="price, VWAP, ATR or level data unavailable: cannot set entry and stop", plan=None)
            return case
        entry, stop, kind, levels = lv
        plan = C.build_plan("intraday", "short", entry, stop, kind)
        problems = C.plan_problems("intraday", plan, levels["day_high"], levels["day_low"])
        below = [x for x in (levels.get("prev_low"), levels["day_low"]) if x and x < plan["entry"]]
        room = round(plan["entry"] - max(below), 2) if below else None
        downside = round(100 * (1 - plan["target2"] / plan["entry"]), 2)
        inval = ["a 5-minute close above VWAP", "price trades at or above the stop %.2f" % plan["stop"],
                 "not filled within 30 minutes, or filled below %.2f (do-not-chase price)" % plan["do_not_enter_past"],
                 "NIFTY reclaims its VWAP with the sector median turning positive", "T1 not reached within 90 minutes (stall exit)",
                 "15:15: square off regardless (MIS short cannot be held overnight)"]
    else:
        d, t = C.val(s, "daily"), C.val(s, "trend")
        if not d or not t:
            case.update(stance="NO SELL CASE", reason="daily or trend data unavailable", plan=None)
            return case
        # For a holder: exit at the next open; the bearish view is wrong above the invalidation level (no short is opened).
        exit_px = d["close"]
        invalid = C.tick(max(d["high"], t["ema20"]) + 0.1 * t["atr14"], up=True)
        r = invalid - exit_px
        plan = {"direction": "exit_long", "entry": exit_px, "entry_kind": "exit or avoid a long at the next open (reference: last close)",
                "do_not_enter_past": None, "stop": invalid, "target1": C.tick(exit_px - 1.5 * r), "target2": C.tick(exit_px - 2.5 * r),
                "risk_per_share": round(r, 2), "stop_pct": round(100 * r / exit_px, 2), "qty": None, "position_value": None,
                "max_loss_incl_costs": None, "net_at_t1": None, "net_at_t2": None, "net_rr_t1": 1.5,
                "holding": "applies to an existing long: exit now rather than hold 1-5 sessions", "notes": [
                    "T1/T2 are the downside a holder avoids by exiting; the 'stop' is the level above which the bearish view is wrong"]}
        problems, room = [], None
        downside = round(100 * (1 - plan["target2"] / exit_px), 2)
        inval = ["a daily close above %.2f" % invalid, "NIFTY regime turns bull with the stock's 20-day RS turning positive"]
    case.update(stance="SELL CASE", setup=setup, plan=plan, plan_problems=problems, potential_downside_pct=downside,
                room_to_next_support=room, hidden_weakness_note=hidden, invalidation=inval,
                confidence={"source": "prior research", "setup_reference": prior, "validated_out_of_sample": False,
                            "note": "no short or exit setup has passed an untouched-period test after costs; treat as UNVALIDATED"},
                risk_flags=[e for e in ev if e["status"] == "FLAG"])
    return case


def challenge(own_case, other_case, snapshot):
    """STEP 6: the Seller questions the Buyer's case."""
    out = []
    if other_case.get("stance") != "BUY CASE":
        return out
    s = snapshot
    vw, lv, price, rv = C.val(s, "vwap"), C.val(s, "levels"), C.val(s, "price"), C.val(s, "relative_volume")
    if vw and vw.get("deviation_atr") is not None and vw["deviation_atr"] > 1.5:
        out.append({"id": "S2", "fatal": True, "text": "The entry is late: price is %.2f ATR(5m) above VWAP (rule: no entry beyond 1.5)."
                    % vw["deviation_atr"]})
    ch = C.val(s, "day_change_pct")
    if ch is not None and ch > 2.5:
        out.append({"id": "S2b", "fatal": True, "text": "The move is mostly done: already %+.2f%% on the day (rule: no entry after 2.5%%)." % ch})
    if rv and rv.get("last_bar_x") is not None and rv["last_bar_x"] < 1.0:
        out.append({"id": "S1", "fatal": False, "text": "Volume is fading: the last bar traded %.2fx its usual volume; the push may be over."
                    % rv["last_bar_x"]})
    if s["mode"] == "intraday" and lv and price and lv.get("prev_high") and 0 <= (lv["prev_high"] - price) / price < 0.004:
        out.append({"id": "S6", "fatal": False, "text": "Resistance is close: previous-day high %.2f is within 0.4%% above price." % lv["prev_high"]})
    for e in E.evaluate(s, "sell"):
        if e["id"] in ("I_FAILBRK", "I_RS", "S_RS", "S_CLOSE") and e["status"] == "PASS":
            out.append({"id": "S3-" + e["id"], "fatal": False, "text": "Counter-evidence: %s (%s)." % (e["description"], e["observed"])})
    if other_case.get("plan_problems"):
        out.append({"id": "S4", "fatal": True, "text": "The long plan fails the arithmetic checks: " + "; ".join(other_case["plan_problems"])})
    out.append({"id": "S5", "fatal": True, "text": "Has this long setup worked on unseen data? Reference: %s."
                % other_case.get("confidence", {}).get("setup_reference")})
    return out


def respond(own_case, challenges, snapshot):
    """STEP 7: answer each challenge with a recomputed fact, or concede it."""
    out = []
    for ch in challenges:
        cid = ch["id"]
        if cid.startswith("B5"):
            out.append({"to": cid, "concede": True, "text": "Conceded: the bearish setup is not validated out of sample (%s)."
                        % own_case.get("confidence", {}).get("setup_reference")})
        elif cid.startswith(("B4", "B2")):
            out.append({"to": cid, "concede": True, "text": "Conceded: " + ch["text"]})
        elif cid.startswith("B3"):
            out.append({"to": cid, "concede": False, "text": "Acknowledged counter-evidence (%s); the bearish case still has %d passing items."
                        % (cid.split("-", 1)[1], len(own_case.get("evidence_cited", [])))})
        else:
            out.append({"to": cid, "concede": False, "text": "Noted; the stop at %s already allows for it." % (own_case.get("plan") or {}).get("stop")})
    return out
