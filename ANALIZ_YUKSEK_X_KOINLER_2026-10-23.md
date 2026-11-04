# 58.316 Coin'in Akıbeti: Yüksek X Yapacak Coin Erken Tespit Edilebilir mi?

**Tarih:** 23-26 Ekim 2026 (sürüm 3, final: zincir durumu 58.316 coin'in tamamı; PumpSwap zirve verisi 1.853 graduate havuzunun tamamı)
**Soru:** Elimizdeki 10 GB veride kayıtlı 58.316 Pump.fun launch'ının sonradan ne olduğuna bakarak, yüksek X yapacak coin'i ilk dakikalarda ayırt etmek mümkün mü? Mümkünse kendimiz girmeli miyiz, yoksa bunu araç olarak mı satmalıyız?
**Yöntem:**
1. Veritabanındaki 58.316 mint'in tamamı için bonding-curve hesabı Solana public RPC'den okundu (`getMultipleAccounts`, 584 çağrı, 0 hata). Böylece her coin için zincirdeki **kesin** durum elde edildi: graduate oldu mu (`complete`), şu anki rezervler, mayhem bayrağı.
2. Graduate olan 2.020 coin için PumpSwap havuzu ve günlük fiyat geçmişi GeckoTerminal'den çekiliyor (ücretsiz API dakikada ~7 istek; ~5 saat sürüyor, devam ediyor).
3. Bunlar veritabanındaki ilk 10/30/60 saniye özellikleri, risk kararları ve creator geçmişiyle eşleştirildi.
4. Tüm sorgular salt-okunur; üretim verisi değiştirilmedi. Ham çıktılar `analiz_ekleri/15x/` altında.

Etiketler: `[DOĞRULANDI]` zincir veya veritabanıyla; `[ÇIKARIM]` veriden türetilmiş yorum; `[VARSAYIM]` doğrulanamadı.

---

## 1. Beş cümlelik sonuç

1. **Bu veride "yüksek X" pratikte "graduate oldu" demek.** Pump.fun eğrisi launch fiyatından dolum fiyatına tam 14,7x yol alır; eğri dolmadan 15x olmaz, eğri dolan her coin de tanım gereği 14,7x'tir. `[DOĞRULANDI]`
2. **58.316 coin'in %3,7'si (2.020) graduate olmuş;** mayhem dışı SOL coin'lerde %4,1 (1.436). Geri kalan %96 eğrinin ilk %1'inde ölmüş ve launch fiyatına geri dönmüş. `[DOĞRULANDI]`
3. **Graduate olanların %63'ü (906) launch ile aynı saniyede, ortalama 2,8 cüzdanla ve tek alıcının alımların %79'unu yaptığı "paketli anında dolum" launch'ları.** Bunlar biz görmeden bitmiş; bize sadece çıkış likiditesi rolü kalır. Erişilebilir hedef, 600 saniyeden sonra graduate olan **398 coin (%1,1)**. `[DOĞRULANDI]`
4. **İlk 60 saniye özellikleri bu %1,1'lik hedefi 4-12 kat zenginleştirebiliyor** (örneğin 60 sn'de 15 SOL+ net giriş ve eğri henüz dolmamışsa graduate oranı %7,3). **Ama 60. saniyede girip gerçek PumpSwap fiyatlarıyla çıkınca gerçekçi her senaryoda her kural zarar ediyor (-6% ile -49%); en iyimser senaryoda bile en iyi kural +5% ile sıfır civarı.** Erişilebilir graduate'lerin dolum sonrası koşusu medyan 1,83x ve aynı gün çöküyor; bugün %89'u launch fiyatının altında. Sinyal var, para yok. `[DOĞRULANDI, 1.853 graduate havuzunun tamamı]`
5. **Verinin özellik analizine uygun kısmı yalnızca 1-17 Eylül.** 18 Eylül'den sonra collector launch'ları kaydetmiş ama trade'leri neredeyse hiç yakalamamış (launch başına trade 60-84'ten 0,6-10'a düşmüş). Bu, 14 Ekim raporunda gözden kaçan en büyük veri hatası. `[DOĞRULANDI]`

