# Türkçe Dokümantasyon / Turkish Documentation

Bu dosya, deponun Türkçe orijinal dokümanlarını tek yerde toplar. İngilizce sürümler ana dizindedir.
This file collects the original Turkish documents in one place. English versions live in the repository root.

## İçindekiler
1. README (Türkçe orijinal)
2. Sistem, Veri ve Gelir Analizi (14 Ekim 2026)
3. 58.316 Coin'in Akıbeti: Yüksek X Erken Tespit Edilebilir mi? (23 Ekim - 4 Kasım 2026)
4. Kapanış Notu (4 Kasım 2026)
5. Tasarım Dokümanı v2.1 (memecoin_analiz_motoru_v2.md)


---

## 1. README (Türkçe orijinal)

## Memecoin Motoru

> **English summary.** A Solana research engine for Pump.fun launches: event-time data pipeline (WebSocket + IDL decoding), rule-based risk scoring and wallet-free, bonding-curve-aware paper trading. Between 1 Sep and 8 Oct 2026 it recorded 58,316 launches and 2.09M trades; every coin's fate was then read back from chain (graduation flag) and PumpSwap price history. **Verdict:** 63% of graduates are filled in the launch block by insiders; the dev sells at a median of 8 s; every outsider entry strategy tested (early-feature selection, post-dev-exit entry, smart-wallet copying, enter-and-ride, post-graduation minute trading) has negative expected value after costs, and the only positive edge exists at 0-second (same-block) latency. Reports are in Turkish: `ANALIZ_RAPORU_2026-10-14.md` (system/data/revenue), `ANALIZ_YUKSEK_X_KOINLER_2026-10-23.md` (58k-coin post-mortem and strategy tests), `KAPANIS_NOTU_2026-11-04.md` (closing note). Raw outputs and read-only analysis scripts live in `turkish/analiz_ekleri/`. The 10 GB SQLite database is not in the repo.

Bu depo, `memecoin_analiz_motoru_v2.md` tasariminin uygulamasidir. Sistem veri
toplar, kural karari ve cuzdansiz paper test uretir; gercek alim-satim yapmaz,
cuzdan istemez ve henuz ML/agent calistirmaz.

> Guncel durum (14 Ekim 2026): Sistem PostgreSQL degil, yaklasik 10.2 GB
> buyuklugundeki `data/memecoin_motor.db` SQLite veritabanini kullanir. Son
> toplanan launch 8 Ekim 2026 tarihlidir. Mevcut sonuclar arastirma verisidir;
> canli para kullanimi icin yeterli performans veya veri surekliligi kaniti yoktur.

### Mevcut kapsam

- Tek Solana programini `logsSubscribe` ile izleme
- Tum slotlari `slotSubscribe` ile takip etme
- Slot bosluklarini kaydetme ve sinirli HTTP backfill
- Olay zamani, gelis zamani ve RPC zenginlestirme gecikmesini ayri tutma
- SQLite WAL ile idempotent olay kaydi
- Resmi Pump IDL discriminatorleriyle `Create`/`CreateV2` decode etme
- `CreateEvent` icinden kesin mint, creator, bonding curve, quote ve rezervler
- Dogrulanmis launch mintleri icin minimal token tablosu
- WebSocket `TradeEvent` icinden RPC cagirmadan Buy/Sell decode etme
- Yalniz collector acikken yakalanan yeni tokenlari varsayilan 600 saniye izleme
- Cuzdan bazli alim/satim ve net token pozisyonu
- 2/5/10/30/60 saniye olay-zamanli snapshotlar
- Creator ve ilk 10 saniyedeki sinirli alicilar icin asenkron analiz kuyrugu
- Sinirli imza gecmisi, acik SOL transferinden fonlayici adayi ve cuzdan grafigi
- Yerel tekrar eden creator/creator satis gecmisi
- Snapshot + creator + cuzdan grafiginden aciklanabilir `GIRME/IZLE/ADAY`
  kural baseline'i (`baseline-v1`)
- `ADAY` icin cuzdansiz, gecikme/fee/slippage/rezerv etkili sanal giris
- 60/300 saniyelik net X, hedef vurma ve drawdown sonuc etiketleri
- `GIRME/IZLE/ADAY` ayrimi yapmadan tum kararlar icin ham piyasa X etiketleri
- Ilk 10 saniyedeki ilk 5 alici icin sniper davranis skoru
- Sinirli tam transaction zenginlestirmesiyle fee payer, priority fee, Jito tip
  ve bundle olasiligi kanitlari
- `.env` ile RPC, program ve limit ayarlari
- Launch `getTransaction` isteklerini WebSocket okuma dongusunden ayiran bellek
  ici kuyruk, uc deneme ve basarisizlikta slot backfill
- Canli paper worker icin yalniz son 120 saniyeyi kapsayan sinirli is yukü;
  buyuk gecmis taramasi icin ayri `paper-run`

### Toplanan veri ve mevcut sonuc

8 Ekim 2026 sonu itibariyla yerel veritabaninda:

| Kayit | Adet |
|---|---:|
| Pump launch | 58.316 |
| Pump trade | 2.094.977 |
| En az bir trade'i olan token | 53.591 |
| Snapshot / risk karari | 291.358 |
| Token-cuzdan pozisyonu | 608.540 |
| Analiz edilmis cuzdan | 14.568 |
| Sniper skoru | 5.615 |
| Paper-v2 giris denemesi | 30.749 |
| Yurutulebilir paper sonucu | 4.389 |

Veri 1 Eylul-8 Ekim 2026 takvim araliginda olsa da collector yalniz 18 farkli
gunde calismistir. Bu nedenle veri 37 gunluk kesintisiz bir zaman serisi degildir.

#### Snapshot kalitesi

| Hedef yas | Zamaninda | Gec | Zamaninda oran |
|---|---:|---:|---:|
| 2 saniye | 2.313 | 55.968 | %4.0 |
| 5 saniye | 5.880 | 52.401 | %10.1 |
| 10 saniye | 13.089 | 45.190 | %22.5 |
| 30 saniye | 15.485 | 42.781 | %26.6 |
| 60 saniye | 16.438 | 41.813 | %28.2 |

Mevcut restart mantigi, onceki acik `snapshot_tracking` kayitlarini yeni process
baslangicinda kapatip eksik snapshotlari sonradan uretebilir. Bu satirlar `LATE`
etiketi tasir fakat collector'in kapali oldugu araligi guvenilir bicimde temsil
etmez. Model, kalibrasyon ve ana performans raporlarinda yalniz kesintisiz oturum
icinde uretilmis `ON_TIME + CONTINUOUS` ornekler kullanilmalidir.

Slot bosluklarinda 207 kucuk gap backfill edilmis; 1.276 buyuk gap limit nedeniyle
atlanmistir. Atlanan araliklar toplam 11.6 milyon slota ulasir. Bu sayi collector'in
kapali oldugu uzun araliklari da icerebilir ve kesintisiz kapsama olarak yorumlanmaz.

#### Paper-v2 baseline sonucu

300 saniyelik, `CONTINUOUS`, kanonik `ADAY` grubunda su an yalniz 163 sonuc vardir:

| Metrik | Sonuc |
|---|---:|
| Medyan gorulebilen tepe | 0.945x |
| Medyan final | 0.804x |
| Medyan kademeli strateji | 0.872x |
| Medyan maksimum dusus | %27.3 |
| 1.5x gorulme | %12.9 |
| 2x gorulme | %9.2 |
| 3x gorulme | %2.5 |
| 5x gorulme | %0.6 |
| Kademeli stratejide karli | %17.2 |

Bu baseline pozitif beklenti gostermemektedir ve orneklem henuz kucuktur. Gercek
para icin kullanilamaz. `IZLE` grubunun daha cok yukselen token icermesi, tek
aday sinifinin erken Pump piyasasindaki konsantre momentumu fazla cezalandirdigini
gosterir; esikler kor test olmadan gevsetilmemelidir.

Pump IDL, resmi `pump-fun/pump-public-docs` deposundan
`src/memecoin_motor/resources/pump.json` altina sabitlenmistir. Canli islemler
IDL instruction ve event discriminatorleriyle decode edilir; islemde gorulen her
mint artik yeni launch kabul edilmez.

### Gereksinimler

- Python 3.11 veya ustu
- Internet erisimi olan Solana HTTP ve WebSocket RPC

### Kurulum

PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Depoda yerel `.env` olusturulmustur ve resmi Pump bonding-curve programi
`6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P` izlenir. Bunun icin Pump.fun
hesabi veya Pump API anahtari gerekmez. Veri Solana RPC/WebSocket'ten okunur.

Varsayilan Solana public RPC ucretsizdir fakat rate-limit ve gecikme garantisi
yoktur. Veri toplama dogrulanirsa daha guvenilir bir RPC saglayicisinin HTTP ve
WebSocket adresleri `.env` icinde degistirilebilir.

### Calistirma

```powershell
memecoin-motor doctor
memecoin-motor init-db
memecoin-motor redecode
memecoin-motor collect
```

Baska terminalde durum:

```powershell
memecoin-motor status
memecoin-motor snapshots --limit 20
memecoin-motor wallets MINT_ADRESI --limit 20
memecoin-motor wallet CUZDAN_ADRESI
memecoin-motor creators --limit 20
memecoin-motor creator CREATOR_ADRESI
memecoin-motor score
memecoin-motor score --mint MINT_ADRESI
memecoin-motor scores --limit 20
memecoin-motor paper-run
memecoin-motor paper --limit 20
memecoin-motor outcomes --limit 20
memecoin-motor labels --limit 20
memecoin-motor outcomes-v2 --limit 20
memecoin-motor missed-watchlist --horizon 300 --minimum-x 1.5
memecoin-motor calibrate-x --horizon 300 --minimum-samples 30
memecoin-motor x-bands --horizon 300 --limit 30
memecoin-motor sniper MINT_ADRESI --limit 20
memecoin-motor snipers --limit 50
memecoin-motor sniper-backfill
```

`collect` canli veri hattidir. Canli paper worker yalniz yakin zamandaki yeni
kararlari kucuk partilerle isler. `paper-run` ise eski veriyi buyuk partilerle
paper-v2 motorundan gecirir; SQLite kullaniminda canli collector ile ayni anda
calistirilmasi gecikme yaratabilir.

Test:

```powershell
pytest
```

### Veri tablolari

- `chain_events`: programla iliskili islemler ve zaman/tamlik bilgisi
- `tokens_minimal`: gozlenen mintler icin minimal kayit
- `pump_launches`: decode edilmis Pump launch ayrintilari ve ilk rezervler
- `pump_trades`: izleme penceresindeki IDL-decode Buy/Sell olaylari
- `wallet_positions`: token/cuzdan bazli alim, satim ve net pozisyon
- `snapshot_tracking`: kesintisiz takip penceresinin baslangic/bitisi
- `token_snapshots`: 2/5/10/30/60 saniye akim ve yogunlasma ozellikleri
- `stream_gaps`: tespit edilen ve backfill edilen slot bosluklari
- `wallet_analysis_queue`: hizli hattan ayrilmis creator/ilk alici is kuyrugu
- `wallet_profiles`: tarama kapsami ve muhtemel fonlayici sonucu
- `wallet_edges`: kanit islemiyle fonlama grafigi kenarlari
- `risk_decisions`: snapshot yasi bazinda puan, guven, nedenler ve kullanilan
  ozelliklerin dondurulmus kopyasi
- `paper_positions`: legacy-v1 sanal giris veya acik basarisizlik nedeni
- `paper_outcomes`: legacy-v1 60/300 saniye sonuc etiketleri
- `market_outcomes`: legacy-v1 ham piyasa X etiketleri
- `transaction_enrichment_queue`: yalniz ilk alicilar icin sinirli RPC kuyrugu
- `early_trade_metadata`: fee payer, compute budget, priority fee ve Jito tip izi
- `sniper_scores`: tekrar erken giris, hizli satis, ayni slot/fonlayici/fee payer
  ile aciklanabilir sniper skoru
- `wallet_behavior_stats`: cüzdanin farkli launchlardaki erken giris sayaci
- `paper_v2_positions`: 8 saniyelik fill penceresi, rezerv girdileri ve 10/30/60 deney gruplari
- `executable_outcomes_v2`: 0.1 SOL icin rezerv etkili X, kademeli cikis ve gap kalitesi
- `x_band_calibration`: yalniz `CONTINUOUS` sonuclardan olusan ampirik X bantlari
- `service_state`: collector checkpoint bilgisi

Veritabani varsayilan olarak `data/memecoin_motor.db` konumundadir ve Git'e eklenmez.
Kod tabani henuz PostgreSQL kullanmaz. Buyuyen veri, eszamanli worker kilitleri ve
analiz sorgulari nedeniyle PostgreSQL'e kontrollu migrasyon planlanmaktadir;
mevcut SQLite dosyasi migrasyon sonrasinda salt-okunur arsiv olarak korunmalidir.
`redecode`, kayitli ham islemleri guncel IDL ile tekrar cozer ve eski kaba
extractor'dan kalan dogrulanmamis Pump mintlerini minimal tablodan temizler.

