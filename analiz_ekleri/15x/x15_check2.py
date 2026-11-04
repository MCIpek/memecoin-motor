"""Validate outliers + recompute 15x base rate with per-token launch reserves (read-only)."""
import sqlite3, time, statistics
from collections import defaultdict, Counter
DB = r"C:\Users\PD\project_claude\memecoin\data\memecoin_motor.db"
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True); con.row_factory = sqlite3.Row
q = lambda s, p=(): con.execute(s, p).fetchall()
t0 = time.time()

print("== 1. Outlier inspection ==")
for prefix in ("7xdYx4ps", "4n8fQdx3", "GWL7za8m", "F1GpEL6Z"):
    L = q("SELECT mint,instruction_name,is_mayhem_mode,is_cashback_enabled,virtual_sol_reserves,virtual_token_reserves,real_token_reserves,token_total_supply,quote_asset,event_timestamp FROM pump_launches WHERE mint LIKE ?", (prefix+"%",))
    for l in L:
        print(" launch", dict(l))
        for t in q("SELECT event_timestamp-? age, is_buy, sol_amount, token_amount, virtual_sol_reserves vs, virtual_token_reserves vt, real_sol_reserves rs, real_token_reserves rt, ix_name, quote_asset FROM pump_trades WHERE mint=? ORDER BY event_timestamp, slot, event_index LIMIT 6", (l["event_timestamp"], l["mint"])):
            print("    trade", dict(t))

print("\n== 2. Launch curve types ==")
for r in q("SELECT virtual_sol_reserves vs, virtual_token_reserves vt, is_mayhem_mode m, COUNT(*) n FROM pump_launches WHERE quote_asset='SOL' GROUP BY 1,2,3 ORDER BY n DESC LIMIT 8"):
    print("  ", dict(r))

print("\n== 3. Recomputed base rates with per-token launch price; standard curve only (30 SOL / 1.073e15) ==")
mints = q("""SELECT l.mint, l.event_timestamp e, l.virtual_sol_reserves vs0, l.virtual_token_reserves vt0, l.is_mayhem_mode m
  FROM pump_launches l WHERE l.quote_asset='SOL'
  AND (SELECT SUM(buy_count+sell_count) FROM wallet_positions w WHERE w.mint=l.mint)>=3
  ORDER BY RANDOM() LIMIT 8000""")
rows = []
for L in mints:
    tr = q("SELECT event_timestamp-? age, virtual_sol_reserves vs, virtual_token_reserves vt FROM pump_trades WHERE mint=? AND virtual_token_reserves>0 ORDER BY event_timestamp, slot, event_index", (L["e"], L["mint"]))
    if not tr: continue
    p0 = L["vs0"]/L["vt0"]
    pts = [(r["age"], r["vs"]/r["vt"]) for r in tr]
    std = (L["vs0"] == 30_000_000_000 and L["vt0"] == 1_073_000_000_000_000)
    rec = {"std": std, "mayhem": L["m"], "xl": max(p for _, p in pts)/p0, "peak_vs": max(r["vs"] for r in tr)/1e9}
    for A in (2, 10, 30):
        ref = [(a, p) for a, p in pts if a >= A]
        if ref:
            a0, pa = ref[0]; fut = [p for a, p in pts if a > a0]
            rec[f"x{A}"] = max(fut)/pa if fut else 1.0
        else:
            rec[f"x{A}"] = None
    rows.append(rec)
print("n:", len(rows), "standard curve:", sum(1 for r in rows if r["std"]), "mayhem:", sum(1 for r in rows if r["mayhem"]), f"{time.time()-t0:.0f}s")
for name, sub in (("ALL", rows), ("STANDARD curve", [r for r in rows if r["std"]]), ("NON-STANDARD curve", [r for r in rows if not r["std"]]), ("STANDARD non-mayhem", [r for r in rows if r["std"] and not r["mayhem"]]), ("STANDARD mayhem", [r for r in rows if r["std"] and r["mayhem"]])):
    print(f"\n{name} n={len(sub)}")
    for key, label in (("xl", "from launch price"), ("x2", "entry >=2s"), ("x10", "entry >=10s"), ("x30", "entry >=30s")):
        s = [r[key] for r in sub if r.get(key) is not None]
        if not s: continue
        print(f"  {label:20s} n={len(s):5d} " + " | ".join(f"{thr}x {sum(1 for v in s if v>=thr)/len(s)*100:5.2f}%" for thr in (2,3,5,10,15,20)) + f" | median {statistics.median(s):.3f}")
std = [r for r in rows if r["std"]]
print("\nSTANDARD: tokens >=15x from launch:", sum(1 for r in std if r["xl"]>=15), "; their peak virtual SOL (median):", statistics.median([r["peak_vs"] for r in std if r["xl"]>=15]) if any(r["xl"]>=15 for r in std) else "n/a")
print("STANDARD: tokens >=10x from launch:", sum(1 for r in std if r["xl"]>=10), "; peak_vs>=115 SOL (graduated):", sum(1 for r in std if r["peak_vs"]>=115))
print(f"done {time.time()-t0:.0f}s")