---

## 2. Veri yakalama 18 Eylül'de çökmüş `[DOĞRULANDI]`

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

## 3. Coin'lerin akıbeti: zincirden okunan kesin durum `[DOĞRULANDI]`

| Grup | n | Graduate | Oran |
|---|---:|---:|---:|
| Tüm SOL-quote launch | 54.904 | 2.020 | %3,68 |
| Mayhem dışı | 35.021 | 1.436 | %4,10 |
| Mayhem | 19.883 | 584 | %2,94 |
| SOL dışı quote (USDC vb.) | 3.412 | 78 | %2,29 |

Graduate olmayan 52.884 coin'in bugünkü durumu: %99,8'i eğri ilerlemesinin %1'inin altında; eğri fiyatı launch fiyatına geri dönmüş (medyan 1,000x). Yani "ölen coin" tam olarak sıfıra gitmiyor, alıcılar satıp çıkınca eğri başlangıç noktasına dönüyor. 0,1 SOL'luk bir pozisyon bugün hâlâ yaklaşık giriş fiyatından satılabilir durumda; kayıp küçük ama sermaye haftalarca kilitli kalıyor.

Mayhem kontrolü: Bizim verimizde "eğri 115 SOL'a ulaştı" görünen 1.859 coin'in 753'ü zincirde graduate olmamış ve **753'ünün tamamı mayhem**. Mayhem modunda sanal rezerv gerçek SOL olmadan şişiyor; önceki raporda tespit edilen "sahte 15x" artefaktı zincirle kesinleşti. Mayhem coin'ler bu analizin geri kalanından çıkarıldı.

### Graduate olanların kompozisyonu (mayhem dışı, 1.436)

| Ne zaman doldu | n | Pay | Yorum |
|---|---:|---:|---|
| Launch ile aynı saniye (yaş 0) | 906 | %63 | Paketli (bundle) launch: ortalama 2,8 alıcı, tek alıcı alımların %79'u |
| 1-600 sn | 132 | %9 | Hızlı organik veya yarı paketli |
| 600 sn sonrası | 398 | %28 | **Erişilebilir hedef**: biz gördüğümüzde henüz dolmamış |

Erişilebilir hedef, mayhem dışı launch'ların **%1,1'i**. "Anında dolum" grubuna girmek mümkün değil: median 22 saniyelik zincir gecikmemizle biz gördüğümüzde eğri çoktan dolmuş ve PumpSwap'ta satışa geçilmiş oluyor.

---

## 4. Yüksek X nerede oluşuyor?

- Launch fiyatından eğri dolumuna kadar yol: **14,7x** (fiyat sanal SOL rezervinin karesiyle büyür; 30 → 115 SOL).
- 60. saniyede gördüğümüz giriş fiyatı launch fiyatının medyan **1,02x**'i (p90: 2,09x). Yani sağlıklı bir 60 sn girişinden graduate'e kadar yaklaşık 14x kalıyor.
- Graduate sonrası PumpSwap koşusu ne kadar? **Bu, GeckoTerminal taraması bitince eklenecek.** Erken örnekleme (ilk 240 coin) güvenilir değil; tam tabloyu bekliyoruz.
- Mayhem dışı coin'lerde 600 sn içinde 10 sn girişinden 15x: **0 / 4.209** (önceki rapor). Eğri dolmadan 15x yok.

Sonuç: "yüksek X yapacak coin'i yakalamak" sorusu pratikte "600 saniyeden sonra graduate olacak %1,1'i ilk 60 saniyede seçmek ve graduate sonrası koşuyu yakalamak" sorusuna indirgeniyor.

---

## 5. İlk 60 saniye özellikleri hedefi ayırt ediyor mu? `[DOĞRULANDI, 9 sağlıklı gün, mayhem dışı]`

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

