# KURULUM — Ne Yapman Gerekiyor

Bu rehber yazılım bilgisi olmadan takip edilebilir. Sırayla git.
Kod yazmayacaksın; Claude Code yazacak. Senin işin hesap açmak,
anahtar almak ve onay vermek.

---

## Adım 0 — Bilgisayarına Claude Code kur

Claude Code'u kur ve bir klasör aç, örneğin `football-intelligence`.
Bu dosyaların hepsini o klasörün içine koy. Klasör yapısı şöyle olmalı:

```
football-intelligence/
  CLAUDE.md
  KURULUM.md
  Makefile
  .env.example
  .gitignore
  docs/
  specs/
```

Claude Code'u bu klasörde başlattığında `CLAUDE.md`'yi kendiliğinden okur.

---

## Adım 1 — Git deposu (5 dakika)

GitHub'da yeni ve **özel (private)** bir depo aç. Adı ne olursa olsun.

Neden gerekli: kodun kaybolmaması ve ileride Render'a otomatik kurulum için.
Şimdi kurmasan da olur ama sonra kurmak daha zahmetli.

Claude Code'a şunu söylemen yeterli:
> "Bu klasörü git deposu yap ve şu adrese bağla: <depo adresi>"

**Önemli:** `.env` dosyası asla depoya gönderilmez. `.gitignore` bunu zaten
engelliyor, ama kontrol et.

---

## Adım 2 — Veritabanı (10 dakika)

Bilgisayarına Postgres kurmana gerek yok. Bulutta ücretsiz bir tane al.

Seçenekler (üçü de ücretsiz katman sunuyor, herhangi biri olur):
- Neon
- Supabase
- Render'ın PostgreSQL hizmeti

Yaptığın şey: hesap aç → yeni veritabanı oluştur → sana verilen
**bağlantı adresini** (connection string) kopyala. `postgresql://...` ile
başlayan uzun bir metin.

Bu adresi kimseyle paylaşma.

---

## Adım 3 — API Football aboneliği (10 dakika)

Adres: api-football.com

Hesap aç ve bir plan seç. **Dikkat edilecek nokta:** ücretsiz plan geçmiş
sezon verisi vermez veya çok kısıtlı verir. Bize geçmiş 3-4 sezon lazım,
o yüzden ücretli bir plana ihtiyaç var. Aylık maliyet kabaca 25-40 dolar
bandındadır; güncel fiyatı sitede kontrol et.

Aldığın **API anahtarını** kopyala.

Bu, MVP'de para ödeyeceğin tek yer.

---

## Adım 4 — Bedava veri kaynağı (0 dakika)

football-data.co.uk için hesap veya anahtar gerekmez. Sistem CSV dosyalarını
doğrudan indirir. Senin bir şey yapmana gerek yok.

Buradan gelen şeyler: geçmiş maç sonuçları ve **kapanış oranları**.
Bunlar 3 ay sonra "tahminlerimiz iyi miydi" sorusunu cevaplamamızı sağlayacak.

---

## Adım 5 — LLM anahtarları

**MVP'de gerekmiyor.** Faz 3'e kadar bu adımı atla.

O zaman geldiğinde Anthropic, OpenAI ve Google'dan API anahtarı alacağız.
Şimdi para harcamana gerek yok.

---

## Adım 6 — Anahtarları yerine koy

Klasörde `.env.example` diye bir dosya var. Onu kopyalayıp adını `.env` yap
ve içine Adım 2 ve 3'te aldığın değerleri yapıştır.

Claude Code'a şunu diyebilirsin:
> ".env.example dosyasını .env olarak kopyala"

Sonra `.env` dosyasını açıp değerleri elle yapıştır. Anahtarları
Claude Code'a yazdırma, kendin yapıştır.

---

## Adım 7 — Başlat

Claude Code'a ilk komutun bu olsun:

> CLAUDE.md ve docs/ klasörünü oku. docs/05-mvp-plan.md içindeki Hafta 1
> işlerini yapacağız. Önce specs/ altına bir şartname yaz, onayımı al,
> sonra kod yaz. Veritabanı şeması ile başla.

Sonrasında her oturuma şöyle başla:

> CLAUDE.md'yi oku, kaldığımız yerden devam ediyoruz.

---

## Sistem hemen çalışır mı?

Hayır, ve bu normal. Gerçekçi takvim:

| Ne zaman | Ne olur |
|---|---|
| 1. gün | Veritabanı şeması kurulur, bağlantı test edilir |
| 2-4. gün | API Football'dan veri akmaya başlar, geçmiş sezonlar iner |
| 1. hafta sonu | Veritabanında binlerce geçmiş maç ve kapanış oranı var |
| 2. hafta | İlk tahminler üretilir, geçmiş sezonlar üzerinde test edilir |
| 3. hafta | Her sabah kendiliğinden çalışan sistem + tarayıcıdan bakabildiğin arayüz |

"Analize hemen başlasın" isteğinin en yakın karşılığı **2. haftadır**.
1. hafta veri toplamakla geçer ve bu atlanamaz — model geçmiş veri olmadan
hiçbir şey üretemez.

---

## Render'a ne zaman geçilir?

**Hemen değil.** İlk 2-3 hafta kod senin bilgisayarında çalışsın, veritabanı
bulutta olsun. Bu yeterli ve daha basit.

Render'a şu ihtiyaç doğunca geçeriz: sistemin her sabah sen bilgisayarını
açmasan bile kendiliğinden çalışması. O da 3. haftanın işi.

O zaman geldiğinde Claude Code'a "bu projeyi Render'a kur" dersin,
gerekli dosyaları o oluşturur. Sen sadece Render'da hesap açıp depoyu
bağlarsın.

---

## Senin sürekli işin ne olacak?

MVP çalışmaya başladıktan sonra günlük işin şu:

1. Akşam tarayıcıdan sisteme gir
2. Günün listesine bak
3. Bitti

Haftada bir de ölçüm sayfasına bakarsın. Manuel veri girişi yok,
buton yok, dosya indirme yok.

Faz 2'de (oran eklendiğinde) günde 1-2 dakikalık manuel oran girişi eklenecek,
sadece sistemin işaretlediği 3-6 maç için.

---

## Maliyet özeti

| Kalem | MVP (ilk 3 ay) | Sonrası |
|---|---|---|
| API Football | ~25-40 $/ay | aynı |
| Veritabanı | 0 (ücretsiz katman) | 0-15 $/ay |
| football-data.co.uk | 0 | 0 |
| Render (3. haftadan sonra) | 0-15 $/ay | aynı |
| LLM | 0 | ~20-60 $/ay (Faz 3) |
| **Toplam** | **~25-55 $/ay** | **~50-130 $/ay** |

Bahis parası bu bütçeye dahil değildir ve MVP'de hiç gerekmez.

---

## Takıldığın yerde

Claude Code'a hata mesajını olduğu gibi yapıştır ve "bu ne demek,
nasıl düzeltirim" diye sor. Hata mesajını anlamana gerek yok.

Sadece şuna dikkat et: `.env` dosyasının içeriğini hiçbir yere yapıştırma.
İçinde API anahtarların var.
