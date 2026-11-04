# Kapanış Notu: Memecoin Motoru

**Tarih:** 4 Kasım 2026
**Karar:** Aktif geliştirme ve "kendi sermayemizle işlem" hedefi durduruldu. Kod, veri ve raporlar arşivlendi.

## Ne vardı

Solana'da Pump.fun launch'larını public WebSocket ile dinleyen, ilk 600 saniyeyi kaydeden, kural tabanlı karar ve cüzdansız paper-trade üreten bir Python sistemi. 1 Eylül - 8 Ekim 2026 arasında 58.316 launch ve 2,09 milyon trade toplandı (10,2 GB SQLite). Collector takvimin %9,6'sında açıktı; trade verisi yalnızca 1-17 Eylül arasında sağlıklı (18 Eylül sonrası ücretsiz RPC kuyruğu yüzünden trade'ler düştü; neden ve ücretsiz çözümü `ANALIZ_15X_KOINLER_2026-10-23.md` §2'de).

## Ne denendi, ne çıktı

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

Yapısal bulgular: "15x" pratikte graduate demek (eğri 14,7x). Graduate'lerin %63'ü launch ile aynı saniyede dolan paketli insider launch'ları. Dev medyan 8. saniyede satıyor. Yükselen coin'lerin zirvesi medyan 9. saniyede. Mayhem-mode coin'lerin fiyatı sanal rezerv şişmesi yüzünden sahte. Bizim zincir gecikmemiz medyan 22 sn.

**Sonuç:** Bu pazarda dışarıdan analizle seçilebilen bir edge yok. Para, coin'i çıkaran/paketleyene ve ilk blokta giren saniye altı botlara gidiyor. Edge yalnızca hızda; hız da aylık 150-500 $ altyapı + özel sunucu + Jito ile başlıyor ve orada bile garanti değil.

## Hangi koşulda yeniden açılır

1. **Bütçe:** Aylık 200-300 $ (gRPC akışı + Frankfurt/Amsterdam VPS) en az 2 ay ayrılabiliyorsa. İlk ay cüzdansız: gecikme ve slot ölçümü; devam kriteri simüle girişlerin ≥%50'sinin ilk alıcıyla aynı/sonraki slotta olması ve paper EV > +5%.
2. **Farklı pencere:** PumpSwap "≤1 dk gir, 1,5x/-25%" hücresini ücretsiz altyapıyla 2-4 hafta canlı paper test etmek istenirse (gecikmeye duyarsız tek aday). Tutarsa küçük sermaye konuşulur.
3. **Ürün/içerik yolu:** Para kazanmak için değil kitle kurmak için: paketli launch tespiti, mayhem uyarısı, dev çıkış sinyali ücretsiz bot + terminal referansı. Plan `ANALIZ_RAPORU_2026-10-14.md` §C ve 3 Kasım notlarında.

Yeniden açılırsa ilk iş değişmez: launch'ı WebSocket log'undan çözmek (RPC kuyruğunu kaldırır), cüzdan/sniper zenginleştirmesini kapatmak, oturum modeli ve karar dondurma (sızıntı) düzeltmeleri.

## Nerede ne var

| Ne | Yer |
|---|---|
| Kod (3.700 satır, 27 test) | `src/`, `tests/`; Git deposu (4 Kasım 2026 ilk commit) |
| Veritabanı (10,2 GB) | `data/memecoin_motor.db` (Git dışı); sıkıştırılmış yedek `../memecoin_backup_2026-11-04/` |
| Sistem/veri/gelir raporu | `ANALIZ_RAPORU_2026-10-14.md` |
| 58.316 coin'in akıbeti, tüm strateji testleri | `ANALIZ_15X_KOINLER_2026-10-23.md` (§1-12) |
| Coin bazlı otopsi (max X, kim sattı) | `analiz_ekleri/coin_otopsi.csv` |
| Creator satışı sonrası, akıllı cüzdan, sürme, PumpSwap testleri | `analiz_ekleri/*.txt`, `analiz_ekleri/*.csv` |
| Zincir durumu (graduate), PumpSwap gün/dakika mumları | `analiz_ekleri/15x/` |
| Tüm betikler (salt-okunur, yeniden çalıştırılabilir) | `analiz_ekleri/*.py`, `analiz_ekleri/15x/*.py` |

Betikler veritabanını yalnızca `mode=ro` ile açar; hiçbir test üretim verisini değiştirmedi, hiçbir gerçek işlem gönderilmedi.
