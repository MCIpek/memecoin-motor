"""Graduate sonrası dakikalık strateji testi (PumpSwap). Giriş: migrasyondan k dk sonra, o dakikanın açılışı. Çıkışlar: tut T dk, hedef/stop, iz süren.
Filtreler: ilk k dakikadaki getiri/hacim. Train/test: migrasyon tarihine göre (<= 09-21 train)."""
import sys; sys.stdout.reconfigure(encoding="utf-8")
import json, os, statistics, datetime
from collections import defaultdict
G = r"C:/Users/PD/AppData/Local/Temp/claude/C--Users-PD-project-claude-memecoin/5a0f1dfe-1637-4fac-95a3-1703257554c2/scratchpad/gecko/"
OUT = r"C:/Users/PD/project_claude/memecoin/analiz_ekleri/pumpswap_dakika_testi.txt"
FEE = 0.03          # PumpSwap: 0.25-0.3% swap + bot fee ~1% + slippage; 3% toplam gidiş-dönüş varsayımı
out = open(OUT, "w", encoding="utf-8")
def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); out.write(s + "\n")
rows = [json.loads(l) for l in open(G + "minute_graduated.jsonl", encoding="utf-8")]
rows = [r for r in rows if r["n"] >= 10]
EARLY = set(json.load(open(G + "early.json")))
for r in rows:
    r["ohlcv"].sort(key=lambda c: c[0])
    r["instant"] = r["mint"] in EARLY
    # trimmed high: wick capped at 1.5x the candle body top (self-traded pools print absurd wicks)
    r["ohlcv"] = [[c[0], c[1], min(c[2], 1.5 * max(c[1], c[4])), c[3], c[4], c[5]] for c in r["ohlcv"]]
GROUPS = {"600 sn SONRASI graduate (erişilebilir)": [r for r in rows if not r["instant"]], "anında dolum (paketli)": [r for r in rows if r["instant"]]}
log(f"pools with >=10 minute candles: {len(rows)}  (candles median {statistics.median(r['n'] for r in rows):.0f})")
def period(r): return "train" if datetime.datetime.utcfromtimestamp(r["t_mig"]).strftime("%Y-%m-%d") <= "2026-09-21" else "test"

