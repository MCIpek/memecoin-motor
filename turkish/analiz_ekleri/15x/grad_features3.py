"""Capture-health per day, then rules on healthy days with realistic loser valuation (current curve price). Read-only."""
import json, sqlite3, statistics, datetime
from collections import defaultdict, Counter
G = r"C:/Users/PD/AppData/Local/Temp/claude/C--Users-PD-project-claude-memecoin/5a0f1dfe-1637-4fac-95a3-1703257554c2/scratchpad/gecko/"
DB = r"C:\Users\PD\project_claude\memecoin\data\memecoin_motor.db"
LAUNCH_PRICE = 30 / 1.073e9; GRAD_PRICE = LAUNCH_PRICE * (115/30)**2; FEE = 0.03
C = {json.loads(l)["mint"]: json.loads(l) for l in open(G + "curves.jsonl")}
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True); con.row_factory = sqlite3.Row
L = {r["mint"]: dict(r) for r in con.execute("SELECT mint,symbol,event_timestamp,is_mayhem_mode,creator,quote_asset FROM pump_launches")}
cn = {}
for _m, _v in sorted(L.items(), key=lambda kv: kv[1]["event_timestamp"]):
    cn[_m] = sum(1 for __ in [0]) and 0
_seen = Counter()
for _m, _v in sorted(L.items(), key=lambda kv: (kv[1]["event_timestamp"], kv[0])):
    cn[_m] = _seen[_v["creator"]]; _seen[_v["creator"]] += 1
TR = {r["mint"]: r["n"] for r in con.execute("SELECT mint, SUM(buy_count+sell_count) n FROM wallet_positions GROUP BY mint")}
S = defaultdict(dict)
for r in con.execute("SELECT mint,target_age_seconds a,trade_count,unique_buyers,net_quote_flow,top_buyer_share,creator_sold,price_quote_per_token,snapshot_quality FROM token_snapshots WHERE target_age_seconds IN (10,30,60)"):
    S[r["mint"]][r["a"]] = dict(r)
D = {r["mint"]: r["decision"] for r in con.execute("SELECT mint,decision FROM risk_decisions WHERE snapshot_age_seconds=60")}
early = {r[0] for r in con.execute("SELECT DISTINCT mint FROM pump_trades WHERE virtual_sol_reserves>=115000000000")}
buy2 = {r["mint"]: r["b"] for r in con.execute("SELECT t.mint, SUM(CASE WHEN t.event_timestamp-l.event_timestamp<=2 AND t.is_buy=1 THEN t.sol_amount ELSE 0 END) b FROM pump_trades t JOIN pump_launches l ON l.mint=t.mint WHERE t.event_timestamp-l.event_timestamp<=2 GROUP BY t.mint")}
day = lambda m: datetime.datetime.utcfromtimestamp(L[m]["event_timestamp"]).strftime("%Y-%m-%d")

print("== capture health by day (SOL, non-mayhem): launches, trades/launch, share with >=1 trade, share with 60s ub>=6 ==")
byday = defaultdict(list)
for m in C:
    if L[m]["quote_asset"] == "SOL" and not L[m]["is_mayhem_mode"]: byday[day(m)].append(m)
healthy = set()
for d in sorted(byday):
    ms = byday[d]; n = len(ms); tpl = sum(TR.get(m, 0) for m in ms)/n; w1 = sum(1 for m in ms if TR.get(m, 0) > 0)/n*100
    ub6 = sum(1 for m in ms if S[m].get(60) and S[m][60]["unique_buyers"] >= 6)/n*100
    if tpl >= 20: healthy.add(d)
    print(f"  {d}  n={n:5d}  trades/launch {tpl:6.1f}  >=1 trade {w1:5.1f}%  ub60>=6 {ub6:5.1f}%  grad {sum(1 for m in ms if C[m]['complete'])/n*100:.2f}%  {'HEALTHY' if tpl>=20 else 'DEGRADED'}")
print("healthy days:", sorted(healthy))

rows = []
for m, c in C.items():
    l = L[m]
    if l["quote_asset"] != "SOL" or l["is_mayhem_mode"] or day(m) not in healthy or not S[m].get(60): continue
    s = S[m][60]; p60 = s["price_quote_per_token"]
    if not p60: continue
    now_p = (c["vq"]/c["vt"]) / 1e9 * 1e6 if c["vt"] else None   # SOL per token now (curve), None if complete
    rows.append({"mint": m, "day": day(m), "grad": bool(c["complete"]), "grad_early": m in early and bool(c["complete"]),
                 "ub": s["unique_buyers"], "flow": s["net_quote_flow"]/1e9, "top": s["top_buyer_share"], "csold": s["creator_sold"],
                 "cn": cn[m], "d60": D.get(m), "p60": p60, "x60_launch": p60/LAUNCH_PRICE, "now_x": (now_p/p60) if now_p else None,
                 "buy2": buy2.get(m, 0)/1e9, "q": s["snapshot_quality"]})
