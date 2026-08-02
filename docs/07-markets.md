# 07 — Marketler ve Türetme

Bütün marketler tek bir kaynaktan türer: **skor olasılık matrisi.**
Her market için ayrı model kurulmaz. Bu, marketler arası tutarlılığı garanti eder —
"2.5 üst %60 ama KG var %20" gibi imkânsız kombinasyonlar oluşamaz.

## Skor matrisi

İki sayı hesaplanır:

```
λ_ev  = beklenen ev sahibi golü
λ_dep = beklenen deplasman golü
```

Bunlardan her skorun olasılığı:

```
P(i, j) = Poisson(i; λ_ev) × Poisson(j; λ_dep) × τ(i, j)
```

`τ`, Dixon-Coles düzeltmesidir. Saf Poisson düşük skorlu sonuçları (0-0, 1-0, 0-1, 1-1)
yanlış tahmin eder çünkü gollerin bağımsız olmadığını varsayar. `τ` bu dört hücreyi düzeltir.

Matris 0-0'dan 10-10'a kadar hesaplanır ve toplamı 1.0'a normalize edilir.

## Tam zaman marketleri

Matris `M[i][j]` üzerinden basit toplamlar:

| Market | Formül |
|---|---|
| MS1 | Σ M[i][j] , i > j |
| MSX | Σ M[i][j] , i = j |
| MS2 | Σ M[i][j] , i < j |
| 1X | MS1 + MSX |
| X2 | MSX + MS2 |
| 12 | MS1 + MS2 |
| 0.5/1.5/2.5/3.5/4.5 Üst | Σ M[i][j] , i+j > eşik |
| Alt | 1 − Üst |
| KG Var | Σ M[i][j] , i ≥ 1 ve j ≥ 1 |
| KG Yok | 1 − KG Var |
| Doğru skor | M[i][j] doğrudan |
| Gol aralığı 0-1 / 2-3 / 4+ | Σ M[i][j] , i+j aralıkta |
| Handikap | Σ M[i][j] , (i + h) > j |

En olası 5 skor: matris değerlerine göre sıralanır, ilk 5 alınır.

## Yarı zaman marketleri

Ayrı bir matris gerekir. İlk yarı gol beklentisi:

```
λ_iy = λ_tam × r_lig
```

`r_lig`, o ligde ilk yarıda atılan gollerin oranıdır. Geçmiş veriden hesaplanır,
varsayılmaz. Tipik aralık 0.42–0.47 ama ligler farklılık gösterir.

İlk yarı matrisinden İY1/İYX/İY2, İY 0.5 ve 1.5 alt/üst, İY KG türetilir.
Tam zaman marketleriyle aynı formüller kullanılır.

## İY/MS

Dokuz kombinasyon (1/1, 1/X, 1/2, X/1, ...). Bunlar bağımsız değildir:
öne geçen takım genellikle savunmaya çekilir, geriye düşen risk alır.

Basit versiyon (MVP): ilk yarı ve ikinci yarı bağımsız kabul edilir.
İkinci yarı matrisi `λ_2y = λ_tam − λ_iy` ile hesaplanır, iki matris birleştirilir.

Bu yaklaşım 1/2 ve 2/1 gibi ters dönüşleri sistematik olarak yanlış tahmin eder.
MVP'de `deneysel` etiketiyle üretilir, ölçüm sayfasında ayrı takip edilir.
Kalibrasyonu düzelmezse çıkarılır.

## λ nasıl hesaplanıyor

```
λ_ev  = hücum_gücü(ev) × savunma_zayıflığı(dep) × lig_ortalaması × ev_avantajı
λ_dep = hücum_gücü(dep) × savunma_zayıflığı(ev) × lig_ortalaması
```

Hücum ve savunma güçleri Dixon-Coles ile bütün lig maçlarından birlikte tahmin edilir.
Bu, "kime karşı oynadı" sorusunun matematiksel cevabıdır — her takımın gücü,
rakiplerinin gücü hesaba katılarak bulunur.

Zaman ağırlığı: her maç `exp(-ξ × geçen_gün)` ile ağırlıklanır.
`ξ` lig bazında ayarlanır, varsayılan yarılanma 180 gün.

Küçültme: az maçı olan takımların katsayıları lig ortalamasına doğru çekilir.
Sezon başında ve yeni yükselen takımlarda kritik.

## Güven puanı

Her market için 1-10 arası bir güven puanı üretilir. Bileşenleri:

| Bileşen | Ne ölçüyor |
|---|---|
| Örneklem büyüklüğü | iki takımın kaç maçlık verisi var |
| Olasılığın uç olması | 0.5'e yakın tahminler doğası gereği belirsiz |
| Predictor'lar arası uyum | Poisson ve Elo aynı şeyi mi söylüyor |
| Veri tazeliği | son maçtan bu yana geçen süre |

**Uyarı:** MVP'de bu puan kalibre edilmemiştir. "Güven 9" ifadesinin ne kadar
haklı olduğu ancak birkaç yüz tahmin sonrası ölçülebilir. Arayüzde bu not görünür
şekilde yazılır. Kalibrasyon ölçüldükten sonra puan yeniden tanımlanır ve
`docs/04-evaluation.md` versiyonu artar.

## Hangi marketlerin ölçüleceği

Ölçüm sayfasında ayrı ayrı takip edilenler:

`1x2`, `ou25`, `ou35`, `btts`, `ht_1x2`, `ht_ou15`, `htft` (deneysel)

Diğerleri (çifte şans, gol aralığı, handikap) bunlardan matematiksel olarak
türediği için ayrı ölçülmez.

## Eklenmeyecekler

Korner, kart, oyuncu bazlı marketler MVP'de yok. Gol modelinden türemezler,
ayrı veri ve ayrı model isterler. İleride değerlendirilir.
