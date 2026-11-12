"""Shared plan arithmetic for the debate agents: ticks, sizing from stop distance, costs, reward-to-risk.

Pure functions with no market opinion. Each agent decides its own levels; this module only does the arithmetic the same way for
everyone, so the Judge compares like with like.
"""
import importlib.util, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TICK = 0.05

CONFIG = {
    "capital": 200000,                  # hypothetical test account (user directive)
    "intraday": {"risk_inr": 500, "leverage": 5, "min_rr": 1.5, "max_stop_pct": 1.5, "t1_r": 1.5, "t2_r": 2.5,
                 "chase_pct": 0.1, "hold": "same day; square off by 15:15; stall exit if T1 not reached in 90 minutes"},
    "swing": {"risk_inr": 1500, "leverage": 1, "min_rr": 1.5, "max_stop_pct": 6.0, "t1_r": 1.5, "t2_r": 2.5,
              "chase_pct": 0.3, "hold": "1-5 sessions; time exit at the close of session 5"},
}


def _costs():
    spec = importlib.util.spec_from_file_location("costs", os.path.join(ROOT, "trader-budget", "costs.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


COSTS = _costs()


def tick(x, up=False):
    return round((math.ceil(x / TICK - 1e-9) if up else math.floor(x / TICK + 1e-9)) * TICK, 2)


def round_trip(mode, qty, buy, sell):
    if qty <= 0:
        return 0.0
    f = COSTS.intraday_costs if mode == "intraday" else COSTS.delivery_costs
    return f(qty, buy, sell)["charges"] + 2 * TICK * qty         # + one tick of slippage each side


def size(mode, direction, entry, stop):
    """Largest quantity whose loss at the stop plus costs and slippage stays within the mode's risk budget and buying power."""
    c = CONFIG[mode]
    per = abs(entry - stop)
    if per <= 0:
        return 0, 0.0
    cap = int(CONFIG["capital"] * c["leverage"] // entry)
    qty = min(cap, int(c["risk_inr"] // per))
    while qty > 0:
        buy, sell = (entry, stop) if direction == "long" else (stop, entry)
        loss = per * qty + round_trip(mode, qty, buy, sell)
        if loss <= c["risk_inr"]:
            return qty, round(loss, 2)
        qty -= max(1, qty // 50)
    return 0, 0.0


def build_plan(mode, direction, entry, stop, entry_kind, notes=()):
    """Entry/stop -> targets at fixed R multiples, size, costs, net reward-to-risk. direction: 'long' or 'short'."""
    c = CONFIG[mode]
    sgn = 1 if direction == "long" else -1
    r = abs(entry - stop)
    qty, max_loss = size(mode, direction, entry, stop)
    # Targets are set NET of costs: T1 pays t1_r x (loss at stop incl. costs) after its own costs; T2 likewise at t2_r.
    cps = round_trip(mode, qty, entry, entry) / qty if qty else 0.0
    t1 = tick(entry + sgn * (c["t1_r"] * r + (c["t1_r"] + 1) * cps), up=sgn > 0)
    t2 = tick(entry + sgn * (c["t2_r"] * r + (c["t2_r"] + 1) * cps), up=sgn > 0)
    net_t1 = net_t2 = None
    if qty:
        buy1, sell1 = (entry, t1) if sgn > 0 else (t1, entry)
        buy2, sell2 = (entry, t2) if sgn > 0 else (t2, entry)
        net_t1 = round(abs(t1 - entry) * qty - round_trip(mode, qty, buy1, sell1), 2)
        net_t2 = round(abs(t2 - entry) * qty - round_trip(mode, qty, buy2, sell2), 2)
    chase = tick(entry * (1 + sgn * c["chase_pct"] / 100), up=sgn > 0)
    return {"direction": direction, "entry": tick(entry, up=sgn > 0), "entry_kind": entry_kind,
            "do_not_enter_past": chase, "stop": tick(stop, up=sgn < 0), "target1": t1, "target2": t2,
            "risk_per_share": round(r, 2), "stop_pct": round(100 * r / entry, 2), "qty": qty,
            "position_value": round(qty * entry, 2), "max_loss_incl_costs": max_loss,
            "net_at_t1": net_t1, "net_at_t2": net_t2,
            "net_rr_t1": round(net_t1 / max_loss, 2) if qty and max_loss else None,
            "holding": c["hold"], "notes": list(notes)}


def plan_problems(mode, plan, day_high=None, day_low=None):
    """Arithmetic checks every plan must pass (the Judge re-runs them)."""
    c = CONFIG[mode]
    out = []
    if not plan["qty"]:
        out.append("position size is 0 within the Rs %d risk budget" % c["risk_inr"])
    if plan["stop_pct"] > c["max_stop_pct"]:
        out.append("stop %.2f%% away exceeds the %.1f%% maximum for %s" % (plan["stop_pct"], c["max_stop_pct"], mode))
    if plan["net_rr_t1"] is not None and plan["net_rr_t1"] < c["min_rr"] - 1e-9:
        out.append("net reward-to-risk at T1 %.2f is below %.1f after costs" % (plan["net_rr_t1"], c["min_rr"]))
    if mode == "intraday" and day_high is not None:
        if plan["direction"] == "long" and plan["target1"] > day_high:
            out.append("T1 %.2f is above today's high %.2f: needs a new high" % (plan["target1"], day_high))
        if plan["direction"] == "short" and plan["target1"] < day_low:
            out.append("T1 %.2f is below today's low %.2f: needs a new low" % (plan["target1"], day_low))
    return out


def val(snapshot, key):
    f = snapshot["fields"].get(key)
    return None if not f or f["class"] == "UNAVAILABLE" else f["value"]
