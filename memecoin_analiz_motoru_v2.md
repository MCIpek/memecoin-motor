# Memecoin Erken Karar, X Potansiyeli ve Agentic Denetim Motoru

**Surum:** 2.1  
**Ilk hedef ag:** Solana  
**Ilk kapsam:** Tek launchpad/program  
**Yaklasim:** Deterministik kurallar + klasik ML + agentic arastirma/denetim

## 1. Amac

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

## 2. Temel ilkeler

- Ilk saniyelerde kesin karar verilmez; yalnizca risk azaltilir.
- Hizli karar yolunda LLM/agent kullanilmaz.
- Acik teknik riskler deterministik kurallarla elenir.
- X ve dump ihtimalleri klasik ML ile tahmin edilir.
- Agentic AI yavas arastirma, denetim, aciklama ve operasyonda calisir.
- Veri gecikmesi olculmeden snapshot egitim verisi sayilmaz.
- Paper trade, teorik fiyattan otomatik fill kabul etmez.
- Yeterli paper test ve kor test olmadan gercek para kullanilmaz.

## 3. Hibrit mimari

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

## 4. Saniyelik karar kapilari

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

## 5. Veri zamani ve butunlugu

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

### Gap ve backfill politikasi

- Son gorulen slot saklanir.
- Slot sicrarsa gap kaydi acilir.
- Eksik slotlar ayri RPC ile backfill edilir.
- Backfill verisi canli gorulmus gibi etiketlenmez.
- Confirmed/finalized veri sonradan uzlastirilir.
- Eksik veya gec ornekler canli fill testinden cikarilir.
- Veri kalitesi modelde filtre ve ozellik olarak kullanilir.

## 6. Veri kaynaklari

### Dogrudan Solana

- Mint, launch, havuz, swap ve transfer olaylari
- Mint/freeze yetkileri ve Token-2022 ozellikleri
- Creator/deployer
- Likidite ve rezerv degisimi
- Ilk alici/saticilar
- Creator ve insider satislari

### Zenginlestirme

- DEX Screener: fiyat, hacim, likidite, islem ve pair bilgisi
- RugCheck: Solana risk raporu
- GoPlus: desteklenen guvenlik kontrolleri

REST servisleri ana olay algilayici degildir; indeksleme gecikebilecegi icin capraz kontrol ve zenginlestirme amaciyla kullanilir.

### Piyasa baglami

- SOL yonu ve oynakligi
- Launchpad aktivitesi
- Genel memecoin risk istahi
- Yakin donemde basarili/basarisiz lansman orani

## 7. Hizli teknik guvenlik kapisi

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

## 8. Cuzdan clustering

Ilk 2-5 saniyede cok sayida cuzdanin tam gecmisi RPC ile sorgulanmaz.

### Hizli yol

- Ayni fee payer veya fonlama islemi
- Ayni slotta koordineli alim
- Creator ile ayni islemde baglanti
- Benzer tutar ve zamanlama
- Gorunen holder yogunlasmasi

### Yavas/asenkron yol

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

## 9. Klasik ML tahmin katmani

Tablo verisi icin ilk adaylar LightGBM, XGBoost, CatBoost ve lojistik regresyondur. LLM bu sayisal tahminin merkezinde kullanilmaz.

### Ozellik gruplari

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

### Ayri modeller

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

## 10. Karar motoru

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

## 11. Gercekci paper trading ve Jito

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

### Uygulanan paper-v2 kurallari

- Fill penceresi karar zamanindan itibaren en fazla 8 saniyedir.
- 0.1 SOL giris/cikisi mikro-trade fiyatindan degil sanal rezervlerden hesaplanir.
- Token basina ilk basarili ADAY kanonik; 10/30/60 saniye girisleri deney grubudur.
- Cozulememis slot gap'i `GAP_AFFECTED` olur ve kalibrasyona alinmaz.
- %40 @ 1.5x, %30 @ 2x, %20 @ 3x satis ve momentum kirilmasi uygulanir.
- Basarili IZLE tokenlari ayri kacirilan-firsat raporunda incelenir.
- X bantlari `CONTINUOUS` sonuclarin p25/p50/p75/p90 dagilimiyla kalibre edilir.

## 12. Iki katmanli veri depolama

Tum tokenlari silmek selection bias yaratir; her tokenin tum ham verisini saklamak ise pahali olabilir.

### Minimal katman: Tum tokenlar

```text
mint, creator, program, launch_slot, block_time,
ilk_likidite, maksimum_hacim, son_durum, ret_nedeni
```

