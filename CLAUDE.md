# CLAUDE.md

Bu dosya projenin anayasasıdır. Kısa tutulur. Detaylar `docs/` altındadır.

## Proje

Futbol maçları için tahmin üreten ve o tahminlerin gerçekten işe yarayıp yaramadığını
ölçen bir platform. Amaç bahis kârıdır. Ölçüm olmadan üretilen tahminin değeri yoktur.

Kullanıcının yazılım bilgisi yoktur. Kurulum, çalıştırma ve hata mesajları basit ve
Türkçe olmalıdır. Karmaşık bir çözüm ile basit bir çözüm arasında kalırsan basit olanı seç.

## Değişmez kurallar

Bu kuralları asla ihlal etme. Bir görev bunlardan birini gerektiriyor gibi görünüyorsa
kod yazmadan önce kullanıcıya sor.

1. Her tahmin `predicted_at` (UTC) ile kaydedilir. `predicted_at` maç başlangıcından
   sonraysa tahmin geçersizdir ve veritabanına yazılmaz.
2. Tahmin üretilirken kullanılan girdinin tamamı saklanır (`input_snapshot` + SHA256 hash).
   Sonradan "bu tahmin hangi veriyle yapıldı" sorusu cevaplanabilmelidir.
3. Hiçbir modele geçmiş tahminler gösterilmez. Her analiz sıfırdan başlar.
4. Modeller birbirinin çıktısını görmez.
5. Tahmin kayıtları güncellenmez. Sadece sonuç ve kapanış oranı alanları sonradan doldurulur.
   Olasılık, prompt versiyonu, model adı gibi alanlar yazıldıktan sonra değişmez.
6. Her tahmin yöntemi `Predictor` arayüzünü uygular. LLM'ler dahil, istisna yok.
   Bkz. `docs/03-predictors.md`.
7. Metrik tanımları `docs/04-evaluation.md` dosyasındadır. Formül değişirse dosyada
   versiyon numarası artar ve eski kayıtlar yeniden hesaplanmaz.
8. Gerçek para ile ilgili hiçbir otomatik işlem yapılmaz. Sistem sadece öneri üretir.

## Görev başlangıcı

Kod yazmadan önce ilgili dokümanı oku:

| Görev | Önce oku |
|---|---|
| Ne yapacağımı bilmiyorum | `docs/05-mvp-plan.md` |
| Yeni tahmin yöntemi | `docs/03-predictors.md` |
| Veritabanı / şema | `docs/02-data-model.md` |
| Metrik, skor, rapor | `docs/04-evaluation.md` |
| Veri çekme / API | `docs/01-architecture.md` |
| İstatistik, hipotez, lig eleme | `docs/06-research-protocol.md` |
| Prompt değişikliği | `docs/prompts/` içindeki en son versiyon |
| Mimari karar | `docs/adr/` |

Yeni bir özellik isteniyorsa önce `specs/` altına kısa bir şartname yaz, onay al, sonra kod yaz.

## Mimari özet

Üç katman. Aşağıdaki katman üstündekini bilmez.

1. **Veri katmanı** — API'lerden veri çeker, ham haliyle saklar. İş mantığı içermez.
2. **Model katmanı** — feature üretir, olasılık üretir. LLM burada özel değildir,
   sadece bir `Predictor`dur.
3. **Karar katmanı** — olasılıkları oranla karşılaştırır, öneri üretir.

LLM çağrısı sadece 2. katmanda olur. Veri çekme veya karar verme kodunda LLM çağrısı olmaz.

## Teknoloji

Python 3.11+, FastAPI, PostgreSQL, SQLAlchemy, Alembic (migration).
Frontend başlangıçta minimum: sunucu tarafında render edilen basit HTML sayfalar.
Redis, Next.js, mikroservis YOK. İhtiyaç kanıtlanmadan bağımlılık eklenmez.

## Komutlar

```
make setup      # bağımlılıklar + veritabanı kurulumu
make migrate    # şema güncelleme
make fetch      # günün maçlarını çek
make predict    # bekleyen maçlar için tahmin üret
make backfill   # sonuçları ve kapanış oranlarını geçmiş tahminlere işle
make report     # ölçüm tablosunu yazdır
make serve      # arayüzü başlat
make test
```

Yeni bir işlem eklersen `Makefile`'a hedef ekle ve bu tabloyu güncelle.

## Kod kuralları

- Sırlar `.env` içinde. Koda API anahtarı yazma, log'a basma.
- Dış API çağrıları tek bir istemci modülünden geçer. Retry ve rate limit orada.
- Para ve olasılık hesabında `float` yerine `Decimal` kullanma zorunlu değil, ancak
  olasılıklar her zaman 0-1 aralığında saklanır, yüzde olarak değil.
- Zaman her yerde UTC. Görüntülemede yerel saate çevrilir.
- Yeni tablo veya sütun migration ile eklenir. Elle SQL çalıştırılmaz.
- Testler: en az `Predictor` çıktı doğrulaması ve metrik hesapları test edilir.

## Bilinmeyenler

Aşağıdakiler henüz karara bağlanmadı. Kod yazarken varsayım yapma, kullanıcıya sor.

- İddaa oranlarının otomatik kaynağı (MVP'de yok, sonradan eklenecek)
- Hangi liglerin kalıcı olacağı (veriyle belirlenecek)
- LLM model seçimi ve prompt versiyonlama detayları
