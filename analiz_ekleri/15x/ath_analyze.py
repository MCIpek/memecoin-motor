"""Post-graduation ATH (GeckoTerminal day candles, SOL price) joined with on-chain state and 60s features. Read-only."""
import json, sqlite3, statistics, datetime, random
from collections import defaultdict, Counter
G = r"C:/Users/PD/AppData/Local/Temp/claude/C--Users-PD-project-claude-memecoin/5a0f1dfe-1637-4fac-95a3-1703257554c2/scratchpad/gecko/"
DB = r"C:\Users\PD\project_claude\memecoin\data\memecoin_motor.db"
LAUNCH_PRICE = 30 / 1.073e9; GRAD_PRICE = LAUNCH_PRICE * (115/30)**2; FEE = 0.03
ATH = {}
for l in open(G + "ath_graduated.jsonl", encoding="utf-8"):
    r = json.loads(l)
    lst = r.get("ohlcv") or []
    if lst:
        # robust ATH: trim wicks beyond 3x the candle body top; conservative: max daily close
        r["ath_robust"] = max(min(c[2], 3*max(c[1], c[4])) for c in lst)
        r["ath_close"] = max(c[4] for c in lst)
        r["ath_raw"] = r["ath_sol"]; r["ath_sol"] = r["ath_robust"]
        r["days_traded"] = len(lst)
    ATH[r["mint"]] = r
GT = {json.loads(l)["mint"]: json.loads(l) for l in open(G + "grad_tokens.jsonl", encoding="utf-8")}
C = {json.loads(l)["mint"]: json.loads(l) for l in open(G + "curves.jsonl")}
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True); con.row_factory = sqlite3.Row
L = {r["mint"]: dict(r) for r in con.execute("SELECT mint,symbol,event_timestamp,is_mayhem_mode,creator,quote_asset FROM pump_launches")}
S60 = {r["mint"]: dict(r) for r in con.execute("SELECT mint,unique_buyers,net_quote_flow,top_buyer_share,creator_sold,price_quote_per_token,snapshot_quality FROM token_snapshots WHERE target_age_seconds=60")}
D60 = {r["mint"]: r["decision"] for r in con.execute("SELECT mint,decision FROM risk_decisions WHERE snapshot_age_seconds=60")}
import os
if os.path.exists(G + "early.json"): early = set(json.load(open(G + "early.json")))
else:
    early = {r[0] for r in con.execute("SELECT DISTINCT mint FROM pump_trades WHERE virtual_sol_reserves>=115000000000")}
    json.dump(sorted(early), open(G + "early.json", "w"))
_seen = Counter(); PRIOR = {}
for m, v in sorted(L.items(), key=lambda kv: (kv[1]["event_timestamp"], kv[0])): PRIOR[m] = _seen[v["creator"]]; _seen[v["creator"]] += 1
day = lambda m: datetime.datetime.utcfromtimestamp(L[m]["event_timestamp"]).strftime("%Y-%m-%d")
HEALTHY = {"2026-09-01","2026-09-03","2026-09-04","2026-09-07","2026-09-08","2026-09-09","2026-09-15","2026-09-16","2026-09-17"}

rows = []
for m, a in ATH.items():
    l = L[m]
    if l["quote_asset"] != "SOL": continue
    rec = {"mint": m, "sym": l["symbol"], "mayhem": bool(l["is_mayhem_mode"]), "instant": m in early, "candles": a.get("candles", 0), "ath_close": a.get("ath_close"), "ath_raw": a.get("ath_raw"),
           "ath": a.get("ath_sol"), "last": a.get("last_close_sol"), "first_open": a.get("first_open_sol"), "first_high": a.get("first_high_sol"),
           "ath_ts": a.get("ath_ts"), "first_ts": a.get("first_ts"), "day": day(m), "prior": PRIOR[m], "d60": D60.get(m), "s60": S60.get(m)}
    ct = GT.get(m, {}).get("completed_at")
    rec["t_grad_h"] = ((datetime.datetime.fromisoformat(ct.replace("Z", "+00:00")).timestamp() - l["event_timestamp"]) / 3600) if ct else None
    if rec["ath"]:
        rec["x_launch"] = rec["ath"] / LAUNCH_PRICE; rec["x_grad"] = rec["ath"] / GRAD_PRICE
        rec["x_first_open"] = rec["ath"] / rec["first_open"] if rec.get("first_open") else None
        rec["ret"] = rec["last"] / rec["ath"] if rec.get("last") else None
        rec["x60"] = rec["ath"] / rec["s60"]["price_quote_per_token"] if rec["s60"] and rec["s60"]["price_quote_per_token"] else None
    rows.append(rec)
ok = [r for r in rows if r.get("ath")]
print(f"ATH rows fetched {len(rows)}  with candles {len(ok)}  (no candles: {len(rows)-len(ok)})  mayhem {sum(r['mayhem'] for r in ok)}  instant-fill {sum(r['instant'] for r in ok)}")
def pct(v, p):
    v = sorted(v); k = (len(v)-1)*p; f = int(k); c = min(f+1, len(v)-1); return v[f] + (v[c]-v[f])*(k-f)
