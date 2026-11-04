"""Read current BondingCurve account state for all launches via public RPC getMultipleAccounts (read-only)."""
import base64, json, os, sqlite3, struct, time, urllib.request, urllib.error

DB = r"C:\Users\PD\project_claude\memecoin\data\memecoin_motor.db"
OUT = r"C:\Users\PD\AppData\Local\Temp\claude\C--Users-PD-project-claude-memecoin\5a0f1dfe-1637-4fac-95a3-1703257554c2\scratchpad\gecko\curves.jsonl"
RPC = "https://api.mainnet-beta.solana.com"
DISC = bytes([23, 183, 248, 55, 96, 216, 172, 96])

def rpc(method, params, tries=8):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    for attempt in range(tries):
        req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json", "User-Agent": "memecoin-research"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                r = json.loads(resp.read().decode())
                if "error" in r: raise RuntimeError(r["error"])
                return r["result"]
        except urllib.error.HTTPError as e:
            wait = 12 if e.code == 429 else 5
            print(f"HTTP {e.code} sleep {wait}", flush=True); time.sleep(wait)
        except Exception as ex:
            print("ERR", str(ex)[:100], flush=True); time.sleep(5)
    return None

def parse(b64):
    raw = base64.b64decode(b64)
    if raw[:8] != DISC or len(raw) < 8 + 40 + 1 + 32 + 2: return {"bad": True, "len": len(raw)}
    vt, vq, rt, rq, ts = struct.unpack_from("<QQQQQ", raw, 8)
    complete = raw[48]; mayhem = raw[49 + 32]; cashback = raw[50 + 32]
    return {"vt": vt, "vq": vq, "rt": rt, "rq": rq, "supply": ts, "complete": bool(complete), "mayhem": bool(mayhem), "cashback": bool(cashback)}

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
pairs = con.execute("SELECT mint, bonding_curve FROM pump_launches ORDER BY event_timestamp").fetchall()
done = set()
if os.path.exists(OUT):
    done = {json.loads(l)["mint"] for l in open(OUT, encoding="utf-8") if l.strip()}
todo = [p for p in pairs if p[0] not in done]
print(f"total {len(pairs)} done {len(done)} todo {len(todo)}", flush=True)
t0 = time.time()
with open(OUT, "a", encoding="utf-8") as f:
    for i in range(0, len(todo), 100):
        batch = todo[i:i+100]
        res = rpc("getMultipleAccounts", [[b for _, b in batch], {"encoding": "base64", "commitment": "confirmed"}])
        vals = (res or {}).get("value") if res else None
        slot = (res or {}).get("context", {}).get("slot")
        for j, (mint, curve) in enumerate(batch):
            acc = vals[j] if vals and j < len(vals) else None
            rec = {"mint": mint, "curve": curve, "slot": slot}
            if vals is None: rec["rpc_failed"] = True
            elif acc is None: rec["missing"] = True
            else:
                rec.update(parse(acc["data"][0])); rec["lamports"] = acc.get("lamports")
            f.write(json.dumps(rec) + "\n")
        f.flush()
        if (i // 100) % 50 == 0: print(f"{i+len(batch)}/{len(todo)} {time.time()-t0:.0f}s", flush=True)
        time.sleep(0.6)
print("DONE", flush=True)
