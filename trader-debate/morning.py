"""Morning pipeline (user choice 12 Nov 2026: scan the Nifty 500).

1. ORB scan of the whole universe (trader/universe.txt = Nifty 50 + Next 50 + Nifty 500 from NSE, ~495 EQ stocks), all candidates confirmed.
2. Day change of every hit as of the scan time (Yahoo 5-minute spark, bars that ended by then).
3. Drop hits already more than 2.5 % from the previous close (CLAUDE.md card rule 1) and list them separately.
4. Rank the rest by day change minus NIFTY's (strongest that has not yet run) and return the top N for debates.
A ranking only chooses which stocks get debated; the Judge decides.
"""
import datetime, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
import snapshot as S     # noqa: E402

MAX_MOVE = 2.5


def run_scan(at=None):
    if not os.path.exists(os.path.join(ROOT, "trader", "universe.txt")):        # NSE Nifty 50 + Next 50 + Nifty 500 lists
        subprocess.run([sys.executable, os.path.join(ROOT, "trader-scanner", "scan.py"), "universe"], cwd=ROOT, check=True,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    cmd = [sys.executable, os.path.join(ROOT, "trader-scanner", "scan.py"), "orb", "--or-minutes", "15", "--max-confirm", "600", "--show", "0"]
    if at:
        cmd += ["--at", at]
    subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    with open(os.path.join(ROOT, "trader", "watchlist.json"), encoding="utf-8") as fh:
        return json.load(fh)


def day_changes(symbols, cutoff_ist):
    """{sym: % change vs previous close} using 5-minute bars that ended by cutoff_ist."""
    out = {}
    for i in range(0, len(symbols), 20):
        chunk = symbols[i:i + 20]
        try:
            data = S.SC.parse_spark(S.SC.yahoo_get(S.SC.spark_path(chunk, "5d", "5m")))
        except Exception:
            continue
        for sym, s in data.items():
            rows = []
            for t, c in zip(s["t"], s["c"]):
                if c is None:
                    continue
                ts = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=t + 19800)
                if ts + datetime.timedelta(minutes=5) <= cutoff_ist:
                    rows.append((ts.date(), c))
            if rows:
                today = rows[-1][0]
                prev = [r for r in rows if r[0] < today]
                if prev and today == cutoff_ist.date():
                    out[sym] = 100 * (rows[-1][1] / prev[-1][1] - 1)
    return out


def candidates(at=None, top=5):
    now = S.ist_now()
    cutoff = now if not at else now.replace(hour=int(at.split(":")[0]), minute=int(at.split(":")[1]), second=0, microsecond=0)
    wl = run_scan(at)
    hits = [h["symbol"] for h in wl.get("hits", [])]
    ch = day_changes(hits, cutoff)
    try:
        nifty = S.index_5m(cutoff - datetime.timedelta(hours=5, minutes=30))
        npc = nifty["levels"].get("prev_close")
        nch = 100 * (nifty["price"] / npc - 1) if npc else 0.0
    except Exception:
        nch = 0.0
    moved = sorted(((s, c) for s, c in ch.items() if abs(c) > MAX_MOVE), key=lambda x: -x[1])
    ok = sorted(((s, c) for s, c in ch.items() if abs(c) <= MAX_MOVE), key=lambda x: -(x[1] - nch))
    return {"as_of": cutoff.isoformat(timespec="minutes"), "scanned": wl.get("scanned"), "hits": len(hits), "nifty_change_pct": round(nch, 2),
            "already_moved": [(s, round(c, 2)) for s, c in moved], "ranked": [(s, round(c, 2)) for s, c in ok],
            "top": [s for s, _ in ok[:top]]}