def dist(label, vals, thrs):
    if not vals: print(f"  {label}: n=0"); return
    print(f"  {label}: n={len(vals)} median {statistics.median(vals):.2f} p75 {pct(vals,.75):.2f} p90 {pct(vals,.9):.2f} max {max(vals):.0f} | " + " ".join(f">={t}x {sum(1 for v in vals if v>=t)/len(vals)*100:.1f}%" for t in thrs))

for label, sub in (("ALL graduated", ok), ("non-mayhem", [r for r in ok if not r["mayhem"]]), ("non-mayhem, graduated AFTER 600s (reachable)", [r for r in ok if not r["mayhem"] and not r["instant"]]), ("non-mayhem, instant/early fill", [r for r in ok if not r["mayhem"] and r["instant"]]), ("mayhem", [r for r in ok if r["mayhem"]])):
    print(f"\n== {label} ==")
    dist("ATH X from LAUNCH price", [r["x_launch"] for r in sub], (15, 30, 50, 100, 300, 1000))
    dist("ATH X from GRADUATION price (PumpSwap run, robust)", [r["x_grad"] for r in sub], (1.5, 2, 3, 5, 10, 30))
    dist("  same, CONSERVATIVE (max daily close)", [r["ath_close"]/GRAD_PRICE for r in sub if r.get("ath_close")], (1.5, 2, 3, 5, 10, 30))
    dist("  same, RAW daily high (wick-prone)", [r["ath_raw"]/GRAD_PRICE for r in sub if r.get("ath_raw")], (1.5, 2, 3, 5, 10, 30))
    dist("ATH X from first PumpSwap day OPEN", [r["x_first_open"] for r in sub if r.get("x_first_open")], (1.5, 2, 3, 5, 10))
    x60 = [r["x60"] for r in sub if r.get("x60")]
    dist("ATH X from 60s entry price (where 60s snapshot exists)", x60, (5, 10, 15, 30, 50, 100))
    ret = [r["ret"] for r in sub if r.get("ret") is not None]
    if ret: print(f"  retained now (last close / ATH): median {statistics.median(ret)*100:.1f}%  >=50% {sum(1 for v in ret if v>=.5)/len(ret)*100:.1f}%  <=10% {sum(1 for v in ret if v<=.1)/len(ret)*100:.1f}%")
    lx = [r["last"]/LAUNCH_PRICE for r in sub if r.get("last")]
    if lx: print(f"  price NOW vs launch: median {statistics.median(lx):.2f}x  >=15x now {sum(1 for v in lx if v>=15)/len(lx)*100:.1f}%  <1x now {sum(1 for v in lx if v<1)/len(lx)*100:.1f}%")
    tg = [r["t_grad_h"] for r in sub if r.get("t_grad_h") is not None]
    if tg: print(f"  time to graduation (h): median {statistics.median(tg):.2f}  p90 {pct(tg,.9):.1f}  >24h {sum(1 for v in tg if v>24)/len(tg)*100:.1f}%")
    at = [(r["ath_ts"] - r["first_ts"])/3600 for r in sub if r.get("ath_ts") and r.get("first_ts")]
    if at: print(f"  ATH day minus first PumpSwap day (h): median {statistics.median(at):.0f}  same day {sum(1 for v in at if v==0)/len(at)*100:.1f}%")

print("\n== top 25 by ATH X from launch (non-mayhem) ==")
for r in sorted([r for r in ok if not r["mayhem"]], key=lambda r: -r["x_launch"])[:25]:
    s = r["s60"] or {}
    print(f"  {r['sym'][:12]:12s} {r['mint'][:6]}… x_launch {r['x_launch']:7.0f} x_grad {r['x_grad']:6.1f} x60 {r.get('x60') or 0:7.0f} instant={int(r['instant'])} t_grad {r['t_grad_h'] if r['t_grad_h'] is None else round(r['t_grad_h'],1)}h ret {((r.get('ret') or 0)*100):5.1f}% ub60={s.get('unique_buyers')} flow60={(s.get('net_quote_flow') or 0)/1e9:.1f} top60={s.get('top_buyer_share') or 0:.2f} d60={r['d60']} prior={r['prior']} day={r['day']}")

# ---- EV with real ATH: healthy days, non-mayhem, 60s entry; staged exit: 40% @2x of grad price, 30% @3x, 30% @ min(ATH*0.5, last)… keep simple & explicit
print("\n== EV with REAL post-graduation prices (healthy days, non-mayhem, 60s snapshot). Non-graduates valued at current curve price. ==")
NG = {}
for m, c in C.items():
    l = L[m]
    if l["quote_asset"] != "SOL" or l["is_mayhem_mode"] or day(m) not in HEALTHY or m not in S60 or not S60[m]["price_quote_per_token"]: continue
    p60 = S60[m]["price_quote_per_token"]
    now_p = (c["vq"]/c["vt"]) / 1e9 * 1e6 if c["vt"] else None
    NG[m] = {"p60": p60, "grad": bool(c["complete"]), "instant": m in early, "now_x": (now_p/p60) if now_p else None, "s": S60[m], "prior": PRIOR[m], "d60": D60.get(m), "day": day(m),
             "ath": ATH.get(m, {}).get("ath_sol"), "last": ATH.get(m, {}).get("last_close_sol"), "buy2": 0}
