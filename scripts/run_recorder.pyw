"""Round 10 order-flow recorder launcher for Windows Task Scheduler (task "IndiaEquity_OrderFlowRecorder", weekdays 09:05).

Runs under pythonw.exe: no console window, so console close / Ctrl+C events (which killed the console-based launcher twice on
13 Nov 2026) cannot reach it. Output goes to trader/ticks_r10/_task.log. Read-only market data; never places orders.
"""
import datetime, os, signal, sys

ROOT = r"C:\Users\jeeva\claude-projects\india-equity-intraday-skill"
os.chdir(ROOT)
os.makedirs(os.path.join("trader", "ticks_r10"), exist_ok=True)
log = open(os.path.join("trader", "ticks_r10", "_task.log"), "a", encoding="utf-8", buffering=1)
sys.stdout = sys.stderr = log
signal.signal(signal.SIGINT, signal.SIG_IGN)
print("%s task start (pythonw)" % datetime.datetime.now().isoformat(timespec="seconds"))
sys.path.insert(0, os.path.join(ROOT, "trader-flows"))
import angel_recorder  # noqa: E402

SYMS = ["RELIANCE", "HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK", "INFY", "TCS", "HCLTECH", "LT", "M&M", "MARUTI",
        "BHARTIARTL", "ITC", "HINDUNILVR", "SUNPHARMA", "TATASTEEL", "BAJFINANCE", "BEL", "MCX", "ADANIENT", "NTPC", "TITAN", "ETERNAL", "BSE"]
try:
    code = angel_recorder.main(["record"] + SYMS + ["--out", os.path.join("trader", "ticks_r10")])
except SystemExit as e:
    code = e.code
except BaseException as e:
    import traceback
    traceback.print_exc()
    code = 1
print("%s task end (exit %s)" % (datetime.datetime.now().isoformat(timespec="seconds"), code))
