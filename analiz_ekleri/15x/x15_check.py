"""15x detectability check (read-only). Entry = first trade at/after age A; max X within 600s window."""
import sqlite3, time, statistics
from collections import defaultdict, Counter

DB = r"C:\Users\PD\project_claude\memecoin\data\memecoin_motor.db"
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True); con.row_factory = sqlite3.Row
q = lambda s, p=(): con.execute(s, p).fetchall()
t0 = time.time()

# sample mints: SOL quote, with >=3 trades (via wallet_positions, cheap), and a 10s snapshot
mints = [r[0] for r in q("""SELECT l.mint FROM pump_launches l
  WHERE l.quote_asset='SOL' AND EXISTS (SELECT 1 FROM token_snapshots s WHERE s.mint=l.mint AND s.target_age_seconds=10)
  AND (SELECT SUM(buy_count+sell_count) FROM wallet_positions w WHERE w.mint=l.mint)>=3
  ORDER BY RANDOM() LIMIT 8000""")]
print("sample mints:", len(mints), f"{time.time()-t0:.0f}s")

rows = []
for m in mints:
    L = q("SELECT event_timestamp e, creator FROM pump_launches WHERE mint=?", (m,))[0]
    tr = q("SELECT event_timestamp e, virtual_sol_reserves vs, virtual_token_reserves vt, is_buy, user_address u, sol_amount a FROM pump_trades WHERE mint=? AND virtual_token_reserves>0 ORDER BY event_timestamp, slot, event_index", (m,))
    if not tr: continue
    pts = [(r["e"]-L["e"], r["vs"]/r["vt"]) for r in tr]
    p_launch = 30e9/1.073e15
    maxp = max(p for _, p in pts); max_age = pts[[p for _, p in pts].index(maxp)][0]
    peak_vs = max(r["vs"] for r in tr)
    s = q("SELECT * FROM token_snapshots WHERE mint=? AND target_age_seconds=10", (m,))[0]
    d = q("SELECT decision FROM risk_decisions WHERE mint=? AND snapshot_age_seconds=10", (m,))
    rec = {"mint": m, "x_from_launch": maxp/p_launch, "peak_vs_sol": peak_vs/1e9, "peak_age": max_age,
           "ub10": s["unique_buyers"], "tc10": s["trade_count"], "flow10": s["net_quote_flow"]/1e9,
           "top10": s["top_buyer_share"], "q10": s["snapshot_quality"], "dec10": d[0][0] if d else None,
           "creator_sold10": s["creator_sold"]}
    for A in (2, 10, 30):
        ref = [(a, p) for a, p in pts if a >= A]
        if ref:
            a0, p0 = ref[0]; fut = [p for a, p in pts if a > a0]
            rec[f"x{A}"] = (max(fut)/p0) if fut else 1.0
            rec[f"final{A}"] = (fut[-1]/p0) if fut else 1.0
        else:
            rec[f"x{A}"] = None
    rows.append(rec)
n = len(rows); print("mints with trades:", n, f"{time.time()-t0:.0f}s")

def rate(key, thr, subset=None):
    sub = [r for r in (subset or rows) if r.get(key) is not None]
    return (sum(1 for r in sub if r[key] >= thr), len(sub))

print("\n== BASE RATES (raw mid-price, no fees/slippage), horizon = rest of 600s window ==")
for key, label in (("x_from_launch", "from launch price (sniper at t=0)"), ("x2", "entry first trade >=2s"), ("x10", "entry first trade >=10s"), ("x30", "entry first trade >=30s")):
    out = []
    for thr in (2, 3, 5, 10, 15, 20):
        h, t = rate(key, thr); out.append(f"{thr}x {h}/{t} ({h/t*100:.2f}%)")
    print(f"{label:38s}", " | ".join(out))
print("\nmedian peak age (s) for tokens reaching >=15x from launch:",
      statistics.median([r["peak_age"] for r in rows if r["x_from_launch"] >= 15]) if any(r["x_from_launch"] >= 15 for r in rows) else "n/a")
print("tokens reaching >=15x from launch that ALSO give >=5x from a 10s entry:",
      sum(1 for r in rows if r["x_from_launch"] >= 15 and (r.get("x10") or 0) >= 5), "/", sum(1 for r in rows if r["x_from_launch"] >= 15))
print("tokens >=15x from launch: final (end of window) x from launch median:",
      statistics.median([ (r["final2"] if r.get("final2") else 0) for r in rows if r["x_from_launch"] >= 15]) if any(r["x_from_launch"] >= 15 for r in rows) else "n/a")

print("\n== Does 10s data separate big winners? (target: >=5x from 10s entry, and >=15x from launch) ==")
def table(bucket_fn, label):
    g = defaultdict(list)
    for r in rows:
        if r.get("x10") is None: continue
        g[bucket_fn(r)].append(r)
    print(f"\n{label}")
    for k in sorted(g, key=lambda v: (str(type(v)), v)):
        sub = g[k]; nn = len(sub)
        h5 = sum(1 for r in sub if r["x10"] >= 5); h15 = sum(1 for r in sub if r["x_from_launch"] >= 15)
        h2 = sum(1 for r in sub if r["x10"] >= 2)
        med_final = statistics.median([r["final10"] for r in sub])
        print(f"   {str(k):22s} n={nn:5d}  >=2x@10s {h2/nn*100:5.1f}%  >=5x@10s {h5/nn*100:5.2f}%  >=15x launch {h15/nn*100:5.2f}%  median final@10s {med_final:.3f}")
table(lambda r: r["dec10"], "by 10s decision")
table(lambda r: "0" if r["ub10"]==0 else "1-2" if r["ub10"]<=2 else "3-5" if r["ub10"]<=5 else "6-10" if r["ub10"]<=10 else "11-20" if r["ub10"]<=20 else "21+", "by unique buyers in first 10s")
table(lambda r: "<=0" if r["flow10"]<=0 else "<0.5" if r["flow10"]<0.5 else "<2" if r["flow10"]<2 else "<5" if r["flow10"]<5 else "<10" if r["flow10"]<10 else ">=10 SOL", "by net SOL flow in first 10s")
table(lambda r: "<0.3" if r["top10"]<0.3 else "<0.5" if r["top10"]<0.5 else "<0.8" if r["top10"]<0.8 else ">=0.8", "by top buyer share at 10s")
table(lambda r: r["q10"], "by snapshot quality at 10s")
table(lambda r: "creator sold" if r["creator_sold10"] else "no", "by creator sold within 10s")

print("\n== Top-20 biggest winners from launch: what did 10s look like? ==")
for r in sorted(rows, key=lambda r: -r["x_from_launch"])[:20]:
    print(f"   {r['mint'][:8]}… x_launch {r['x_from_launch']:6.1f}  x@10s {r.get('x10') or 0:5.1f}  final@10s {r.get('final10') or 0:5.2f}  peak_age {r['peak_age']:4d}s  peak_vs {r['peak_vs_sol']:6.1f} SOL  ub10 {r['ub10']:3d} tc10 {r['tc10']:3d} flow10 {r['flow10']:6.2f} top {r['top10']:.2f} q {r['q10']} dec {r['dec10']}")
print(f"\ndone {time.time()-t0:.0f}s")
