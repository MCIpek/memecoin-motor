# Memecoin Motoru: Sistem, Veri ve Gelir Analizi

**Tarih:** 14 Ekim 2026
**Kapsam:** README, `memecoin_analiz_motoru_v2.md`, `src/memecoin_motor/*` (3.700 satır), 27 test, `data/memecoin_motor.db` (10,2 GB SQLite, salt-okunur incelendi), web ile pazar/fiyat doğrulaması.
**Yöntem:** Her bulgu `[DOĞRULANDI]` (kod veya veriyle), `[ÇIKARIM]` (veriden türetilmiş yorum) veya `[VARSAYIM]` (doğrulanamadı) olarak etiketlendi. Üretim verisi değiştirilmedi; veritabanı `mode=ro` ile açıldı.

---

## A) Sistemin mevcut durumu ve en kritik beş bulgu

### Sistem ne yapıyor?

Pump.fun bonding-curve programını (`6EF8rrec…`) Solana public WebSocket üzerinden dinler, `Create/CreateV2` ve `TradeEvent` olaylarını resmi IDL ile çözer, her yeni token için ilk 600 saniyeyi izler, 2/5/10/30/60 saniyelik olay-zamanlı snapshot üretir, kural tabanlı `GIRME/IZLE/ADAY` kararı verir ve cüzdansız bir paper-trade motoruyla 60/300 saniyelik sonuç etiketler. Yan hatlar: creator/ilk alıcı cüzdan analizi, sniper ve bundle kanıtı, X-bant kalibrasyonu.

Değer üreteceği kitle tasarımda "kendi işlemlerimiz" olarak tanımlı (`memecoin_analiz_motoru_v2.md` §17). Şu an **kimse için çalışan bir ürün değil; araştırma altyapısı.**

### Çalışan / yarım / yalnızca dokümanda

| Durum | Özellik | Kanıt |
|---|---|---|
| Çalışıyor | IDL decode, idempotent kayıt, slot gap tespiti, snapshot, risk kuralı, paper-v2 fill/çıkış matematiği, sniper skoru | 27/27 test geçti; `pump.json` SHA-256 README ile aynı; 58.316 launch, 2.094.977 trade; FK/orphan ihlali 0 |
| Yarım | Paper-v2 geçmiş taraması | 174.796 kararın 144.047'si (%82) hiç paper pozisyonuna dönüşmemiş; 11.155 açık pozisyonun 9.005'inin 300 sn sonucu yok; kanonik sonuçlar yalnızca **1-4 Eylül** tarihli |
| Yarım | Cüzdan/sniper zenginleştirme | Cüzdan kuyruğunda 111.194, tx kuyruğunda 20.557 bekleyen iş; sniper skoru 58.316 mint'in 4.890'ında (%8) |
| Yarım | Gap backfill | 1.276 gap "çok büyük" diye atlandı (11,6 M slot); 28 gap FAILED |
| Yalnızca dokümanda | PumpSwap takibi, ML modelleri, agentic denetim, dinamik fee/Jito replay, RugCheck/GoPlus/DEX Screener zenginleştirme, PostgreSQL | Kodda karşılığı yok (`grep` ile doğrulandı) |
| Ölü/legacy kod | `paper_positions`, `paper_outcomes`, `market_outcomes` (v1), `parser.extract_token_mints`, `paper.market_outcome` | v2 motoru kullanmıyor; CLI hâlâ gösteriyor; `Storage.initialize()` her açılışta legacy tabloya UPDATE atıyor |

### En kritik beş bulgu

**1. Collector takvim süresinin yalnızca %9,6'sında açık kalmış; "veri hattı" henüz sürekli değil. [DOĞRULANDI]**
Launch zaman damgalarında 15 dakikadan uzun boşluklara göre 36 ayrı oturum tespit edildi. Toplam kapsama 84,6 saat; takvim aralığı 885 saat. Oturumlar neredeyse hep 05:00-14:00 UTC arasında, yani bir iş günü deseninde. README "18 gün" diyor; doğru ama eksik: günlerin çoğunda 1-2 saatlik parçalar var.

**2. Public RPC'de zincirden istemciye gecikme medyan 22,5 saniye; 2/5/10 saniyelik snapshot kavramı bu kaynakla fiziksel olarak mümkün değil. [DOĞRULANDI]**
20.000 launch örnekleminde `first_seen_at - event_timestamp`: p10 4,3 sn, p50 22,5 sn, p90 173 sn, p99 396 sn. Snapshot "ON_TIME" oranlarının 2 sn'de %4, 10 sn'de %22 olmasının kök nedeni bu. Daha önemlisi: ON_TIME etiketli snapshot'ların **%41,7'si** (3.000 örneklem) pencere içindeki trade'ler istemciye ulaşmadan üretilmiş. 400 mint üzerinde yeniden hesaplamada snapshot'ların %21,9'unda `trade_count` ve `net_quote_flow` ham veriyle uyuşmuyor. Yani "ON_TIME" bile tam değil; `snapshot_quality` yalnızca üretim gecikmesini ölçüyor, veri tamlığını değil (`storage.py:1432-1433`).