### Kurallar: zaman ayrımlı test ve beklenen getiri

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

## 6. Paketli anında-dolum launch'ları `[DOĞRULANDI]`

600 sn içinde graduate olan 1.038 mayhem dışı coin'in **906'sı (%87) launch ile aynı saniyede** dolmuş. Ortalama 2,8 alıcı, tek alıcı alımların %79'u. İlk 2 saniyede ≥20 SOL alım olan 1.706 coin'in %62'si graduate olmuş ama bunların neredeyse hepsi biz görmeden. Bu grup için:
- Girmek imkânsız (22 sn gecikme, zaten dolum fiyatında).
- Ama **tespit etmek kolay ve değerli**: "bu coin paketli açıldı, PumpSwap'ta dağıtım bekle" uyarısı, bir araç için somut özellik. Zincir verisiyle %100 doğrulukla etiketlenebiliyor.

---

## 7. Bu ne anlama geliyor: kendimiz mi gireriz, araç mı?

**Kendimiz girmek:** Bu veriyle hayır. Seçim kuralı graduate'i 4-12 kat zenginleştiriyor ama 60. saniyede girip gerçek PumpSwap fiyatlarıyla çıkınca gerçekçi her çıkış politikasında her kural zarar ediyor, iyimser politikada bile sıfır civarı (bölüm 8). Medyan PumpSwap koşusu 1,83x ve aynı gün sönüyor; kazanan, kaybedenlerin %35-65'lik erimesini karşılamıyor. Bu pencerede (ilk dakikalar, zincir verisi, 22 sn gecikme) alpha yok. Alpha varsa başka yerde: dolum anından sonraki dakikalarda PumpSwap'ta kademeli satış (saniye hassasiyeti ve ücretli altyapı ister) ya da zincir dışı sinyal (sosyal, cüzdan takibi). Bunlar bu verinin cevaplayamadığı ayrı sorular.

**Araç için** şu an elde olan, satılabilir üç somut sinyal: (1) paketli launch tespiti (kesin), (2) mayhem artefakt uyarısı (kesin), (3) 60 sn'de "erişilebilir graduate" skoru (lift 4-12x, küçük örneklem). Bunlar RugCheck/Bubblemaps'in vermediği, trenches trader'ının saniyeler içinde istediği bilgiler. Ancak satış için 7/24 çalışan, 18 Eylül'deki gibi çökmeyen bir hat şart.

**Her iki yol için ön koşul aynı:** trade yakalama çöküşünün nedeni bulunup düzeltilmeli (ücretli WS/gRPC), izleme 600 sn'den 24 saate ve PumpSwap'a uzatılmalı, 14 gün kesintisiz temiz veri toplanmalı. Bu plan 14 Ekim raporunun P0 listesiyle aynı; tek fark, PumpSwap takibinin P2'den P0'a çıkması.

---

## 8. Graduate sonrası zirve: GeckoTerminal günlük mumlar `[DOĞRULANDI, 1.853 havuzun tamamı]`

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

### Gerçek fiyatlarla beklenen getiri (60 sn girişi, sağlıklı günler, mayhem dışı, n=17.543)

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

## 9. Sınırlar ve dürüstlük notları

- Public WebSocket'in launch'ların bir kısmını kaçırmış olma ihtimali sürüyor (`[VARSAYIM]`); zincir taraması yalnızca kaydettiğimiz 58.316 coin'i kapsar, Pump.fun'ın tamamını değil.
- 60 sn snapshot'ların %42'si eksik trade ile üretilmişti (14 Ekim raporu); özellikler gerçekten biraz daha güçlü olabilir, zayıf değil.
- Graduate olmayanların "bugünkü fiyat" değerlemesi 0,1 SOL'luk küçük pozisyon için geçerli; büyük pozisyonda boş eğriye satış daha kötü sonuç verir.
- Creator geçmişi an-itibarıyla hesaplandı; sniper skorları yalnızca %8 coin'de olduğu için kurallara alınmadı.
- Tüm rakamlar 1-17 Eylül 2026 piyasa rejimine ait; farklı dönemde taban oranlar değişebilir.