def series(r):
    """minute index from migration -> candle (o,h,l,c,v). gaps = no trade that minute."""
    return {int((c[0] - r["t_mig"]) // 60): c[1:] for c in r["ohlcv"]}
def run(r, k, policy):
    s = series(r); keys = sorted(s)
    ent = next((i for i in keys if i >= k), None)
    if ent is None: return None
    pe = s[ent][0]            # open of entry minute
    if pe <= 0: return None
    path = [(i, s[i]) for i in keys if i > ent]
    if not path: return None
    return policy(path, pe, ent) * (1 - FEE)
def p_hold(T):
    def f(path, pe, ent):
        for i, (o, h, l, c, v) in path:
            if i >= ent + T: return c / pe
        return path[-1][1][3] / pe
    return f
def p_tpsl(tp, sl):
    def f(path, pe, ent):
        for i, (o, h, l, c, v) in path:
            if l / pe <= sl: return sl          # stop assumed to fill at level (optimistic in crash)
            if h / pe >= tp: return tp
        return path[-1][1][3] / pe
    return f
def p_trail(tr, T=None):
    def f(path, pe, ent):
        peak = pe
        for i, (o, h, l, c, v) in path:
            if T and i >= ent + T: return c / pe
            peak = max(peak, h)
            if c <= peak * (1 - tr): return c / pe
        return path[-1][1][3] / pe
    return f
POL = {
 "3 dk tut": p_hold(3), "5 dk tut": p_hold(5), "10 dk tut": p_hold(10), "30 dk tut": p_hold(30), "2 saat tut": p_hold(120), "6 saat tut": p_hold(360), "16 saat tut": p_hold(960),
 "2x hedef / -30% stop": p_tpsl(2.0, 0.7), "1.5x hedef / -25% stop": p_tpsl(1.5, 0.75), "3x hedef / -40% stop": p_tpsl(3.0, 0.6),
 "iz süren %25": p_trail(0.25), "iz süren %40": p_trail(0.40), "iz süren %25, max 2 saat": p_trail(0.25, 120),
}
def feat(r, k):
    s = series(r); keys = [i for i in sorted(s) if i < k]
    if not keys: return None
    first = s[keys[0]]; last = s[keys[-1]]
    ret = last[3] / first[0] if first[0] else None
    vol = sum(s[i][4] for i in keys)
    mins_traded = len(keys)
    return {"ret_k": ret, "vol_k": vol, "mins": mins_traded}
FILT = {
 "hepsi": lambda f: True,
 "ilk k dk getiri > +20%": lambda f: f["ret_k"] and f["ret_k"] > 1.2,
 "ilk k dk getiri < -20%": lambda f: f["ret_k"] and f["ret_k"] < 0.8,
 "ilk k dk getiri -20%..+20%": lambda f: f["ret_k"] and 0.8 <= f["ret_k"] <= 1.2,
 "ilk k dk hacim üst %25": None,   # filled below
 "her dakika işlem gördü": lambda f: f["mins"] >= 1 and f["mins"] == f["_k"],
}
def fmt(v):
    if not v: return "n=0"
    w = [min(x, 10.0) for x in v]
    m = statistics.mean(w); se = statistics.pstdev(w) / len(w) ** 0.5
    return f"n={len(v):4d} ort(10x tavan) {(m-1)*100:+6.1f}% (±{se*100:.1f}) kazan {sum(x>1 for x in v)/len(v)*100:3.0f}% medyan {statistics.median(v):.3f}"

log("\n=== A. Migrasyondan k dk sonra gir, filtre yok (gruplara göre) ===")
for gname, grp in GROUPS.items():
    log(f"\n### {gname}: {len(grp)} havuz")
    for k in (1, 5, 15):
        log(f"\n  giriş: +{k} dk")
        for pname, pf in POL.items():
            tr_ = [x for r in grp if period(r) == "train" and (x := run(r, k, pf)) is not None]
            te = [x for r in grp if period(r) == "test" and (x := run(r, k, pf)) is not None]
            log(f"    {pname:28s} | train {fmt(tr_)} | test {fmt(te)}")

rows_all = rows; rows = GROUPS["600 sn SONRASI graduate (erişilebilir)"]
log("\n=== B. Filtreler (yalnız erişilebilir grup; giriş +5 dk ve +15 dk), seçili çıkışlar ===")
for k in (5, 15):
    feats = {r["mint"]: feat(r, k) for r in rows}
    vols = sorted(f["vol_k"] for f in feats.values() if f)
    q75 = vols[int(len(vols) * .75)] if vols else 0
    FILT["ilk k dk hacim üst %25"] = lambda f, q=q75: f["vol_k"] >= q
    log(f"\n  giriş +{k} dk")
    for fname, ff in FILT.items():
        for pname in ("5 dk tut", "30 dk tut", "1.5x hedef / -25% stop", "2x hedef / -30% stop", "iz süren %25"):
            sel = []
            for r in rows:
                f = feats[r["mint"]]
                if not f: continue
                f["_k"] = k
                if not ff(f): continue
                sel.append(r)
            tr_ = [x for r in sel if period(r) == "train" and (x := run(r, k, POL[pname])) is not None]
            te = [x for r in sel if period(r) == "test" and (x := run(r, k, POL[pname])) is not None]
            log(f"    {fname:30s} {pname:22s} | train {fmt(tr_)} | test {fmt(te)}")

log("\n=== C. Migrasyon sonrası yol (yalnız erişilebilir grup): dakika bazında fiyat (migrasyon dakikası açılışı = 1.0) ===")
for mins in (1, 5, 15, 30, 60, 120, 360, 960):
    v = []
    for r in rows:
        s = series(r); keys = sorted(s)
        if not keys or s[keys[0]][0] <= 0: continue
        p0 = s[keys[0]][0]
        c = next((s[i][3] for i in keys if i >= mins), None)
        if c: v.append(c / p0)
    if v: log(f"   +{mins:4d} dk: n={len(v):4d} medyan {statistics.median(v):.3f}  ort(10x tavan) {statistics.mean([min(x,10) for x in v]):.3f}  >1 {sum(x>1 for x in v)/len(v)*100:.0f}%  ≥2x {sum(x>=2 for x in v)/len(v)*100:.1f}%")
peak_min = []
for r in rows:
    s = series(r); keys = sorted(s)
    if not keys: continue
    pk = max(keys, key=lambda i: s[i][1]); peak_min.append(pk)
log(f"   zirve dakikası: medyan {statistics.median(peak_min):.0f}  ≤5 dk {sum(x<=5 for x in peak_min)/len(peak_min)*100:.0f}%  ≤30 dk {sum(x<=30 for x in peak_min)/len(peak_min)*100:.0f}%  ≤2 saat {sum(x<=120 for x in peak_min)/len(peak_min)*100:.0f}%")
log("\nNot: dakikalık mum 'high'ı fitil içerir; hedef dolumu iyimser, stop dolumu da seviyeden varsayıldı. Ücret %3 gidiş-dönüş.")
