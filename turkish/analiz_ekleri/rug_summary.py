"""Per-coin autopsy from local trades (first 600 s) + on-chain state + PumpSwap ATH. Read-only. Writes CSV + summary."""
import sys; sys.stdout.reconfigure(encoding="utf-8")
import csv, json, sqlite3, statistics, datetime, time
from collections import Counter, defaultdict
from itertools import groupby

ROOT = r"C:/Users/PD/project_claude/memecoin/"
DB = ROOT + "data/memecoin_motor.db"
EK = ROOT + "analiz_ekleri/15x/"
OUT_CSV = ROOT + "analiz_ekleri/coin_otopsi.csv"
OUT_TXT = ROOT + "analiz_ekleri/coin_otopsi_ozet.txt"
P0 = 30e9 / 1.073e15            # launch price (lamports per raw token unit ratio)
GRAD_X = (115 / 30) ** 2
HEALTHY = {"2026-09-01","2026-09-03","2026-09-04","2026-09-07","2026-09-08","2026-09-09","2026-09-15","2026-09-16","2026-09-17"}
t0 = time.time()
out = open(OUT_TXT, "w", encoding="utf-8")
def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); out.write(s + "\n")

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True); con.row_factory = sqlite3.Row
L = {r["mint"]: dict(r) for r in con.execute("SELECT mint,symbol,event_timestamp,creator,is_mayhem_mode,quote_asset FROM pump_launches")}
C = {json.loads(l)["mint"]: json.loads(l) for l in open(EK + "curves.jsonl")}
ATH = {}
for l in open(EK + "ath_graduated.jsonl", encoding="utf-8"):
    r = json.loads(l); lst = r.get("ohlcv") or []
    if lst:
        ATH[r["mint"]] = {"ath": max(min(c[2], 3 * max(c[1], c[4])) for c in lst), "last": lst[0][4], "ath_ts": max(lst, key=lambda c: min(c[2], 3*max(c[1], c[4])))[0]}
GRAD_PRICE_SOL = 30 / 1.073e9 * GRAD_X       # SOL per token at curve full
LAUNCH_PRICE_SOL = 30 / 1.073e9
log(f"loaded meta {time.time()-t0:.0f}s")

import csv as _csv
def _v(x):
    if x in ("", "None"): return None
    if x in ("True", "False"): return x == "True"
    try: return int(x)
    except ValueError:
        try: return float(x)
        except ValueError: return x
rows = [{k: _v(v) for k, v in r.items()} for r in _csv.DictReader(open(OUT_CSV, encoding="utf-8-sig"), delimiter=";")]
log(f"read {len(rows)} rows from csv")
H = [r for r in rows if r["veri_saglikli"] and not r["mayhem"]]
log(f"\n=== ÖZET: sağlıklı günler (1-17 Eylül), mayhem dışı, trade'i olan coin: {len(H)} ===")
mx = [r["max_x_600s"] for r in H]
log("İlk 600 sn içinde ulaşılan max X (launch fiyatına göre):")
for lo, hi in ((0, 1.1), (1.1, 1.5), (1.5, 2), (2, 3), (3, 5), (5, 10), (10, 14.4), (14.4, 1e9)):
    k = sum(1 for v in mx if lo <= v < hi); log(f"   {lo:>5}x - {hi if hi < 1e9 else '∞':>5}x : {k:6d}  ({k/len(H)*100:5.1f}%)")
