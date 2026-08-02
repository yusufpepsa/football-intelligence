# 000 — Veri Katmanı (Hafta 1)

İlk iş bu. Claude Code buradan başlar.

## Amaç

Veritabanını kurmak ve iki kaynaktan veri akıtmak. Bu hafta tahmin üretilmez.
Hafta sonunda veritabanında binlerce geçmiş maç ve kapanış oranı olmalıdır.

## Kapsam

**Yapılacak**
- Alembic migration ile şema (`docs/02-data-model.md`)
- API Football istemcisi: lig, takım, fikstür, sonuç
- football-data.co.uk indirici: geçmiş sezon CSV'leri
- Takım ismi eşleştirme (`team_aliases`) ve eşleşmeyen kayıt raporu
- `make seed`, `make fetch`, `make backfill` komutları
- Bağlantı ve veri sağlığı kontrolü (`make report` basit sayımlar döner)

**Yapılmayacak**
- Feature üretimi, model, tahmin
- Arayüz
- LLM

## Adımlar

### 1. Şema

`docs/02-data-model.md` içindeki tabloların hepsi oluşturulur — tahmin tabloları
bu hafta kullanılmasa bile. Sonradan migration yazmak yerine baştan doğru kurulur.

`predictions` tablosuna `predicted_at < kickoff_utc` kontrolü eklenir
(trigger veya uygulama seviyesinde zorunlu doğrulama).

### 2. Lig listesi

Başlangıç ligleri `leagues` tablosuna eklenir. Öncelik football-data.co.uk
kapsamındaki ligler — kapanış oranı arşivi ücretsiz mevcut:

Norveç, İsveç, İrlanda, Finlandiya, Danimarka, Polonya, Romanya,
İsviçre, Avusturya, ve mevcut olan diğerleri.

Her lig için `api_football_id` ve `fd_code` eşleştirilir. Bu eşleştirme elle
yapılır ve bir kez yapılır.

### 3. API Football istemcisi

Tek modül: `app/sources/api_football.py`

- Rate limit ve retry burada. Başka yerde HTTP çağrısı yapılmaz.
- Yanıtlar ham haliyle önce diske/tabloya yazılır, sonra parse edilir.
  Parse hatası olursa ham veri kaybolmaz.
- Kota kullanımı loglanır. Plan sınırına yaklaşıldığında uyarı.

Çekilecekler: ligler, takımlar, fikstürler (geçmiş 3-4 sezon + gelecek 7 gün), sonuçlar.

### 4. football-data.co.uk indirici

`app/sources/football_data.py`

- İlgili lig CSV'leri indirilir, parse edilir
- Maç sonuçları ve **açılış/kapanış oranları** alınır
- Pinnacle sütunu kullanılmaz (2025 ortasından beri güvenilmez);
  piyasa ortalaması / maksimum sütunları kullanılır
- Haftalık güncelleme için aynı modül tekrar çalışır

### 5. İsim eşleştirme

İki kaynak takım isimlerini farklı yazar ("St Patricks" / "St Patrick's Athletic").

- Önce `team_aliases` tablosuna bakılır
- Bulunamazsa bulanık eşleştirme denenir (yüksek eşik, örn. 0.9)
- Yine bulunamazsa `unmatched_fixtures` tablosuna yazılır

**Eşleşmeyen kayıt sessizce atılmaz.** `make report` çıktısında sayısı görünür.
Kullanıcı gerekirse elle alias ekler.

### 6. Arşivleme

Aynı maç tekrar geldiğinde `ON CONFLICT DO NOTHING`. Günlük çekilen veri
kalıcı olarak birikir; zamanla kendi arşivin oluşur.

## Kabul kriterleri

1. `make setup` temiz bir makinede hatasız çalışıyor
2. `make seed` sonrası veritabanında en az 5.000 geçmiş maç var
3. Bu maçların en az %80'inde kapanış oranı dolu
4. `make fetch` gelecek 7 günün fikstürünü çekiyor
5. `make report` şunları yazdırıyor: lig sayısı, takım sayısı, maç sayısı,
   oranı olan maç sayısı, eşleşmeyen kayıt sayısı
6. Eşleşmeyen kayıt oranı %5'in altında
7. `.env` dosyası git'e gitmemiş

## Riskler

**API kotası.** Geçmiş sezonları çekmek çok sayıda çağrı gerektirir. Önce tek bir
lig ve tek bir sezon ile test edilir, kota tüketimi ölçülür, sonra tamamı çekilir.

**İsim eşleştirme.** En sık zaman kaybettiren yer burasıdır. Bulanık eşleştirmede
eşik düşük tutulursa yanlış takımlar birleşir ve veri sessizce bozulur.
Eşik yüksek tutulur, kalanlar elle çözülür.

**Lig kodu eşleştirme.** football-data.co.uk kodları ile API Football lig id'leri
elle eşleştirilir. Yanlış eşleştirme fark edilmesi zor bir hatadır; her lig için
birkaç maç elle doğrulanır.

## Sonraki adım

Bu spec bittiğinde `specs/002-model-katmani.md` yazılır: feature üretimi,
Dixon-Coles ve Elo predictor'ları, evaluation modülü.
