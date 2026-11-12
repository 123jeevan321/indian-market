"""Debate STEP 10: terminal view of a stored debate record. Everything shown is read from the record; nothing is written here.

Layout: header -> chronological TIMELINE (watch the debate) -> BUYER panel -> SELLER panel -> JUDGE panel.
`render(rec, columns=True)` puts the Buyer and Seller panels side by side when the terminal is wide enough.
"""
import os, shutil, textwrap

W = 110


def _box(title, lines, width=W):
    inner = width - 4
    out = ["+" + "-" * (width - 2) + "+", "| " + title.ljust(inner) + " |", "+" + "-" * (width - 2) + "+"]
    for ln in lines:
        indent = len(ln) - len(ln.lstrip())
        for i, piece in enumerate(textwrap.wrap(ln.strip(), inner - indent) or [""]):
            out.append("| " + (" " * indent + piece).ljust(inner) + " |")
    out.append("+" + "-" * (width - 2) + "+")
    return out


def _msgs(rec, agent=None, kind=None):
    return [m for m in rec["messages"] if (agent is None or m["agent"] == agent) and (kind is None or m["kind"] == kind)]


def _plan_lines(p):
    if not p:
        return ["  (no plan)"]
    if p["direction"] == "exit_long":
        return ["  %s" % p["entry_kind"], "  bearish view wrong above %.2f; downside a holder avoids: %.2f / %.2f" % (p["stop"], p["target1"], p["target2"])]
    side = "BUY" if p["direction"] == "long" else "SHORT"
    return ["  %s %s @ %.2f (do not enter past %.2f)" % (side, p["qty"], p["entry"], p["do_not_enter_past"]),
            "  entry: %s" % p["entry_kind"],
            "  stop %.2f (%.2f%%) | T1 %.2f | T2 %.2f" % (p["stop"], p["stop_pct"], p["target1"], p["target2"]),
            "  max loss incl. costs Rs %s | net at T1 Rs %s | net at T2 Rs %s | net R:R at T1 %s" % (
                p["max_loss_incl_costs"], p["net_at_t1"], p["net_at_t2"], p["net_rr_t1"]),
            "  holding: %s" % p["holding"]]


def _agent_panel(rec, agent):
    case = _msgs(rec, agent, "initial_case")[0]["content"]
    other = "SELLER" if agent == "BUYER" else "BUYER"
    got = _msgs(rec, other, "challenges")
    resp = _msgs(rec, agent, "responses")
    L = ["INITIAL ANALYSIS  (written before seeing the %s's case)" % other.lower(),
         "  stance: %s%s" % (case.get("stance"), "  | setup: %s" % case["setup"] if case.get("setup") else ""),]
    if case.get("reason") or case.get("error"):
        L.append("  reason: %s" % (case.get("reason") or case.get("error")))
    if case.get("sell_type"):
        L.append("  sell type: %s" % case["sell_type"])
    for k in ("weak_market_note", "hidden_weakness_note"):
        if case.get(k):
            L.append("  note: %s" % case[k])
    L.append("EVIDENCE CITED")
    L += ["  + %-10s %s  [needs: %s]" % (e["id"], e["observed"], e["threshold"]) for e in case.get("evidence_cited", [])] or ["  (none)"]
    against = case.get("evidence_against", [])
    if against:
        L.append("EVIDENCE AGAINST (own side, reported honestly)")
        L += ["  - %-10s %-5s %s" % (e["id"], e["status"], e.get("observed", "")) for e in against]
    if case.get("unavailable"):
        L.append("UNAVAILABLE: " + ", ".join(case["unavailable"]))
    L.append("PROPOSED ENTRY AND EXIT")
    L += _plan_lines(case.get("plan"))
    if case.get("plan_problems"):
        L += ["  ! " + x for x in case["plan_problems"]]
    if case.get("invalidation"):
        L.append("INVALIDATED IF")
        L += ["  - " + x for x in case["invalidation"]]
    if case.get("confidence"):
        c = case["confidence"]
        L.append("CONFIDENCE (historical, not opinion): %s | validated out of sample: %s" % (c["setup_reference"], c["validated_out_of_sample"]))
    L.append("CHALLENGES RECEIVED FROM %s" % other)
    chs = got[0]["content"] if got else []
    L += ["  [%s]%s %s" % (c["id"], " FATAL" if c.get("fatal") else "", c["text"]) for c in (chs if isinstance(chs, list) else [])] or ["  (none)"]
    L.append("FINAL RESPONSE")
    rs = resp[0]["content"] if resp else []
    L += ["  -> %s: %s%s" % (r["to"], "CONCEDED. " if r["concede"] else "", r["text"]) for r in (rs if isinstance(rs, list) else [])] or ["  (none)"]
    return _box("%s AGENT  %s" % (agent, case.get("version", "")), L)


