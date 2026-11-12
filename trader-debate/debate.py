#!/usr/bin/env python3
"""Debate orchestrator: STEPS 1-10 in order, every message timestamped and stored. Paper mode only.

    python trader-debate/debate.py run intraday BAJFINANCE [--now "2026-11-12 10:35"] [--no-angel]
    python trader-debate/debate.py run swing BHEL
    python trader-debate/debate.py show trader/debates/2026-11-12/<file>.json

Records go to trader/debates/YYYY-MM-DD/ (git-ignored) and are never edited after they are written; a reassessment is a new record
that names the earlier one in "reassesses".
"""
import argparse, concurrent.futures as cf, copy, datetime, json, os, sys, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import buyer, seller, judge, snapshot as SNAP     # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "trader", "debates")
TIMEOUT_S = 60


def now_ist():
    return SNAP.ist_now().isoformat(timespec="milliseconds")


def guarded(fn, agent, *args):
    """Run one agent step with a timeout. A failure or timeout becomes an explicit AGENT FAILED record, never a signal."""
    with cf.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(fn, *args)
        try:
            return fut.result(timeout=TIMEOUT_S), None
        except cf.TimeoutError:
            return None, "%s timed out after %d s" % (agent, TIMEOUT_S)
        except Exception as e:
            return None, "%s raised %s: %s" % (agent, type(e).__name__, str(e)[:200]) + "\n" + traceback.format_exc(limit=3)


def run(snapshot, state=None, stats=None, reassesses=None):
    rec = {"id": "%s-%s-%s" % (snapshot["symbol"], snapshot["snapshot_time_ist"].replace(":", "").replace("-", ""), snapshot["hash"]),
           "mode": snapshot["mode"], "symbol": snapshot["symbol"], "paper_only": True, "reassesses": reassesses,
           "engines": {"snapshot": SNAP.VERSION, "buyer": buyer.VERSION, "seller": seller.VERSION, "judge": judge.VERSION,
                       "llm": None},
           "snapshot": snapshot, "messages": []}

    def say(step, agent, kind, content):
        rec["messages"].append({"t": now_ist(), "step": step, "agent": agent, "kind": kind, "snapshot_hash": snapshot["hash"],
                                "content": content})

    say(1, "SYSTEM", "snapshot", {"hash": snapshot["hash"], "unavailable": snapshot.get("unavailable")})
    # STEPS 2-3: independent first opinions. Each agent gets its own deep copy; neither sees the other's case.
    bcase, err_b = guarded(buyer.analyse, "BUYER", copy.deepcopy(snapshot))
    if err_b:
        bcase = {"agent": "BUYER", "stance": "AGENT FAILED", "error": err_b, "evidence_cited": []}
    say(2, "BUYER", "initial_case", bcase)
    scase, err_s = guarded(seller.analyse, "SELLER", copy.deepcopy(snapshot))
    if err_s:
        scase = {"agent": "SELLER", "stance": "AGENT FAILED", "error": err_s, "evidence_cited": []}
    say(3, "SELLER", "initial_case", scase)
    # STEP 4 is the display of both initial cases (render). STEPS 5-6: challenges.
    bch, e1 = guarded(buyer.challenge, "BUYER", bcase, scase, snapshot) if not err_b else ([], None)
    say(5, "BUYER", "challenges", bch if not e1 else {"error": e1})
    sch, e2 = guarded(seller.challenge, "SELLER", scase, bcase, snapshot) if not err_s else ([], None)
    say(6, "SELLER", "challenges", sch if not e2 else {"error": e2})
    # STEP 7: responses to the challenges received.
    bresp, e3 = guarded(buyer.respond, "BUYER", bcase, sch or [], snapshot) if not err_b else ([], None)
    say(7, "BUYER", "responses", bresp if not e3 else {"error": e3})
    sresp, e4 = guarded(seller.respond, "SELLER", scase, bch or [], snapshot) if not err_s else ([], None)
    say(7, "SELLER", "responses", sresp if not e4 else {"error": e4})
    if any((e1, e2, e3, e4)):
        for c, e in ((bcase, e1 or e3), (scase, e2 or e4)):
            if e:
                c["stance"], c["error"] = "AGENT FAILED", e
    # STEPS 8-9: the Judge.
    verdict, ej = guarded(judge.decide, "JUDGE", snapshot, bcase, scase, bch or [], sch or [], bresp or [], sresp or [], stats, state)
    if ej:
        verdict = {"agent": "JUDGE", "decision": "NO TRADE", "why": "judge failed: " + ej}
    say(9, "JUDGE", "verdict", verdict)
    rec["decision"] = verdict["decision"]
    return rec


def save(rec):
    day = rec["snapshot"]["snapshot_time_ist"][:10]
    folder = os.path.join(OUT, day)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, rec["id"] + ".json")
    if os.path.exists(path):                       # append-only: never overwrite an earlier record
        path = path[:-5] + "-%s.json" % datetime.datetime.now().strftime("%H%M%S%f")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1, default=str)
    return path


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("mode", choices=["intraday", "swing"]); r.add_argument("symbol")
    r.add_argument("--now"); r.add_argument("--no-angel", action="store_true"); r.add_argument("--state")
    s = sub.add_parser("show"); s.add_argument("path")
    a = p.parse_args(argv)
    if a.cmd == "show":
        with open(a.path, encoding="utf-8") as fh:
            rec = json.load(fh)
    else:
        sym = a.symbol.upper()
        if a.mode == "intraday":
            snap = SNAP.intraday(sym, datetime.datetime.strptime(a.now, "%Y-%m-%d %H:%M") if a.now else None, use_angel=not a.no_angel)
        else:
            snap = SNAP.swing(sym, datetime.date.fromisoformat(a.now[:10]) if a.now else None)
        state = json.load(open(a.state, encoding="utf-8")) if a.state else None
        rec = run(snap, state=state)
        print("saved", save(rec))
    try:
        import render
        print(render.render(rec))
    except ImportError:
        v = rec["messages"][-1]["content"]
        print("%s %s %s -> %s: %s" % (rec["mode"], rec["symbol"], rec["snapshot"]["snapshot_time_ist"], v["decision"], v["why"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
