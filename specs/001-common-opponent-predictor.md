# 001 — Ortak Rakip Predictor

## Amaç

Kullanıcının hâlihazırda kullandığı ortak rakip ağırlıklı analiz yöntemini,
ölçülebilir bir `Predictor` olarak Python'da uygulamak.

Amaç yöntemi zayıflatmak değil, adil bir sınavdan geçirmek. Bu predictor
`poisson_dc` ile aynı maçlar üzerinde karşılaştırılacak.

## Neden bu ayrı bir predictor

Kullanıcı bu yaklaşımın diğer istatistiksel yöntemlerden üstün olduğuna inanıyor.
Bu iddia test edilebilir. Ayrı bir predictor olarak kurulursa, geçmiş sezonlar
üzerinde Brier score karşılaştırması yapılabilir ve tartışma veriyle biter.

Üç olası sonuç, üçü de değerli:
1. Ortak rakip yöntemi kazanır → ana model o olur
2. Dixon-Coles kazanır → ortak rakip mantığı zaten model içinde demektir
3. Belirli koşullarda biri, diğerlerinde öteki kazanır → ikisi birleştirilir

## Kapsam

**Yapılacak:** deterministik Python uygulaması, olasılık çıktısı, `1x2` + `ou25` + `btts`
**Yapılmayacak:** LLM çağrısı, serbest metin yorum, "oyun karakteri" katmanı

Bu predictor LLM kullanmaz. Kullanıcının promptundaki mantık kodla uygulanır,
böylece deterministik ve tekrarlanabilir olur. LLM versiyonu ayrıca Faz 3'te
`docs/prompts/` altında ele alınacaktır.

## Algoritma

### Adım 1 — Ortak rakiplerin bulunması

Her iki takımın son N maçındaki rakipler listelenir, kesişim alınır.

```
ortak = set(rakipler_A) ∩ set(rakipler_B)
```

Bir rakiple birden fazla maç oynanmışsa hepsi ayrı ayrı değerlendirilir.

### Adım 2 — Her ortak rakip için puanlama

Her ortak rakip `R` için, A'nın ve B'nin R'ye karşı performansı karşılaştırılır.
Ham skor değil, **takım perspektifine göre normalize edilmiş** sonuç kullanılır.

Puanlama bileşenleri:

| Bileşen | Puan |
|---|---|
| Galibiyet | +3 |
| Beraberlik | +1 |
| Mağlubiyet | 0 |
| Gol farkı | ± her gol için 0.5 (üst sınır ±2.0) |
| Deplasman galibiyeti bonusu | +1.0 |
| Ev mağlubiyeti cezası | −0.5 |
| Gol yemeden kazanma | +0.5 |

A'nın toplam puanı ile B'nin toplam puanı karşılaştırılır. Fark `d_R`.

**Saha eşitliği düzeltmesi:** A rakibi evinde, B deplasmanda oynadıysa
karşılaştırma adil değildir. Bu durumda `d_R` bir ev avantajı katsayısı ile
düzeltilir (lig ortalamasından hesaplanır, tipik olarak ~0.35 gol).

### Adım 3 — Zaman ağırlığı

Her ortak rakip maçı `exp(-ξ × geçen_gün)` ile ağırlıklanır. Aynı `ξ`
Dixon-Coles ile paylaşılır (`docs/07-markets.md`).

### Adım 4 — Ortak rakip skoru

```
S_ortak = Σ (w_R × d_R) / Σ w_R
```

Pozitif → A üstün. Negatif → B üstün. Ölçek ~[-4, +4].

### Adım 5 — Diğer katmanlar

Kullanıcının promptundaki katmanlar ayrı ayrı hesaplanır ve her biri
aynı ölçeğe normalize edilir:

| Katman | Bileşenler |
|---|---|
| `S_form` | G/B/M, gol ortalamaları, son 5 maç trendi |
| `S_istatistik` | KG, alt/üst oranları, clean sheet, gol atamama |
| `S_saha` | ev performansı vs deplasman performansı |
| `S_iy` | ilk yarı eğilimleri |

