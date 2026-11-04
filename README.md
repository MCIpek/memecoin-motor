# Memecoin Motoru

> **English summary.** A Solana research engine for Pump.fun launches: event-time data pipeline (WebSocket + IDL decoding), rule-based risk scoring and wallet-free, bonding-curve-aware paper trading. Between 1 Sep and 8 Oct 2026 it recorded 58,316 launches and 2.09M trades; every coin's fate was then read back from chain (graduation flag) and PumpSwap price history. **Verdict:** 63% of graduates are filled in the launch block by insiders; the dev sells at a median of 8 s; every outsider entry strategy tested (early-feature selection, post-dev-exit entry, smart-wallet copying, enter-and-ride, post-graduation minute trading) has negative expected value after costs, and the only positive edge exists at 0-second (same-block) latency. Reports are in Turkish: `ANALIZ_RAPORU_2026-10-14.md` (system/data/revenue), `ANALIZ_YUKSEK_X_KOINLER_2026-10-23.md` (58k-coin post-mortem and strategy tests), `KAPANIS_NOTU_2026-11-04.md` (closing note). Raw outputs and read-only analysis scripts live in `analiz_ekleri/`. The 10 GB SQLite database is not in the repo.

Bu depo, `memecoin_analiz_motoru_v2.md` tasariminin uygulamasidir. Sistem veri
toplar, kural karari ve cuzdansiz paper test uretir; gercek alim-satim yapmaz,
cuzdan istemez ve henuz ML/agent calistirmaz.

> Guncel durum (14 Ekim 2026): Sistem PostgreSQL degil, yaklasik 10.2 GB
> buyuklugundeki `data/memecoin_motor.db` SQLite veritabanini kullanir. Son
> toplanan launch 8 Ekim 2026 tarihlidir. Mevcut sonuclar arastirma verisidir;
> canli para kullanimi icin yeterli performans veya veri surekliligi kaniti yoktur.

## Mevcut kapsam

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

## Toplanan veri ve mevcut sonuc

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

### Snapshot kalitesi

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

### Paper-v2 baseline sonucu

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

## Gereksinimler

- Python 3.11 veya ustu
- Internet erisimi olan Solana HTTP ve WebSocket RPC

## Kurulum

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

## Calistirma

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

## Veri tablolari

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

## Risk baseline-v1

Bu katman tahmin modeli degildir ve islem acmaz. Net quote akisi, benzersiz
alici, tek/top-5 alici yogunlasmasi, creator satisi/gecmisi, snapshot kalitesi,
cuzdan analiz kapsami ve ortak fonlayiciyi puanlar. `ADAY` en erken 10 saniyede
ve yeterli guvenle verilir. Kritik creator satisi disinda 2/5 saniyelik yetersiz
veri `GIRME` degil `IZLE` sonucudur. Her karar nedenleri ve warnings alanlariyla
saklanir; esikler paper test verisi birikince kalibre edilmelidir.

## Cuzdansiz paper test

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

## Paper-v2 ve X kalibrasyonu

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

## Sniper ve bundle kanitlari

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

## Bilinen sinirlar

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

## Gelistirme onceligi

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