**3. Risk kararına geleceğe ait bilgi sızıyor; paper sonuçları bu yüzden "karar anı" sonucu değil. [DOĞRULANDI, kod]**
`service.py:420-423` ve `493-495`: cüzdan analizi veya sniper zenginleştirmesi saatler sonra bittiğinde `score_snapshots(storage, mint, False)` ile o mint'in **tüm** snapshot kararları yeniden hesaplanıp `risk_decisions` üzerine yazılıyor (`save_risk_decision` upsert). Veride: ADAY kararlarının %44'ü (2.213/5.000) snapshot cutoff'undan 60 sn'den sonra, p90'ı 16,5 saat sonra değerlendirilmiş. Paper motoru pozisyonu "cutoff+2 sn" fiyatından açıyor ama kararı saatler sonraki bilgiyle alıyor. Ayrıca `features_json` iki farklı şemada (sniper alanları olan/olmayan, 1.034 vs 966 örneklem) fakat `ruleset_version` hep `baseline-v1` (`scoring.py:9`); karşılaştırılabilirlik yok.

**4. Kural motorunun ADAY sınıfı rastgele seçimden daha kötü; "paper baseline negatif" iddiası doğru ama yalnızca 2 güne dayanıyor. [DOĞRULANDI]**
README'deki 163 kanonik sonuç birebir doğrulandı (medyan tepe 0,945x, final 0,804x, kademeli 0,872x, 2x görülme %9,2). Ancak:
- Aynı pencerede koşulsuz taban oranı (3.000 mint örneklemi, 10 sn sonrası ilk trade'den 300 sn, ham fiyat): 2x görülme **%16,5**, 1,5x **%27,2**.
- IZLE grubu (n=1.194, yürütülebilir): 2x %17,4, ortalama final 1,026x.
- GIRME grubu (n=493): 2x %7,3, ortalama final 0,755x.
- ADAY (n=163): 2x %9,2, ortalama final 0,807x.
ADAY, hem IZLE'den hem de koşulsuz taban oranından daha az yükselen token seçiyor. Kural "güvenli görünen ama hareketsiz" tokenları seçiyor. Kademeli strateji toplam PnL: 163 × 0,1 SOL = 16,3 SOL ile **-2,23 SOL (%-13,7)**. Tüm kanonik CONTINUOUS sonuçlar 1-4 Eylül'den; sonraki 34 gün için paper hiç çalıştırılmamış. Dolayısıyla "negatif beklenti" bulgusu da, olası "pozitif" bir bulgu da henüz istatistiksel olarak dayanıksız.

**5. Restart mantığı collector kapalıyken geçen süreyi "izlendi" sayıyor; LATE satırlar bu yüzden sahte. [DOĞRULANDI, kod + veri]**
`service.py:47`: yeni process başlarken `end_snapshot_tracking(int(time.time()))` çağrılıyor; `ended_at` olarak çökme anı değil **yeniden başlama anı** yazılıyor. Çökme ile restart arasındaki saatler takip edilmiş gibi görünüyor, `create_due_snapshots` bu aralık için LATE snapshot üretiyor (LATE gecikme p50 994 sn, p90 24 saat, max 4,7 gün). 6.080 tracking kaydı hâlâ `ended_at IS NULL` (son oturum düzgün kapanmamış), 9 snapshot cutoff'u `ended_at`'ten sonra, 2 kayıtta `ended_at < launch_timestamp`. Buna rağmen LATE snapshot'lar ADAY üretebiliyor: 8.195 ADAY kararının **3.802'si (%46)** LATE snapshot'tan (LATE cezası -0,20 ile güven 0,47'ye düşüyor ama eşik 0,45).

### Diğer önemli bulgular

- **Sürüm kontrolü yok. [DOĞRULANDI]** `git log`: "branch 'main' does not have any commits yet". 3.700 satır kod ve 10 GB veri yedeksiz.
- **Depolama şişkin ve sorgular yavaş. [DOĞRULANDI]** `pump_trades` her satırda `raw_event_json` (çözülmüş alanların kopyası) taşıyor; `chain_events` 2,02 M LOG_EVENT satırında `logs_json` (ort. 628 B) ve 61.790 ham tx JSON (ort. 29,7 KB ≈ 1,8 GB). Tek tam tarama 200-400 sn. `create_due_snapshots` (`storage.py:1371-1376`) her 0,5 sn'de `token_snapshots`'ın tüm anahtarlarını (291 k satır) belleğe çekiyor; veri büyüdükçe snapshot işçisi kendi kendini boğacak.
- **Launch tx getirme kuyruğu saatlerce birikmiş. [DOĞRULANDI]** COMPLETE olaylarda `ingestion_latency_ms` p50 452 ms ama p90 23 saat, max 4,7 gün. Public RPC `getTransaction` darboğazı; tracking ancak tx geldikten sonra açıldığı için snapshot'lar baştan LATE doğuyor.
- **Gap politikası restart boşluklarını da "stream gap" sayıyor. [ÇIKARIM]** En büyük 8 gap (1,89 M slota kadar) restart anlarına denk geliyor; `SlotTracker` önceki oturumun son slotundan devam ettiği için. `MAX_BACKFILL_SLOTS=32` (~13 sn) üstü her şey atlanıyor.
- **Launch kapsaması muhtemelen eksik. [VARSAYIM]** Oturum içinde saatte ~835 launch görülüyor (günlük ~20 k hız). Eylül 2026 kamu verisi günlük ~32-34 k launch raporluyor. Saat dilimi etkisi olabilir; public WS'nin olay düşürüp düşürmediği dış kaynakla (Bitquery/Dune, aynı saat penceresi) doğrulanmalı.
- **SOL dışı quote tokenlar karışık. [DOĞRULANDI]** 3.412 launch (%5,9) SOL dışı quote (USDC 828, `pumpCm…` 580 vb.); 45.501 trade satırında `virtual_sol_reserves=0`; 17.058 snapshot'ta fiyat NULL; paper'da 883 `UNSUPPORTED_QUOTE`. Risk kuralı bu tokenları SOL ile aynı eşiklerle puanlıyor (`net_quote_flow` farklı ondalıkta).
- **Test kapsamı çekirdeği atlıyor.** `service.py` (565 satır, collector) için sıfır test; `run_paper_cycle`, `calibrate_x_bands`, WS replay testi yok. Mevcut testler saf fonksiyonları doğruluyor.
- **Güvenlik.** Cüzdan/özel anahtar yok, `sendTransaction` yok, `.env` yalnızca public URL içeriyor ve gitignore'da. SQL string birleştirmeleri sabit listelerden (`counts()`, `where` parçaları) geliyor; enjeksiyon yüzeyi yok. Dışa açık servis yok. Risk düşük. Tek not: `_stream_once` içinde `raise message.data` WS hata nesnesini istisna olarak fırlatıyor; `aiohttp` sürümüne göre tip hatası verebilir.

