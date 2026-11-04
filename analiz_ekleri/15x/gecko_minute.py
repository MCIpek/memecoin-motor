"""Graduate sonrası ilk ~16 saat dakikalık mumlar (GeckoTerminal, ücretsiz, ~5/dk). Mayhem dışı graduate'ler, rastgele sıra, resumable."""
import json, os, sqlite3, time, random, datetime, urllib.request, urllib.error
G = r"C:\Users\PD\AppData\Local\Temp\claude\C--Users-PD-project-claude-memecoin\5a0f1dfe-1637-4fac-95a3-1703257554c2\scratchpad\gecko"
EK = r"C:\Users\PD\project_claude\memecoin\analiz_ekleri\15x"
OUT = os.path.join(G, "minute_graduated.jsonl"); LOG = os.path.join(G, "progress_minute.log")
INTERVAL = 7.0; _last = [0.0]
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
            if e.code == 429: time.sleep(20); continue
            if e.code == 404: return 404, None
            log(f"HTTP {e.code}"); time.sleep(5)
        except Exception as ex: log(f"ERR {str(ex)[:60]}"); time.sleep(10)
    return None, None
con = sqlite3.connect(r"file:C:\Users\PD\project_claude\memecoin\data\memecoin_motor.db?mode=ro", uri=True)
mayhem = {r[0]: r[1] for r in con.execute("SELECT mint, is_mayhem_mode FROM pump_launches")}
GT = [json.loads(l) for l in open(os.path.join(EK, "grad_tokens.jsonl"), encoding="utf-8")]
pools = [r for r in GT if r.get("migrated_pool") and r.get("completed_at") and not mayhem.get(r["mint"])]
random.seed(23); random.shuffle(pools)
done = {json.loads(l)["mint"] for l in open(OUT, encoding="utf-8")} if os.path.exists(OUT) else set()
todo = [r for r in pools if r["mint"] not in done]
log(f"non-mayhem graduated pools {len(pools)}, done {len(done)}, todo {len(todo)} (~{len(todo)*INTERVAL/60:.0f} min)")
with open(OUT, "a", encoding="utf-8") as f:
    for k, r in enumerate(todo):
        t_mig = int(datetime.datetime.fromisoformat(r["completed_at"].replace("Z", "+00:00")).timestamp())
        before = t_mig + 1000 * 60
        st, d = get(f"https://api.geckoterminal.com/api/v2/networks/solana/pools/{r['migrated_pool']}/ohlcv/minute?aggregate=1&limit=1000&currency=token&before_timestamp={before}")
        lst = (((d or {}).get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []
        lst = [c for c in lst if c[0] >= t_mig - 60]
        f.write(json.dumps({"mint": r["mint"], "pool": r["migrated_pool"], "t_mig": t_mig, "status": st, "n": len(lst), "ohlcv": lst}) + "\n"); f.flush()
        if k % 50 == 0: log(f"{k}/{len(todo)}")
log("ALL DONE")
