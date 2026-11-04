"""Read-only data quality checks for memecoin_motor.db. Writes results to dq_results.txt."""
import json, sqlite3, sys, time, statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone

DB = r"C:\Users\PD\project_claude\memecoin\data\memecoin_motor.db"
OUT = r"C:\Users\PD\AppData\Local\Temp\claude\C--Users-PD-project-claude-memecoin\5a0f1dfe-1637-4fac-95a3-1703257554c2\scratchpad\dq_results.txt"
sys.path.insert(0, r"C:\Users\PD\project_claude\memecoin\src")
from memecoin_motor.risk import RiskFeatures, evaluate  # noqa

out = open(OUT, "w", encoding="utf-8")
def log(*a):
    s = " ".join(str(x) for x in a)
    print(s); out.write(s + "\n"); out.flush()

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
def q(sql, params=()):
    t = time.time(); rows = con.execute(sql, params).fetchall(); dt = time.time() - t
    if dt > 5: log(f"   [slow {dt:.1f}s] {sql[:80]}")
    return rows
def one(sql, params=()):
    return q(sql, params)[0][0]
def ts(x):
    return datetime.fromtimestamp(int(x), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if x else None
def pct(vals, p):
    if not vals: return None
    vals = sorted(vals); k = (len(vals)-1)*p; f=int(k); c=min(f+1,len(vals)-1)
    return vals[f] + (vals[c]-vals[f])*(k-f)

log("=== 0. SCHEMA / PRAGMA ===")
log("page_size", one("PRAGMA page_size"), "page_count", one("PRAGMA page_count"))
log("tables:", [r[0] for r in q("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")])
log("indexes:", [r[0] for r in q("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name")])
log("service_state:", [dict(r) for r in q("SELECT * FROM service_state")])

log("\n=== 1. TABLE COUNTS (README claims in brackets) ===")
claims = {"pump_launches":58316,"pump_trades":2094977,"token_snapshots":291358,"risk_decisions":291358,
          "wallet_positions":608540,"wallet_profiles":14568,"sniper_scores":5615,"paper_v2_positions":30749,
          "executable_outcomes_v2":4389}
for t in ["chain_events","tokens_minimal","pump_launches","snapshot_tracking","pump_trades","wallet_positions",
          "wallet_behavior_stats","token_snapshots","stream_gaps","wallet_analysis_queue","wallet_profiles",
          "wallet_edges","risk_decisions","paper_positions","paper_outcomes","market_outcomes",
          "transaction_enrichment_queue","early_trade_metadata","sniper_scores","paper_v2_positions",
          "executable_outcomes_v2","x_band_calibration"]:
    n = one(f"SELECT COUNT(*) FROM {t}")
    log(f"{t:32s} {n:>10,}  [{claims.get(t,'-')}]")

log("\n=== 2. PUMP_LAUNCHES ===")
r = q("SELECT MIN(event_timestamp) a, MAX(event_timestamp) b, MIN(slot) s1, MAX(slot) s2, COUNT(DISTINCT creator) c, COUNT(DISTINCT date(event_timestamp,'unixepoch')) d FROM pump_launches")[0]
log("event_timestamp range:", ts(r["a"]), "->", ts(r["b"]), "| slots", r["s1"], "-", r["s2"], "| distinct creators", r["c"], "| distinct days", r["d"])
log("by instruction:", [tuple(x) for x in q("SELECT instruction_name, COUNT(*) FROM pump_launches GROUP BY 1")])
log("by quote_asset:", [tuple(x) for x in q("SELECT quote_asset, COUNT(*) FROM pump_launches GROUP BY 1")])
log("mayhem/cashback:", [tuple(x) for x in q("SELECT is_mayhem_mode,is_cashback_enabled, COUNT(*) FROM pump_launches GROUP BY 1,2")])
log("token_program:", [tuple(x) for x in q("SELECT token_program, COUNT(*) FROM pump_launches GROUP BY 1")])
log("null block_time:", one("SELECT COUNT(*) FROM pump_launches WHERE block_time IS NULL"))
log("block_time != event_timestamp:", one("SELECT COUNT(*) FROM pump_launches WHERE block_time IS NOT NULL AND block_time<>event_timestamp"))
log("|block_time - event_timestamp|>2:", one("SELECT COUNT(*) FROM pump_launches WHERE block_time IS NOT NULL AND abs(block_time-event_timestamp)>2"))
log("initial reserves distinct:", [tuple(x) for x in q("SELECT virtual_sol_reserves, virtual_token_reserves, real_token_reserves, token_total_supply, COUNT(*) FROM pump_launches GROUP BY 1,2,3,4 ORDER BY 5 DESC LIMIT 5")])
log("creator==user:", one("SELECT COUNT(*) FROM pump_launches WHERE creator=user_address"), "creator!=user:", one("SELECT COUNT(*) FROM pump_launches WHERE creator<>user_address"))
log("launches per day:")
for x in q("SELECT date(event_timestamp,'unixepoch') d, COUNT(*) n, MIN(event_timestamp) a, MAX(event_timestamp) b FROM pump_launches GROUP BY 1 ORDER BY 1"):
    log(f"   {x['d']}  {x['n']:>6}  {ts(x['a'])[11:]} - {ts(x['b'])[11:]}")
log("top creators by launch count:", [tuple(x) for x in q("SELECT creator, COUNT(*) n FROM pump_launches GROUP BY 1 ORDER BY 2 DESC LIMIT 5")])
log("creators with >1 launch:", one("SELECT COUNT(*) FROM (SELECT creator FROM pump_launches GROUP BY 1 HAVING COUNT(*)>1)"))
log("first_seen_at vs event_timestamp delay (s) sample 20000:")
d = [ (datetime.fromisoformat(x["f"]).timestamp() - x["e"]) for x in q("SELECT first_seen_at f, event_timestamp e FROM pump_launches ORDER BY RANDOM() LIMIT 20000")]
log("   p10 p50 p90 p99 max:", [round(pct(d,p),2) for p in (.1,.5,.9,.99,1.0)], "negative:", sum(1 for v in d if v<0))
log("launches without chain_event:", one("SELECT COUNT(*) FROM pump_launches l WHERE NOT EXISTS (SELECT 1 FROM chain_events c WHERE c.signature=l.signature)"))
log("launches without tokens_minimal:", one("SELECT COUNT(*) FROM pump_launches l WHERE NOT EXISTS (SELECT 1 FROM tokens_minimal t WHERE t.mint=l.mint)"))
log("tokens_minimal without launch:", one("SELECT COUNT(*) FROM tokens_minimal t WHERE NOT EXISTS (SELECT 1 FROM pump_launches l WHERE l.mint=t.mint)"))
log("tokens_minimal completeness:", [tuple(x) for x in q("SELECT data_completeness, COUNT(*) FROM tokens_minimal GROUP BY 1")])

log("\n=== 3. COLLECTOR SESSIONS (gaps > 15 min between consecutive launches) ===")
tsl = [x[0] for x in q("SELECT event_timestamp FROM pump_launches ORDER BY event_timestamp")]
sessions = []; start = tsl[0]; prev = tsl[0]
for t in tsl[1:]:
    if t - prev > 900:
        sessions.append((start, prev)); start = t
    prev = t
sessions.append((start, prev))
total_h = sum((b-a) for a,b in sessions)/3600
log(f"sessions: {len(sessions)}  total covered hours: {total_h:.1f}  calendar span days: {(tsl[-1]-tsl[0])/86400:.1f}  coverage: {total_h/((tsl[-1]-tsl[0])/3600)*100:.1f}%")
for a,b in sessions:
    log(f"   {ts(a)} -> {ts(b)}  {(b-a)/3600:6.2f} h")

log("\n=== 4. PUMP_TRADES ===")
r = q("SELECT MIN(event_timestamp) a, MAX(event_timestamp) b, COUNT(DISTINCT mint) m, COUNT(DISTINCT user_address) u, SUM(is_buy) buys FROM pump_trades")[0]
log("range:", ts(r["a"]), "->", ts(r["b"]), "| distinct mints", r["m"], "| distinct users", r["u"], "| buys", r["buys"])
log("ix_name:", [tuple(x) for x in q("SELECT ix_name, COUNT(*) FROM pump_trades GROUP BY 1")])
log("quote_asset:", [tuple(x) for x in q("SELECT quote_asset, COUNT(*) FROM pump_trades GROUP BY 1")])
log("quote_amount=0:", one("SELECT COUNT(*) FROM pump_trades WHERE quote_amount=0"), "token_amount=0:", one("SELECT COUNT(*) FROM pump_trades WHERE token_amount=0"))
log("sol_amount<>quote_amount:", one("SELECT COUNT(*) FROM pump_trades WHERE sol_amount<>quote_amount"))
log("virtual_sol<>virtual_quote:", one("SELECT COUNT(*) FROM pump_trades WHERE virtual_sol_reserves<>virtual_quote_reserves"))
log("negative/zero reserves:", one("SELECT COUNT(*) FROM pump_trades WHERE virtual_sol_reserves<=0 OR virtual_token_reserves<=0"))
log("orphan trades (mint w/o launch):", one("SELECT COUNT(*) FROM pump_trades t WHERE NOT EXISTS (SELECT 1 FROM pump_launches l WHERE l.mint=t.mint)"))
log("trades w/o chain_event (FK):", one("SELECT COUNT(*) FROM pump_trades t WHERE NOT EXISTS (SELECT 1 FROM chain_events c WHERE c.signature=t.signature)"))
log("trade age vs launch: <0 / >600:", one("SELECT COUNT(*) FROM pump_trades t JOIN pump_launches l USING(mint) WHERE t.event_timestamp<l.event_timestamp"), "/", one("SELECT COUNT(*) FROM pump_trades t JOIN pump_launches l USING(mint) WHERE t.event_timestamp>l.event_timestamp+600"))
log("trades per mint distribution:")
tpm = [x[0] for x in q("SELECT COUNT(*) FROM pump_trades GROUP BY mint")]
log("   mints w/ trades:", len(tpm), "p50 p90 p99 max:", [pct(tpm,p) for p in (.5,.9,.99,1.0)], "mean", round(statistics.mean(tpm),1))
log("   mints with >=10 trades:", sum(1 for v in tpm if v>=10), ">=50:", sum(1 for v in tpm if v>=50), ">=200:", sum(1 for v in tpm if v>=200))
log("launches with 0 trades:", one("SELECT COUNT(*) FROM pump_launches l WHERE NOT EXISTS (SELECT 1 FROM pump_trades t WHERE t.mint=l.mint)"))
log("trade age distribution (s): buckets 0-10/10-60/60-300/300-600:", [tuple(x) for x in q("SELECT CASE WHEN a<=10 THEN '0-10' WHEN a<=60 THEN '10-60' WHEN a<=300 THEN '60-300' ELSE '300-600' END b, COUNT(*) FROM (SELECT t.event_timestamp-l.event_timestamp a FROM pump_trades t JOIN pump_launches l USING(mint)) GROUP BY 1")])
log("fee bps distribution (fee/quote*1e4) sample:", Counter(min(200, round(x["fee"]/max(1,x["q"])*10000)) for x in q("SELECT fee, quote_amount q FROM pump_trades WHERE quote_amount>0 ORDER BY RANDOM() LIMIT 20000")).most_common(6))
log("reserve monotonic check sample (buy must raise virtual_sol): ", end="")
bad=0; tot=0
for m in [x[0] for x in q("SELECT mint FROM pump_trades GROUP BY mint HAVING COUNT(*)>=20 ORDER BY RANDOM() LIMIT 300")]:
    rows = q("SELECT is_buy, virtual_sol_reserves v, event_timestamp, slot, event_index FROM pump_trades WHERE mint=? ORDER BY slot,event_timestamp,event_index", (m,))
    for i in range(1,len(rows)):
        tot+=1
        if rows[i]["is_buy"] and rows[i]["v"] < rows[i-1]["v"]: bad+=1
        if not rows[i]["is_buy"] and rows[i]["v"] > rows[i-1]["v"]: bad+=1
log(f"violations {bad}/{tot} ({bad/max(1,tot)*100:.2f}%) [ordering by slot; violations hint at intra-slot ordering/missing events]")

log("\n=== 5. CHAIN_EVENTS ===")
log("completeness:", [tuple(x) for x in q("SELECT data_completeness, is_backfilled, COUNT(*) FROM chain_events GROUP BY 1,2")])
log("provider:", [tuple(x) for x in q("SELECT provider_name, commitment, COUNT(*) FROM chain_events GROUP BY 1,2")])
log("raw json present:", one("SELECT COUNT(*) FROM chain_events WHERE raw_transaction_json IS NOT NULL"))
log("transaction_error not null:", one("SELECT COUNT(*) FROM chain_events WHERE transaction_error IS NOT NULL"))
for comp in ("COMPLETE","LOG_EVENT"):
    lat = [x[0] for x in q("SELECT ingestion_latency_ms FROM chain_events WHERE data_completeness=? AND ingestion_latency_ms IS NOT NULL ORDER BY RANDOM() LIMIT 30000", (comp,))]
    if lat: log(f"ingestion_latency_ms {comp}: p50 {pct(lat,.5):.0f} p90 {pct(lat,.9):.0f} p99 {pct(lat,.99):.0f} max {max(lat)}")
log("sizes: avg len raw json (sample 500):", one("SELECT AVG(LENGTH(raw_transaction_json)) FROM (SELECT raw_transaction_json FROM chain_events WHERE raw_transaction_json IS NOT NULL ORDER BY RANDOM() LIMIT 500)"))
log("sizes: avg len logs_json LOG_EVENT (sample 2000):", one("SELECT AVG(LENGTH(logs_json)) FROM (SELECT logs_json FROM chain_events WHERE data_completeness='LOG_EVENT' ORDER BY RANDOM() LIMIT 2000)"))
log("block_time null (live):", one("SELECT COUNT(*) FROM chain_events WHERE block_time IS NULL"))
log("events per day (client_received_at):", [tuple(x) for x in q("SELECT substr(client_received_at,1,10), COUNT(*) FROM chain_events GROUP BY 1 ORDER BY 1")])

log("\n=== 6. STREAM_GAPS ===")
log("status:", [tuple(x) for x in q("SELECT status, COUNT(*), SUM(end_slot-start_slot+1) FROM stream_gaps GROUP BY 1")])
log("largest gaps:", [(ts_ := x["detected_at"], x["end_slot"]-x["start_slot"]+1, x["status"]) for x in q("SELECT * FROM stream_gaps ORDER BY end_slot-start_slot DESC LIMIT 8")])
log("gap size distribution (slots) for SKIPPED:", [tuple(x) for x in q("SELECT CASE WHEN end_slot-start_slot+1<=100 THEN '33-100' WHEN end_slot-start_slot+1<=1000 THEN '101-1k' WHEN end_slot-start_slot+1<=100000 THEN '1k-100k' ELSE '>100k' END, COUNT(*), SUM(end_slot-start_slot+1) FROM stream_gaps WHERE status='SKIPPED_TOO_LARGE' GROUP BY 1")])

log("\n=== 7. SNAPSHOT_TRACKING ===")
log("ended_at null:", one("SELECT COUNT(*) FROM snapshot_tracking WHERE ended_at IS NULL"))
log("launches without tracking:", one("SELECT COUNT(*) FROM pump_launches l WHERE NOT EXISTS (SELECT 1 FROM snapshot_tracking s WHERE s.mint=l.mint)"))
log("tracking ended before launch+600 (incomplete):", one("SELECT COUNT(*) FROM snapshot_tracking WHERE ended_at IS NOT NULL AND ended_at<launch_timestamp+600"))
log("tracking ended before launch+300:", one("SELECT COUNT(*) FROM snapshot_tracking WHERE ended_at IS NOT NULL AND ended_at<launch_timestamp+300"))
log("tracking ended before launch+60:", one("SELECT COUNT(*) FROM snapshot_tracking WHERE ended_at IS NOT NULL AND ended_at<launch_timestamp+60"))
log("ended_at < launch_timestamp (negative):", one("SELECT COUNT(*) FROM snapshot_tracking WHERE ended_at IS NOT NULL AND ended_at<launch_timestamp"))
log("distinct ended_at values (= restart count):", one("SELECT COUNT(DISTINCT ended_at) FROM snapshot_tracking"))
log("ended_at values:", [(ts(x[0]), x[1]) for x in q("SELECT ended_at, COUNT(*) FROM snapshot_tracking GROUP BY 1 ORDER BY 1")])

log("\n=== 8. TOKEN_SNAPSHOTS ===")
log("quality by age (README table check):")
for x in q("SELECT target_age_seconds a, SUM(snapshot_quality='ON_TIME') ot, SUM(snapshot_quality='LATE') late, COUNT(*) n FROM token_snapshots GROUP BY 1 ORDER BY 1"):
    log(f"   {x['a']:>3}s  on_time {x['ot']:>7,}  late {x['late']:>7,}  ratio {x['ot']/x['n']*100:5.1f}%")
log("generation_delay_ms percentiles LATE (sample):", end="")
dl=[x[0] for x in q("SELECT generation_delay_ms FROM token_snapshots WHERE snapshot_quality='LATE' ORDER BY RANDOM() LIMIT 30000")]
log(f" p50 {pct(dl,.5)/1000:.0f}s p90 {pct(dl,.9)/1000:.0f}s p99 {pct(dl,.99)/3600000:.1f}h max {max(dl)/86400000:.1f}d")
log("LATE but delay<=1500ms:", one("SELECT COUNT(*) FROM token_snapshots WHERE snapshot_quality='LATE' AND generation_delay_ms<=1500"))
log("ON_TIME with delay>1500:", one("SELECT COUNT(*) FROM token_snapshots WHERE snapshot_quality='ON_TIME' AND generation_delay_ms>1500"))
log("snapshots with cutoff > tracking ended_at (should be 0):", one("SELECT COUNT(*) FROM token_snapshots s JOIN snapshot_tracking t USING(mint) WHERE t.ended_at IS NOT NULL AND s.cutoff_timestamp>t.ended_at"))
log("snapshots generated AFTER a restart that ended tracking (generated_at > ended_at):", one("SELECT COUNT(*) FROM token_snapshots s JOIN snapshot_tracking t USING(mint) WHERE t.ended_at IS NOT NULL AND CAST(strftime('%s',substr(s.generated_at,1,19))AS INTEGER)>t.ended_at+5"))
log("mints with all 5 snapshots:", one("SELECT COUNT(*) FROM (SELECT mint FROM token_snapshots GROUP BY mint HAVING COUNT(*)=5)"), "mints with any:", one("SELECT COUNT(DISTINCT mint) FROM token_snapshots"))
log("snapshot null price:", one("SELECT COUNT(*) FROM token_snapshots WHERE price_quote_per_token IS NULL"))
log("trade_count=0 by age:", [tuple(x) for x in q("SELECT target_age_seconds, SUM(trade_count=0), COUNT(*) FROM token_snapshots GROUP BY 1")])

log("\n=== 9. SNAPSHOT RECOMPUTATION (raw trades vs stored) sample 400 mints ===")
mism = Counter(); checked = 0
for m in [x[0] for x in q("SELECT DISTINCT mint FROM token_snapshots ORDER BY RANDOM() LIMIT 400")]:
    L = q("SELECT * FROM pump_launches WHERE mint=?", (m,))[0]
    for s in q("SELECT * FROM token_snapshots WHERE mint=?", (m,)):
        tr = q("SELECT * FROM pump_trades WHERE mint=? AND event_timestamp>=? AND event_timestamp<=?", (m, L["event_timestamp"], s["cutoff_timestamp"]))
        buys=[t for t in tr if t["is_buy"]]; sells=[t for t in tr if not t["is_buy"]]
        checked += 1
        if len(tr)!=s["trade_count"]: mism["trade_count"]+=1
        if len({t["user_address"] for t in buys})!=s["unique_buyers"]: mism["unique_buyers"]+=1
        if sum(t["quote_amount"] for t in buys)-sum(t["quote_amount"] for t in sells)!=s["net_quote_flow"]: mism["net_quote_flow"]+=1
        if any(t["user_address"]==L["creator"] for t in sells)!=bool(s["creator_sold"]): mism["creator_sold"]+=1
log("checked snapshots:", checked, "mismatches:", dict(mism), "(mismatch = trades arrived AFTER snapshot was generated, i.e. snapshot used incomplete data)")
# deeper: how many ON_TIME snapshots were generated before all trades in window arrived?
log("ON_TIME snapshots whose window trades were observed after generated_at (sample 3000):", end=" ")
late_arrivals=0; n=0
for s in q("SELECT s.mint, s.cutoff_timestamp c, s.generated_at g, l.event_timestamp e FROM token_snapshots s JOIN pump_launches l USING(mint) WHERE s.snapshot_quality='ON_TIME' ORDER BY RANDOM() LIMIT 3000"):
    n+=1
    cnt = one("SELECT COUNT(*) FROM pump_trades WHERE mint=? AND event_timestamp BETWEEN ? AND ? AND observed_at>?", (s["mint"], s["e"], s["c"], s["g"]))
    if cnt: late_arrivals+=1
log(f"{late_arrivals}/{n} ({late_arrivals/max(1,n)*100:.1f}%)")

log("\n=== 10. RISK_DECISIONS ===")
log("ruleset:", [tuple(x) for x in q("SELECT ruleset_version, COUNT(*) FROM risk_decisions GROUP BY 1")])
log("decision by age:")
for x in q("SELECT snapshot_age_seconds a, SUM(decision='ADAY') aday, SUM(decision='IZLE') izle, SUM(decision='GIRME') girme, COUNT(*) n FROM risk_decisions GROUP BY 1 ORDER BY 1"):
    log(f"   {x['a']:>3}s ADAY {x['aday']:>6} ({x['aday']/x['n']*100:4.1f}%) IZLE {x['izle']:>6} GIRME {x['girme']:>6}")
log("decisions without snapshot:", one("SELECT COUNT(*) FROM risk_decisions d WHERE NOT EXISTS (SELECT 1 FROM token_snapshots s WHERE s.mint=d.mint AND s.target_age_seconds=d.snapshot_age_seconds)"))
log("snapshots without decision:", one("SELECT COUNT(*) FROM token_snapshots s WHERE NOT EXISTS (SELECT 1 FROM risk_decisions d WHERE d.mint=s.mint AND d.snapshot_age_seconds=s.target_age_seconds)"))
log("ADAY with quality by age:", [tuple(x) for x in q("SELECT d.snapshot_age_seconds, s.snapshot_quality, COUNT(*) FROM risk_decisions d JOIN token_snapshots s ON s.mint=d.mint AND s.target_age_seconds=d.snapshot_age_seconds WHERE d.decision='ADAY' GROUP BY 1,2 ORDER BY 1,2")])
log("re-evaluate stored features_json through evaluate() (sample 20000):", end=" ")
diff=0; n=0; diffs=Counter()
for d in q("SELECT * FROM risk_decisions ORDER BY RANDOM() LIMIT 20000"):
    f = json.loads(d["features_json"]); n+=1
    try:
        res = evaluate(RiskFeatures(**f))
    except TypeError as e:
        diffs["schema:"+str(e)[:40]]+=1; continue
    if res.decision!=d["decision"] or res.risk_score!=d["risk_score"] or res.opportunity_score!=d["opportunity_score"]:
        diff+=1; diffs[f"{d['decision']}->{res.decision}"]+=1
log(f"{diff}/{n} differ; {dict(diffs)}")
log("features_json key sets:", Counter(tuple(sorted(json.loads(d[0]).keys())) for d in q("SELECT features_json FROM risk_decisions ORDER BY RANDOM() LIMIT 2000")).most_common(3))
log("evaluated_at - cutoff (s) for ADAY decisions (sample):", end=" ")
dd=[datetime.fromisoformat(x["e"]).timestamp()-x["c"] for x in q("SELECT d.evaluated_at e, s.cutoff_timestamp c FROM risk_decisions d JOIN token_snapshots s ON s.mint=d.mint AND s.target_age_seconds=d.snapshot_age_seconds WHERE d.decision='ADAY' ORDER BY RANDOM() LIMIT 5000")]
log(f"p50 {pct(dd,.5):.0f} p90 {pct(dd,.9):.0f} max {max(dd)/3600:.1f}h  (>60s: {sum(1 for v in dd if v>60)}/{len(dd)})")
log("confidence distribution ADAY:", [tuple(x) for x in q("SELECT round(confidence,2), COUNT(*) FROM risk_decisions WHERE decision='ADAY' GROUP BY 1 ORDER BY 1")])

log("\n=== 11. WALLET ENRICHMENT ===")
log("wallet queue status:", [tuple(x) for x in q("SELECT status, reason, COUNT(*) FROM wallet_analysis_queue GROUP BY 1,2")])
log("tx enrichment status:", [tuple(x) for x in q("SELECT status, COUNT(*) FROM transaction_enrichment_queue GROUP BY 1")])
log("wallet_profiles funding_label:", [tuple(x) for x in q("SELECT funding_label, history_complete, COUNT(*) FROM wallet_profiles GROUP BY 1,2")])
log("wallet_profiles confidence:", [tuple(x) for x in q("SELECT confidence, COUNT(*) FROM wallet_profiles GROUP BY 1")])
log("sniper classification:", [tuple(x) for x in q("SELECT classification, bundle_likelihood, COUNT(*) FROM sniper_scores GROUP BY 1,2")])
log("early_trade_metadata jito tip>0:", one("SELECT COUNT(*) FROM early_trade_metadata WHERE jito_tip_lamports>0"), "/", one("SELECT COUNT(*) FROM early_trade_metadata"))
log("mints with sniper scores:", one("SELECT COUNT(DISTINCT mint) FROM sniper_scores"), "mints with analyzed creator:", one("SELECT COUNT(DISTINCT q.mint) FROM wallet_analysis_queue q JOIN wallet_profiles p ON p.address=q.address WHERE q.reason='CREATOR'"))
log("wallet_behavior_stats top:", [tuple(x) for x in q("SELECT early_launch_count, COUNT(*) FROM wallet_behavior_stats GROUP BY 1 ORDER BY 1 DESC LIMIT 5")])
log("wallet_behavior_stats vs recompute: stored", one("SELECT COUNT(*) FROM wallet_behavior_stats"), "recomputed", one("SELECT COUNT(*) FROM (SELECT w.user_address FROM wallet_positions w JOIN pump_launches l ON l.mint=w.mint WHERE w.buy_count>0 AND w.first_trade_timestamp-l.event_timestamp BETWEEN 0 AND 10 GROUP BY 1)"))
log("wallet_positions vs trade aggregate mismatches:", one("""SELECT COUNT(*) FROM wallet_positions w JOIN (SELECT mint,user_address,SUM(CASE WHEN is_buy=1 THEN token_amount ELSE 0 END) bt, SUM(CASE WHEN is_buy=1 THEN 1 ELSE 0 END) bc, SUM(CASE WHEN is_buy=0 THEN 1 ELSE 0 END) sc FROM pump_trades GROUP BY 1,2) t ON t.mint=w.mint AND t.user_address=w.user_address WHERE t.bt<>w.buy_token_amount OR t.bc<>w.buy_count OR t.sc<>w.sell_count"""), "positions w/o trades:", one("SELECT COUNT(*) FROM wallet_positions w WHERE NOT EXISTS (SELECT 1 FROM pump_trades t WHERE t.mint=w.mint AND t.user_address=w.user_address)"))
log("top repeated early-entry wallets (early_launch_count):", [tuple(x) for x in q("SELECT address, early_launch_count FROM wallet_behavior_stats ORDER BY 2 DESC LIMIT 5")])

log("\n=== 12. PAPER V2 ===")
log("positions status/reason:", [tuple(x) for x in q("SELECT status, failure_reason, is_canonical, COUNT(*) FROM paper_v2_positions GROUP BY 1,2,3 ORDER BY 4 DESC")])
log("by experiment group / decision:", [tuple(x) for x in q("SELECT p.experiment_group, d.decision, p.status, COUNT(*) FROM paper_v2_positions p JOIN risk_decisions d ON d.mint=p.mint AND d.snapshot_age_seconds=p.decision_age_seconds GROUP BY 1,2,3 ORDER BY 1,2,3")])
log("canonical count:", one("SELECT COUNT(*) FROM paper_v2_positions WHERE is_canonical=1"), "distinct mints canonical:", one("SELECT COUNT(DISTINCT mint) FROM paper_v2_positions WHERE is_canonical=1"))
log("OPEN positions entry fill delay (entry_ts - cutoff):", [tuple(x) for x in q("SELECT entry_timestamp-decision_cutoff_timestamp, COUNT(*) FROM paper_v2_positions WHERE status='OPEN' GROUP BY 1 ORDER BY 1")])
log("estimated_impact_bps OPEN percentiles:", end=" ")
ib=[x[0] for x in q("SELECT estimated_impact_bps FROM paper_v2_positions WHERE status='OPEN'")]
log(f"p50 {pct(ib,.5)} p90 {pct(ib,.9)} max {max(ib)}")
log("ADAY decisions (10/30/60) lacking any v2 position:", one("SELECT COUNT(*) FROM risk_decisions d WHERE d.decision='ADAY' AND d.snapshot_age_seconds IN (10,30,60) AND NOT EXISTS (SELECT 1 FROM paper_v2_positions p WHERE p.mint=d.mint AND p.decision_age_seconds=d.snapshot_age_seconds)"))
log("v2 OPEN positions lacking 300s outcome:", one("SELECT COUNT(*) FROM paper_v2_positions p WHERE p.status='OPEN' AND NOT EXISTS (SELECT 1 FROM executable_outcomes_v2 o WHERE o.mint=p.mint AND o.decision_age_seconds=p.decision_age_seconds AND o.horizon_seconds=300)"))
log("OPEN positions whose tracking ended before entry+300:", one("SELECT COUNT(*) FROM paper_v2_positions p JOIN snapshot_tracking t USING(mint) WHERE p.status='OPEN' AND t.ended_at IS NOT NULL AND t.ended_at<p.entry_timestamp+300"))

log("\n=== 13. EXECUTABLE_OUTCOMES_V2 ===")
log("by horizon/quality/decision/canonical:")
for x in q("SELECT horizon_seconds h, data_quality dq, decision d, is_canonical c, COUNT(*) n FROM executable_outcomes_v2 GROUP BY 1,2,3,4 ORDER BY 1,2,3,4"):
    log(f"   {x['h']:>3}s {x['dq']:13s} {x['d']:5s} canon={x['c']} n={x['n']}")
def summarize(label, rows):
    if not rows: log(f"   {label}: n=0"); return
    mx=[r["max_x"] for r in rows]; fx=[r["final_x"] for r in rows]; sx=[r["strategy_x"] for r in rows]; dd=[r["max_drawdown_pct"] for r in rows]
    n=len(rows)
    log(f"   {label}: n={n} | median max_x {statistics.median(mx):.3f} final_x {statistics.median(fx):.3f} strategy_x {statistics.median(sx):.3f} dd {statistics.median(dd):.1f}% | mean final {statistics.mean(fx):.3f} mean strategy {statistics.mean(sx):.3f} | hit1.5 {sum(r['hit_1_5x'] for r in rows)/n*100:.1f}% hit2 {sum(r['hit_2x'] for r in rows)/n*100:.1f}% hit3 {sum(r['hit_3x'] for r in rows)/n*100:.1f}% hit5 {sum(r['hit_5x'] for r in rows)/n*100:.1f}% | strategy>1: {sum(1 for v in sx if v>1)/n*100:.1f}% final>1: {sum(1 for v in fx if v>1)/n*100:.1f}% | sum strategy PnL (SOL @0.1): {sum(v-1 for v in sx)*0.1:.2f}")
for h in (60,300):
    summarize(f"{h}s CANONICAL ADAY CONTINUOUS (README claim n=163)", q("SELECT * FROM executable_outcomes_v2 WHERE horizon_seconds=? AND is_canonical=1 AND data_quality='CONTINUOUS'", (h,)))
    summarize(f"{h}s CANONICAL ADAY ALL quality", q("SELECT * FROM executable_outcomes_v2 WHERE horizon_seconds=? AND is_canonical=1", (h,)))
    for dcs in ("ADAY","IZLE","GIRME"):
        summarize(f"{h}s {dcs} CONTINUOUS all groups", q("SELECT * FROM executable_outcomes_v2 WHERE horizon_seconds=? AND decision=? AND data_quality='CONTINUOUS'", (h,dcs)))
    for age in (10,30,60):
        summarize(f"{h}s ADAY age {age} CONTINUOUS", q("SELECT * FROM executable_outcomes_v2 WHERE horizon_seconds=? AND decision='ADAY' AND decision_age_seconds=? AND data_quality='CONTINUOUS'", (h,age)))
log("exit_reason canonical 300:", [tuple(x) for x in q("SELECT exit_reason, COUNT(*) FROM executable_outcomes_v2 WHERE horizon_seconds=300 AND is_canonical=1 GROUP BY 1")])
log("canonical 300 CONTINUOUS by day:", [tuple(x) for x in q("SELECT date(p.entry_timestamp,'unixepoch'), COUNT(*), round(AVG(o.strategy_x),3), round(AVG(o.final_x),3) FROM executable_outcomes_v2 o JOIN paper_v2_positions p ON p.mint=o.mint AND p.decision_age_seconds=o.decision_age_seconds WHERE o.horizon_seconds=300 AND o.is_canonical=1 AND o.data_quality='CONTINUOUS' GROUP BY 1 ORDER BY 1")])
log("canonical 300 CONTINUOUS: ON_TIME snapshot subset:", end=" ")
summarize("ON_TIME only", q("SELECT o.* FROM executable_outcomes_v2 o JOIN token_snapshots s ON s.mint=o.mint AND s.target_age_seconds=o.decision_age_seconds WHERE o.horizon_seconds=300 AND o.is_canonical=1 AND o.data_quality='CONTINUOUS' AND s.snapshot_quality='ON_TIME'"))
log("x_band_calibration rows:", [dict(x) for x in q("SELECT * FROM x_band_calibration ORDER BY sample_count DESC LIMIT 10")])
log("legacy paper_positions status:", [tuple(x) for x in q("SELECT status, failure_reason, COUNT(*) FROM paper_positions GROUP BY 1,2")])
log("legacy market_outcomes by decision 300s:", end=" ")
for x in q("SELECT d.decision, COUNT(*) n, AVG(o.hit_2x) h2, AVG(o.final_market_x) f FROM market_outcomes o JOIN risk_decisions d ON d.mint=o.mint AND d.snapshot_age_seconds=o.decision_age_seconds WHERE o.horizon_seconds=300 GROUP BY 1"):
    log(f"{x['decision']} n={x['n']} hit2x={x['h2']*100:.1f}% mean_final={x['f']:.3f};", end=" ")
log("")

log("\n=== 14. GLOBAL MARKET OUTCOME (no selection): raw max X within 300s from 10s price, all mints w/ >=5 trades ===")
# Using trades: price = virtual_sol/virtual_token. For each mint, reference at first trade after launch+10s; max within next 300s.
rows = q("""SELECT mint, event_timestamp e, virtual_sol_reserves vs, virtual_token_reserves vt FROM pump_trades WHERE mint IN (SELECT mint FROM pump_trades GROUP BY mint HAVING COUNT(*)>=5 ORDER BY RANDOM() LIMIT 3000) ORDER BY mint, event_timestamp, slot, event_index""")
by=defaultdict(list)
for r in rows: by[r["mint"]].append((r["e"], r["vs"]/r["vt"]))
launch_ts = {x[0]:x[1] for x in q("SELECT mint,event_timestamp FROM pump_launches WHERE mint IN (%s)" % ",".join("'%s'"%m for m in by))}
res=[]
for m, pts in by.items():
    ref=[p for p in pts if p[0]>=launch_ts[m]+10]
    if not ref: continue
    t0,p0=ref[0]; fut=[p for t,p in pts if t0<t<=t0+300]
    if not fut: continue
    res.append((max(fut)/p0, fut[-1]/p0))
n=len(res)
log(f"n={n} | hit1.5 {sum(1 for a,b in res if a>=1.5)/n*100:.1f}% hit2 {sum(1 for a,b in res if a>=2)/n*100:.1f}% hit3 {sum(1 for a,b in res if a>=3)/n*100:.1f}% | median max {statistics.median([a for a,b in res]):.3f} median final {statistics.median([b for a,b in res]):.3f} | final>1 {sum(1 for a,b in res if b>1)/n*100:.1f}%")
log("(this is raw mid-price, no fees; shows unconditional base rate the rule engine must beat)")

log("\n=== 15. GRADUATION proxy: max virtual_sol_reserves reached within 600s window ===")
mv=[x[0] for x in q("SELECT MAX(virtual_sol_reserves) FROM pump_trades GROUP BY mint")]
log("mints:", len(mv), "reached >=60 SOL virtual (~30 SOL real):", sum(1 for v in mv if v>=60e9), ">=85 SOL (near graduation ~115):", sum(1 for v in mv if v>=85e9), ">=115 SOL:", sum(1 for v in mv if v>=115e9))
log("DONE")
out.close()