---

## B) Veri kalite raporu (kanıtlarıyla)

**Kaynak:** Yalnızca `api.mainnet-beta.solana.com` (confirmed), 2.078.144 olayın tamamı. Güncelleme mekanizması: elle başlatılan `memecoin-motor collect`; zamanlayıcı/servis yok. Son veri 8 Ekim 2026 05:49 UTC.

### Kapsam ve tarih aralığı

| Metrik | Değer |
|---|---|
| Launch aralığı | 2026-09-01 07:46 → 2026-10-08 05:49 UTC |
| Farklı gün | 18 (README ile uyumlu) |
| Oturum sayısı (>15 dk boşluk) | 36 |
| Kapsanan süre | 84,6 saat / 885 saat (%9,6) |
| En uzun kesintisiz oturum | 9,1 saat (7 Eylül) |
| Oturum içi launch hızı | ~835/saat |

### README sayı doğrulaması

| Tablo | README | Veritabanı | Sonuç |
|---|---:|---:|---|
| pump_launches | 58.316 | 58.316 | ✔ |
| pump_trades | 2.094.977 | 2.094.977 | ✔ |
| Trade'i olan token | 53.591 | 53.591 | ✔ |
| token_snapshots / risk_decisions | 291.358 | 291.358 / 291.358 | ✔ |
| wallet_positions | 608.540 | 608.540 | ✔ |
| wallet_profiles | 14.568 | 14.568 | ✔ |
| sniper_scores | 5.615 | 5.615 | ✔ |
| paper_v2_positions | 30.749 | 30.749 | ✔ |
| executable_outcomes_v2 | 4.389 | 4.389 | ✔ |
| Snapshot ON_TIME oranları (2/5/10/30/60 sn) | %4,0 / 10,1 / 22,5 / 26,6 / 28,2 | aynı | ✔ |
| Backfill edilen / atlanan gap | 207 / 1.276 | 207 / 1.276 (+28 FAILED, 1 DETECTED) | ✔ |
| Atlanan slot | 11,6 M | 11.626.799 | ✔ |
| Kanonik 300 sn CONTINUOUS | 163 | 163 | ✔ |
| Cüzdan kuyruğu bekleyen | ~111 k | 111.194 | ✔ |
| Tx kuyruğu bekleyen | ~20 k | 20.557 | ✔ |

README'nin sayıları dürüst. Eksik olan, bu sayıların arkasındaki **zaman kapsaması ve veri tamlığı** bilgisi.

### Bütünlük kontrolleri

| Kontrol | Sonuç |
|---|---|
| Tekrar (PK: signature, event_index / mint) | 0 |
| Trade → launch yetim | 0 |
| Trade → chain_event FK | 0 |
| Launch → chain_event / tokens_minimal | 0 / 0 |
| Trade yaşı < 0 veya > 600 sn | 0 / 0 |
| `block_time ≠ event_timestamp` (launch) | 0 |
| `quote_amount=0` trade | 248 |
| `virtual_sol_reserves=0` trade (SOL dışı quote) | 45.501 |
| Rezerv monotonluğu ihlali (300 mint, slot sırası) | 143 / 38.260 (%0,37) |
| Snapshot `cutoff > ended_at` | 9 |
| `ended_at < launch_timestamp` | 2 |
| Tracking `ended_at IS NULL` (kapanmamış) | 6.080 |
| Launch'ı olup tracking'i olmayan | 34 |
| `wallet_behavior_stats` saklanan / yeniden hesaplanan | 39.759 / 40.015 (drift) |
| Protokol fee (fee/quote) | %95 örnekte 95 bps; %25'te 0 (quote=0 veya mayhem) |

### Zaman doğruluğu

| Metrik | p10 | p50 | p90 | p99 |
|---|---:|---:|---:|---:|
| WS gelişi − blok zamanı (launch) | 4,3 sn | 22,5 sn | 173 sn | 396 sn |
| LATE snapshot gecikmesi | – | 994 sn | 24 saat | 84 saat |
| COMPLETE olay işleme gecikmesi | – | 452 ms | 23 saat | 84 saat |
| ADAY `evaluated_at − cutoff` | – | 31 sn | 16,5 saat | – |