### Risk baseline-v1

Bu katman tahmin modeli degildir ve islem acmaz. Net quote akisi, benzersiz
alici, tek/top-5 alici yogunlasmasi, creator satisi/gecmisi, snapshot kalitesi,
cuzdan analiz kapsami ve ortak fonlayiciyi puanlar. `ADAY` en erken 10 saniyede
ve yeterli guvenle verilir. Kritik creator satisi disinda 2/5 saniyelik yetersiz
veri `GIRME` degil `IZLE` sonucudur. Her karar nedenleri ve warnings alanlariyla
saklanir; esikler paper test verisi birikince kalibre edilmelidir.

### Cuzdansiz paper test

Paper motoru yalniz veritabanindaki olaylari okur; private key, seed phrase,
cuzdan adresi veya RPC `sendTransaction` kullanmaz. V2 motoru 2 saniye sanal
gecikme sonrasinda, karar anindan en gec 8 saniyeye kadar fill arar. Son mikro
trade fiyatini degil, 0.1 SOL pozisyonun sanal rezervlerdeki yurutulebilir
giris/cikis degerini kullanir. Ucret, slippage ve rezerv etkisi dahil edilir.

Bu ilk maliyet baseline'idir: priority fee/Jito degerleri simdilik sabittir,
gercek block landing veya Jito acik artirmasi replay edilmez. Bu nedenle sonuc
canli uygulanabilirlik kaniti degil, iyimser backtestleri elemek icin muhafazakar
bir testtir.

`executable_outcomes_v2`, selection bias olusmamasi icin yalniz `ADAY`lari
degil tum karar siniflarini etiketler. Yalniz `is_canonical=1` satirlari ana
paper performansidir; digerleri deney ve kural denetimi icindir.

### Paper-v2 ve X kalibrasyonu

V2 motoru karar anindan itibaren en fazla 8 saniye icinde fill arar. Kucuk bir
trade'in fiyatini pozisyona carpmaz; o slotun sanal quote/token rezervlerinde
0.1 SOL'un alabilecegi tokeni ve bu tokenlerin satilabilecegi net SOL'u hesaplar.
Ag ucretleri, Pump event fee tahmini, slippage ve rezerv etkisi uygulanir.
Cozulememis slot gap'i ile cakisan sonuc `GAP_AFFECTED` olur ve kalibrasyona girmez.

Ayni tokenin ilk basarili `ADAY` girisi kanonik islemdir. 10/30/60 saniye
sonuclari deney gruplari olarak saklanir; `IZLE/GIRME` sanal etiketleri yalniz
kural denetiminde kullanilir. Strateji %40 @ 1.5x, %30 @ 2x, %20 @ 3x satar;
kalan kisim alici/satici ivmesi, negatif akis ve %15 geri cekilme birlikteyse cikar.

```powershell
memecoin-motor paper-run
memecoin-motor outcomes-v2 --limit 20
memecoin-motor missed-watchlist --horizon 300 --minimum-x 1.5
memecoin-motor calibrate-x --horizon 300 --minimum-samples 30
memecoin-motor x-bands --horizon 300
```

Kalibrasyon karar yasi, karar sinifi, risk ve firsat kovalarina gore
p25/p50/p75/p90 yurutulebilir X ile 1.5x/2x/3x/5x gorulme oranlarini verir.

### Sniper ve bundle kanitlari

Sniper katmani cüzdan baglamaz ve transaction gondermez. Launch sonrasi ilk 10
saniyedeki en fazla 5 benzersiz alicinin tam islemi asenkron/dusuk hizli RPC ile
okunur. Ilk giris yasi, ayni slot alicilari, farkli launchlarda tekrar erken
giris, hizli satis, ortak fonlayici, ortak fee payer, priority fee, resmi Jito
tip hesabi transferi ve `jitodontfront` izi puanlanir.

`JITO_ROUTED` yalniz resmi tip hesaplarindan birine transfer goruldugunu;
`bundle_likelihood=HIGH/MEDIUM/LOW` ise zincir ustu kanitlardan uretilen
heuristigi belirtir. Bundle ID bilinmeden ayni slot veya Jito tip tek basina
kesin bundle kaniti degildir; sistem bu nedenle `BUNDLE_CONFIRMED` uretmez.
Jito bundle'lari en fazla 5 transaction'dan olusur ve ayni slotta atomik
calisir. Public RPC limiti nedeniyle her trade degil yalniz erken secili
islemler zenginlestirilir.

### Bilinen sinirlar

- Ucretsiz RPC canli islem icin yeterli kabul edilmez.
- Launch `getTransaction` islemleri WebSocket'ten ayrilmis bellek ici kuyrukta
  uc kez denenir; son basarisizlikta ilgili slot backfill'e verilir. Kuyruk henuz
  kalici degildir ve process kapanisinda bekleyen isler kaybolabilir.
- Gap backfill, buyuk bosluklari maliyet/rate-limit nedeniyle atlar.
- Pump launch ve bonding-curve Buy/Sell snapshot decoderlari vardir; PumpSwap
  migrasyon sonrasi islemler henuz kapsamda degildir.
- Cuzdan taramasi ucretsiz RPC'yi korumak icin varsayilan olarak 2x100 imzayla
  sinirlidir. Bu sinira ulasilirsa bulunan transfer `RECENT_FUNDING_CANDIDATE`,
  gecmis sonuna ulasilirsa `FIRST_FUNDING` olarak etiketlenir. Transfer olmayan
  bakiye farklarindan fonlayici tahmini yapilmaz.
- `TRADE_TRACK_SECONDS` varsayilan 600 saniyedir; tum Pump piyasasi kaydedilmez.
- Collector kapaliyken gecen sure eksiksiz degildir. Mevcut restart/tracking
  mantigi eksik snapshotlari sonradan `LATE` olarak uretebildigi icin bu satirlar
  egitim veya ana performans verisi kabul edilmez.
- Veritabani SQLite'tir; agir `paper-run`, rapor veya enrichment islemleri canli
  collector ile ayni anda calistirilirsa kilit beklemesi ve gecikme yaratabilir.
- Wallet enrichment kuyruğunda 111 bin, transaction enrichment kuyruğunda 20 bin
  civarinda bekleyen is vardir; sniper/cuzdan kapsami tum tokenlari temsil etmez.
- 300 saniyelik guvenilir kanonik paper orneklemi yalniz 163 satirdir; ML icin
  yeterli ve donemler arasi dengeli bir egitim seti degildir.
- Dinamik landing/Jito replay, PumpSwap, ML ve agentic katmanlar henuz yoktur.
- Public RPC uzerinde uzun sureli uretim kullanimi hedeflenmez.

### Gelistirme onceligi

1. **Collection session ve continuity:** Her collector calismasini ayri oturum
   olarak kaydet; beklenmedik kapanista son gercek slot/zamani kullan; kesinti
   uzerinden geriye donuk snapshot uretme.
2. **Veri kullanilabilirlik etiketi:** Eski `LATE` satirlari silmeden
   `LEGACY_LATE/UNUSABLE` olarak ayir; model ve raporlari yalniz
   `ON_TIME + CONTINUOUS` veriyle calistir.
3. **PostgreSQL migrasyonu:** Bolumlenmis `pump_trades`, ayri baglanti havuzlari,
   `FOR UPDATE SKIP LOCKED` kuyruklari ve ham JSON saklama suresi uygula.
4. **Guvenilir RPC/Geyser:** Canli collector'u wallet/sniper arastirma
   cagrisindan ayir; saglayici gecikmesi, timeout, 429 ve gap metrikleri tut.
5. **Paper-v2 tamamlama:** Ayni mintin 10/30/60 deneylerini tek basari gibi
   saymadan kanonik sonuclari backfill et; tarih sirali train/test donemleri kur.
6. **Iki aday sinifi:** Organik/dagitik aday ile konsantre-yuksek-risk momentum
   adayini farkli pozisyon, fill ve cikis kurallariyla A/B paper test et.
7. **PumpSwap takibi:** Bonding curve migrasyonu sonrasi havuz, swap, rezerv ve
   1 saat/6 saat/24 saat yurutulebilir X sonucunu ekle.
8. **ML en son:** Birden fazla piyasa doneminden birkac bin guvenilir kanonik
   sonuc birikince kalibre `P(1.5x)`, `P(2x)`, `P(dump)` ve net getiri modelleri kur.

Ilk teknik hedef daha fazla veri toplamak degil, hangi saniyelerde gercekten
kesintisiz veri goruldugunu kanitlayan collection-session modelidir.


---

## 2. Sistem, Veri ve Gelir Analizi (14 Ekim 2026)

## Memecoin Motoru: Sistem, Veri ve Gelir Analizi

**Tarih:** 14 Ekim 2026
**Kapsam:** README, `memecoin_analiz_motoru_v2.md`, `src/memecoin_motor/*` (3.700 satır), 27 test, `data/memecoin_motor.db` (10,2 GB SQLite, salt-okunur incelendi), web ile pazar/fiyat doğrulaması.
**Yöntem:** Her bulgu `[DOĞRULANDI]` (kod veya veriyle), `[ÇIKARIM]` (veriden türetilmiş yorum) veya `[VARSAYIM]` (doğrulanamadı) olarak etiketlendi. Üretim verisi değiştirilmedi; veritabanı `mode=ro` ile açıldı.

---

### A) Sistemin mevcut durumu ve en kritik beş bulgu

#### Sistem ne yapıyor?

Pump.fun bonding-curve programını (`6EF8rrec…`) Solana public WebSocket üzerinden dinler, `Create/CreateV2` ve `TradeEvent` olaylarını resmi IDL ile çözer, her yeni token için ilk 600 saniyeyi izler, 2/5/10/30/60 saniyelik olay-zamanlı snapshot üretir, kural tabanlı `GIRME/IZLE/ADAY` kararı verir ve cüzdansız bir paper-trade motoruyla 60/300 saniyelik sonuç etiketler. Yan hatlar: creator/ilk alıcı cüzdan analizi, sniper ve bundle kanıtı, X-bant kalibrasyonu.

Değer üreteceği kitle tasarımda "kendi işlemlerimiz" olarak tanımlı (`memecoin_analiz_motoru_v2.md` §17). Şu an **kimse için çalışan bir ürün değil; araştırma altyapısı.**

#### Çalışan / yarım / yalnızca dokümanda

| Durum | Özellik | Kanıt |
|---|---|---|
| Çalışıyor | IDL decode, idempotent kayıt, slot gap tespiti, snapshot, risk kuralı, paper-v2 fill/çıkış matematiği, sniper skoru | 27/27 test geçti; `pump.json` SHA-256 README ile aynı; 58.316 launch, 2.094.977 trade; FK/orphan ihlali 0 |
| Yarım | Paper-v2 geçmiş taraması | 174.796 kararın 144.047'si (%82) hiç paper pozisyonuna dönüşmemiş; 11.155 açık pozisyonun 9.005'inin 300 sn sonucu yok; kanonik sonuçlar yalnızca **1-4 Eylül** tarihli |
| Yarım | Cüzdan/sniper zenginleştirme | Cüzdan kuyruğunda 111.194, tx kuyruğunda 20.557 bekleyen iş; sniper skoru 58.316 mint'in 4.890'ında (%8) |
| Yarım | Gap backfill | 1.276 gap "çok büyük" diye atlandı (11,6 M slot); 28 gap FAILED |
| Yalnızca dokümanda | PumpSwap takibi, ML modelleri, agentic denetim, dinamik fee/Jito replay, RugCheck/GoPlus/DEX Screener zenginleştirme, PostgreSQL | Kodda karşılığı yok (`grep` ile doğrulandı) |
| Ölü/legacy kod | `paper_positions`, `paper_outcomes`, `market_outcomes` (v1), `parser.extract_token_mints`, `paper.market_outcome` | v2 motoru kullanmıyor; CLI hâlâ gösteriyor; `Storage.initialize()` her açılışta legacy tabloya UPDATE atıyor |

#### En kritik beş bulgu

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

#### Diğer önemli bulgular

