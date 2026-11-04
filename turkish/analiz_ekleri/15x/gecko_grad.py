"""GeckoTerminal: migrated pool + day OHLCV (SOL price) for on-chain-graduated mints only. Gentle pacing, resumable."""
import json, os, time, urllib.request, urllib.error
G = r"C:\Users\PD\AppData\Local\Temp\claude\C--Users-PD-project-claude-memecoin\5a0f1dfe-1637-4fac-95a3-1703257554c2\scratchpad\gecko"
P1 = os.path.join(G, "grad_tokens.jsonl"); P2 = os.path.join(G, "ath_graduated.jsonl"); LOG = os.path.join(G, "progress_grad.log")
INTERVAL = 8.5; _last = [0.0]
def log(m):
    s = f"{time.strftime('%H:%M:%S')} {m}"; print(s, flush=True); open(LOG, "a", encoding="utf-8").write(s + "\n")
def get(url, tries=8):
    for a in range(tries):
        w = INTERVAL - (time.time() - _last[0])
        if w > 0: time.sleep(w)
        _last[0] = time.time()
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 memecoin-research", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r: return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(30); continue
            if e.code == 404: return 404, None
            log(f"HTTP {e.code}"); time.sleep(5)
        except Exception as ex: log(f"ERR {str(ex)[:60]}"); time.sleep(10)
    return None, None
def done_keys(p):
    return {json.loads(l)["mint"] for l in open(p, encoding="utf-8") if l.strip()} if os.path.exists(p) else set()

comp = json.load(open(os.path.join(G, "complete_mints.json")))["complete"]
done = done_keys(P1); todo = [m for m in comp if m not in done]
log(f"phase A tokens/multi: {len(comp)} graduated, todo {len(todo)}")
with open(P1, "a", encoding="utf-8") as f:
    for i in range(0, len(todo), 30):
        batch = todo[i:i+30]; st, d = get("https://api.geckoterminal.com/api/v2/networks/solana/tokens/multi/" + ",".join(batch))
        found = {}
        for t in ((d or {}).get("data") or []):
            a = t["attributes"]; lp = a.get("launchpad_details") or {}
            found[a["address"]] = {"mint": a["address"], "found": 1, "completed": lp.get("completed"), "completed_at": lp.get("completed_at"),
                                   "migrated_pool": lp.get("migrated_destination_pool_address"), "fdv_usd": a.get("fdv_usd"), "reserve_usd": a.get("total_reserve_in_usd"), "vol24": (a.get("volume_usd") or {}).get("h24")}
        for m in batch: f.write(json.dumps(found.get(m, {"mint": m, "found": 0, "status": st})) + "\n")
        f.flush()
        if (i // 30) % 10 == 0: log(f"phase A {i+len(batch)}/{len(todo)}")
rows = [json.loads(l) for l in open(P1, encoding="utf-8") if l.strip()]
grad = [r for r in rows if r.get("migrated_pool")]
done = done_keys(P2); todo = [r for r in grad if r["mint"] not in done]
log(f"phase B ohlcv: pools {len(grad)} todo {len(todo)} (~{len(todo)*INTERVAL/60:.0f} min)")
with open(P2, "a", encoding="utf-8") as f:
    for k, r in enumerate(todo):
        st, d = get(f"https://api.geckoterminal.com/api/v2/networks/solana/pools/{r['migrated_pool']}/ohlcv/day?aggregate=1&limit=100&currency=token")
        lst = (((d or {}).get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []
        rec = {"mint": r["mint"], "pool": r["migrated_pool"], "status": st, "candles": len(lst)}
        if lst:
            hi = max(lst, key=lambda c: c[2])
            rec.update({"ath_sol": hi[2], "ath_ts": hi[0], "first_ts": lst[-1][0], "first_open_sol": lst[-1][1], "first_high_sol": lst[-1][2], "last_close_sol": lst[0][4], "last_ts": lst[0][0], "vol_sum": sum(c[5] for c in lst)})
        f.write(json.dumps(rec) + "\n"); f.flush()
        if k % 100 == 0: log(f"phase B {k}/{len(todo)}")
log("ALL DONE")