print(f"\nrows on healthy days with 60s price: {len(rows)}  grad {sum(r['grad'] for r in rows)/len(rows)*100:.2f}%  grad>600s {sum(1 for r in rows if r['grad'] and not r['grad_early'])/len(rows)*100:.2f}%")
nx = [r["now_x"] for r in rows if r["now_x"] is not None]
print(f"non-graduates: value NOW vs 60s entry price: median {statistics.median(nx):.3f}  mean {statistics.mean(nx):.3f}  >=1 {sum(1 for v in nx if v>=1)/len(nx)*100:.1f}%  <=0.5 {sum(1 for v in nx if v<=.5)/len(nx)*100:.1f}%")
print(f"60s price vs launch (how much already up at entry): median {statistics.median([r['x60_launch'] for r in rows]):.3f}  p90 {sorted([r['x60_launch'] for r in rows])[int(len(rows)*.9)]:.2f}")

def ev(sel, grad_mult=None):
    vals = []
    for r in sel:
        if r["grad"] and not r["grad_early"]:
            vals.append((grad_mult if grad_mult else GRAD_PRICE/r["p60"])*(1-FEE) - 1)
        elif r["grad_early"]:
            vals.append(-FEE)                       # bought at/near full curve, assume flat
        else:
            vals.append(r["now_x"]*(1-FEE) - 1 if r["now_x"] is not None else -1)
    return statistics.mean(vals)*100 if vals else float("nan")

rules = {
 "ALL (buy everything)": lambda r: True,
 "prior launches==0": lambda r: r["cn"]==0,
 "prior==0 & !csold": lambda r: r["cn"]==0 and not r["csold"],
 "prior==0 & ub>=6 & flow>=1": lambda r: r["cn"]==0 and r["ub"]>=6 and r["flow"]>=1,
 "prior==0 & ub>=11 & flow>=3 & top<0.5": lambda r: r["cn"]==0 and r["ub"]>=11 and r["flow"]>=3 and r["top"]<.5,
 "ub>=21 & flow>=5": lambda r: r["ub"]>=21 and r["flow"]>=5,
 "ub>=51": lambda r: r["ub"]>=51,
 "flow>=15 & not full yet (x60<10)": lambda r: r["flow"]>=15 and r["x60_launch"]<10,
 "flow 5-40 & prior==0 & top<0.4": lambda r: 5<=r["flow"]<40 and r["cn"]==0 and r["top"]<.4,
 "d60==ADAY": lambda r: r["d60"]=="ADAY",
 "d60==ADAY & prior==0": lambda r: r["d60"]=="ADAY" and r["cn"]==0,
 "buy2s>=20 SOL (bundle launch)": lambda r: r["buy2"]>=20,
 "x60<1.5 & ub>=6 & prior==0": lambda r: r["x60_launch"]<1.5 and r["ub"]>=6 and r["cn"]==0,
}
train = [r for r in rows if r["day"] <= "2026-09-09"]; test = [r for r in rows if r["day"] >= "2026-09-15"]
print(f"\n== rules: train = healthy days <=09-09 (n={len(train)}, grad>600s {sum(1 for r in train if r['grad'] and not r['grad_early'])/len(train)*100:.2f}%), test = healthy days >=09-15 (n={len(test)}, grad>600s {sum(1 for r in test if r['grad'] and not r['grad_early'])/len(test)*100:.2f}%) ==")
print("EV = buy at 60s price; graduates(>600s) sold at curve-full price; non-graduates valued at CURRENT curve price (weeks later); 3% costs. EV_x3 = same but graduates sold at 3x curve-full price (optimistic PumpSwap run).")
for name, fn in rules.items():
    line = f"  {name:36s}"
    for lab, sub in (("train", train), ("test", test)):
        sel = [r for r in sub if fn(r)]; n = len(sel)
        if n == 0: line += f" | {lab}: 0"; continue
        gl = sum(1 for r in sel if r["grad"] and not r["grad_early"]); ge = sum(1 for r in sel if r["grad_early"])
        base = sum(1 for r in sub if r["grad"] and not r["grad_early"])/len(sub)
        line += f" | {lab}: n={n:5d} grad>600s {gl:3d} ({gl/n*100:5.2f}%, lift {gl/n/max(base,1e-9):4.1f}x) full@60s {ge:3d}  EV {ev(sel):+5.0f}%  EV_x3 {ev(sel, None) if False else ev_x3(sel) if False else 0:+.0f}%" if False else f" | {lab}: n={n:5d} grad>600s {gl:3d} ({gl/n*100:5.2f}%, lift {gl/n/max(base,1e-9):4.1f}x) full@60s {ge:3d}  EV {ev(sel):+5.0f}%"
    print(line)
# Optimistic variant: graduates sold at 3x of curve-full price
print("\n== same rules, graduates sold at 3x curve-full price (optimistic; real ATH pending from GeckoTerminal) ==")
def ev3(sel):
    vals = []
    for r in sel:
        if r["grad"] and not r["grad_early"]: vals.append(3*GRAD_PRICE/r["p60"]*(1-FEE) - 1)
        elif r["grad_early"]: vals.append(2*(1-FEE) - 1)
        else: vals.append(r["now_x"]*(1-FEE) - 1 if r["now_x"] is not None else -1)
    return statistics.mean(vals)*100 if vals else float("nan")
for name, fn in rules.items():
    print(f"  {name:36s} train EV {ev3([r for r in train if fn(r)]):+5.0f}%   test EV {ev3([r for r in test if fn(r)]):+5.0f}%")