print(f"universe {len(NG)}  graduated {sum(1 for v in NG.values() if v['grad'])}  of which with ATH data {sum(1 for v in NG.values() if v['grad'] and v['ath'])}")

def payoff(v):
    """(A, B, C) multiples of entry for a GRADUATED position with ATH data. instant-fill: manipulated pools -> hold-to-today only for A/B, cap C at 2x."""
    p = v["p60"]; ath = v["ath"]/p; last = (v["last"] or 0)/p; g = GRAD_PRICE/p
    if v["instant"]:
        return last, last, min(ath, 2.0)*0.5 if ath > 1 else last
    a = g
    b = (0.5*2*g + 0.5*last) if ath >= 2*g else (0.5*g + 0.5*last)
    c = 0.5*ath
    return a, b, c
def ev_cond(sel):
    """Conditional expectation: P(non-grad)*E[now_x] + P(grad,reachable)*E[payoff | sampled] + P(grad,instant)*E[payoff | sampled]."""
    n = len(sel); ng = [v for v in sel if not v["grad"]]
    gr = [v for v in sel if v["grad"] and not v["instant"]]; gi = [v for v in sel if v["grad"] and v["instant"]]
    out = []
    for pol in range(3):
        e_ng = statistics.mean([(v["now_x"] if v["now_x"] is not None else 0) for v in ng]) if ng else 0
        sr = [payoff(v)[pol] for v in gr if v["ath"]]; si = [payoff(v)[pol] for v in gi if v["ath"]]
        e_gr = statistics.mean(sr) if sr else 0.2*statistics.mean([GRAD_PRICE/v["p60"] for v in gr]) if gr else 0
        e_gi = statistics.mean(si) if si else 0.3
        ev = (len(ng)/n)*e_ng + (len(gr)/n)*e_gr + (len(gi)/n)*e_gi
        out.append(((ev*(1-FEE)) - 1)*100)
    return out, len(gr), sum(1 for v in gr if v["ath"]), len(gi), sum(1 for v in gi if v["ath"])
F = lambda v: (v["s"]["unique_buyers"], v["s"]["net_quote_flow"]/1e9, v["s"]["top_buyer_share"], v["s"]["creator_sold"], v["prior"], v["p60"]/LAUNCH_PRICE)
rules = {
 "ALL": lambda v: True,
 "prior==0": lambda v: F(v)[4]==0,
 "prior==0 & ub>=6 & flow>=1": lambda v: F(v)[4]==0 and F(v)[0]>=6 and F(v)[1]>=1,
 "prior==0 & ub>=11 & flow>=3 & top<0.5": lambda v: F(v)[4]==0 and F(v)[0]>=11 and F(v)[1]>=3 and F(v)[2]<.5,
 "ub>=21 & flow>=5": lambda v: F(v)[0]>=21 and F(v)[1]>=5,
 "ub>=51": lambda v: F(v)[0]>=51,
 "flow>=15 & x60<10 (not full)": lambda v: F(v)[1]>=15 and F(v)[5]<10,
 "flow 15-40 & x60<10": lambda v: 15<=F(v)[1]<40 and F(v)[5]<10,
 "d60==ADAY": lambda v: v["d60"]=="ADAY",
 "d60==ADAY & prior==0": lambda v: v["d60"]=="ADAY" and F(v)[4]==0,
 "x60<1.5 & ub>=6 & prior==0 (cheap entry)": lambda v: F(v)[5]<1.5 and F(v)[0]>=6 and F(v)[4]==0,
 "x60>=10 (already full at 60s)": lambda v: F(v)[5]>=10,
}
ALLH = NG
print("policies: A = sell at graduation price (instant-fill: hold to today) | B = half at 2x grad price if reached, half to today | C = capture 50% of robust ATH (instant-fill capped 2x)")
print("EV = P(non-grad)*E[today/entry] + P(grad after 600s)*E[payoff|sample] + P(grad instant)*E[payoff|sample]; 3% costs")
for name, fn in rules.items():
    sel = [v for v in ALLH.values() if fn(v)]
    if not sel: print(f"  {name:42s} 0"); continue
    (a, b, c), gr, gra, gi, gia = ev_cond(sel)
    e_ng = statistics.mean([(v["now_x"] if v["now_x"] is not None else 0) for v in sel if not v["grad"]]) if any(not v["grad"] for v in sel) else 0
    print(f"  {name:42s} n={len(sel):5d} grad>600s {gr:3d} ({gr/len(sel)*100:4.2f}%, ATH sampled {gra:3d}) instant {gi:3d} (sampled {gia:3d}) | losers today/entry {e_ng:.2f} | EV A {a:+5.0f}% B {b:+5.0f}% C {c:+5.0f}%")
print("Caveats: ATH = daily candle high with wicks trimmed to 3x body; same-day collapse is the norm (97% of reachable graduates hit ATH on first PumpSwap day). C assumes selling at half the intraday peak, which requires being there in minutes.")
