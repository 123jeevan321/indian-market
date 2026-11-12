"""Three-Agent Trading Report: the user's standing chat format (2026-11-12), built ONLY from a stored debate record.

Sections, always in this order and in one response:
  🟢 1. BUYER AGENT: BULLISH VIEW    🔴 2. SELLER AGENT: BEARISH VIEW    ⚖️ 3. JUDGE AGENT: FINAL DECISION    📊 4. FINAL TRADE REPORT
Every evidence row carries its data class and time (LIVE / DELAYED / PAST SESSION / NOT AVAILABLE). Nothing is estimated here; the
decision is the Judge's, never re-decided by the writer. If the Judge says NO TRADE, the report says 🟡 WAIT / NO TRADE.
"""
import json, os

from render import _msgs

HERE = os.path.dirname(os.path.abspath(__file__))
CLASS_TAG = {"REALTIME": "LIVE", "DELAYED": "DELAYED", "HISTORICAL": "PAST SESSION", "UNAVAILABLE": "NOT AVAILABLE"}
FIELD_FOR = {"I_VWAP": "vwap", "I_RVOL": "relative_volume", "I_RS": "nifty", "I_SECTOR": "sector", "I_ORB": "levels", "I_PDL": "levels",
             "I_FAILBRK": "levels", "I_SWEEP": "levels", "I_IMPULSE": "impulse_last_6_bars", "I_OPEN": "opening_1m",
             "I_DELIV": "delivery_prev", "I_OI": "futures_prev", "X_EXTENDED": "vwap", "X_MOVED": "day_change_pct",
             "S_TREND": "trend", "S_RS": "relative_strength", "S_BRK20": "trend", "S_ADX": "trend", "S_WEEKLY": "weekly",
             "S_CLOSE": "daily", "S_RSI": "trend", "X_RSI": "trend"}
BADGE = {"BUY": "🟢 BUY", "SELL": "🔴 SELL"}


def _tag(rec, item_id):
    f = rec["snapshot"]["fields"].get(FIELD_FOR.get(item_id, ""), {})
    return "%s, %s" % (CLASS_TAG.get(f.get("class"), "?"), f.get("as_of") or "-")


def _money(x):
    return "₹{:,.2f}".format(x) if isinstance(x, (int, float)) else "-"


def _plan_table(p):
    if not p:
        return "_No entry proposed: not enough evidence for this side._"
    if p["direction"] == "exit_long":
        return ("| Action | Bearish view wrong above | Downside T1 | Downside T2 |\n|---|---|---|---|\n"
                "| Exit / avoid a long (no overnight short) | %s | %s | %s |" % (_money(p["stop"]), _money(p["target1"]), _money(p["target2"])))
    act = "BUY" if p["direction"] == "long" else "SHORT (MIS, square off by 15:15)"
    return ("| Action | Entry | Do not enter past | Stop-loss | Target 1 | Target 2 | Qty | Max loss incl. costs | Net at T1 |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            "| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                act, _money(p["entry"]), _money(p["do_not_enter_past"]), _money(p["stop"]), _money(p["target1"]),
                _money(p["target2"]), p["qty"], _money(p["max_loss_incl_costs"]), _money(p["net_at_t1"])))


def _side(rec, agent, emoji, title, word):
    case = _msgs(rec, agent, "initial_case")[0]["content"]
    other = "SELLER" if agent == "BUYER" else "BUYER"
    got = _msgs(rec, other, "challenges")
    chs = got[0]["content"] if got and isinstance(got[0]["content"], list) else []
    resp = _msgs(rec, agent, "responses")
    ans = {r["to"]: r for r in (resp[0]["content"] if resp and isinstance(resp[0]["content"], list) else [])}
    L = ["## %s %s" % (emoji, title), "",
         "**Stance:** %s%s" % (case.get("stance"), " · setup `%s`" % case["setup"] if case.get("setup") else "")]
    if case.get("reason") or case.get("error"):
        L.append("**Why no case:** %s" % (case.get("reason") or case.get("error")))
    if case.get("sell_type"):
        L.append("**What SELL means here:** %s" % case["sell_type"])
    for k in ("weak_market_note", "hidden_weakness_note"):
        if case.get(k):
            L.append("**Note:** %s" % case[k])
    L += ["", "**Why it may go %s** (only evidence that checks out on the data)" % word, "",
          "| Evidence | What the data shows | Needed | Data |", "|---|---|---|---|"]
    L += ["| %s | %s | %s | %s |" % (e["description"], e["observed"], e["threshold"], _tag(rec, e["id"]))
          for e in case.get("evidence_cited", [])] or ["| none | - | - | - |"]
    L += ["", "**Entry and exit proposed**", "", _plan_table(case.get("plan")), ""]
    if case.get("plan"):
        risks = ["%s: %s" % (e["description"], e["observed"]) for e in case.get("evidence_against", []) if e["status"] == "FLAG"]
        risks += ["plan problem: %s" % x for x in case.get("plan_problems", [])]
        c = case.get("confidence") or {}
        risks.append("history: %s (validated on unseen data: %s)" % (c.get("setup_reference", "n/a"),
                                                                     "yes" if c.get("validated_out_of_sample") else "no"))
        L += ["**Risks**", ""] + ["- " + x for x in risks] + [""]
        if case.get("invalidation"):
            L += ["**Wrong if:** " + "; ".join(case["invalidation"]), ""]
    if chs:
        L += ["**Challenged by the %s → answer**" % other.lower(), ""]
        for ch in chs:
            a = ans.get(ch["id"])
            L.append("- %s%s → %s" % ("⚠️ " if ch.get("fatal") else "", ch["text"],
                                       "**conceded**" if a and a["concede"] else (a["text"] if a else "no answer")))
        L.append("")
    return "\n".join(L)


