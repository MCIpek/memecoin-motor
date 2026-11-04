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

rows = []
cur = con.execute("""SELECT mint, event_timestamp ts, is_buy, user_address u, sol_amount a, token_amount t,
                     virtual_sol_reserves vs, virtual_token_reserves vt FROM pump_trades
                     ORDER BY mint, event_timestamp, slot, event_index""")
n = 0
for mint, grp in groupby(cur, key=lambda r: r["mint"]):
    l = L.get(mint)
    if not l or l["quote_asset"] != "SOL": continue
    tr = [r for r in grp if r["vt"] > 0]
    if not tr: continue
    n += 1
    if n % 5000 == 0: log(f"  {n} coins {time.time()-t0:.0f}s")
    lt = l["event_timestamp"]; creator = l["creator"]
    px = [(r["ts"] - lt, (r["vs"] / r["vt"]) / P0) for r in tr]
    ip = max(range(len(px)), key=lambda i: px[i][1]); t_peak, x_peak = px[ip]
    after = px[ip:]
    x_min_after = min(x for _, x in after)
    dd = 1 - x_min_after / x_peak if x_peak > 0 else 0
    t50 = next((a - t_peak for a, x in after if x <= 0.5 * x_peak), None)
    t80 = next((a - t_peak for a, x in after if x <= 0.2 * x_peak), None)
    x_end = px[-1][1]
    # who sold: creator, and the biggest single price-moving sell after peak
    buys_by = defaultdict(int); sells_by = defaultdict(int); sold_sol_by = defaultdict(int)
    for r in tr:
        if r["is_buy"]: buys_by[r["u"]] += r["a"]
        else: sells_by[r["u"]] += r["t"]; sold_sol_by[r["u"]] += r["a"]
    creator_sold_sol = sold_sol_by.get(creator, 0) / 1e9
    creator_bought_sol = buys_by.get(creator, 0) / 1e9
    creator_first_sell = next((r["ts"] - lt for r in tr if not r["is_buy"] and r["u"] == creator), None)
    # biggest drop caused by a single trade (relative), after peak
    big_drop, big_drop_t, big_drop_u, big_drop_sol = 0, None, None, 0
    for i in range(max(1, ip), len(tr)):
        if tr[i]["is_buy"]: continue
        prev = (tr[i-1]["vs"] / tr[i-1]["vt"]); now = (tr[i]["vs"] / tr[i]["vt"])
        d = 1 - now / prev if prev > 0 else 0
        if d > big_drop: big_drop, big_drop_t, big_drop_u, big_drop_sol = d, tr[i]["ts"] - lt, tr[i]["u"], tr[i]["a"] / 1e9
    top3 = sorted(buys_by, key=buys_by.get, reverse=True)[:3]
    sell_sol_total = sum(sold_sol_by.values())
    top3_sell_share = (sum(sold_sol_by.get(u, 0) for u in top3) / sell_sol_total) if sell_sol_total else 0
    dumper = ("creator" if big_drop_u == creator else "top3_buyer" if big_drop_u in top3 else "other") if big_drop_u else None
    c = C.get(mint, {}); grad = bool(c.get("complete"))
    filled_600 = x_peak >= GRAD_X * 0.98
    a = ATH.get(mint)
    now_x = ((c["vq"] / c["vt"]) / P0) if c.get("vt") else None
    ps_ath_x = a["ath"] / LAUNCH_PRICE_SOL if a else None
    ps_now_x = a["last"] / LAUNCH_PRICE_SOL if a else None
    day = datetime.datetime.utcfromtimestamp(lt).strftime("%Y-%m-%d")
    # classification (only meaningful for healthy days & non-mayhem)
    if l["is_mayhem_mode"]: cls = "MAYHEM (fiyat güvenilmez)"
    elif grad and t_peak <= 2 and filled_600: cls = "PAKETLİ ANINDA DOLUM"
    elif grad: cls = "GRADUATE (600 sn sonrası)" if not filled_600 else "GRADUATE (600 sn içinde)"
    elif x_peak < 1.5: cls = "HİÇ YÜKSELMEDİ (<1,5x)"
    elif t80 is not None and creator_first_sell is not None and big_drop_u == creator: cls = "CREATOR RUG"
    elif t80 is not None and dumper == "top3_buyer": cls = "İLK ALICI DUMP"
    elif t80 is not None: cls = "POMPALA-BOŞALT (diğer)"
    else: cls = "SÖNDÜ (%80 düşüş yok)"
    rows.append({
        "mint": mint, "symbol": l["symbol"], "gun": day, "veri_saglikli": day in HEALTHY, "mayhem": bool(l["is_mayhem_mode"]),
        "trade_600s": len(tr), "max_x_600s": round(x_peak, 3), "zirve_saniye": t_peak,
        "zirveden_dusus_pct": round(dd * 100, 1), "50pct_dusus_sn_zirveden": t50, "80pct_dusus_sn_zirveden": t80,
        "x_600s_sonu": round(x_end, 3), "en_buyuk_tek_satis_dususu_pct": round(big_drop * 100, 1),
        "en_buyuk_satis_saniye": big_drop_t, "en_buyuk_satis_sol": round(big_drop_sol, 3), "en_buyuk_satici": dumper,
        "creator_alim_sol": round(creator_bought_sol, 3), "creator_satis_sol": round(creator_sold_sol, 3), "creator_ilk_satis_sn": creator_first_sell,
        "top3_alicinin_satis_payi": round(top3_sell_share, 3),
        "graduate": grad, "pumpswap_zirve_x_launch": round(ps_ath_x, 2) if ps_ath_x else None,
        "pumpswap_bugun_x_launch": round(ps_now_x, 3) if ps_now_x else None,
        "egri_bugun_x_launch": round(now_x, 3) if now_x else None, "sinif": cls,
    })
log(f"computed {len(rows)} coins {time.time()-t0:.0f}s")

with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=";"); w.writeheader(); w.writerows(rows)
log("csv written:", OUT_CSV)

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