### İşlenmiş çıktı vs ham veri

| Kontrol | Örneklem | Sonuç |
|---|---|---|
| Snapshot yeniden hesaplama | 400 mint, 2.000 snapshot | trade_count %21,9, unique_buyers %13,3, creator_sold %4,5 uyumsuz |
| ON_TIME snapshot'ta sonradan gelen trade | 3.000 snapshot | %41,7 |
| `features_json` → `evaluate()` yeniden değerlendirme | 20.000 karar | Tam şemalı 10.036 satırda **0 fark** (kural deterministik); 9.964 satır eski şemada (sniper alanları yok) |
| Paper fill gecikmesi (entry − cutoff) | 11.155 OPEN | 2 sn: %56, 8 sn: %3 |
| Paper rezerv etkisi (OPEN) | – | p50 33 bps, p90 145 bps |

### Karar dağılımı (risk_decisions)

| Yaş | ADAY | IZLE | GIRME |
|---|---:|---:|---:|
| 2 sn | 0 | 56.823 | 1.458 |
| 5 sn | 0 | 55.657 | 2.624 |
| 10 sn | 2.190 (%3,8) | 46.719 | 9.370 |
| 30 sn | 3.089 (%5,3) | 40.732 | 14.445 |
| 60 sn | 2.916 (%5,0) | 37.773 | 17.562 |

### Paper-v2 ve sonuç etiketleri (300 sn, CONTINUOUS)

| Grup | n | Medyan tepe | Medyan final | Medyan kademeli | 1,5x | 2x | 3x | Kademeli kârlı | Kademeli PnL (0,1 SOL) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Taban oranı (ham fiyat, ücret yok) | 2.544 | 1,104 | 0,866 | – | %27,2 | %16,5 | %7,6 | – | – |
| ADAY kanonik | 163 | 0,945 | 0,804 | 0,872 | %12,9 | %9,2 | %2,5 | %17,2 | −2,23 SOL |
| IZLE | 1.194 | 1,038 | 0,788 | 0,903 | %27,5 | %17,4 | %8,0 | %27,7 | −9,17 SOL |
| GIRME | 493 | 0,936 | 0,827 | 0,879 | %15,2 | %7,3 | %2,2 | %17,2 | −6,70 SOL |

Hiçbir grup ücret sonrası pozitif beklenti vermiyor. Kalibrasyon tablosu (`x_band_calibration`, 10 satır) 18 Eylül'de üretilmiş ve yine aynı 1-4 Eylül örneklemine dayanıyor; en büyük kova 205 örnek.

### Yapılamayan kontroller