def _confidence(rec, v):
    try:
        with open(os.path.join(HERE, "stats.json"), encoding="utf-8") as fh:
            stats = json.load(fh)
    except (OSError, ValueError):
        stats = {}
    out = []
    for side in ("buyer", "seller"):
        st = (v.get(side + "_assessment") or {}).get("setup")
        if not st:
            continue
        r = (stats.get(rec["mode"]) or {}).get(st)
        out.append("%s setup `%s`: %s" % (side.capitalize(), st, "tested on unseen data: %d trades, ₹%s per trade after costs (range ₹%s to ₹%s)"
                                          % (r["n"], r["expectancy"], r["ci_low"], r["ci_high"]) if r else "never tested on unseen data"))
    return out or ["No setup was proposed by either side."]


def report_md(rec):
    v = _msgs(rec, "JUDGE", "verdict")[0]["content"]
    snap, dec = rec["snapshot"], v["decision"]
    badge = BADGE.get(dec, "🟡 WAIT / NO TRADE")
    price = snap["fields"].get("price", {})
    L = ["# 📈 Three-Agent Trading Report: %s (%s)" % (rec["symbol"], rec["mode"]), "",
         "| Snapshot (IST) | Price | Source | Orders |", "|---|---|---|---|",
         "| %s | %s | %s (%s) | paper analysis; you place every order yourself |" % (
             snap["snapshot_time_ist"].replace("T", " ")[:16], _money(price.get("value")), price.get("source", "-"),
             CLASS_TAG.get(price.get("class"), "?")), ""]
    if snap.get("unavailable"):
        L += ["**Not available for this analysis:** %s" % ", ".join(snap["unavailable"]), ""]
    L.append(_side(rec, "BUYER", "🟢", "1. BUYER AGENT: BULLISH VIEW", "UP"))
    L.append(_side(rec, "SELLER", "🔴", "2. SELLER AGENT: BEARISH VIEW", "DOWN"))
    L += ["## ⚖️ 3. JUDGE AGENT: FINAL DECISION", "", "### %s" % badge, "", "**Why:** %s" % v["why"], ""]
    for side, nm in (("buyer", "Buyer"), ("seller", "Seller")):
        a = v.get(side + "_assessment") or {}
        right = v.get(side + "_right", [])
        L.append("**%s, what checked out:** %s" % (nm, "; ".join(right[:4]) if right else "nothing"))
        if a.get("reasons"):
            L += ["", "**%s, why rejected:**" % nm, ""] + ["- " + x for x in a["reasons"]]
        L.append("")
    if v.get("more_reliable_evidence"):
        L += ["**Evidence quality:** %s" % v["more_reliable_evidence"]["note"], ""]
    p = v.get("plan")
    hold = (p or {}).get("holding") or ("same day, flat by 15:15" if rec["mode"] == "intraday" else "1-5 sessions")
    L += ["## 📊 4. FINAL TRADE REPORT", ""]
    if p:
        L += ["| Decision | Entry | Stop-loss | Target 1 | Target 2 | Net R:R at T1 | Qty | Max loss | Timeframe |",
              "|---|---|---|---|---|---|---|---|---|",
              "| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (badge, _money(p["entry"]), _money(p["stop"]), _money(p["target1"]),
                                                             _money(p["target2"]), p["net_rr_t1"], p["qty"], _money(p["max_loss_incl_costs"]), hold)]
    else:
        L += ["| Decision | Entry | Stop-loss | Targets | Timeframe |", "|---|---|---|---|---|",
              "| %s | none | none | none | %s |" % (badge, hold)]
    L += ["", "**Confidence (from tested history, not opinion):**", ""] + ["- " + x for x in _confidence(rec, v)]
    L += ["", "**What would change the decision:**", ""] + ["- " + x for x in v.get("what_would_change_it", [])]
    L += ["", "_Every evidence row is computed from the data shown, with its source and time; nothing is estimated or filled in. "
          "No profit or win rate is guaranteed. Record: `%s`._" % rec["id"]]
    return "\n".join(L)


def pick(records):
    """Choose ONE stock to present from several debates on the same mode: a BUY/SELL decision first, else the side with the most
    evidence that reproduced. Selection never changes a decision."""
    def key(rec):
        v = _msgs(rec, "JUDGE", "verdict")[0]["content"]
        kept = max(len(v.get("buyer_right", [])), len(v.get("seller_right", [])))
        return (v["decision"] in ("BUY", "SELL"), kept)
    return max(records, key=key) if records else None