def _judge_panel(rec):
    v = _msgs(rec, "JUDGE", "verdict")[0]["content"]
    L = ["DECISION: %s" % v["decision"], "  why: %s" % v["why"]]
    if v.get("plan"):
        L.append("ENTRY, STOP, TARGETS")
        L += _plan_lines(v["plan"])
    for side in ("buyer", "seller"):
        a = v.get(side + "_assessment") or {}
        L.append("%s'S STRONGEST VERIFIED POINTS" % side.upper())
        L += ["  + %s" % x for x in v.get(side + "_right", [])[:5]] or ["  (none reproduce)"]
        if a.get("struck"):
            L.append("  struck out (did not reproduce):")
            L += ["    x %s: %s" % (s["id"], s["why"]) for s in a["struck"]]
    L.append("EVIDENCE RELIABILITY")
    r = v.get("more_reliable_evidence") or {}
    if r:
        L.append("  buyer: %s reproducing items, %s with a measured edge | seller: %s reproducing, %s with a measured edge" % (
            r["buyer_reproducing_items"], r["buyer_items_with_measured_edge"], r["seller_reproducing_items"], r["seller_items_with_measured_edge"]))
        L.append("  " + r["note"])
    L.append("REJECTED ARGUMENTS")
    for ra in v.get("rejected_arguments", []):
        L.append("  %s side:" % ra["side"])
        L += ["    - " + x for x in ra["reasons"]]
    L.append("WHAT WOULD CHANGE THE DECISION")
    L += ["  - " + x for x in v.get("what_would_change_it", [])]
    return _box("JUDGE  %s" % v.get("version", ""), L)


def _summary(m):
    c = m["content"]
    if m["kind"] == "snapshot":
        return "snapshot %s; unavailable: %s" % (c["hash"], ", ".join(c.get("unavailable") or []) or "none")
    if m["kind"] == "initial_case":
        return "%s: %d items cited%s" % (c.get("stance"), len(c.get("evidence_cited", [])),
                                         ", entry %.2f stop %.2f" % (c["plan"]["entry"], c["plan"]["stop"]) if c.get("plan") else "")
    if m["kind"] == "challenges":
        if isinstance(c, dict):
            return "ERROR " + c.get("error", "")[:80]
        return "%d challenge(s), %d fatal: %s" % (len(c), sum(1 for x in c if x.get("fatal")), ", ".join(x["id"] for x in c))
    if m["kind"] == "responses":
        if isinstance(c, dict):
            return "ERROR " + c.get("error", "")[:80]
        return "%d answered, %d conceded" % (len(c), sum(1 for x in c if x["concede"]))
    if m["kind"] == "verdict":
        return "%s - %s" % (c["decision"], c["why"])
    return str(c)[:90]


def render(rec, columns=False):
    width = shutil.get_terminal_size((W, 40)).columns
    head = ["=" * W, "DEBATE %s | %s %s | snapshot %s IST | PAPER ONLY%s" % (
        rec["id"], rec["mode"].upper(), rec["symbol"], rec["snapshot"]["snapshot_time_ist"],
        " | reassesses %s" % rec["reassesses"] if rec.get("reassesses") else ""),
        "engines: " + ", ".join("%s=%s" % kv for kv in rec["engines"].items()), "=" * W, "TIMELINE"]
    head += ["  %s  step %-2s %-7s %s" % (m["t"][11:23], m["step"], m["agent"], _summary(m)) for m in rec["messages"]]
    b, s = _agent_panel(rec, "BUYER"), _agent_panel(rec, "SELLER")
    if columns and width >= 2 * W + 2:
        n = max(len(b), len(s))
        b += [" " * W] * (n - len(b)); s += [" " * W] * (n - len(s))
        body = [x + "  " + y for x, y in zip(b, s)]
    else:
        body = b + s
    return "\n".join(head + [""] + body + _judge_panel(rec))


def history_table(records):
    rows = ["%-19s %-12s %-8s %-9s %-13s %-13s %s" % ("snapshot (IST)", "symbol", "mode", "decision", "buyer", "seller", "record")]
    for path, r in records:
        cases = {m["agent"]: m["content"].get("stance") for m in r["messages"] if m["kind"] == "initial_case"}
        rows.append("%-19s %-12s %-8s %-9s %-13s %-13s %s" % (r["snapshot"]["snapshot_time_ist"][:19], r["symbol"], r["mode"],
                                                            r.get("decision"), cases.get("BUYER"), cases.get("SELLER"),
                                                            os.path.relpath(path)))
    return "\n".join(rows)