- **Sürüm kontrolü yok. [DOĞRULANDI]** `git log`: "branch 'main' does not have any commits yet". 3.700 satır kod ve 10 GB veri yedeksiz.
- **Depolama şişkin ve sorgular yavaş. [DOĞRULANDI]** `pump_trades` her satırda `raw_event_json` (çözülmüş alanların kopyası) taşıyor; `chain_events` 2,02 M LOG_EVENT satırında `logs_json` (ort. 628 B) ve 61.790 ham tx JSON (ort. 29,7 KB ≈ 1,8 GB). Tek tam tarama 200-400 sn. `create_due_snapshots` (`storage.py:1371-1376`) her 0,5 sn'de `token_snapshots`'ın tüm anahtarlarını (291 k satır) belleğe çekiyor; veri büyüdükçe snapshot işçisi kendi kendini boğacak.
- **Launch tx getirme kuyruğu saatlerce birikmiş. [DOĞRULANDI]** COMPLETE olaylarda `ingestion_latency_ms` p50 452 ms ama p90 23 saat, max 4,7 gün. Public RPC `getTransaction` darboğazı; tracking ancak tx geldikten sonra açıldığı için snapshot'lar baştan LATE doğuyor.
- **Gap politikası restart boşluklarını da "stream gap" sayıyor. [ÇIKARIM]** En büyük 8 gap (1,89 M slota kadar) restart anlarına denk geliyor; `SlotTracker` önceki oturumun son slotundan devam ettiği için. `MAX_BACKFILL_SLOTS=32` (~13 sn) üstü her şey atlanıyor.
- **Launch kapsaması muhtemelen eksik. [VARSAYIM]** Oturum içinde saatte ~835 launch görülüyor (günlük ~20 k hız). Eylül 2026 kamu verisi günlük ~32-34 k launch raporluyor. Saat dilimi etkisi olabilir; public WS'nin olay düşürüp düşürmediği dış kaynakla (Bitquery/Dune, aynı saat penceresi) doğrulanmalı.
- **SOL dışı quote tokenlar karışık. [DOĞRULANDI]** 3.412 launch (%5,9) SOL dışı quote (USDC 828, `pumpCm…` 580 vb.); 45.501 trade satırında `virtual_sol_reserves=0`; 17.058 snapshot'ta fiyat NULL; paper'da 883 `UNSUPPORTED_QUOTE`. Risk kuralı bu tokenları SOL ile aynı eşiklerle puanlıyor (`net_quote_flow` farklı ondalıkta).
- **Test kapsamı çekirdeği atlıyor.** `service.py` (565 satır, collector) için sıfır test; `run_paper_cycle`, `calibrate_x_bands`, WS replay testi yok. Mevcut testler saf fonksiyonları doğruluyor.
- **Güvenlik.** Cüzdan/özel anahtar yok, `sendTransaction` yok, `.env` yalnızca public URL içeriyor ve gitignore'da. SQL string birleştirmeleri sabit listelerden (`counts()`, `where` parçaları) geliyor; enjeksiyon yüzeyi yok. Dışa açık servis yok. Risk düşük. Tek not: `_stream_once` içinde `raise message.data` WS hata nesnesini istisna olarak fırlatıyor; `aiohttp` sürümüne göre tip hatası verebilir.

---

### B) Veri kalite raporu (kanıtlarıyla)

**Kaynak:** Yalnızca `api.mainnet-beta.solana.com` (confirmed), 2.078.144 olayın tamamı. Güncelleme mekanizması: elle başlatılan `memecoin-motor collect`; zamanlayıcı/servis yok. Son veri 8 Ekim 2026 05:49 UTC.

#### Kapsam ve tarih aralığı

| Metrik | Değer |
|---|---|
| Launch aralığı | 2026-09-01 07:46 → 2026-10-08 05:49 UTC |
| Farklı gün | 18 (README ile uyumlu) |
| Oturum sayısı (>15 dk boşluk) | 36 |
| Kapsanan süre | 84,6 saat / 885 saat (%9,6) |
| En uzun kesintisiz oturum | 9,1 saat (7 Eylül) |
| Oturum içi launch hızı | ~835/saat |

#### README sayı doğrulaması

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

#### Bütünlük kontrolleri

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

#### Zaman doğruluğu

| Metrik | p10 | p50 | p90 | p99 |
|---|---:|---:|---:|---:|
| WS gelişi − blok zamanı (launch) | 4,3 sn | 22,5 sn | 173 sn | 396 sn |
| LATE snapshot gecikmesi | – | 994 sn | 24 saat | 84 saat |
| COMPLETE olay işleme gecikmesi | – | 452 ms | 23 saat | 84 saat |
| ADAY `evaluated_at − cutoff` | – | 31 sn | 16,5 saat | – |

#### İşlenmiş çıktı vs ham veri

| Kontrol | Örneklem | Sonuç |
|---|---|---|
| Snapshot yeniden hesaplama | 400 mint, 2.000 snapshot | trade_count %21,9, unique_buyers %13,3, creator_sold %4,5 uyumsuz |
| ON_TIME snapshot'ta sonradan gelen trade | 3.000 snapshot | %41,7 |
| `features_json` → `evaluate()` yeniden değerlendirme | 20.000 karar | Tam şemalı 10.036 satırda **0 fark** (kural deterministik); 9.964 satır eski şemada (sniper alanları yok) |
| Paper fill gecikmesi (entry − cutoff) | 11.155 OPEN | 2 sn: %56, 8 sn: %3 |
| Paper rezerv etkisi (OPEN) | – | p50 33 bps, p90 145 bps |

#### Karar dağılımı (risk_decisions)

| Yaş | ADAY | IZLE | GIRME |
|---|---:|---:|---:|
| 2 sn | 0 | 56.823 | 1.458 |
| 5 sn | 0 | 55.657 | 2.624 |
| 10 sn | 2.190 (%3,8) | 46.719 | 9.370 |
| 30 sn | 3.089 (%5,3) | 40.732 | 14.445 |
| 60 sn | 2.916 (%5,0) | 37.773 | 17.562 |

#### Paper-v2 ve sonuç etiketleri (300 sn, CONTINUOUS)

| Grup | n | Medyan tepe | Medyan final | Medyan kademeli | 1,5x | 2x | 3x | Kademeli kârlı | Kademeli PnL (0,1 SOL) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Taban oranı (ham fiyat, ücret yok) | 2.544 | 1,104 | 0,866 | – | %27,2 | %16,5 | %7,6 | – | – |
| ADAY kanonik | 163 | 0,945 | 0,804 | 0,872 | %12,9 | %9,2 | %2,5 | %17,2 | −2,23 SOL |
| IZLE | 1.194 | 1,038 | 0,788 | 0,903 | %27,5 | %17,4 | %8,0 | %27,7 | −9,17 SOL |
| GIRME | 493 | 0,936 | 0,827 | 0,879 | %15,2 | %7,3 | %2,2 | %17,2 | −6,70 SOL |

Hiçbir grup ücret sonrası pozitif beklenti vermiyor. Kalibrasyon tablosu (`x_band_calibration`, 10 satır) 18 Eylül'de üretilmiş ve yine aynı 1-4 Eylül örneklemine dayanıyor; en büyük kova 205 örnek.

#### Yapılamayan kontroller