log(f"   medyan {statistics.median(mx):.2f}x")
pumped = [r for r in H if r["max_x_600s"] >= 1.5 and not r["graduate"]]
log(f"\nYükselip graduate OLMAYAN (max ≥1,5x): {len(pumped)}")
zs = [r["zirve_saniye"] for r in pumped]
log(f"   zirve anı (launch'tan saniye): medyan {statistics.median(zs):.0f}  ilk 10 sn {sum(1 for v in zs if v<=10)/len(zs)*100:.1f}%  ilk 60 sn {sum(1 for v in zs if v<=60)/len(zs)*100:.1f}%  ilk 300 sn {sum(1 for v in zs if v<=300)/len(zs)*100:.1f}%")
dds = [r["zirveden_dusus_pct"] for r in pumped]
log(f"   zirveden 600 sn içindeki düşüş: medyan %{statistics.median(dds):.0f}  ≥%50 {sum(1 for v in dds if v>=50)/len(dds)*100:.1f}%  ≥%80 {sum(1 for v in dds if v>=80)/len(dds)*100:.1f}%")
t80 = [r["80pct_dusus_sn_zirveden"] for r in pumped if r["80pct_dusus_sn_zirveden"] is not None]
if t80: log(f"   %80 düşüş zirveden kaç sn sonra: medyan {statistics.median(t80):.0f}  ≤10 sn {sum(1 for v in t80 if v<=10)/len(t80)*100:.1f}%  ≤60 sn {sum(1 for v in t80 if v<=60)/len(t80)*100:.1f}%")
t50 = [r["50pct_dusus_sn_zirveden"] for r in pumped if r["50pct_dusus_sn_zirveden"] is not None]
if t50: log(f"   %50 düşüş zirveden kaç sn sonra: medyan {statistics.median(t50):.0f}  ≤10 sn {sum(1 for v in t50 if v<=10)/len(t50)*100:.1f}%  ≤60 sn {sum(1 for v in t50 if v<=60)/len(t50)*100:.1f}%")
d = Counter(r["en_buyuk_satici"] for r in pumped)
log(f"   en büyük tek düşüşü yapan satıcı: " + ", ".join(f"{k}: {v} ({v/len(pumped)*100:.1f}%)" for k, v in d.most_common()))
bd = [r["en_buyuk_tek_satis_dususu_pct"] for r in pumped]
log(f"   tek bir satışın yarattığı en büyük düşüş: medyan %{statistics.median(bd):.0f}  ≥%30 {sum(1 for v in bd if v>=30)/len(bd)*100:.1f}%  ≥%50 {sum(1 for v in bd if v>=50)/len(bd)*100:.1f}%")
cs = [r for r in pumped if r["creator_satis_sol"] > 0]
log(f"   creator 600 sn içinde sattı: {len(cs)} ({len(cs)/len(pumped)*100:.1f}%)  ilk satış medyan {statistics.median([r['creator_ilk_satis_sn'] for r in cs]):.0f} sn")
log(f"   ilk 3 alıcının toplam satıştaki payı: medyan %{statistics.median([r['top3_alicinin_satis_payi'] for r in pumped])*100:.0f}")

log("\nSınıflar (sağlıklı günler, mayhem dışı):")
for k, v in Counter(r["sinif"] for r in H).most_common():
    log(f"   {k:30s} {v:6d}  ({v/len(H)*100:5.1f}%)")

log("\nEn yüksek max X'e ulaşan, graduate OLMAYAN 15 coin (600 sn içinde):")
for r in sorted(pumped, key=lambda r: -r["max_x_600s"])[:15]:
    log(f"   {r['symbol'][:14]:14s} {r['mint'][:8]}… max {r['max_x_600s']:5.2f}x @ {r['zirve_saniye']:3d} sn | düşüş %{r['zirveden_dusus_pct']:.0f} | %80 düşüş +{r['80pct_dusus_sn_zirveden']} sn | büyük satıcı {r['en_buyuk_satici']} ({r['en_buyuk_satis_sol']} SOL) | bugün eğri {r['egri_bugun_x_launch']}x")

G = [r for r in H if r["graduate"] and r["pumpswap_zirve_x_launch"]]
log(f"\nGraduate olanlar (PumpSwap verisi olan {len(G)}): launch fiyatına göre")
for lab, sub in (("600 sn sonrası graduate", [r for r in G if r["sinif"].startswith("GRADUATE (600 sn sonrası)")]), ("paketli anında dolum", [r for r in G if r["sinif"] == "PAKETLİ ANINDA DOLUM"])):
    if not sub: continue
    z = [r["pumpswap_zirve_x_launch"] for r in sub]; b = [r["pumpswap_bugun_x_launch"] for r in sub if r["pumpswap_bugun_x_launch"] is not None]
    log(f"   {lab:26s} n={len(sub):4d}  zirve medyan {statistics.median(z):.1f}x  p90 {sorted(z)[int(len(z)*.9)]:.1f}x  | bugün medyan {statistics.median(b):.2f}x  bugün <1x {sum(1 for v in b if v<1)/len(b)*100:.0f}%")
log(f"\ndone {time.time()-t0:.0f}s")
out.close()