### Ayrintili katman: Terfi eden tokenlar

Launchpad'e gore minimum hacim/likidite, benzersiz alici, yasam suresi veya onemli anomali esigini gecen tokenlarda swap, holder, likidite ve zaman serisi tutulur.

Ham RPC/API JSON'lari sinirsiz saklanmaz; sikistirma, tekillestirme ve saklama suresi uygulanir. Basarisiz token sinifi tamamen kaybedilmez.

## 13. Agentic AI katmani

Agent saniyelik alim-satim beyni degildir.

### Arastirma agenti

- Creatorin onceki tokenlarini inceler.
- Cuzdan ve fonlama baglantilarini derinlestirir.
- Web sitesi ve sosyal hesap gecmisini arastirir.
- Benzer veya supheli projeleri raporlar.

### Risk/model denetim agenti

- Yanlis ADAY/PAPER BUY sinyallerini analiz eder.
- Launchpad ve doneme gore performans bozulmasini bulur.
- Veri dagilimi ve model drift izler.
- Yeni rug kaliplari ve ozellikler onerir.

### Operasyon agenti

- RPC gecikmesi, 429, kopma ve slot bosluklarini izler.
- Veri kalitesi dusunce sinyalleri durdurmayi onerir.
- Servis arizalarini ozetler.
- Gunluk performans/risk raporu hazirlar.

### Agent yetki sinirlari

Agent:

- Cuzdan imzalayamaz ve kendi basina islem yapamaz.
- Pozisyon veya kayip limitini artiramaz.
- Stop/guvenlik filtresini kapatamaz.
- Modeli otomatik canliya alamaz.
- Deterministik risk motorunu gecersiz kilamaz.

Kritik agent onerileri insan onayi ve yeniden test gerektirir.

## 14. Backtest ve etiketleme

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

## 15. Basari olcutleri

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

## 16. Gelistirme asamalari

1. **Guvenilir veri hatti:** WebSocket, slot gap, backfill ve iki katmanli depolama.
2. **Kural tabanli baseline:** Teknik ret, hizli ozellikler ve asenkron clustering.
3. **Gercekci paper trading:** Dinamik fee/Jito, landing, slippage ve basarisiz islem.
4. **Klasik ML:** X, dump ve fill modelleri; zaman sirali kor test.
5. **Agentic denetim:** Arastirma, drift, operasyon ve performans raporlari.
6. **Kontrollu canli test:** Yalnizca basarili paper testten sonra; cok kucuk sermaye ve kill-switch ile.

## 17. Urunlestirme

Performans dogrulanmadan Telegram, paylasim veya gelir modeli gelistirilmez.

1. Yalnizca kendi islemlerimizde kullanma
2. Analiz/sinyal servisi
3. Kullanicinin kendi cuzdanindaki islemlerden islem veya performans bazli gelir

Ucuncu secenek; cuzdan yetkisi, fon saklama, guvenlik, vergi, tuketici korumasi ve finansal duzenlemeler icin ayri hukuki inceleme gerektirir.

## 18. Ilk teknik basari tanimi

Ilk basari para kazanmak veya bir AI agent calistirmak degildir:

> Secilen launch kaynagindaki tokenlari kesintisiz algilamak, slot kayiplarini tespit edip tamamlamak, ilk 2-60 saniyedeki verinin gercek yasini dogru kaydetmek ve sonuclari gelecege ait veri sizdirmadan eslestirmek.

Bu temel dogrulanmadan ML tahmini, agent yorumu veya "girmeye deger" karari guvenilir kabul edilmez.

## 19. Uygulama durumu - cuzdansiz paper baseline

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

## 20. Sniper ve bundle kanit katmani

Ilk 10 saniyedeki sinirli sayida erken alici icin tam transaction asenkron
olarak okunur. Fee payer, Compute Budget priority fee, resmi Jito tip hesabina
transfer, `jitodontfront`, ayni slot, ortak fonlayici, tekrar eden erken giris ve
hizli satis davranislari `EARLY_TRADER`, `SNIPER_CANDIDATE` veya
`COORDINATED_SNIPER` skoruna donusturulur.

Jito tip veya ayni slot tek basina bundle kaniti degildir. Bundle ID olmadan
sonuc yalniz `LOW/MEDIUM/HIGH bundle likelihood` olarak tutulur; kesin bundle
etiketi uretilmez. Koordineli sniper ve yuksek bundle ihtimali risk baseline'ina
ceza olarak eklenir.