"Oyun karakteri" katmanı **uygulanmaz.** Sadece skor verisinden türetilemez;
şut, topla oynama veya xG verisi gerektirir. Bu veri eklenirse katman eklenir.

### Adım 6 — Ağırlıklandırma

Kullanıcının belirlediği başlangıç ağırlıkları:

```
S = 0.40×S_ortak + 0.15×S_form + 0.15×S_istatistik + 0.10×S_saha + 0.10×S_iy
```

Ortak rakip sayısına göre ağırlık ayarlanır (kullanıcının kuralları):

| Ortak rakip sayısı | S_ortak ağırlığı |
|---|---|
| 8+ | 0.50 |
| 5–7 | 0.40 |
| 3–4 | 0.25 |
| 0–2 | 0.10 (yalnızca destekleyici) |

Ağırlık düşürüldüğünde açığa çıkan pay diğer katmanlara oranlı dağıtılır.

**Bu ağırlıklar `v1`de sabittir.** `v2`de veriden öğrenilecektir (aşağıya bak).

### Adım 7 — Olasılığa çevirme

`S` skoru tek bir sayıdır; olasılığa çevrilmesi gerekir.

```
λ_ev  = lig_ortalaması × exp(α × S) × ev_avantajı
λ_dep = lig_ortalaması × exp(-α × S)
```

`α` kalibrasyon katsayısıdır, geçmiş veriden fit edilir. Buradan skor matrisi
üretilir ve `docs/07-markets.md` formülleriyle bütün marketler türetilir.

Bu adım önemli: skor doğrudan "MS1 %60" gibi bir sayıya dönüştürülmez.
Skor matrisinden geçirilir, böylece marketler birbiriyle tutarlı kalır.

## Doğrulama

Ortak rakip sayısı ve `S_ortak` değeri `Prediction.notes` alanına yazılır.
Bu, sonradan "ortak rakip sayısı arttıkça isabet artıyor mu" sorusunun
cevaplanmasını sağlar.

`input_snapshot` içine ortak rakip listesi ve her birinin `d_R` değeri konur.

## v2 — Öğrenilen ağırlıklar

`common_opponent_v2` ayrı bir predictor olarak eklenecektir. Farkı: ağırlıklar
sabit değil, geçmiş veriden lojistik regresyon ile öğrenilir.

Girdi değişkenleri: `S_ortak`, `S_form`, `S_istatistik`, `S_saha`, `S_iy`,
ortak rakip sayısı, örneklem büyüklükleri.

v1 ve v2 yan yana ölçülür. Sezginin mi verinin mi daha iyi ağırlık bulduğu
böylece görülür.

## Kabul kriterleri

1. Predictor `docs/03-predictors.md` sözleşmesine uyuyor
2. Aynı girdiyle her zaman aynı çıktı (deterministik)
3. Geçmiş 3 sezon üzerinde backtest çalışıyor
4. `poisson_dc` ile aynı maç kümesi üzerinde Brier karşılaştırması raporlanıyor
5. Ortak rakip sayısına göre dilimlenmiş performans tablosu üretiliyor

## Riskler

**Çifte sayım.** Aynı ligde iki takım genellikle aynı rakiplerin çoğuyla oynamıştır.
Örnek veride ortak rakip sayıları 14 maçta 6–14 arasında çıkmıştır — yani maçların
%43–%100'ü ortak. Bu durumda `S_ortak` ile `S_form` büyük ölçüde aynı bilgiyi taşır
ve toplam %55 ağırlık aynı sinyale verilmiş olur.

Bu risk **ölçülecek**, varsayılmayacak. Kabul kriteri 5'teki dilimlenmiş tablo
tam olarak bunu gösterir: ortak rakip sayısı düşük olan maçlarda (farklı ligler,
kupa maçları, sezon başı) yöntem daha mı iyi çalışıyor?

**Ölçek kalibrasyonu.** `S` skorunun olasılığa çevrilmesindeki `α` katsayısı
yanlış fit edilirse model sistematik olarak fazla iddialı veya fazla temkinli olur.
Kalibrasyon eğrisi ile kontrol edilir.
