# ADR 0002 — MVP oransız başlar, ama oran kaydedilir

Tarih: 2026-08-02
Durum: Kabul edildi

## Bağlam

Kâr hesabı için İddaa oranı gereklidir. Ancak İddaa oranlarının güvenilir,
geçmişe dönük ve otomatik bir kaynağı yoktur. Bu belirsizliğin çözülmesini
beklemek, çalışan bir sistemin ortaya çıkmasını aylarca geciktirir.

Kullanıcının önceliği çalışan bir sistem görmektir.

## Karar

MVP'de oran gösterilmez, edge hesaplanmaz, bahis önerisi üretilmez.
Ancak football-data.co.uk üzerinden **kapanış oranları geçmişe dönük olarak
tahminlere işlenir**. Bu haftalık otomatik bir işle yapılır ve kullanıcıdan
hiçbir emek istemez.

İddaa oranı Faz 2'de manuel giriş ve marj köprüsü tablosu ile eklenir.

## Gerekçe

Kapanış oranı geriye dönük olarak elde edilebilir bir veridir. Bu sayede
"şimdi kaydetme, sonra ekleriz" tuzağına düşmeden hız kazanılır.
Uluslararası kapanış oranı, İddaa fiyatı olmasa bile modelin gerçek
kalitesini ölçmek için yeterli referanstır.

## Sonuçlar

- MVP 3 haftada çalışır hale gelir.
- 3. ayda ölçüm mümkündür, çünkü oranlar arka planda birikmiştir.
- MVP'de maç sıralaması "güven" puanına göre yapılır; bu geçici ve zayıf
  bir ölçüttür, arayüzde bu not görünür şekilde yazılır.