- Launch kapsaması (public WS'nin kaçırdığı Create olayları) dış referans olmadan ölçülemedi. Önerilen sorgu: Bitquery `Solana.Instructions` ile 4 Eylül 05:41-13:41 UTC penceresinde `create_v2` sayısını alıp 6.670 ile karşılaştırmak.
- `wallet_positions` ile trade toplamlarının tam eşleşmesi: 608.540 pozisyonun tamamı trade toplamlarıyla (alım token, alım/satım sayısı) **0 uyumsuz** (tam tarama, 263 sn). Bu tablo güvenilir.

Ham kontrol çıktıları ve çalıştırılan betik `turkish/analiz_ekleri/` klasöründe (`dq_check.py`, `dq_results*.txt`); betik veritabanını yalnızca `mode=ro` ile açar.
- Graduation yakınlığı (bonding curve dolumu) yalnızca 600 sn penceresi içinde ölçülebiliyor; PumpSwap sonrası veri yok. 600 sn içinde ölçülebilen kadarı: 50.739 SOL-quote mint'in 1.859'u (%3,7) `virtual_sol_reserves ≥ 115 SOL` (≈ 85 SOL gerçek rezerv, curve dolumu) seviyesine ulaşmış; 2.747'si ≥ 85 SOL, 4.700'ü ≥ 60 SOL. Bu oran kamu kaynaklarındaki %1-3 graduation bandıyla uyumlu ama 600 sn sonrası izlenmediği için üst sınırdır.

---

### C) Gelir modelleri karşılaştırması ve seçilen model

#### Kim, hangi sonuç için öder?

Sistemin bugün satılabilir tek varlığı **"olay-zamanı dürüstlüğü olan, yürütülebilir-fiyatla etiketlenmiş Pump.fun launch-penceresi verisi ve bunu üreten hat"**. Satılabilir olmayan: sinyal (ADAY taban oranın altında), gerçek-zamanlı uyarı (22 sn gecikme), getiri (negatif).

Pazar bağlamı [DOĞRULANDI, web, Ekim 2026]: Pump.fun günde ~25-42 k launch; graduation oranı yönteme göre %0,26-2,8; haftalık protokol geliri ~18,6 M$ (7 Ekim haftası); trading botları işlem başına ~%0,9-1 alıyor; ücretli "alpha" grupları 100-300 $/ay (satıcı beyanı). Veri/altyapı fiyat çapaları: Bitquery 49-299 $/ay, Shyft gRPC 199-649 $/ay, SolanaTracker 50-1.499 €/ay (stream 397 €'dan), Helius Business 499 $/ay (LaserStream dahil), Birdeye Premium ~199 $/ay. Kaynaklar raporun sonunda.

#### Üç model

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

#### Seçilen model: M2 (araştırma veri seti + harness), M1'e geçiş opsiyonu ile

Gerekçe:
1. M2'nin ön koşulları yalnızca P0 düzeltmeleridir; kural motorunun alpha üretmesini gerektirmez. M1 ve M3 bugün sağlanmayan şartlara bağlı.
2. Sistemin gerçek farkı (veri gecikmesini ölçmek, backfill'i canlı gibi etiketlememek, mikro-trade fiyatı yerine rezervden fill hesaplamak) tam olarak M2'nin alıcısının önemsediği şey.
3. M2 müşterisi düşük maliyetle test edilebilir: ödeme isteği 14 günde, kod yazmadan ölçülür (bkz. E).
4. M2 gelir getirmese bile, 30-90 gün kesintisiz veri M1 için zorunlu altyapıdır; harcanan efor boşa gitmez.

Eleştiri: M2 pazarı küçüktür ve ham veri ücretsiz/ucuz. Ödeyecek kişi, "bir haftada kendim toplarım" demeyen, etiketli-temiz veriyi hemen isteyen bot ekibidir. Bu kitlenin büyüklüğü **[VARSAYIM]**; deney bunu test eder.

#### Gelir ve kâr senaryoları (aylık, USD)

Varsayımlar: RPC 499 $ (Helius Business; Shyft Build 199 $ ile düşük senaryo), VPS 60 $, Postgres/depolama 50 $, ödeme/araç 40 $ → opex 350-650 $. Kurucu emeği hariç. Ödeme komisyonu %4.

| Senaryo | Müşteri | ARPU | Gelir | Opex | Kâr |
|---|---:|---:|---:|---:|---:|
| Düşük | 3 | 99 $ | 297 $ | 350 $ | −65 $ |
| Orta | 10 | 149 $ | 1.490 $ | 650 $ | +780 $ |
| Yüksek | 30 + 2 kurumsal | 199 $ / 999 $ | 7.970 $ | 900 $ | +6.750 $ |

**Başabaş:** 650 $ opex için 149 $'dan 5 müşteri (ya da 99 $'dan 7). Kurucu zamanı 20 saat/ay × 50 $ eklenirse başabaş 12 müşteri.

#### "Para kazandırıyor mu?" testi

README böyle bir iddia taşımıyor; tersini söylüyor. Veriyle teyit: 163 kanonik ADAY, 0,1 SOL/pozisyon, kademeli strateji **−%13,7**, en iyi alt grup (30 sn ADAY, n=63) bile ortalama 0,908x. 1-4 Eylül dışı dönem için paper sonucu yok; gelecek için kanıt yok.

---

### D) Önceliklendirilmiş teknik iş listesi

Format: Sorun → Kanıt → Değişiklik → Etki → Efor → Bağımlılık → Kabul kriteri.

#### P0: Veri doğruluğu ve çalışmayı engelleyenler

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

#### P1: İlk ücretli kullanımı mümkün kılanlar

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

#### P2: Ölçekleme ve işletme verimliliği

**P2-1. PostgreSQL migrasyonu** (README planı) — yalnızca P1-1 sonrası hâlâ gerekiyorsa; `pump_trades` bölümleme, `SKIP LOCKED` kuyruklar. Efor 3 gün.
**P2-2. PumpSwap sonrası takip ve 1h/6h/24h etiketler** — M1 ve ML için şart. Efor 4 gün.
**P2-3. İki aday sınıfı A/B ve kural revizyonu** — Yalnızca P0-5 sonrası, IZLE'nin neden daha iyi olduğunu görerek. Efor 2 gün.
**P2-4. ML** — Birkaç bin SETTLED+CONTINUOUS kanonik sonuç ve en az iki piyasa dönemi birikmeden başlama.
**P2-5. Yetkilendirme/ödeme otomasyonu** — Müşteri 10'u geçince anahtar yönetimi, kullanım ölçümü, faturalama.

Yapılmaması gerekenler: Yeniden yazma, dil/framework değişimi, Telegram sinyal botu (kural taban oranı yenmiyor), agent katmanı.

---

### E) 7 / 30 / 90 günlük uygulama planı

#### İlk 7 gün: Kritik doğrulamalar ve düzeltmeler

Teslimatlar: P0-6 (gün 1), P0-1, P0-2, P0-3, P0-4 (ücretli RPC denemesi), P0-5 başlangıcı. Mevcut DB'nin salt-okunur arşiv kopyası.
Başarı ölçütü: 72 saat kesintisiz koşu; `chain_lag_ms` p50 < 2 sn; 10 sn ON_TIME ≥ %80; yapay kesinti testinde sahte snapshot 0; sızıntı testi geçer.
Devam/durdur: Ücretli RPC ile bile p50 gecikme > 5 sn ise erken-snapshot ürünü (M1) kalıcı olarak rafa; M2'ye odaklan. Gecikme düzeliyorsa M1 opsiyonu açık kalır.

#### İlk 30 gün: Satılabilir minimum sürüm ve pilot

Teslimatlar: P1-1, P1-2, P1-3, P1-4, P1-5; 21+ gün kesintisiz veri; tam geçmiş üzerinde paper raporu (gün bazlı). **Ödeme isteği deneyi** (aşağıda) gün 8-21 arasında.
Başarı ölçütü: Uptime > %98; veri seti ≥ 500 saat; 3 ücretli pilot (toplam ≥ 300 $/ay) veya 2 ön ödeme.
Devam/durdur: 14 günlük deneyde 0 ödeme ve < 5 nitelikli görüşme → M2 fiyatını/kitleyi bir kez değiştir, 14 gün daha; yine 0 ise ticari hedefi durdur, sistemi kişisel araştırma aracı olarak tut.

#### İlk 90 gün: Talep doğrulaması, sürdürülebilir gelir, ölçekleme

Teslimatlar: 10+ müşteri hedefi; P1-6, P2-2 (PumpSwap) ; kural motorunun 60+ gün SETTLED veride taban oranla karşılaştırılması; müşteri geri bildirimiyle 2. veri ürünü (ör. sniper/bundle cüzdan listesi).
Başarı ölçütü: MRR ≥ 1.500 $ (opex'in 2 katı); churn < %20/ay; chain_lag p50 < 2 sn ile 60 gün.
Devam/durdur: MRR < 650 $ ise altyapıyı en ucuz RPC'ye indir ve ürünü açık kaynak + danışmanlık modeline çevir. Kural motoru taban oranı yeniyorsa (2x görülme ≥ taban + 5 puan, n ≥ 1.000) M1 için 30 günlük ek plan yaz.

#### Ödeme isteği deneyi (büyük geliştirme öncesi)

Kod yazmadan, 14 gün:
1. Mevcut veriden 4 Eylül oturumu (8 saat, 6.670 launch) temiz Parquet örnek seti üret; veri sözlüğü ve 1 notebook ("gerçekçi fill ile 300 sn X dağılımı").
2. Tek sayfalık açıklama + fiyat: "30 gün kesintisiz launch-penceresi veri seti + paper harness, 149 $/ay, ilk 5 müşteriye 99 $". Stripe/Lemon Squeezy ödeme linki.
3. 20 doğrudan ulaşım (Solana dev Discord, X'te bot geliştiren hesaplar, 2 bot ekibi), 2 açık paylaşım.
4. Ölçüt: ≥ 3 ödeme veya ≥ 5 "veri gelince alırım" yazılı taahhüdü → P1-4'e yatırım. Aksi → dur, nedenleri yaz.

---

### F) İlk yapılacak somut iş ve kabul kriteri

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

### Ek: Kaynaklar (web doğrulaması)

- Pump.fun launch/graduation: [Solana Compass](https://solanacompass.com/news/pumpfun-launched-42000-tokens-in-one-day-fewer-than-2-will-ever-reach-a-dex), [DEXTools](https://www.dextools.io/news/pump-fun-graduation-collapse-solana-fees-2026), [pumpfundata](https://pumpfundata.com/blog/pumpfun-graduation-rate-analysis), [Medium cohort yöntemi](https://medium.com/coinmonks/pump-fun-api-how-to-track-bonding-curves-graduations-and-pumpswap-on-chain-879b689fbedb), [Cryptopolitan](https://www.cryptopolitan.com/pump-fun-graduating-tokens-break-to-1-15-of-new-launches/)
- Protokol geliri Ekim 2026: [CoinMarketCap](https://coinmarketcap.com/cmc-ai/pump-fun/latest-updates/)
- Fee yapısı: [Blockworks](https://blockworks.com/news/pumpdotfun-fee-model), [The Block](https://www.theblock.co/post/354038/pumpswap-revenue-tokens), [Cointelegraph](https://cointelegraph.com/news/pump-fun-creator-fee-cap-update-memecoin-model)
- RPC/veri fiyatları: [Helius pricing](https://helius.dev/pricing), [Helius credits](https://helius.dev/docs/billing/credits), [Shyft gRPC](https://www.shyft.to/solana-yellowstone-grpc), [Bitquery Pump.fun API](https://bitquery.io/products/pumpfun-api), [SolanaTracker pricing](https://docs.solanatracker.io/pricing), [Birdeye karşılaştırma](https://madeonsol.com/api-alternatives/birdeye), [Nansen API](https://api-docs.nansen.ai/reference/pricing)
- Bot ücretleri: [solanatools.io](https://solanatools.io/blog/solana-trading-bot-fees-compared), [memegateway](https://memegateway.com/academy/solana-trading-bot-fees-compared-2026/), [madeonsol Trojan](https://madeonsol.com/blog/trojan-bot-review)
- Ücretli alpha grupları (satıcı beyanı): [Gumroad ilanı](https://memecointrenches.gumroad.com/l/discordmembership); sniper bot vakası: [Transak](https://transak.com/blog/crypto-memecoin-sniping-guide)
- Graduation eşiği/PumpSwap: [madeonsol PumpSwap](https://madeonsol.com/blog/what-is-pumpswap)

Not: Fiyat ve oran kaynaklarının bir kısmı satıcı veya affiliate içeriğidir; bütçe kararından önce resmi sayfalardan teyit edilmelidir.


---

## 3. 58.316 Coin'in Akıbeti: Yüksek X Erken Tespit Edilebilir mi? (23 Ekim - 4 Kasım 2026)

## 58.316 Coin'in Akıbeti: Yüksek X Yapacak Coin Erken Tespit Edilebilir mi?

**Tarih:** 23-26 Ekim 2026 (sürüm 3, final: zincir durumu 58.316 coin'in tamamı; PumpSwap zirve verisi 1.853 graduate havuzunun tamamı)
**Soru:** Elimizdeki 10 GB veride kayıtlı 58.316 Pump.fun launch'ının sonradan ne olduğuna bakarak, yüksek X yapacak coin'i ilk dakikalarda ayırt etmek mümkün mü? Mümkünse kendimiz girmeli miyiz, yoksa bunu araç olarak mı satmalıyız?
**Yöntem:**
1. Veritabanındaki 58.316 mint'in tamamı için bonding-curve hesabı Solana public RPC'den okundu (`getMultipleAccounts`, 584 çağrı, 0 hata). Böylece her coin için zincirdeki **kesin** durum elde edildi: graduate oldu mu (`complete`), şu anki rezervler, mayhem bayrağı.
2. Graduate olan 2.020 coin için PumpSwap havuzu ve günlük fiyat geçmişi GeckoTerminal'den çekiliyor (ücretsiz API dakikada ~7 istek; ~5 saat sürüyor, devam ediyor).
3. Bunlar veritabanındaki ilk 10/30/60 saniye özellikleri, risk kararları ve creator geçmişiyle eşleştirildi.
4. Tüm sorgular salt-okunur; üretim verisi değiştirilmedi. Ham çıktılar `turkish/analiz_ekleri/15x/` altında.

Etiketler: `[DOĞRULANDI]` zincir veya veritabanıyla; `[ÇIKARIM]` veriden türetilmiş yorum; `[VARSAYIM]` doğrulanamadı.

---

### 1. Beş cümlelik sonuç

1. **Bu veride "yüksek X" pratikte "graduate oldu" demek.** Pump.fun eğrisi launch fiyatından dolum fiyatına tam 14,7x yol alır; eğri dolmadan 15x olmaz, eğri dolan her coin de tanım gereği 14,7x'tir. `[DOĞRULANDI]`
2. **58.316 coin'in %3,7'si (2.020) graduate olmuş;** mayhem dışı SOL coin'lerde %4,1 (1.436). Geri kalan %96 eğrinin ilk %1'inde ölmüş ve launch fiyatına geri dönmüş. `[DOĞRULANDI]`
3. **Graduate olanların %63'ü (906) launch ile aynı saniyede, ortalama 2,8 cüzdanla ve tek alıcının alımların %79'unu yaptığı "paketli anında dolum" launch'ları.** Bunlar biz görmeden bitmiş; bize sadece çıkış likiditesi rolü kalır. Erişilebilir hedef, 600 saniyeden sonra graduate olan **398 coin (%1,1)**. `[DOĞRULANDI]`
4. **İlk 60 saniye özellikleri bu %1,1'lik hedefi 4-12 kat zenginleştirebiliyor** (örneğin 60 sn'de 15 SOL+ net giriş ve eğri henüz dolmamışsa graduate oranı %7,3). **Ama 60. saniyede girip gerçek PumpSwap fiyatlarıyla çıkınca gerçekçi her senaryoda her kural zarar ediyor (-6% ile -49%); en iyimser senaryoda bile en iyi kural +5% ile sıfır civarı.** Erişilebilir graduate'lerin dolum sonrası koşusu medyan 1,83x ve aynı gün çöküyor; bugün %89'u launch fiyatının altında. Sinyal var, para yok. `[DOĞRULANDI, 1.853 graduate havuzunun tamamı]`
5. **Verinin özellik analizine uygun kısmı yalnızca 1-17 Eylül.** 18 Eylül'den sonra collector launch'ları kaydetmiş ama trade'leri neredeyse hiç yakalamamış (launch başına trade 60-84'ten 0,6-10'a düşmüş). Bu, 14 Ekim raporunda gözden kaçan en büyük veri hatası. `[DOĞRULANDI]`

---

### 2. Veri yakalama 18 Eylül'de çökmüş `[DOĞRULANDI]`

Mayhem dışı SOL launch'ları için gün bazında:

| Gün | Launch | Trade/launch | ≥1 trade'i olan | 60 sn'de ≥6 alıcı | Graduate | Durum |
|---|---:|---:|---:|---:|---:|---|
| 09-03 | 489 | 57,9 | %97,1 | %35,0 | %4,1 | sağlıklı |
| 09-04 | 3.718 | 69,5 | %94,8 | %36,5 | %5,2 | sağlıklı |
| 09-07 | 4.696 | 84,4 | %94,6 | %38,8 | %5,1 | sağlıklı |
| 09-08 | 3.972 | 60,2 | %93,6 | %38,2 | %3,9 | sağlıklı |
| 09-16 | 2.142 | 60,1 | %98,3 | %38,4 | %6,1 | sağlıklı |
| 09-17 | 2.175 | 50,5 | %96,6 | %35,2 | %4,5 | sağlıklı |
| 09-18 | 2.621 | 9,7 | %82,1 | %8,1 | %3,3 | **bozuk** |
| 09-21 | 2.518 | 3,0 | %84,4 | %0,4 | %4,0 | **bozuk** |
| 09-30 | 2.976 | 1,1 | %89,7 | %0,1 | %2,9 | **bozuk** |
| 10-01 | 3.121 | 1,0 | %93,5 | %0,0 | %4,1 | **bozuk** |
| 10-07 | 3.794 | 0,6 | %63,1 | %0,0 | %2,5 | **bozuk** |

Zincirdeki graduate oranı bozuk günlerde de %2,5-4 olduğu için coin'ler değişmemiş; değişen, collector'ın trade görme yeteneği.

**Neden (3 Kasım'da doğrulandı) `[DOĞRULANDI]`:** Collector bu günlerde açıktı ve launch'ları WebSocket'ten görüyordu. Ama her launch için `getTransaction` çağrısı ücretsiz public RPC'de kuyrukta birikti. WebSocket'te görülmeden launch'ın işlenip izlemenin başlamasına kadar geçen süre (medyan):

| Gün | 1-17 Eylül | 18 Eylül | 21 Eylül | 29 Eylül | 30 Eylül | 1 Ekim | 7 Ekim |
|---|---:|---:|---:|---:|---:|---:|---:|
| Gecikme | 0 sn | 16 dk | 84 dk | 22 dk | 17 saat | 24 saat | 20 saat |
| >600 sn gecikenler | %0 | %64 | %86 | %81 | %95 | %100 | %99 |

Kod (`service.py` `_handle_logs`) bir coin'in trade'ini yalnızca o coin izlemeye alındıktan sonra kaydediyor; izleme de launch işlemi RPC'den alınınca başlıyor. Kuyruk 600 saniyeyi aşınca coin'in bütün trade'leri atıldı. 1 Ekim'de kalan trade'lerin %99'u launch işleminin kendi içindeki dev alımı. Bu bir kod/altyapı darboğazı; sistem kapatılmasından kaynaklanmıyor ve aynı kodla tekrar çalıştırılırsa tekrarlar.

**Ücretsiz çözüm:** Launch işlemlerinin %97'sinde `CreateEvent` WebSocket log'larının içinde zaten geliyor (300 launch kontrol edildi). Launch'ı RPC'ye gitmeden log'dan çözmek bu darboğazı tamamen kaldırır; `getTransaction` yalnızca eksik kalanlar için yedek olarak kullanılır.

Bu raporun özellik analizleri yalnızca 9 sağlıklı güne (17.543 coin, 60 sn fiyatı olanlar) dayanır.

---

### 3. Coin'lerin akıbeti: zincirden okunan kesin durum `[DOĞRULANDI]`

| Grup | n | Graduate | Oran |
|---|---:|---:|---:|
| Tüm SOL-quote launch | 54.904 | 2.020 | %3,68 |
| Mayhem dışı | 35.021 | 1.436 | %4,10 |
| Mayhem | 19.883 | 584 | %2,94 |
| SOL dışı quote (USDC vb.) | 3.412 | 78 | %2,29 |

Graduate olmayan 52.884 coin'in bugünkü durumu: %99,8'i eğri ilerlemesinin %1'inin altında; eğri fiyatı launch fiyatına geri dönmüş (medyan 1,000x). Yani "ölen coin" tam olarak sıfıra gitmiyor, alıcılar satıp çıkınca eğri başlangıç noktasına dönüyor. 0,1 SOL'luk bir pozisyon bugün hâlâ yaklaşık giriş fiyatından satılabilir durumda; kayıp küçük ama sermaye haftalarca kilitli kalıyor.

Mayhem kontrolü: Bizim verimizde "eğri 115 SOL'a ulaştı" görünen 1.859 coin'in 753'ü zincirde graduate olmamış ve **753'ünün tamamı mayhem**. Mayhem modunda sanal rezerv gerçek SOL olmadan şişiyor; önceki raporda tespit edilen "sahte 15x" artefaktı zincirle kesinleşti. Mayhem coin'ler bu analizin geri kalanından çıkarıldı.

#### Graduate olanların kompozisyonu (mayhem dışı, 1.436)

| Ne zaman doldu | n | Pay | Yorum |
|---|---:|---:|---|
| Launch ile aynı saniye (yaş 0) | 906 | %63 | Paketli (bundle) launch: ortalama 2,8 alıcı, tek alıcı alımların %79'u |
| 1-600 sn | 132 | %9 | Hızlı organik veya yarı paketli |
| 600 sn sonrası | 398 | %28 | **Erişilebilir hedef**: biz gördüğümüzde henüz dolmamış |

Erişilebilir hedef, mayhem dışı launch'ların **%1,1'i**. "Anında dolum" grubuna girmek mümkün değil: median 22 saniyelik zincir gecikmemizle biz gördüğümüzde eğri çoktan dolmuş ve PumpSwap'ta satışa geçilmiş oluyor.

---

### 4. Yüksek X nerede oluşuyor?

- Launch fiyatından eğri dolumuna kadar yol: **14,7x** (fiyat sanal SOL rezervinin karesiyle büyür; 30 → 115 SOL).
- 60. saniyede gördüğümüz giriş fiyatı launch fiyatının medyan **1,02x**'i (p90: 2,09x). Yani sağlıklı bir 60 sn girişinden graduate'e kadar yaklaşık 14x kalıyor.
- Graduate sonrası PumpSwap koşusu ne kadar? **Bu, GeckoTerminal taraması bitince eklenecek.** Erken örnekleme (ilk 240 coin) güvenilir değil; tam tabloyu bekliyoruz.
- Mayhem dışı coin'lerde 600 sn içinde 10 sn girişinden 15x: **0 / 4.209** (önceki rapor). Eğri dolmadan 15x yok.

Sonuç: "yüksek X yapacak coin'i yakalamak" sorusu pratikte "600 saniyeden sonra graduate olacak %1,1'i ilk 60 saniyede seçmek ve graduate sonrası koşuyu yakalamak" sorusuna indirgeniyor.

---

### 5. İlk 60 saniye özellikleri hedefi ayırt ediyor mu? `[DOĞRULANDI, 9 sağlıklı gün, mayhem dışı]`

Taban oran (tüm coin'ler): graduate %4,8; 600 sn sonrası graduate %0,59.

| Özellik (60 sn) | Kova | n | Graduate | 600 sn sonrası graduate |
|---|---|---:|---:|---:|
| Net SOL girişi | ≤0 | 4.179 | %0,45 | %0,43 |
| | <0,5 SOL | 15.519 | %0,92 | %0,89 |
| | 5-15 SOL | 2.389 | %1,51 | %1,34 |
| | 15-40 SOL | 879 | %9,90 | **%7,17** |
| | ≥40 SOL | 1.144 | %90,56 | %3,23 (çoğu zaten dolmuş) |
| Benzersiz alıcı | 1-2 | 20.791 | %4,48 | %1,28 |
| | 6-10 | 2.234 | %9,00 | %0,40 |
| | 21-50 | 1.616 | %4,64 | %1,92 |
| | 51+ | 1.244 | %8,12 | **%3,86** |
| Tek alıcı payı | <0,2 | 6.831 | %2,21 | %1,30 |
| | <0,4 | 2.992 | %9,93 | %0,87 |
| | ≥0,7 | 22.129 | %4,31 | %1,25 |
| Creator 60 sn'de sattı | evet | 6.460 | %1,38 | %0,90 |
| | hayır | 28.512 | %4,72 | %1,19 |
| Creator'ın önceki launch sayısı* | 0 | – | – | lift 1,0-1,3x |
| | 21+ | 7.299 | %0,62 | %0,48 |
| İlk 2 sn'de alım | ≥20 SOL | 1.706 | %61,96 | %3,69 |
| | yok | 4.228 | %0,47 | %0,47 |
| 60 sn risk kararı | ADAY | 2.523 | %14,74 | %1,70 |
| | IZLE | 21.721 | %4,39 | %1,27 |
| | GIRME | 10.728 | %1,02 | %0,73 |

\* İlk sürümde creator'ın toplam launch sayısı kullanılmıştı; bu gelecekteki launch'ları da saydığı için sızıntıydı. Düzeltilmiş "o ana kadarki launch sayısı" ile lift 1,7x'ten 1,0-1,3x'e düştü. "Seri creator" sinyali gerçek ama geriye dönük bakmadan zayıf.

Önemli okuma: Graduate oranı yüksek görünen kovaların çoğu (≥40 SOL giriş, ADAY, ≥20 SOL ilk 2 sn) aslında **zaten dolmuş** coin'leri yakalıyor. Erişilebilir hedef için en güçlü sinyaller: 60 sn'de **15-40 SOL net giriş ve eğri henüz dolmamış**, **51+ benzersiz alıcı**, creator satmamış.

#### Kurallar: zaman ayrımlı test ve beklenen getiri

Eğitim: sağlıklı günler ≤ 9 Eylül (n=13.126). Test: 15-17 Eylül (n=4.417). Giriş 60 sn fiyatından, %3 toplam maliyet. Graduate olmayanlar **bugünkü eğri fiyatıyla** değerlendi (gerçek ölçüm, varsayım değil). Graduate olanlar için iki çıkış senaryosu: (A) eğri dolum fiyatından sat; (B) dolum fiyatının 3 katından sat (PumpSwap koşusu varsayımı, taramayla değişecek).

| Kural (60 sn) | Test seçim | 600 sn sonrası graduate | Lift | EV (A) | EV (B, 3x) |
|---|---:|---:|---:|---:|---:|
| Hepsini al | 4.417 | %0,86 | 1,0x | -10% | +3% |
| Creator'ın ilk launch'ı | 2.451 | %1,14 | 1,3x | -9% | +9% |
| İlk launch & ≥6 alıcı & ≥1 SOL | 716 | %3,77 | 4,4x | -18% | +30% |
| İlk launch & ≥11 alıcı & ≥3 SOL & tek alıcı <0,5 | 411 | %5,60 | 6,5x | -19% | +42% |
| ≥21 alıcı & ≥5 SOL | 472 | %5,30 | 6,2x | -29% | +20% |
| ≥51 alıcı | 250 | %6,80 | 7,9x | -22% | +47% |
| ≥15 SOL giriş & eğri dolmamış | 238 | %9,66 | 11,2x | -30% | +49% |
| ADAY (mevcut kural) | 853 | %2,58 | 3,0x | -18% | +18% |
| ADAY & ilk launch | 649 | %2,77 | 3,2x | -15% | +28% |

Eğitim ve test sonuçları aynı yönde (tam tablo ekte). Okuma:
- **Seçim gücü var:** Basit kurallar erişilebilir graduate oranını %0,9'dan %4-10'a çıkarıyor ve bu, eğitim döneminden test dönemine taşınıyor.
- **Tek başına yetmiyor:** Graduate fiyatından çıkışla her kural zarar ediyor, çünkü %90-95 kaybeden pozisyon ortalama %10-35 değer kaybediyor ve kazananın 14x'i bunu kapatmıyor.
- **Kârlılık graduate sonrası koşuya bağlı:** Kazananlar PumpSwap'ta ortalama 3x daha giderse en iyi kurallar +30-50% EV veriyor. "3x" şu an varsayım; gerçek ATH dağılımı tarama bitince bu tabloya yazılacak.
- **Örneklem küçük:** Test kümesindeki kazanan sayısı kural başına 17-27. Bu, yön gösterir ama güven aralığı geniştir; 14 gün temiz veriyle tekrarlanmalı.

---

### 6. Paketli anında-dolum launch'ları `[DOĞRULANDI]`

600 sn içinde graduate olan 1.038 mayhem dışı coin'in **906'sı (%87) launch ile aynı saniyede** dolmuş. Ortalama 2,8 alıcı, tek alıcı alımların %79'u. İlk 2 saniyede ≥20 SOL alım olan 1.706 coin'in %62'si graduate olmuş ama bunların neredeyse hepsi biz görmeden. Bu grup için:
- Girmek imkânsız (22 sn gecikme, zaten dolum fiyatında).
- Ama **tespit etmek kolay ve değerli**: "bu coin paketli açıldı, PumpSwap'ta dağıtım bekle" uyarısı, bir araç için somut özellik. Zincir verisiyle %100 doğrulukla etiketlenebiliyor.

---

### 7. Bu ne anlama geliyor: kendimiz mi gireriz, araç mı?

**Kendimiz girmek:** Bu veriyle hayır. Seçim kuralı graduate'i 4-12 kat zenginleştiriyor ama 60. saniyede girip gerçek PumpSwap fiyatlarıyla çıkınca gerçekçi her çıkış politikasında her kural zarar ediyor, iyimser politikada bile sıfır civarı (bölüm 8). Medyan PumpSwap koşusu 1,83x ve aynı gün sönüyor; kazanan, kaybedenlerin %35-65'lik erimesini karşılamıyor. Bu pencerede (ilk dakikalar, zincir verisi, 22 sn gecikme) alpha yok. Alpha varsa başka yerde: dolum anından sonraki dakikalarda PumpSwap'ta kademeli satış (saniye hassasiyeti ve ücretli altyapı ister) ya da zincir dışı sinyal (sosyal, cüzdan takibi). Bunlar bu verinin cevaplayamadığı ayrı sorular.

**Araç için** şu an elde olan, satılabilir üç somut sinyal: (1) paketli launch tespiti (kesin), (2) mayhem artefakt uyarısı (kesin), (3) 60 sn'de "erişilebilir graduate" skoru (lift 4-12x, küçük örneklem). Bunlar RugCheck/Bubblemaps'in vermediği, trenches trader'ının saniyeler içinde istediği bilgiler. Ancak satış için 7/24 çalışan, 18 Eylül'deki gibi çökmeyen bir hat şart.

**Her iki yol için ön koşul aynı:** trade yakalama çöküşünün nedeni bulunup düzeltilmeli (ücretli WS/gRPC), izleme 600 sn'den 24 saate ve PumpSwap'a uzatılmalı, 14 gün kesintisiz temiz veri toplanmalı. Bu plan 14 Ekim raporunun P0 listesiyle aynı; tek fark, PumpSwap takibinin P2'den P0'a çıkması.

---

### 8. Graduate sonrası zirve: GeckoTerminal günlük mumlar `[DOĞRULANDI, 1.853 havuzun tamamı]`

GeckoTerminal'de PumpSwap havuzu bulunan 1.853 graduate coin'in tamamının günlük mumları çekildi (1.838'inde işlem var). Zirve ölçümü "sağlam" tanımla yapıldı: günlük mumun yükseği, mum gövdesinin 3 katıyla sınırlandı; çünkü tek cüzdanlı havuzlarda boş havuza atılan mikro işlemler 277.359x gibi anlamsız fitiller üretiyor.

| Grup | n | Dolum fiyatından zirve (medyan / p75 / p90) | ≥2x | ≥3x | ≥5x | En iyi günün kapanışı / dolum fiyatı (medyan) | Bugün / zirve (medyan) | Bugün launch fiyatının altında |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| **Erişilebilir** (mayhem dışı, 600 sn sonrası graduate) | 372 | **1,83x / 3,00x / 3,33x** | %45 | %26 | %5 | **0,06x** | %2,9 | %89 |
| Anında dolum (paketli) | 895 | 7,8x / 51x / 440x (güvenilmez: tek cüzdanlı havuz, kendi kendine işlem) | – | – | – | 0,05x | %0,6 | %97 |
| Mayhem | 571 | 0,00x | – | – | – | 0,00x | – | %99 |

Okuma:
- **Erişilebilir graduate'lerde PumpSwap koşusu küçük ve aynı gün bitiyor.** Medyan zirve dolum fiyatının 1,83 katı; %96,5'i zirveyi ilk PumpSwap gününde yapıyor ve o günün kapanışında fiyat dolum fiyatının %6'sına düşmüş oluyor. Yani "graduate olunca al, tut" değil, "dolumdan sonraki dakikalarda sat" oyunu.
- **"15x yapan coin"ler bugün ölü.** Erişilebilir grupta %89'u, paketli grupta %97'si bugün launch fiyatının altında. Zirvesinin %3'ünden azını koruyor.
- **Paketli grup zirveleri sahte.** 60. saniyede tek alıcı (85 SOL ile tüm eğriyi alan cüzdan) havuzu kendisiyle işleterek fitil üretiyor; "USPR 154.724x" gibi rakamlar gerçek alıcı için ulaşılabilir değil. 60 sn giriş fiyatından hesaplanan devasa x60 değerleri de aynı artefakt.

#### Gerçek fiyatlarla beklenen getiri (60 sn girişi, sağlıklı günler, mayhem dışı, n=17.543)

Hesap: EV = P(graduate olmayan) × E[bugünkü fiyat / giriş] + P(600 sn sonrası graduate) × E[kazanç | örneklem] + P(anında dolum) × E[kazanç | örneklem]; %3 maliyet. Üç çıkış politikası: **A** dolum fiyatından sat (paketli: bugüne kadar tut); **B** yarısını dolumun 2 katından sat (ulaşılırsa), kalanı bugüne tut; **C** sağlam zirvenin yarısından sat (iyimser; dakikalar içinde orada olmayı gerektirir).

| Kural (60 sn) | n | 600 sn sonrası graduate | Kaybedenlerin bugünkü değeri / giriş | EV A | EV B | EV C |
|---|---:|---:|---:|---:|---:|---:|
| Hepsini al | 17.543 | %0,59 | 0,90 | -13% | -14% | -3% |
| Creator'ın ilk launch'ı | 7.869 | %0,70 | 0,89 | -16% | -17% | -6% |
| İlk launch & ≥6 alıcı & ≥1 SOL | 1.927 | %2,65 | 0,64 | -32% | -35% | -8% |
| İlk launch & ≥11 alıcı & ≥3 SOL & tek alıcı <0,5 | 1.038 | %4,14 | 0,53 | -31% | -34% | 0% |
| ≥21 alıcı & ≥5 SOL | 1.694 | %4,25 | 0,47 | -39% | -44% | -34% |
| ≥51 alıcı | 1.221 | %3,85 | 0,54 | -34% | -39% | -30% |
| ≥15 SOL giriş & eğri dolmamış | 901 | %7,33 | 0,33 | -41% | -49% | -34% |
| ADAY (mevcut kural) | 2.432 | %1,69 | 0,71 | -31% | -33% | -10% |
| ADAY & ilk launch | 1.574 | %1,84 | 0,70 | -33% | -35% | -1% |
| Ucuz giriş (fiyat <1,5x launch) & ≥6 alıcı & ilk launch | 1.872 | %0,48 | 0,91 | -6% | -8% | +5% |
| 60 sn'de zaten dolmuş (x60 ≥10) | 706 | – | 0,09 | -95% | -95% | -9% |

Zirve verisi kapsamı: sağlıklı günlerdeki 848 graduate'in 732'si (erişilebilir 104'ün 103'ü).

**Gerçekçi politikalarda (A, B) her kural negatif; iyimser politikada (C: gün içi zirvenin yarısında satış) en iyi sonuç +5% ve sıfır civarı.** Mekanizma şu: graduate oranını yükselten her sinyal (çok alıcı, çok SOL girişi) aynı zamanda 60. saniyede yükselmiş bir fiyata girmek demek; o coin'lerin %93-96'sı graduate olmuyor ve launch fiyatına geri dönüyor (kaybedenler girişin %33-65'ini kaybediyor). Kazananların PumpSwap koşusu (medyan 1,83x, aynı gün çöküş) bunu kapatmıyor. Ucuz girişli kural kaybı küçültüyor ama kazanan bulamıyor (%0,48). +5%'lik tek pozitif hücre, ücret/kayma varsayımı %3'ten %5'e çıkınca ya da zirvenin yarısı yerine üçte biri yakalanınca kayboluyor; istatistiksel olarak sıfırdan ayırt edilemez.

---

### 9. Sınırlar ve dürüstlük notları

- Public WebSocket'in launch'ların bir kısmını kaçırmış olma ihtimali sürüyor (`[VARSAYIM]`); zincir taraması yalnızca kaydettiğimiz 58.316 coin'i kapsar, Pump.fun'ın tamamını değil.
- 60 sn snapshot'ların %42'si eksik trade ile üretilmişti (14 Ekim raporu); özellikler gerçekten biraz daha güçlü olabilir, zayıf değil.
- Graduate olmayanların "bugünkü fiyat" değerlemesi 0,1 SOL'luk küçük pozisyon için geçerli; büyük pozisyonda boş eğriye satış daha kötü sonuç verir.
- Creator geçmişi an-itibarıyla hesaplandı; sniper skorları yalnızca %8 coin'de olduğu için kurallara alınmadı.
- Tüm rakamlar 1-17 Eylül 2026 piyasa rejimine ait; farklı dönemde taban oranlar değişebilir.

### Ekler

`turkish/analiz_ekleri/15x/`: `curves.jsonl` (58.316 zincir durumu), `curve_scan.py`, `grad_features3.py` ve çıktıları, `x15_check*.py` ve çıktıları, GeckoTerminal çıktıları (tamamlanınca).

---

### 10. Ek test (3 Kasım): akıllı cüzdan kopyalama `[DOĞRULANDI]`

Soru: Erken girip kârla çıkmayı sürekli başaran cüzdanlar var mı, ve onları kopyalamak kâr bırakır mı?
Yöntem: 1-8 Eylül'de (train) her cüzdanın ilk 60 saniyedeki alımları puanlandı; 9-17 Eylül'de (test) bu cüzdanlar kopyalandı. Kopya kuralı: cüzdan alınca +d sn sonra gir, cüzdan ilk sattığında +d sn sonra çık, satmazsa 600. saniyede çık; %3 maliyet. 16.722 coin, 47.852 cüzdan, 268 bin erken alım. Ayrıntı: `turkish/analiz_ekleri/akilli_cuzdan_ozet.txt`, liste: `turkish/analiz_ekleri/akilli_cuzdan_listesi.csv`.

| Train skoruna göre cüzdan dilimi | Test, gecikmesiz (+0 sn) | Test, +5 sn | Test, +22 sn (bizim gecikmemiz) |
|---|---:|---:|---:|
| En kötü %20 | -3,8% | -10,1% | -7,0% |
| Orta %20 | -0,9% | -3,5% | -4,0% |
| En iyi %20 | **+10,0%** | -4,3% | -1,9% |
| Seçilmiş "akıllı" cüzdanlar (5 farklı kural) | +2% … +14% | -17% … +1,6% | -6,6% … +3,9% |

Okuma:
- **Beceri gerçek ve kalıcı.** Train'de iyi olan cüzdanlar testte de iyi; sıralama beş dilimde de korunuyor. Bu, projede şimdiye kadar bulunan tek zaman ayrımlı pozitif sonuç.
- **Ama kâr tamamen hızda.** Kopyalamaya 5 saniye geç kalınca kazanç kayboluyor; 22 saniyede de yok. Tek pozitif hücre (+3,9%, 317 coin) beş kuraldan birinde çıkıyor ve standart hatası ~3-4 puan; gürültüden ayırt edilemiyor.
- **Sonuç:** Akıllı cüzdan edge'i var ama yalnızca aynı saniyede işlem yapabilen ücretli, hızlı altyapıya sahip olana ait. Ücretsiz altyapıyla bu yol da kapalı.

### 11. Ek test (3 Kasım): "coin'i gör, gir, hareketi sür" `[DOĞRULANDI]`

Soru: Cüzdan seçmeden, coin'i gördüğümüz an girip çıkış kuralıyla ilerlersek ne olur? Ayrıntı: `turkish/analiz_ekleri/coin_surme_testi.txt`.
Yöntem: Sağlıklı günler, mayhem dışı; giriş launch'tan +2 sn (WebSocket senaryosu), +5 sn, +22 sn (bugünkü gecikme) sonraki ilk işlem fiyatı; 8 çıkış kuralı (tut, 60 sn, hedef/stop çiftleri, iz süren stop %25/%40, kademeli); 6 launch-anı filtresi; %3 maliyet; train 1-8 Eylül, test 9-17 Eylül.

Sonuç: **144 kombinasyonun tamamında test dönemi negatif.** Filtresiz +2 sn girişte en iyi kural (iz süren stop %25) train -4,5%, test -3,2%; +22 sn'de -3,7% / -3,5%. Gecikmeyi 22'den 2 saniyeye indirmek sonucu değiştirmiyor. En iyi filtre (creator'ın ilk launch'ı, dev ilk alımı 0,5-3 SOL, iz süren %25) train +0,8%, test -2,9%; sıfırdan ayırt edilemez. "Dev ilk alımı ≥5 SOL" filtresi en kötüsü (-10% … -23%): bunlar paketli dump'lar. Kazanma oranı tüm kombinasyonlarda %6-22.

Yorum: Erken girip sürmek, 2 ile 22 saniye arasındaki her gecikmede zarar. Aradaki tek pozitif nokta 0. saniye, yani ilk alıcıyla aynı blokta olmak; bu da WebSocket'le değil, sniper altyapısıyla alınır.

### 12. Ek test (4 Kasım): graduate sonrası PumpSwap, dakikalık `[DOĞRULANDI]`

Veri: Mayhem dışı 1.278 graduate havuzun migrasyon sonrası ilk ~16 saatlik dakikalık mumları (GeckoTerminal, ücretsiz; 1.251'inde ≥10 mum). Fitiller mum gövdesinin 1,5 katında kırpıldı; ortalamalar işlem başına 10x ile tavanlandı; %3 maliyet. Train: migrasyon ≤ 21 Eylül; test: sonrası. Ayrıntı: `turkish/analiz_ekleri/pumpswap_dakika_testi.txt`, ham mumlar: `turkish/analiz_ekleri/15x/minute_graduated.jsonl`.

**Fiyat yolu (erişilebilir grup, 365 havuz, migrasyon açılışı = 1,0):** +1 dk medyan 0,99; +5 dk 0,91; +15 dk **0,19**; +60 dk 0,07; +6 saat 0,06. Zirve medyan 4. dakikada; %57'si ilk 5 dakikada. Yani PumpSwap'ta "al-tut" yok; olsa olsa ilk 1-5 dakikalık bir sıçrama var ve havuzların yarısında o da yok.

**Stratejiler (erişilebilir grup, giriş migrasyondan +1 dk):**

| Çıkış | Train (n=176) | Test (n=189) |
|---|---:|---:|
| 3 dk tut | +13,4% | -2,6% |
| 5 dk tut | +5,7% | -13,0% |
| 30 dk tut | -36% | -45% |
| 2x hedef / -30% stop | +2,4% (±4,2) | +3,4% (±4,1) |
| **1,5x hedef / -25% stop** | **+5,1% (±2,7)** | **+2,1% (±2,6)** |
| İz süren stop %25 | -0,8% | -9,2% |

Giriş +5 dk veya +15 dk'da tüm kurallar negatif. Filtreler (ilk dakikalardaki getiri, hacim) testte tutarlı bir iyileşme vermiyor. Paketli grupta "1,5x / -25%" testte +10% görünüyor ama bu havuzlar paketleyicinin kendi işlemleriyle dolu; dolumlar güvenilmez.

**Okuma:** 144+ kombinasyon içinde sıfırın altında olmayan tek hücre "migrasyondan 1 dakika içinde gir, +%50'de sat, -%25'te çık". Beklenen getiri +2 ile +5% arasında ve hata payı kadar; hedef dolumu kırpılmış fitile, stop dolumu tam seviyeye göre varsayıldı, ikisi de iyimser. Havuzlar seyrek işlem görüyor (16 saatte medyan 60 dakikada işlem). Gerçek kaymayla bu hücre büyük ihtimalle sıfıra iner. Para makinesi değil; ama bu projede ilk kez gecikmenin öldürmediği bir strateji: dakika ölçeğinde 22 saniyelik gecikme kabul edilebilir. Bu yüzden ücretsiz altyapıyla canlı paper teste konu olabilecek tek aday bu.


---

## 4. Kapanış Notu (4 Kasım 2026)

## Kapanış Notu: Memecoin Motoru

**Tarih:** 4 Kasım 2026
**Karar:** Aktif geliştirme ve "yüksek X yapacak coin'i erken yakalayıp kendi sermayemizle girmek" hedefi durduruldu. Kod, veri ve raporlar arşivlendi.

### Ne vardı

Solana'da Pump.fun launch'larını public WebSocket ile dinleyen, ilk 600 saniyeyi kaydeden, kural tabanlı karar ve cüzdansız paper-trade üreten bir Python sistemi. 1 Eylül - 8 Ekim 2026 arasında 58.316 launch ve 2,09 milyon trade toplandı (10,2 GB SQLite). Collector takvimin %9,6'sında açıktı; trade verisi yalnızca 1-17 Eylül arasında sağlıklı (18 Eylül sonrası ücretsiz RPC kuyruğu yüzünden trade'ler düştü; neden ve ücretsiz çözümü `ANALIZ_YUKSEK_X_KOINLER_2026-10-23.md` §2'de).

### Ne denendi, ne çıktı

Tüm testler zaman ayrımlı (eğitim 1-8 Eylül, test 9-17 Eylül), %3 maliyet dahil, mayhem-mode coin'ler dışarıda.

| Yol | Sonuç |
|---|---|
| İlk 10-60 sn özellikleriyle coin seçip girmek | Her kural negatif (-6% … -49%). Seçim gücü var (graduate oranı 4-12 kat artıyor) ama giriş fiyatı da artıyor |
| Mevcut ADAY kuralı | Rastgele seçimden kötü (2x görme %9 vs taban %16) |
| Creator sattıktan sonra girmek | 2x görme %4 → %7'ye çıkıyor; EV -8% … -14%. 437 kazananın ortak özelliği "zaten kalabalık ve pahalı" |
| Akıllı cüzdan kopyalama | Beceri kalıcı; aynı blokta +10-14%, 1 sn gecikmede 0, 5 sn'de negatif |
| Erken gir ve sür (144 kombinasyon, 2/5/22 sn giriş) | Tamamı negatif; 2 sn ile 22 sn arasında fark yok |
| Graduate sonrası PumpSwap (dakikalık, 1.278 havuz) | 15 dk'da fiyat medyan 0,19x. Tek sıfır-üstü hücre: migrasyondan ≤1 dk gir, 1,5x hedef / -25% stop → test +2% (±2,6), iyimser dolum varsayımıyla |
| Sniper (kör) | Erken alımların ortalaması 0. sn'de +1-3%, sonrası negatif; kâr tamamen ilk blokta |

Yapısal bulgular: Yüksek X (15x ve üstü) pratikte graduate demek; bonding curve launch fiyatından dolum fiyatına 14,7x gider. Graduate'lerin %63'ü launch ile aynı saniyede dolan paketli insider launch'ları. Dev medyan 8. saniyede satıyor. Yükselen coin'lerin zirvesi medyan 9. saniyede. Mayhem-mode coin'lerin fiyatı sanal rezerv şişmesi yüzünden sahte. Bizim zincir gecikmemiz medyan 22 sn.

**Sonuç:** Bu pazarda dışarıdan analizle seçilebilen bir edge yok. Para, coin'i çıkaran/paketleyene ve ilk blokta giren saniye altı botlara gidiyor. Edge yalnızca hızda; hız da aylık 150-500 $ altyapı + özel sunucu + Jito ile başlıyor ve orada bile garanti değil.

### Hangi koşulda yeniden açılır

1. **Bütçe:** Aylık 200-300 $ (gRPC akışı + Frankfurt/Amsterdam VPS) en az 2 ay ayrılabiliyorsa. İlk ay cüzdansız: gecikme ve slot ölçümü; devam kriteri simüle girişlerin ≥%50'sinin ilk alıcıyla aynı/sonraki slotta olması ve paper EV > +5%.
2. **Farklı pencere:** PumpSwap "≤1 dk gir, 1,5x/-25%" hücresini ücretsiz altyapıyla 2-4 hafta canlı paper test etmek istenirse (gecikmeye duyarsız tek aday). Tutarsa küçük sermaye konuşulur.
3. **Ürün/içerik yolu:** Para kazanmak için değil kitle kurmak için: paketli launch tespiti, mayhem uyarısı, dev çıkış sinyali ücretsiz bot + terminal referansı. Plan `ANALIZ_RAPORU_2026-10-14.md` §C ve 3 Kasım notlarında.

Yeniden açılırsa ilk iş değişmez: launch'ı WebSocket log'undan çözmek (RPC kuyruğunu kaldırır), cüzdan/sniper zenginleştirmesini kapatmak, oturum modeli ve karar dondurma (sızıntı) düzeltmeleri.

### Nerede ne var

| Ne | Yer |
|---|---|
| Kod (3.700 satır, 27 test) | `src/`, `tests/`; Git deposu (4 Kasım 2026 ilk commit) |
| Veritabanı (10,2 GB) | Orijinal 4 Kasım 2026'da silindi. Tek kopya: `../memecoin_backup_2026-11-04/memecoin_motor.db.gz` (2,2 GB, gzip; bayt bayt doğrulandı). Geri almak için: `gzip -dc memecoin_motor.db.gz > data/memecoin_motor.db` (10,2 GB boş yer gerekir). Eski küçük `.bak` dosyaları da aynı klasörde |
| Sistem/veri/gelir raporu | `ANALIZ_RAPORU_2026-10-14.md` |
| 58.316 coin'in akıbeti, tüm strateji testleri | `ANALIZ_YUKSEK_X_KOINLER_2026-10-23.md` (§1-12) |
| Coin bazlı otopsi (max X, kim sattı) | `turkish/analiz_ekleri/coin_otopsi.csv` |
| Creator satışı sonrası, akıllı cüzdan, sürme, PumpSwap testleri | `turkish/analiz_ekleri/*.txt`, `turkish/analiz_ekleri/*.csv` |
| Zincir durumu (graduate), PumpSwap gün/dakika mumları | `turkish/analiz_ekleri/15x/` |
| Tüm betikler (salt-okunur, yeniden çalıştırılabilir) | `turkish/analiz_ekleri/*.py`, `turkish/analiz_ekleri/15x/*.py` |

Betikler veritabanını yalnızca `mode=ro` ile açar; hiçbir test üretim verisini değiştirmedi, hiçbir gerçek işlem gönderilmedi.


---

## 5. Tasarım Dokümanı v2.1 (memecoin_analiz_motoru_v2.md)

## Memecoin Erken Karar, X Potansiyeli ve Agentic Denetim Motoru

**Surum:** 2.1  
**Ilk hedef ag:** Solana  
**Ilk kapsam:** Tek launchpad/program  
**Yaklasim:** Deterministik kurallar + klasik ML + agentic arastirma/denetim

### 1. Amac

Yeni cikan memecoinleri erken algilayip su sorulara olasiliksal cevap vermek:

1. Token teknik olarak alinabilir ve satilabilir mi?
2. Rug, honeypot veya sert dump riski ne kadar?
3. 1.5x, 2x, 3x ve 5x seviyelerine ulasma ihtimali nedir?
4. Gecikme, maliyet ve risk dahil edildiginde girmeye deger mi?

Motor "kesin X yapar" veya "kesin rug olmaz" demeyecek. Her sonuc olasilik, veri kalitesi ve guven seviyesiyle verilecek.

```text
Token: ABC
Zincir yasi: 14.2 saniye
Veri gecikmesi: 1.4 saniye
P(1 saat icinde 2x): %31
P(10 dakika icinde %70 dusus): %48
Tahmini fill olasiligi: %62
Karar: GIRME
Guven: Dusuk
```

### 2. Temel ilkeler

- Ilk saniyelerde kesin karar verilmez; yalnizca risk azaltilir.
- Hizli karar yolunda LLM/agent kullanilmaz.
- Acik teknik riskler deterministik kurallarla elenir.
- X ve dump ihtimalleri klasik ML ile tahmin edilir.
- Agentic AI yavas arastirma, denetim, aciklama ve operasyonda calisir.
- Veri gecikmesi olculmeden snapshot egitim verisi sayilmaz.
- Paper trade, teorik fiyattan otomatik fill kabul etmez.
- Yeterli paper test ve kor test olmadan gercek para kullanilmaz.

### 3. Hibrit mimari

```text
Solana WebSocket/RPC (ileride Geyser)
                 |
                 v
        Olay ve slot kayit hatti
                 |
        +--------+---------+
        |                  |
        v                  v
 HIZLI KARAR HATTI    YAVAS AGENTIC HAT
 - Teknik kurallar    - Creator arastirmasi
 - Anlik ozellikler   - Derin clustering
 - Klasik ML          - Sosyal/web incelemesi
 - Fill modeli        - Veri/model denetimi
 - Risk motoru        - Hata analizi
        |                  |
        v                  v
 GIRME/IZLE/ADAY      Rapor/uyari/oneri
        |
        v
 Paper trade
```

Agentic hat, hizli karari gecmise donuk degistirmez. Gec gelen bilgi ancak sonraki skor veya cikis uyarisinda kullanilir.

### 4. Saniyelik karar kapilari

| Hedef yas | Islem | Guven |
|---|---|---|
| 0-2 saniye | Islem yapisi, yetkiler, likidite, acik teknik risk | Cok dusuk |
| 2-5 saniye | Ilk islemler, creator hareketi, gorunen yogunlasma | Dusuk |
| 5-10 saniye | Benzersiz alici artisi, ilk satislar, net akim | Dusuk-orta |
| 10-30 saniye | Momentum, wash trading ve bot davranisi | Orta |
| 30-60 saniye | Holder ve asenkron analiz sonuclari | Orta |

Bu sureler garanti degil, hedef zamandir. Gec gelen veri erken snapshot olarak yazilmaz.

```text
YENI -> REDDEDILDI
YENI -> IZLE -> REDDEDILDI
YENI -> IZLE -> ADAY -> PAPER BUY
ADAY/PAPER BUY -> RISK ARTTI -> CIKIS UYARISI
```

### 5. Veri zamani ve butunlugu

Ucretsiz RPC/WebSocket gecikebilir, kopabilir veya slot kacirabilir. Client saati tek gercek kabul edilmez.

Her olayda zorunlu alanlar:

```text
slot
block_time
tx_index_in_block
signature
commitment
provider_name
client_received_at
processed_at
ingestion_latency_ms
is_backfilled
stream_gap_detected
data_completeness
```

`block_time` tahmini ve saniye cozunurlugundedir; slot, islem sirasi ve yerel gelis zamaniyla birlikte kullanilir.

```text
target_age_ms: 2000
actual_chain_age_ms: 7800
ingestion_delay_ms: 6100
snapshot_quality: LATE
```

#### Gap ve backfill politikasi

- Son gorulen slot saklanir.
- Slot sicrarsa gap kaydi acilir.
- Eksik slotlar ayri RPC ile backfill edilir.
- Backfill verisi canli gorulmus gibi etiketlenmez.
- Confirmed/finalized veri sonradan uzlastirilir.
- Eksik veya gec ornekler canli fill testinden cikarilir.
- Veri kalitesi modelde filtre ve ozellik olarak kullanilir.

### 6. Veri kaynaklari

#### Dogrudan Solana

- Mint, launch, havuz, swap ve transfer olaylari
- Mint/freeze yetkileri ve Token-2022 ozellikleri
- Creator/deployer
- Likidite ve rezerv degisimi
- Ilk alici/saticilar
- Creator ve insider satislari

#### Zenginlestirme

- DEX Screener: fiyat, hacim, likidite, islem ve pair bilgisi
- RugCheck: Solana risk raporu
- GoPlus: desteklenen guvenlik kontrolleri

REST servisleri ana olay algilayici degildir; indeksleme gecikebilecegi icin capraz kontrol ve zenginlestirme amaciyla kullanilir.

#### Piyasa baglami

- SOL yonu ve oynakligi
- Launchpad aktivitesi
- Genel memecoin risk istahi
- Yakin donemde basarili/basarisiz lansman orani

### 7. Hizli teknik guvenlik kapisi

Dogudan ret nedenleri:

- Satis simulasyonu basarisiz
- Tehlikeli mint/freeze/transfer yetkisi
- Riskli Token-2022 uzantisi
- Cikis yapmaya yetmeyecek likidite
- Ani likidite cekimi
- Erken creator/insider satisi
- Acik koordineli/yapay alim paterni
- Risk limitinin uzerinde gorunen arz yogunlasmasi

RugCheck veya GoPlus tarafindan risk bulunmamasi, tokenin guvenli oldugu anlamina gelmez.

### 8. Cuzdan clustering

Ilk 2-5 saniyede cok sayida cuzdanin tam gecmisi RPC ile sorgulanmaz.

#### Hizli yol

- Ayni fee payer veya fonlama islemi
- Ayni slotta koordineli alim
- Creator ile ayni islemde baglanti
- Benzer tutar ve zamanlama
- Gorunen holder yogunlasmasi

#### Yavas/asenkron yol

- `getSignaturesForAddress` ve transfer gecmisi
- CEX/bridge fonlama izleri
- Cok adimli transfer grafigi
- Creatorin onceki tokenlari
- Uzun sureli davranis benzerligi

Tercih edilen yapi, surekli guncellenen yerel bir cuzdan/fonlama grafigidir. Baglanti bulunamamasi "insider yok" anlamina gelmez.

```text
gozlenen_insider_orani: %8
tahmini_baglantili_oran: %17-%31
clustering_kapsami: %42
tespit_edilemeyen_risk: YUKSEK
```

### 9. Klasik ML tahmin katmani

Tablo verisi icin ilk adaylar LightGBM, XGBoost, CatBoost ve lojistik regresyondur. LLM bu sayisal tahminin merkezinde kullanilmaz.

#### Ozellik gruplari

- Teknik risk ve yetkiler
- Likidite/market-cap ve quote rezervi
- Fiyat etkisi ve tahmini slippage
- Benzersiz alici artis hizi
- Alis/satis orani ve net SOL akimi
- Islem buyuklugu dagilimi
- Holder/insider yogunlugu
- Creator gecmisi
- Momentum, oynaklik ve piyasa rejimi
- Wash trading/bot olasiligi
- Veri gecikmesi ve tamlik skoru

#### Ayri modeller

1. `P(1.5x / 2x / 3x / 5x)` modeli
2. Belirli sure icinde rug/sert dump modeli
3. Maksimum yukselis ve maksimum dusus modeli
4. Landing/fill ve slippage modeli

```text
P(10 dakika icinde 1.5x): %48
P(1 saat icinde 2x): %27
P(24 saat icinde 3x): %9
P(10 dakika icinde %70 dusus): %41
```

### 10. Karar motoru

```text
isleme_deger = beklenen_net_getiri
               x fill_olasiligi
               - rug_riski_cezasi
               - likidite_cezasi
               - veri_belirsizligi_cezasi
```

- **GIRME:** Kritik sorun veya negatif risk ayarli beklenti
- **IZLE:** Veri yetersiz ya da skor sinirda
- **ADAY:** Pozitif beklenti var, henuz islem yok
- **PAPER BUY:** Sanal islem kosullari saglandi
- **CIKIS UYARISI:** Insider satisi, likidite kaybi veya momentum bozulmasi

ML, deterministik guvenlik ve risk limitlerini gecersiz kilamaz.

### 11. Gercekci paper trading ve Jito

Paper motoru sinyal fiyatindan otomatik fill yazmaz:

```text
base_fee
priority_fee
jito_tip
slippage
price_impact
ata_creation_cost
failed_attempt_cost
landing_probability
landing_latency_slots
```

Sabit 0.50-1.00 USD maliyet yalnizca kaba baseline olabilir. SOL fiyati, ag yogunlugu ve Jito acik artirmasi degisken oldugu icin dinamik senaryolar kullanilir.

1. Karar zamani kaydedilir.
2. Islem hazirlama/gonderme gecikmesi eklenir.
3. Donemin priority fee ve Jito tip dagilimi uygulanir.
4. Landing olasiligi ve slotu tahmin edilir.
5. Landing slotundaki havuz durumu kullanilir.
6. Slippage veya likidite yetersizse islem basarisiz sayilir.
7. Basarisiz denemeler net sonuca eklenir.

Iyimser, gercekci ve kotumser senaryolar ayri raporlanir.

#### Uygulanan paper-v2 kurallari

- Fill penceresi karar zamanindan itibaren en fazla 8 saniyedir.
- 0.1 SOL giris/cikisi mikro-trade fiyatindan degil sanal rezervlerden hesaplanir.
- Token basina ilk basarili ADAY kanonik; 10/30/60 saniye girisleri deney grubudur.
- Cozulememis slot gap'i `GAP_AFFECTED` olur ve kalibrasyona alinmaz.
- %40 @ 1.5x, %30 @ 2x, %20 @ 3x satis ve momentum kirilmasi uygulanir.
- Basarili IZLE tokenlari ayri kacirilan-firsat raporunda incelenir.
- X bantlari `CONTINUOUS` sonuclarin p25/p50/p75/p90 dagilimiyla kalibre edilir.

### 12. Iki katmanli veri depolama

Tum tokenlari silmek selection bias yaratir; her tokenin tum ham verisini saklamak ise pahali olabilir.

#### Minimal katman: Tum tokenlar

```text
mint, creator, program, launch_slot, block_time,
ilk_likidite, maksimum_hacim, son_durum, ret_nedeni
```

#### Ayrintili katman: Terfi eden tokenlar

Launchpad'e gore minimum hacim/likidite, benzersiz alici, yasam suresi veya onemli anomali esigini gecen tokenlarda swap, holder, likidite ve zaman serisi tutulur.

Ham RPC/API JSON'lari sinirsiz saklanmaz; sikistirma, tekillestirme ve saklama suresi uygulanir. Basarisiz token sinifi tamamen kaybedilmez.

### 13. Agentic AI katmani

Agent saniyelik alim-satim beyni degildir.

#### Arastirma agenti

- Creatorin onceki tokenlarini inceler.
- Cuzdan ve fonlama baglantilarini derinlestirir.
- Web sitesi ve sosyal hesap gecmisini arastirir.
- Benzer veya supheli projeleri raporlar.

#### Risk/model denetim agenti

- Yanlis ADAY/PAPER BUY sinyallerini analiz eder.
- Launchpad ve doneme gore performans bozulmasini bulur.
- Veri dagilimi ve model drift izler.
- Yeni rug kaliplari ve ozellikler onerir.

#### Operasyon agenti

- RPC gecikmesi, 429, kopma ve slot bosluklarini izler.
- Veri kalitesi dusunce sinyalleri durdurmayi onerir.
- Servis arizalarini ozetler.
- Gunluk performans/risk raporu hazirlar.

#### Agent yetki sinirlari

Agent:

- Cuzdan imzalayamaz ve kendi basina islem yapamaz.
- Pozisyon veya kayip limitini artiramaz.
- Stop/guvenlik filtresini kapatamaz.
- Modeli otomatik canliya alamaz.
- Deterministik risk motorunu gecersiz kilamaz.

Kritik agent onerileri insan onayi ve yeniden test gerektirir.

### 14. Backtest ve etiketleme

Elle secilen tokenlar kullanilmaz. Tum tokenlar minimal katmanda saklanir. Hedef snapshotlar:

```text
2 sn, 5 sn, 10 sn, 30 sn, 60 sn,
5 dk, 1 saat, 6 saat, 24 saat, 72 saat
```

Hedef yas ile gercek zincir yasi birlikte tutulur. Gecikmeli veri erken zamanda mevcutmus gibi modele verilmez.

Etiketler:

- Sinyalden sonra maksimum alinabilir X
- Maksimum dusus
- Hedeflere ulasma suresi
- Hedeften once gorulen dusus
- Likidite cekimi ve zamani
- Creator/insider satis zamani
- Gercekci paper giris/cikis fiyati
- Tum maliyetlerden sonra net sonuc

Egitim ve test tarih sirasina gore ayrilir. Gelecek bilgisi karar ani ozelliklerine sizamaz.

### 15. Basari olcutleri

- Rug/dump precision ve recall
- Yanlis guvenli/ADAY orani
- Olasilik kalibrasyonu
- Fill tahmin uyumu
- Maliyet sonrasi net getiri
- Maksimum drawdown
- Basit baseline'a gore ek fayda
- Piyasa donemleri arasinda dayaniklilik
- Algilama, karar ve landing gecikmesi
- Eksik/gec snapshot orani

Yuksek isabet tek basina basari degildir. Gorulmemis donemde gercekci maliyetlerle pozitif sonuc ve kabul edilebilir risk gerekir.

### 16. Gelistirme asamalari

1. **Guvenilir veri hatti:** WebSocket, slot gap, backfill ve iki katmanli depolama.
2. **Kural tabanli baseline:** Teknik ret, hizli ozellikler ve asenkron clustering.
3. **Gercekci paper trading:** Dinamik fee/Jito, landing, slippage ve basarisiz islem.
4. **Klasik ML:** X, dump ve fill modelleri; zaman sirali kor test.
5. **Agentic denetim:** Arastirma, drift, operasyon ve performans raporlari.
6. **Kontrollu canli test:** Yalnizca basarili paper testten sonra; cok kucuk sermaye ve kill-switch ile.

### 17. Urunlestirme

Performans dogrulanmadan Telegram, paylasim veya gelir modeli gelistirilmez.

1. Yalnizca kendi islemlerimizde kullanma
2. Analiz/sinyal servisi
3. Kullanicinin kendi cuzdanindaki islemlerden islem veya performans bazli gelir

Ucuncu secenek; cuzdan yetkisi, fon saklama, guvenlik, vergi, tuketici korumasi ve finansal duzenlemeler icin ayri hukuki inceleme gerektirir.

### 18. Ilk teknik basari tanimi

Ilk basari para kazanmak veya bir AI agent calistirmak degildir:

> Secilen launch kaynagindaki tokenlari kesintisiz algilamak, slot kayiplarini tespit edip tamamlamak, ilk 2-60 saniyedeki verinin gercek yasini dogru kaydetmek ve sonuclari gelecege ait veri sizdirmadan eslestirmek.

Bu temel dogrulanmadan ML tahmini, agent yorumu veya "girmeye deger" karari guvenilir kabul edilmez.

### 19. Uygulama durumu - cuzdansiz paper baseline

Mevcut uygulama `baseline-v1` ADAY kararlarini cüzdan baglamadan test eder.
Private key/seed phrase saklanmaz ve zincire transaction gonderilmez. Karardan
sonraki gecikmeli ilk gozlenen trade, sanal giris referansidir. Base fee,
priority fee, Jito tip, iki yonlu slippage ve rezerv etki limiti uygulanir.
Kesintisiz takip varsa 60 ve 300 saniyede maliyet sonrasi maksimum X, minimum X,
final X, hedef vurma ve drawdown kaydedilir.

Selection bias'i onlemek icin ham piyasa sonucu yalniz ADAY sinyallerinde degil,
GIRME ve IZLE dahil tum karar snapshotlarinda etiketlenir. Paper pozisyonu ise
yalniz ADAY kararinda olusur.

Bu surum gercek landing replay degildir. Fee/Jito varsayimlari sabittir ve
PumpSwap migrasyon sonrasi fiyatlar kapsam disidir. Paper sonucunun pozitif
olmasi canli para kullanma izni sayilmaz.

### 20. Sniper ve bundle kanit katmani

Ilk 10 saniyedeki sinirli sayida erken alici icin tam transaction asenkron
olarak okunur. Fee payer, Compute Budget priority fee, resmi Jito tip hesabina
transfer, `jitodontfront`, ayni slot, ortak fonlayici, tekrar eden erken giris ve
hizli satis davranislari `EARLY_TRADER`, `SNIPER_CANDIDATE` veya
`COORDINATED_SNIPER` skoruna donusturulur.

Jito tip veya ayni slot tek basina bundle kaniti degildir. Bundle ID olmadan
sonuc yalniz `LOW/MEDIUM/HIGH bundle likelihood` olarak tutulur; kesin bundle
etiketi uretilmez. Koordineli sniper ve yuksek bundle ihtimali risk baseline'ina
ceza olarak eklenir.
