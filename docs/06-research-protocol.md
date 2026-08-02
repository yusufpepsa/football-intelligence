# 06 — Araştırma Protokolü

Bu dosya projeyi kullanıcının kendi yanılgılarına karşı korur. Faz 5'te
Research Lab devreye girdiğinde bağlayıcıdır, ama kural bugünden geçerlidir.

## Problem

Üç ay veri topladıktan sonra tabloya bakıp "Finlandiya'da KG VAR tahminlerimiz
iyiymiş" demek çok kolaydır. Ama 40 hipotezi aynı anda test ediyorsan, hiçbir
gerçek etki olmasa bile birkaçı %5 seviyesinde "anlamlı" çıkar. Bu istatistiğin
kaçınılmaz sonucudur, dikkatsizlik değil.

Sonra o sahte bulguya para yatırılır ve ortalamaya dönüş yaşanır.

## Kural 1 — Hipotez önce kaydedilir

Veriye bakmadan önce `hypotheses` tablosuna yazılır:

```
id, olusturulma_tarihi, ifade, olculecek_metrik, minimum_n, durum
```

`durum`: `beklemede` → `test_edildi` → `kabul` / `red`

Kayıtlı olmayan hipotez test edilmez. Sonradan akla gelen fikirler
kaydedilir ve **yeni veriyle** test edilir, mevcut veriyle değil.

## Kural 2 — Minimum n önceden belirlenir

Hipotez kaydedilirken kaç gözlem gerektiği yazılır. O sayıya ulaşmadan
sonuca bakılmaz. "Şu an nasıl gidiyor" diye ara bakış yapılırsa bu
kayda not edilir, çünkü ara bakış karar eşiğini bozar.

## Kural 3 — Çoklu test düzeltmesi

Aynı anda birden fazla hipotez test edilirse Benjamini-Hochberg düzeltmesi
uygulanır. Ham p değeri raporlanmaz, düzeltilmiş değer raporlanır.

## Kural 4 — Güven aralığı zorunlu

Hiçbir yüzde tek başına gösterilmez. Yanında `n` ve güven aralığı durur.

Örnek: "%64.3" değil, "%64.3 (n=14, GA %38.8–%83.7)".

14 maçlık örneklemde neredeyse her yüzdenin güven aralığı çok geniştir.
Bu gerçeğin ekranda görünür olması, yanlış karar vermeyi zorlaştırır.

## Kural 5 — Lig eleme protokolü

Bir ligi kapatmak veya açmak için:

- En az 150–200 tahmin birikmiş olmalı
- Karar kâr/zarara göre değil, Brier ve kalibrasyona göre verilir
- Karar `docs/adr/` altına gerekçesiyle yazılır
- Kapatılan lig 6 ay sonra yeniden değerlendirilebilir

Küçük örneklemde kâr tamamen gürültüdür. 20 maç sonra "bu lig harika"
demek, sonraki 200 maçta pişman olmanın en yaygın yoludur.

## Kural 6 — Ortak rakip hipotezi hakkında not

Erken bir gözlem: 16 takımlı bir ligde iki takım 14 maç sonunda zaten
neredeyse aynı rakiplerle oynamış olur. Örnek veride ortak rakip sayıları
6 ile 14 arasında çıktı, hiçbiri 6'nın altında değildi.

Yani "ortak rakip sayısı" değişkeni lig maçlarında bilgi taşımaz —
sezonun hangi haftası olduğunun kılık değiştirmiş halidir.

Test edilecekse "sayı" değil, **ortak rakiplere karşı performans farkı**
test edilmelidir.

## Sonuç kaydı

Her test sonucu, kabul de red de olsa, kaydedilir. Red edilen hipotezler
silinmez — hangi fikirlerin denendiği ve işe yaramadığı bilgisi zamanla
en değerli varlık haline gelir.