- Launch kapsaması (public WS'nin kaçırdığı Create olayları) dış referans olmadan ölçülemedi. Önerilen sorgu: Bitquery `Solana.Instructions` ile 4 Eylül 05:41-13:41 UTC penceresinde `create_v2` sayısını alıp 6.670 ile karşılaştırmak.
- `wallet_positions` ile trade toplamlarının tam eşleşmesi: 608.540 pozisyonun tamamı trade toplamlarıyla (alım token, alım/satım sayısı) **0 uyumsuz** (tam tarama, 263 sn). Bu tablo güvenilir.

Ham kontrol çıktıları ve çalıştırılan betik `analiz_ekleri/` klasöründe (`dq_check.py`, `dq_results*.txt`); betik veritabanını yalnızca `mode=ro` ile açar.
- Graduation yakınlığı (bonding curve dolumu) yalnızca 600 sn penceresi içinde ölçülebiliyor; PumpSwap sonrası veri yok. 600 sn içinde ölçülebilen kadarı: 50.739 SOL-quote mint'in 1.859'u (%3,7) `virtual_sol_reserves ≥ 115 SOL` (≈ 85 SOL gerçek rezerv, curve dolumu) seviyesine ulaşmış; 2.747'si ≥ 85 SOL, 4.700'ü ≥ 60 SOL. Bu oran kamu kaynaklarındaki %1-3 graduation bandıyla uyumlu ama 600 sn sonrası izlenmediği için üst sınırdır.

---

## C) Gelir modelleri karşılaştırması ve seçilen model

### Kim, hangi sonuç için öder?

Sistemin bugün satılabilir tek varlığı **"olay-zamanı dürüstlüğü olan, yürütülebilir-fiyatla etiketlenmiş Pump.fun launch-penceresi verisi ve bunu üreten hat"**. Satılabilir olmayan: sinyal (ADAY taban oranın altında), gerçek-zamanlı uyarı (22 sn gecikme), getiri (negatif).

Pazar bağlamı [DOĞRULANDI, web, Ekim 2026]: Pump.fun günde ~25-42 k launch; graduation oranı yönteme göre %0,26-2,8; haftalık protokol geliri ~18,6 M$ (7 Ekim haftası); trading botları işlem başına ~%0,9-1 alıyor; ücretli "alpha" grupları 100-300 $/ay (satıcı beyanı). Veri/altyapı fiyat çapaları: Bitquery 49-299 $/ay, Shyft gRPC 199-649 $/ay, SolanaTracker 50-1.499 €/ay (stream 397 €'dan), Helius Business 499 $/ay (LaserStream dahil), Birdeye Premium ~199 $/ay. Kaynaklar raporun sonunda.

### Üç model

| | M1: Erken risk/sniper feed (API + Telegram) | M2: Araştırma veri seti + paper harness lisansı | M3: Kendi sermayesi / performans ücreti |
|---|---|---|---|
| Müşteri | Trenches trader'ları, küçük bot ekipleri | Bot/quant geliştiriciler, akademik araştırmacılar, bot şirketlerinin veri ekipleri | Kendisi; sonra "copy-trade" abonesi |
| Teklif | Launch sonrası ≤10 sn içinde risk skoru, creator geçmişi, bundle/sniper kanıtı | Launch-penceresi (0-600 sn) olay-zamanlı veri, latency etiketleri, yürütülebilir X etiketleri, paper motoru; Parquet + API | Kanıtlanmış pozitif beklenti ile canlı işlem |
| Fiyat mantığı | 49-149 $/ay abonelik; bot fee'sinin yanında küçük | 149-299 $/ay API veya 499-999 $ tek seferlik set; kurumsal 999 $+/ay | Performans ücreti %20 |
| Satış kanalı | X/Telegram trenches toplulukları, bot referral | Solana dev Discord'ları, X, bot ekiplerine doğrudan ulaşım, GitHub örnek notebook | – |
| İşletme maliyeti | ≥499 $/ay RPC (gRPC şart) + 7/24 VPS + nöbet | 199-499 $/ay RPC + VPS + depolama ≈ 300-700 $/ay | Sermaye + kayıp riski |
| Ön koşul | Gecikme <3 sn, uptime >%99, kuralın taban oranı yenmesi (**bugün sağlanmıyor**) | 30+ gün kesintisiz veri, P0 düzeltmeleri | Pozitif beklenti (**yok**), hukuki inceleme |
| Rekabet | RugCheck, Bubblemaps, GMGN/Axiom yerleşik filtreler (ücretsiz) | Bitquery/Dune ham veri; "yürütülebilir etiket + latency" niş | Binlerce bot |
| Zayıf nokta | Ücretsiz rakipler, latency, güven inşası | Niş ve küçük pazar; veri moat zayıf | Kanıt yok |

### Seçilen model: M2 (araştırma veri seti + harness), M1'e geçiş opsiyonu ile

Gerekçe:
1. M2'nin ön koşulları yalnızca P0 düzeltmeleridir; kural motorunun alpha üretmesini gerektirmez. M1 ve M3 bugün sağlanmayan şartlara bağlı.
2. Sistemin gerçek farkı (veri gecikmesini ölçmek, backfill'i canlı gibi etiketlememek, mikro-trade fiyatı yerine rezervden fill hesaplamak) tam olarak M2'nin alıcısının önemsediği şey.
3. M2 müşterisi düşük maliyetle test edilebilir: ödeme isteği 14 günde, kod yazmadan ölçülür (bkz. E).
4. M2 gelir getirmese bile, 30-90 gün kesintisiz veri M1 için zorunlu altyapıdır; harcanan efor boşa gitmez.

Eleştiri: M2 pazarı küçüktür ve ham veri ücretsiz/ucuz. Ödeyecek kişi, "bir haftada kendim toplarım" demeyen, etiketli-temiz veriyi hemen isteyen bot ekibidir. Bu kitlenin büyüklüğü **[VARSAYIM]**; deney bunu test eder.

### Gelir ve kâr senaryoları (aylık, USD)

Varsayımlar: RPC 499 $ (Helius Business; Shyft Build 199 $ ile düşük senaryo), VPS 60 $, Postgres/depolama 50 $, ödeme/araç 40 $ → opex 350-650 $. Kurucu emeği hariç. Ödeme komisyonu %4.

| Senaryo | Müşteri | ARPU | Gelir | Opex | Kâr |
|---|---:|---:|---:|---:|---:|
| Düşük | 3 | 99 $ | 297 $ | 350 $ | −65 $ |
| Orta | 10 | 149 $ | 1.490 $ | 650 $ | +780 $ |
| Yüksek | 30 + 2 kurumsal | 199 $ / 999 $ | 7.970 $ | 900 $ | +6.750 $ |

**Başabaş:** 650 $ opex için 149 $'dan 5 müşteri (ya da 99 $'dan 7). Kurucu zamanı 20 saat/ay × 50 $ eklenirse başabaş 12 müşteri.

### "Para kazandırıyor mu?" testi

README böyle bir iddia taşımıyor; tersini söylüyor. Veriyle teyit: 163 kanonik ADAY, 0,1 SOL/pozisyon, kademeli strateji **−%13,7**, en iyi alt grup (30 sn ADAY, n=63) bile ortalama 0,908x. 1-4 Eylül dışı dönem için paper sonucu yok; gelecek için kanıt yok.

---

## D) Önceliklendirilmiş teknik iş listesi

Format: Sorun → Kanıt → Değişiklik → Etki → Efor → Bağımlılık → Kabul kriteri.

### P0: Veri doğruluğu ve çalışmayı engelleyenler

**P0-1. Oturum modeli ve dürüst `ended_at`**
Sorun: Restart anı "izleme bitişi" sayılıyor. → Kanıt: `service.py:47`; LATE p90 24 saat; 6.080 açık tracking. → Değişiklik: `collection_sessions` tablosu (id, started_at, last_heartbeat_slot/time, ended_at, ended_reason). Her slot'ta heartbeat yaz; açılışta önceki oturumun `ended_at = last_heartbeat`. `snapshot_tracking.session_id` ekle; `create_due_snapshots` yalnızca cutoff ≤ heartbeat olan snapshot üretsin. → Etki: LATE sahteleri biter; "kesintisiz" tanımı makineyle ispatlanır. → Efor: 1,5 gün. → Bağımlılık: yok. → Kabul: Yapay kesinti testinde (collector 10 dk durdur) kesinti aralığına tek snapshot üretilmez; mevcut LATE satırlar `LEGACY_LATE` olarak işaretlenir, silinmez.

**P0-2. Karar dondurma (look-ahead sızıntısı)**
Sorun: Geç gelen cüzdan/sniper bilgisi eski kararı eziyor. → Kanıt: `service.py:420-423, 493-495`; ADAY `evaluated_at − cutoff` p90 16,5 saat. → Değişiklik: `risk_decisions` append-only (`decision_seq`), `ruleset_version`'a özellik şema hash'i ekle; paper motoru yalnızca `evaluated_at ≤ cutoff + latency` olan ilk kararı kullansın; sonraki kararlar `REVISED` olarak ayrı saklansın. → Etki: Paper sonuçları gerçekten karar-anı sonucu olur. → Efor: 1 gün. → Bağımlılık: yok. → Kabul: Yeniden skorlanan bir mint'te ilk karar satırı değişmez; paper pozisyonları `decision_seq=1`'e bağlanır; sızıntı testi (geç bilgiyi enjekte et, paper girişi değişmemeli) geçer.

**P0-3. Snapshot tamlık işareti (watermark)**
Sorun: ON_TIME snapshot'ların %41,7'si eksik veriyle üretiliyor. → Kanıt: B bölümü yeniden hesaplama. → Değişiklik: Snapshot'a `watermark_slot` ve `completeness` (LIVE/SETTLED) ekle; cutoff + lag geçince aynı snapshot'ı `SETTLED` olarak yeniden üret; model/kalibrasyon SETTLED'ı kullansın, canlı karar LIVE'ı. → Etki: Eğitim verisi doğru, canlı veri dürüst. → Efor: 1 gün. → Bağımlılık: P0-1. → Kabul: 1.000 rastgele SETTLED snapshot ham trade'den yeniden hesaplandığında %100 eşleşir.

**P0-4. Gecikme ölçümü ve ücretli WS/gRPC denemesi**
Sorun: Medyan 22,5 sn chain→client gecikme. → Kanıt: B. → Değişiklik: Her olaya `chain_lag_ms = received − block_time` yaz; Helius Business veya Shyft Build 7 günlük deneme ile aynı metriği ölç. → Etki: Erken snapshot'lar anlamlı hale gelir ya da projenin bu gecikmede yaşayamayacağı kanıtlanır. → Efor: 0,5 gün + sağlayıcı maliyeti. → Bağımlılık: yok. → Kabul: 24 saatlik koşuda `chain_lag_ms` p50 < 2.000, p90 < 5.000; aksi halde sağlayıcı değiştir.

**P0-5. Paper motorunu tüm geçmişe çalıştır**
Sorun: Kararların %82'si paper'a girmemiş; kanonik sonuçlar 2 güne sıkışmış. → Kanıt: 144.047 / 174.796; by-day tablosu. → Değişiklik: P0-2 sonrası `paper-run`'ı toplu çalıştır; `GAP_AFFECTED` ve `LEGACY_LATE` dışla; sonuçları tarih sıralı raporla. → Etki: Kural motorunun değeri ilk kez 18 gün üzerinde ölçülür. → Efor: 0,5 gün + hesaplama süresi. → Bağımlılık: P0-1, P0-2, P1-1 (performans). → Kabul: 10/30/60 sn tüm ADAY/IZLE/GIRME kararlarının 300 sn sonucu var; gün bazlı rapor üretildi.

**P0-6. Git ve yedek**
Sorun: Hiç commit yok. → Değişiklik: `git init`, ilk commit, uzak depo; DB için haftalık `VACUUM INTO` yedeği. → Efor: 1 saat. → Kabul: Uzak depoda kod; yedek dosyası geri yüklenerek `status` çalışıyor.

### P1: İlk ücretli kullanımı mümkün kılanlar

**P1-1. Depolama diyeti ve O(n) döngüler**
Sorun: 10 GB, 200-400 sn tarama, 0,5 sn'de 291 k satır okuma. → Kanıt: `storage.py:1371-1376`; boyut ölçümleri. → Değişiklik: `pump_trades.raw_event_json` kaldır (decode edilmiş alanlar yeterli; IDL sürümü sakla); ham tx JSON'ı zstd ile dosya sistemine taşı; `snapshot_due` kuyruk tablosu (mint, age, due_at) ile snapshot işçisi; `risk_feature_rows` korelasyonlu alt sorgular yerine önceden toplanmış `mint_wallet_stats`. → Etki: DB ≈ 3 GB; işçi sabit zamanlı. → Efor: 2 gün. → Bağımlılık: P0-6. → Kabul: `status` < 5 sn; snapshot döngüsü 100 k tracking ile < 50 ms.

**P1-2. SOL dışı quote normalizasyonu**
Değişiklik: `quote_decimals` sakla, `net_quote_flow`'u SOL eşdeğerine çevir ya da SOL dışıları açıkça `UNSUPPORTED` olarak karar/kalibrasyon dışı bırak. → Efor: 0,5 gün. → Kabul: Snapshot'ta NULL fiyat yalnızca `quote_asset≠SOL` satırlarda ve bunlar `decision='UNSUPPORTED'`.

**P1-3. Servisleştirme ve gözlemlenebilirlik**
Değişiklik: NSSM/systemd servisi, otomatik yeniden başlatma, `/health` ve Prometheus metrikleri (chain_lag, gap sayısı, kuyruk derinliği, RPC 429/timeout), Telegram alarmı. → Efor: 1,5 gün. → Kabul: 7 gün kesintisiz koşu; kesintide 5 dk içinde alarm.

**P1-4. Dışa aktarım ve ürün yüzeyi (M2)**
Değişiklik: Günlük Parquet export (launches, trades, snapshots SETTLED, decisions, outcomes, sessions); API anahtarlı salt-okunur FastAPI (3-4 endpoint); README-tarzı veri sözlüğü; örnek notebook. Ödeme: Stripe Payment Link veya Lemon Squeezy; anahtar e-postayla. → Efor: 3 gün. → Bağımlılık: P1-1. → Kabul: Yeni müşteri 10 dakikada örnek notebook'u kendi anahtarıyla çalıştırabiliyor.

**P1-5. Çekirdek testler**
Değişiklik: WS replay fixture'ı ile `_handle_logs`/`_handle_slot` testi, `run_paper_cycle` uçtan uca testi, oturum/kesinti testi, sızıntı testi. → Efor: 1,5 gün. → Kabul: `service.py` ve `paper_engine.py` için satır kapsaması > %70.

**P1-6. Gap tanımını ayır**
Değişiklik: Oturum başlangıcındaki boşluk `SESSION_GAP`, oturum içi `STREAM_GAP`; `MAX_BACKFILL_SLOTS`'u ücretli RPC ile 300'e çıkar. → Efor: 0,5 gün. → Kabul: `stream_gaps` içinde restart kaynaklı satır kalmaz.

### P2: Ölçekleme ve işletme verimliliği

**P2-1. PostgreSQL migrasyonu** (README planı) — yalnızca P1-1 sonrası hâlâ gerekiyorsa; `pump_trades` bölümleme, `SKIP LOCKED` kuyruklar. Efor 3 gün.
**P2-2. PumpSwap sonrası takip ve 1h/6h/24h etiketler** — M1 ve ML için şart. Efor 4 gün.
**P2-3. İki aday sınıfı A/B ve kural revizyonu** — Yalnızca P0-5 sonrası, IZLE'nin neden daha iyi olduğunu görerek. Efor 2 gün.
**P2-4. ML** — Birkaç bin SETTLED+CONTINUOUS kanonik sonuç ve en az iki piyasa dönemi birikmeden başlama.
**P2-5. Yetkilendirme/ödeme otomasyonu** — Müşteri 10'u geçince anahtar yönetimi, kullanım ölçümü, faturalama.

Yapılmaması gerekenler: Yeniden yazma, dil/framework değişimi, Telegram sinyal botu (kural taban oranı yenmiyor), agent katmanı.

---

## E) 7 / 30 / 90 günlük uygulama planı

### İlk 7 gün: Kritik doğrulamalar ve düzeltmeler

Teslimatlar: P0-6 (gün 1), P0-1, P0-2, P0-3, P0-4 (ücretli RPC denemesi), P0-5 başlangıcı. Mevcut DB'nin salt-okunur arşiv kopyası.
Başarı ölçütü: 72 saat kesintisiz koşu; `chain_lag_ms` p50 < 2 sn; 10 sn ON_TIME ≥ %80; yapay kesinti testinde sahte snapshot 0; sızıntı testi geçer.
Devam/durdur: Ücretli RPC ile bile p50 gecikme > 5 sn ise erken-snapshot ürünü (M1) kalıcı olarak rafa; M2'ye odaklan. Gecikme düzeliyorsa M1 opsiyonu açık kalır.

### İlk 30 gün: Satılabilir minimum sürüm ve pilot

Teslimatlar: P1-1, P1-2, P1-3, P1-4, P1-5; 21+ gün kesintisiz veri; tam geçmiş üzerinde paper raporu (gün bazlı). **Ödeme isteği deneyi** (aşağıda) gün 8-21 arasında.
Başarı ölçütü: Uptime > %98; veri seti ≥ 500 saat; 3 ücretli pilot (toplam ≥ 300 $/ay) veya 2 ön ödeme.
Devam/durdur: 14 günlük deneyde 0 ödeme ve < 5 nitelikli görüşme → M2 fiyatını/kitleyi bir kez değiştir, 14 gün daha; yine 0 ise ticari hedefi durdur, sistemi kişisel araştırma aracı olarak tut.

### İlk 90 gün: Talep doğrulaması, sürdürülebilir gelir, ölçekleme

Teslimatlar: 10+ müşteri hedefi; P1-6, P2-2 (PumpSwap) ; kural motorunun 60+ gün SETTLED veride taban oranla karşılaştırılması; müşteri geri bildirimiyle 2. veri ürünü (ör. sniper/bundle cüzdan listesi).
Başarı ölçütü: MRR ≥ 1.500 $ (opex'in 2 katı); churn < %20/ay; chain_lag p50 < 2 sn ile 60 gün.
Devam/durdur: MRR < 650 $ ise altyapıyı en ucuz RPC'ye indir ve ürünü açık kaynak + danışmanlık modeline çevir. Kural motoru taban oranı yeniyorsa (2x görülme ≥ taban + 5 puan, n ≥ 1.000) M1 için 30 günlük ek plan yaz.

### Ödeme isteği deneyi (büyük geliştirme öncesi)

Kod yazmadan, 14 gün:
1. Mevcut veriden 4 Eylül oturumu (8 saat, 6.670 launch) temiz Parquet örnek seti üret; veri sözlüğü ve 1 notebook ("gerçekçi fill ile 300 sn X dağılımı").
2. Tek sayfalık açıklama + fiyat: "30 gün kesintisiz launch-penceresi veri seti + paper harness, 149 $/ay, ilk 5 müşteriye 99 $". Stripe/Lemon Squeezy ödeme linki.
3. 20 doğrudan ulaşım (Solana dev Discord, X'te bot geliştiren hesaplar, 2 bot ekibi), 2 açık paylaşım.
4. Ölçüt: ≥ 3 ödeme veya ≥ 5 "veri gelince alırım" yazılı taahhüdü → P1-4'e yatırım. Aksi → dur, nedenleri yaz.

---

## F) İlk yapılacak somut iş ve kabul kriteri

**İş:** P0-6 + P0-1 birlikte: depoyu Git'e al, ardından `collection_sessions` tablosu ve heartbeat tabanlı dürüst `ended_at` mantığını uygula; mevcut LATE satırları `LEGACY_LATE` olarak işaretle.

**Neden ilk bu:** Diğer her ölçüm (paper, kalibrasyon, gecikme, müşteri verisi) "collector gerçekten ne zaman açıktı" sorusuna dayanıyor; README'nin kendi 1. önceliği de bu.

**Kabul kriterleri:**
1. `git log` en az bir commit gösterir; `.env`, `data/*.db` depoda yoktur.
2. `collection_sessions` tablosu vardır; collector her slot'ta `last_heartbeat_at/slot` günceller; açılışta önceki açık oturumu `ended_at = last_heartbeat_at` ile kapatır (restart zamanı ile değil).
3. Collector 10 dakika durdurulup başlatıldığında, kesinti aralığına düşen cutoff'lar için **hiç** snapshot üretilmez; kesinti `collection_sessions`'ta tek satır olarak görünür.
4. Mevcut 291.358 snapshot'ın cutoff'u bir oturum aralığına düşmeyenleri `snapshot_quality='LEGACY_LATE'` alır; silinmez; `calibrate-x` ve paper raporları bu satırları dışlar.
5. Yeni test: `tests/test_sessions.py` kesinti senaryosunu kapsar; `pytest` 28+/28+ geçer.
6. `memecoin-motor status` oturum sayısı ve toplam kapsanan saati yazdırır; mevcut veri için 36 oturum / ~84,6 saat ile uyumludur.

---

## Ek: Kaynaklar (web doğrulaması)

- Pump.fun launch/graduation: [Solana Compass](https://solanacompass.com/news/pumpfun-launched-42000-tokens-in-one-day-fewer-than-2-will-ever-reach-a-dex), [DEXTools](https://www.dextools.io/news/pump-fun-graduation-collapse-solana-fees-2026), [pumpfundata](https://pumpfundata.com/blog/pumpfun-graduation-rate-analysis), [Medium cohort yöntemi](https://medium.com/coinmonks/pump-fun-api-how-to-track-bonding-curves-graduations-and-pumpswap-on-chain-879b689fbedb), [Cryptopolitan](https://www.cryptopolitan.com/pump-fun-graduating-tokens-break-to-1-15-of-new-launches/)
- Protokol geliri Ekim 2026: [CoinMarketCap](https://coinmarketcap.com/cmc-ai/pump-fun/latest-updates/)
- Fee yapısı: [Blockworks](https://blockworks.com/news/pumpdotfun-fee-model), [The Block](https://www.theblock.co/post/354038/pumpswap-revenue-tokens), [Cointelegraph](https://cointelegraph.com/news/pump-fun-creator-fee-cap-update-memecoin-model)
- RPC/veri fiyatları: [Helius pricing](https://helius.dev/pricing), [Helius credits](https://helius.dev/docs/billing/credits), [Shyft gRPC](https://www.shyft.to/solana-yellowstone-grpc), [Bitquery Pump.fun API](https://bitquery.io/products/pumpfun-api), [SolanaTracker pricing](https://docs.solanatracker.io/pricing), [Birdeye karşılaştırma](https://madeonsol.com/api-alternatives/birdeye), [Nansen API](https://api-docs.nansen.ai/reference/pricing)
- Bot ücretleri: [solanatools.io](https://solanatools.io/blog/solana-trading-bot-fees-compared), [memegateway](https://memegateway.com/academy/solana-trading-bot-fees-compared-2026/), [madeonsol Trojan](https://madeonsol.com/blog/trojan-bot-review)
- Ücretli alpha grupları (satıcı beyanı): [Gumroad ilanı](https://memecointrenches.gumroad.com/l/discordmembership); sniper bot vakası: [Transak](https://transak.com/blog/crypto-memecoin-sniping-guide)
- Graduation eşiği/PumpSwap: [madeonsol PumpSwap](https://madeonsol.com/blog/what-is-pumpswap)

Not: Fiyat ve oran kaynaklarının bir kısmı satıcı veya affiliate içeriğidir; bütçe kararından önce resmi sayfalardan teyit edilmelidir.