## Ekler

`analiz_ekleri/15x/`: `curves.jsonl` (58.316 zincir durumu), `curve_scan.py`, `grad_features3.py` ve çıktıları, `x15_check*.py` ve çıktıları, GeckoTerminal çıktıları (tamamlanınca).

---

## 10. Ek test (3 Kasım): akıllı cüzdan kopyalama `[DOĞRULANDI]`

Soru: Erken girip kârla çıkmayı sürekli başaran cüzdanlar var mı, ve onları kopyalamak kâr bırakır mı?
Yöntem: 1-8 Eylül'de (train) her cüzdanın ilk 60 saniyedeki alımları puanlandı; 9-17 Eylül'de (test) bu cüzdanlar kopyalandı. Kopya kuralı: cüzdan alınca +d sn sonra gir, cüzdan ilk sattığında +d sn sonra çık, satmazsa 600. saniyede çık; %3 maliyet. 16.722 coin, 47.852 cüzdan, 268 bin erken alım. Ayrıntı: `analiz_ekleri/akilli_cuzdan_ozet.txt`, liste: `analiz_ekleri/akilli_cuzdan_listesi.csv`.

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

## 11. Ek test (3 Kasım): "coin'i gör, gir, hareketi sür" `[DOĞRULANDI]`

Soru: Cüzdan seçmeden, coin'i gördüğümüz an girip çıkış kuralıyla ilerlersek ne olur? Ayrıntı: `analiz_ekleri/coin_surme_testi.txt`.
Yöntem: Sağlıklı günler, mayhem dışı; giriş launch'tan +2 sn (WebSocket senaryosu), +5 sn, +22 sn (bugünkü gecikme) sonraki ilk işlem fiyatı; 8 çıkış kuralı (tut, 60 sn, hedef/stop çiftleri, iz süren stop %25/%40, kademeli); 6 launch-anı filtresi; %3 maliyet; train 1-8 Eylül, test 9-17 Eylül.

Sonuç: **144 kombinasyonun tamamında test dönemi negatif.** Filtresiz +2 sn girişte en iyi kural (iz süren stop %25) train -4,5%, test -3,2%; +22 sn'de -3,7% / -3,5%. Gecikmeyi 22'den 2 saniyeye indirmek sonucu değiştirmiyor. En iyi filtre (creator'ın ilk launch'ı, dev ilk alımı 0,5-3 SOL, iz süren %25) train +0,8%, test -2,9%; sıfırdan ayırt edilemez. "Dev ilk alımı ≥5 SOL" filtresi en kötüsü (-10% … -23%): bunlar paketli dump'lar. Kazanma oranı tüm kombinasyonlarda %6-22.

Yorum: Erken girip sürmek, 2 ile 22 saniye arasındaki her gecikmede zarar. Aradaki tek pozitif nokta 0. saniye, yani ilk alıcıyla aynı blokta olmak; bu da WebSocket'le değil, sniper altyapısıyla alınır.

## 12. Ek test (4 Kasım): graduate sonrası PumpSwap, dakikalık `[DOĞRULANDI]`

Veri: Mayhem dışı 1.278 graduate havuzun migrasyon sonrası ilk ~16 saatlik dakikalık mumları (GeckoTerminal, ücretsiz; 1.251'inde ≥10 mum). Fitiller mum gövdesinin 1,5 katında kırpıldı; ortalamalar işlem başına 10x ile tavanlandı; %3 maliyet. Train: migrasyon ≤ 21 Eylül; test: sonrası. Ayrıntı: `analiz_ekleri/pumpswap_dakika_testi.txt`, ham mumlar: `analiz_ekleri/15x/minute_graduated.jsonl`.

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
