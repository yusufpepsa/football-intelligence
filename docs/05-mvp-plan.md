# 05 — MVP Planı

## Hedef

Üç hafta sonunda kullanıcı şunu yapabilecek: tarayıcıdan sisteme girer, günün
maçlarını ve her maç için tahmin olasılıklarını görür, en güvenilir bulunanları
sıralı halde okur.

Bu sürümde oran yoktur, edge hesabı yoktur, bahis önerisi yoktur.
Ama **ölçüm verisi arka planda birikir**.

## Kapsam

Yapılacaklar:

- [ ] Postgres şeması + migration (`docs/02-data-model.md`)
- [ ] API Football istemcisi: lig, takım, fikstür, sonuç
- [ ] football-data.co.uk indirici: geçmiş sezonlar + haftalık güncelleme
- [ ] İsim eşleştirme (`team_aliases`) ve eşleşmeyenlerin raporlanması
- [ ] Feature üretimi: son N maç formu, gol oranları, ev/deplasman ayrımı,
      rakip gücü düzeltmesi, küçültme (shrinkage)
- [ ] `PoissonDixonColes` predictor
- [ ] `EloPredictor`
- [ ] Predictor arayüzü ve çıktı doğrulaması
- [ ] Günlük otomatik çalışan iş (cron)
- [ ] Haftalık backfill işi (sonuç + kapanış oranı)
- [ ] Basit web arayüzü: 2 sayfa

Yapılmayacaklar:

- LLM katmanı (Faz 3)
- İddaa oran entegrasyonu
- Edge hesabı, stake, kupon önerisi
- Research Lab
- Kullanıcı hesapları

## Arayüz — 2 sayfa

### Sayfa 1: Bugün

Günün maçları, modelin en emin olduğu sırada. Her satır:

```
Molde - Sarpsborg 08          Eliteserien       19:00
  1X2      Ev %58   Ber %24   Dep %18
  2.5      Üst %61  Alt %39
  KG       Var %54  Yok %46
  veri     14 maç / 12 maç        güven: orta
```

"Güven" alanı örneklem büyüklüğü ve modeller arası uyuma göre hesaplanır.
Bu geçici bir sıralama ölçütüdür — oran eklendiğinde yerini edge alacaktır.
Arayüzde bu not görünür şekilde yazılıdır.

### Sayfa 2: Ölçüm

Basit tablo. Süslü grafik yok.

```
Predictor      Market   n     Brier   Kalibrasyon   Son güncelleme
poisson_dc     1x2      412   0.198   iyi           2 saat önce
poisson_dc     ou25     412   0.221   orta
elo            1x2      412   0.213   iyi
```

`n` her satırda görünür. `n < 100` ise satır soluk gösterilir ve
"henüz yorumlanamaz" etiketi konur.

## Haftalar

**Hafta 1 — veri**
Şema, API Football istemcisi, football-data indirici, isim eşleştirme.
Çıktı: veritabanında 3-4 sezonluk geçmiş maç ve kapanış oranı var.
Bu haftanın sonunda hiçbir tahmin yok ama arşiv duruyor.

**Hafta 2 — model**
Feature üretimi, Poisson ve Elo predictor'ları, evaluation modülü.
Çıktı: geçmiş sezonlar üzerinde backtest. İlk gerçek bilgi burada gelir —
model kapanış çizgisine karşı ne yapıyor.

**Hafta 3 — çalışan sistem**
Cron işleri, iki sayfalık arayüz, haftalık backfill.
Çıktı: her sabah kendiliğinden çalışan, akşam bakılabilen bir sistem.

## Kabul kriterleri

MVP bitti sayılır eğer:

1. Sistem 7 gün boyunca müdahalesiz çalıştıysa
2. Her tahminin `predicted_at` değeri maç başlangıcından önceyse
3. Backfill sonuçların en az %90'ını eşleştirdiyse
4. Ölçüm sayfası backtest sonuçlarını gösteriyorsa
5. Bir lig `is_active = false` yapılarak kod değişikliği olmadan kapatılabiliyorsa

## Sonraki fazlar

- **Faz 2:** İddaa oranı (manuel giriş + marj köprüsü tablosu), edge hesabı
- **Faz 3:** LLM katmanı — hem predictor hem feature üretici olarak, ölçülerek
- **Faz 4:** Kupon önerisi, staking kuralları, kağıt üstü bahis takibi
- **Faz 5:** Research Lab, hipotez kaydı, lig eleme raporları

## Karar noktaları

**3. ay:** en az 500 tekil tahmin birikmiş olmalı. Poisson baseline'ın kalibrasyonu
düzgün mü, Brier makul mü? Değilse veri veya feature tarafında sorun var demektir.

**6. ay:** oranlar eklendikten sonra, kapanış çizgisine karşı sonuç ne?
Bu noktada devam/kapat kararı verilir.
