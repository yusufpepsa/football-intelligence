# ADR 0001 — Ölçüm altyapısı tahminden önce kurulur

Tarih: 2026-08-02
Durum: Kabul edildi

## Bağlam

Projenin amacı bahis kârıdır. Tahmin üretmek kolaydır; üretilen tahminin
işe yarayıp yaramadığını anlamak zordur. Ölçüm altyapısı olmadan biriken
tahminler sonradan değerlendirilemez, çünkü o anki oran ve girdi verisi
geriye dönük olarak elde edilemez.

## Karar

Şema, kayıt disiplini ve değerlendirme modülü, herhangi bir LLM entegrasyonundan
önce kurulur. Her tahmin `predicted_at`, `input_snapshot` ve `input_hash` ile
saklanır. Tahmin kayıtları değişmezdir.

## Gerekçe

Kaybedilen ölçüm verisi geri gelmez. Kaybedilen bir haftalık geliştirme süresi gelir.

## Sonuçlar

- İlk çalışan tahmin çıktısı birkaç gün gecikir.
- Buna karşılık 3. ayda "bu sistem işe yarıyor mu" sorusu cevaplanabilir.
- Şema karmaşıklığı artar (snapshot ve hash alanları).
