# 04 — Ölçüm

**Versiyon: 1.0** — Formüller değişirse bu numara artar ve değişiklik aşağıya not edilir.
Eski `metrics_snapshots` kayıtları yeniden hesaplanmaz, versiyon etiketiyle korunur.

## Neden bu dosya var

"Başarı oranı" gibi tanımı kayabilen ifadeler uzun vadede karşılaştırmayı imkânsız
kılar. Metrik tanımları burada dondurulur.

## Neden isabet oranı kullanılmıyor

İsabet oranı ikili bir metriktir ve olasılık bilgisini yok eder.
"%70 ev sahibi" ile "%95 ev sahibi" aynı sayılır, oysa çok farklı iddialardır.

Daha kötüsü: en kolay yüksek isabet, favorileri seçmektir. Ağır favorileri seçen
bir sistem %75 isabet yapar ve para kaybeder, çünkü o maçların oranı 1.30'dur.
Yüksek isabet ile kâr aynı şey değildir.

İsabet oranı arayüzde bilgi amaçlı gösterilebilir, ama **karar bu metriğe göre
verilmez.**

## Birincil metrikler

### Brier score

Olasılık tahmininin kare hatası. Düşük iyidir. Aralık: 0 (mükemmel) – 1.

Çok sonuçlu marketler için (1X2):

```
BS = (1/N) * Σ_i Σ_k (p_ik - o_ik)²
```

`p_ik` = i. maçta k sonucuna verilen olasılık, `o_ik` = gerçekleştiyse 1, yoksa 0.

Referans değerler (1X2, tipik lig):
- Rastgele (her sonuca 1/3): ~0.667
- Zayıf model: ~0.25
- İyi model: ~0.19–0.21
- Kapanış oranı: ~0.18–0.19

Modelin kapanış oranını yenmesi beklenmez. Yaklaşması bile iyi sonuçtur.

### Log loss

Aşırı güvene ağır ceza verir. Düşük iyidir.

```
LL = -(1/N) * Σ_i log(p_i,gerçekleşen)
```

Olasılıklar [0.001, 0.999] aralığına kırpılır, aksi halde tek bir hata sonucu
sonsuza götürür.

### Kalibrasyon

En önemli metrik. "%60 dediğinde gerçekten %60 mı geliyor?"

Yöntem: olasılıklar 10 kovaya bölünür (0–0.1, 0.1–0.2, ...). Her kovada
tahmin edilen ortalama olasılık ile gerçekleşme oranı karşılaştırılır.

```
kova     n     ortalama_tahmin    gerçekleşen    fark
0.5-0.6  84    0.548              0.512          -0.036
0.6-0.7  61    0.641              0.590          -0.051
```

Sistematik olarak pozitif fark = model fazla temkinli.
Sistematik negatif fark = model fazla iddialı. LLM'lerde ikincisi yaygındır.

Kalibrasyon bozuksa olasılıklar bahis kararında kullanılamaz — Kelly benzeri
her staking yöntemi girdisi olarak doğru olasılık ister.

Kova başına `n < 20` ise o kova raporlanır ama yorumlanmaz.

## Karşılaştırma metrikleri (Faz 2, oran eklendikten sonra)

### Vig kaldırma

Ham oranlar toplamı 1'i aşar; fazlası bahis şirketinin marjıdır.

```
implied_k = 1 / oran_k
marj      = Σ implied_k - 1
fair_k    = implied_k / Σ implied_k     # oransal yöntem
```

Oransal yöntem favorilerde marjı hafif abartır. MVP için yeterlidir;
gerekirse Shin veya güç yöntemi ile değiştirilir (o zaman versiyon artar).

### Edge

```
edge = model_olasılık - fair_olasılık
```

Eşik `docs/06-betting-rules.md` içinde tanımlıdır. MVP'de edge hesaplanmaz.

### CLV (Closing Line Value)

Alınan oranın kapanış oranına göre durumu. Kârdan çok daha hızlı sinyal verir.

```
CLV% = (alınan_oran / kapanış_oranı - 1) * 100
```

Pozitif ortalama CLV, kâr henüz gelmemiş olsa bile edge'in varlığına işarettir.
Negatif CLV ile kâr etmek şanstır ve devam ettirilirse kaybedilir.

## Örneklem eşikleri

Hiçbir sonuç `n` olmadan raporlanmaz. Bir metrik şu eşiklerin altındaysa
gösterilir ama "henüz yorumlanamaz" etiketiyle işaretlenir.

| Karar | Gereken n |
|---|---|
| Genel kalibrasyon okuması | 400+ tahmin |
| Lig bazında karar (aç/kapa) | 150–200 tahmin |
| İki predictor'ü karşılaştırma | 500+ ortak maç |
| Kâr/zarar yorumu | 1000+ bahis (ve o zaman bile zayıf) |

Bu eşikler keyfi değil: %5'lik farkları gürültüden ayırmak için gereken
kaba örneklem büyüklüklerinden gelir.

## Karşılaştırma kuralı

İki predictor karşılaştırılırken **aynı maç kümesi** kullanılır. Biri 400 maç,
diğeri 380 maç tahmin ettiyse, ortak 380 üzerinden karşılaştırılır.
Farklı kümeler üzerindeki Brier değerleri yan yana konmaz.

## Raporlama

Haftalık `metrics_snapshots` yazılır. Geçmiş anlık görüntüler silinmez —
metriklerin zaman içindeki seyri kendi başına bilgidir.

Arayüzde gösterim sırası: predictor, market, n, Brier, kalibrasyon durumu.
Renk veya "iyi/kötü" etiketi eşik tablosuna göre otomatik atanır, elle değil.
