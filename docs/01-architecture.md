# 01 — Mimari

## Amaç

Sistem iki şey yapar: tahmin üretir, ve o tahminleri ölçer. İkincisi birincisinden
önemlidir. Ölçüm altyapısı olmadan üretilen tahmin, işe yarayıp yaramadığı asla
bilinemeyecek bir çıktıdır.

## Katmanlar

```
[ API Football ]  [ football-data.co.uk CSV ]
        |                    |
        v                    v
  +-----------------------------------+
  |  1. VERİ KATMANI                  |   ham veri, iş mantığı yok
  |  fetchers/  →  raw tabloları      |
  +-----------------------------------+
        |
        v
  +-----------------------------------+
  |  2. MODEL KATMANI                 |
  |  features/   metrik üretimi       |
  |  predictors/ olasılık üretimi     |   Poisson | Elo | LLM
  +-----------------------------------+
        |
        v
  +-----------------------------------+
  |  3. KARAR KATMANI                 |
  |  edge hesabı, öneri, stake        |   (MVP'de oran yok, sadece sıralama)
  +-----------------------------------+
        |
        v
  +-----------------------------------+
  |  ÖLÇÜM (yan hat, sürekli çalışır) |
  |  backfill → sonuç + kapanış oranı |
  |  evaluation → Brier, kalibrasyon  |
  +-----------------------------------+
```

Kural: alt katman üst katmanı import etmez. Veri katmanı Poisson'u bilmez,
Poisson LLM'i bilmez, karar katmanı hangi predictor'ün konuştuğunu umursamaz.

## Neden bu ayrım

- **Veri katmanı ayrı**, çünkü API sağlayıcısı değişebilir. Değiştiğinde sadece
  bir modül değişsin, model kodu bozulmasın.
- **Predictor arayüzü ortak**, çünkü asıl sorulan soru "hangi yöntem daha iyi".
  Yöntemler aynı arayüzden geçmezse karşılaştırılamaz.
- **Ölçüm yan hat**, çünkü tahmin üretiminden bağımsız çalışması gerekir.
  Tahmin durursa ölçüm devam eder, ölçüm bozulursa tahmin devam eder.

## Veri akışı — günlük

```
07:00  fetch_fixtures    bugünün maçları (seçili ligler)
07:05  fetch_team_form   her takım için son N maç
07:10  build_features    form endeksi, gol oranları, rakip gücü düzeltmesi
07:15  run_predictors    Poisson + Elo → olasılık
07:20  (opsiyonel) LLM   sadece filtreden geçen maçlar
07:25  publish           arayüzde günün listesi hazır
```

Kullanıcı gün içinde arayüze girer, listeyi görür. Manuel tetikleme de mümkündür
ama varsayılan otomatiktir. Kullanıcının her sabah butona basması gerekmez.

## Veri akışı — haftalık ölçüm

```
Pazartesi 03:00
  1. football-data.co.uk CSV indir (Norveç, İsveç, İrlanda, Finlandiya, ...)
  2. sonuçları eşleştir → predictions.actual_outcome doldur
  3. kapanış oranlarını eşleştir → predictions.closing_odds doldur
  4. metrikleri yeniden hesapla → metrics_snapshot yaz
```

Bu hattın MVP'de de çalışması şart. Kullanıcı çıktısını görmese bile veri birikmelidir.

Takım isimleri iki kaynakta farklı yazılır ("St Patricks" / "St Patrick's Athletic").
Eşleştirme için `team_aliases` tablosu tutulur. Eşleşmeyen kayıtlar sessizce atılmaz,
`unmatched_fixtures` tablosuna yazılır ve raporda sayısı gösterilir.

## Veri kaynakları

| Kaynak | Ne için | Maliyet | Not |
|---|---|---|---|
| API Football | fikstür, sonuç, takım formu | aylık abonelik | ana kaynak |
| football-data.co.uk | geçmiş sonuç + açılış/kapanış oranı | ücretsiz CSV | backtest ve ölçüm |
| İddaa oranı | gerçek bahis fiyatı | — | MVP'de YOK, sonra eklenecek |
| LLM API'leri | yorumlama katmanı | kullanım başına | Faz 3 |

football-data.co.uk'in "extra" bölümü Norveç, İsveç, İrlanda, Finlandiya, Danimarka
gibi ligleri kapsar. Pinnacle sütunu 2025 ortasından itibaren güvenilmez kabul edilmiştir,
piyasa ortalaması/maksimum sütunları kullanılır.

## Arşivleme kuralı

Her gün çekilen maç verisi kalıcı olarak saklanır. Aynı maç tekrar geldiğinde
`ON CONFLICT DO NOTHING` ile atlanır. Bu, ek maliyet olmadan zamanla kendi
veri tabanını oluşturmanı sağlar.

## MVP kapsamı dışında

Bilerek yapılmayanlar. İhtiyaç kanıtlanırsa eklenir:

- Redis / cache
- Next.js veya React arayüz
- Canlı bahis, maç içi veri
- xG sağlayıcıları
- Kullanıcı hesapları, çoklu kullanıcı
- Mobil uygulama
