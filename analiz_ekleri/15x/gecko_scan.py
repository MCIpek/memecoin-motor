"""Resumable GeckoTerminal scan of all pump_launches mints (read-only DB, public API, ~27 req/min).
Phase 1: /tokens/multi -> graduation status, fdv, reserve.
Phase 2: graduated tokens -> day OHLCV of migrated pool (price in SOL) -> ATH.
Phase 3: random sample of non-graduated -> pump-fun pool -> day OHLCV -> bonding-phase ATH.
"""
import json, os, sqlite3, sys, time, random, urllib.request, urllib.error

DB = r"C:\Users\PD\project_claude\memecoin\data\memecoin_motor.db"
OUT = r"C:\Users\PD\AppData\Local\Temp\claude\C--Users-PD-project-claude-memecoin\5a0f1dfe-1637-4fac-95a3-1703257554c2\scratchpad\gecko"
os.makedirs(OUT, exist_ok=True)
P1 = os.path.join(OUT, "tokens.jsonl"); P2 = os.path.join(OUT, "ath_graduated.jsonl"); P3 = os.path.join(OUT, "ath_sample.jsonl")
LOG = os.path.join(OUT, "progress.log")
MIN_INTERVAL = 2.15
_last = [0.0]

def log(msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f: f.write(line + "\n")

def get(url, tries=6):
    for attempt in range(tries):
        wait = MIN_INTERVAL - (time.time() - _last[0])
        if wait > 0: time.sleep(wait)
        _last[0] = time.time()
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 memecoin-research", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                log(f"429 -> sleep 65s (attempt {attempt+1})"); time.sleep(65); continue
            if e.code == 404:
                return 404, None
            log(f"HTTP {e.code} {url[-60:]}"); time.sleep(5)
        except Exception as ex:
            log(f"ERR {type(ex).__name__} {str(ex)[:80]}"); time.sleep(10)
    return None, None

def done_keys(path, key="mint"):
    if not os.path.exists(path): return set()
    with open(path, encoding="utf-8") as f:
        return {json.loads(l)[key] for l in f if l.strip()}

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
mints = [r[0] for r in con.execute("SELECT mint FROM pump_launches ORDER BY event_timestamp")]
log(f"total mints {len(mints)}")

# ---- Phase 1
done = done_keys(P1)
todo = [m for m in mints if m not in done]
log(f"phase1: done {len(done)} todo {len(todo)} (~{len(todo)/30*MIN_INTERVAL/60:.0f} min)")
with open(P1, "a", encoding="utf-8") as f:
    for i in range(0, len(todo), 30):
        batch = todo[i:i+30]
        st, data = get("https://api.geckoterminal.com/api/v2/networks/solana/tokens/multi/" + ",".join(batch))
        found = {}
        if data and "data" in data:
            for t in data["data"]:
                a = t.get("attributes", {})
                lp = a.get("launchpad_details") or {}
                found[a.get("address")] = {
                    "mint": a.get("address"), "found": 1,
                    "grad_pct": lp.get("graduation_percentage"), "completed": lp.get("completed"),
                    "completed_at": lp.get("completed_at"), "migrated_pool": lp.get("migrated_destination_pool_address"),
                    "fdv_usd": a.get("fdv_usd"), "price_usd": a.get("price_usd"),
                    "reserve_usd": a.get("total_reserve_in_usd"), "vol24": (a.get("volume_usd") or {}).get("h24"),
                    "supply": a.get("normalized_total_supply"),
                }
        for m in batch:
            f.write(json.dumps(found.get(m, {"mint": m, "found": 0, "status": st})) + "\n")
        f.flush()
        if (i // 30) % 50 == 0: log(f"phase1 {i+len(batch)}/{len(todo)}")
log("phase1 complete")

# ---- Phase 2: graduated -> migrated pool day OHLCV (currency=token => price in SOL)
rows = [json.loads(l) for l in open(P1, encoding="utf-8") if l.strip()]
grad = [r for r in rows if r.get("completed") and r.get("migrated_pool")]
done = done_keys(P2)
todo = [r for r in grad if r["mint"] not in done]
log(f"phase2: graduated {len(grad)} todo {len(todo)} (~{len(todo)*MIN_INTERVAL/60:.0f} min)")
with open(P2, "a", encoding="utf-8") as f:
    for k, r in enumerate(todo):
        st, data = get(f"https://api.geckoterminal.com/api/v2/networks/solana/pools/{r['migrated_pool']}/ohlcv/day?aggregate=1&limit=100&currency=token")
        lst = (((data or {}).get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []
        rec = {"mint": r["mint"], "pool": r["migrated_pool"], "status": st, "candles": len(lst)}
        if lst:
            hi = max(lst, key=lambda c: c[2])
            rec.update({"ath_sol": hi[2], "ath_ts": hi[0], "first_ts": lst[-1][0], "first_open_sol": lst[-1][1],
                        "last_close_sol": lst[0][4], "last_ts": lst[0][0], "vol_sum": sum(c[5] for c in lst)})
        f.write(json.dumps(rec) + "\n"); f.flush()
        if k % 100 == 0: log(f"phase2 {k}/{len(todo)}")
log("phase2 complete")

# ---- Phase 3: sample of non-graduated with a pool -> pump-fun pool day OHLCV
nongrad = [r for r in rows if r.get("found") and not r.get("completed")]
random.seed(7); sample = random.sample(nongrad, min(600, len(nongrad)))
done = done_keys(P3)
todo = [r for r in sample if r["mint"] not in done]
log(f"phase3: sample {len(sample)} todo {len(todo)} (~{len(todo)*2*MIN_INTERVAL/60:.0f} min)")
with open(P3, "a", encoding="utf-8") as f:
    for k, r in enumerate(todo):
        st, data = get(f"https://api.geckoterminal.com/api/v2/networks/solana/tokens/{r['mint']}/pools")
        pools = ((data or {}).get("data") or [])
        rec = {"mint": r["mint"], "pools": len(pools), "status": st}
        if pools:
            p = pools[0]["attributes"]; rec["pool"] = p["address"]; rec["pool_created_at"] = p.get("pool_created_at")
            st2, d2 = get(f"https://api.geckoterminal.com/api/v2/networks/solana/pools/{p['address']}/ohlcv/day?aggregate=1&limit=100&currency=token")
            lst = (((d2 or {}).get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []
            rec["candles"] = len(lst)
            if lst:
                hi = max(lst, key=lambda c: c[2])
                rec.update({"ath_sol": hi[2], "ath_ts": hi[0], "first_ts": lst[-1][0], "last_close_sol": lst[0][4], "last_ts": lst[0][0], "vol_sum": sum(c[5] for c in lst)})
        f.write(json.dumps(rec) + "\n"); f.flush()
        if k % 50 == 0: log(f"phase3 {k}/{len(todo)}")
log("ALL DONE")
