# Prompt v1 — Maç Analizi

**Versiyon: 1.0** · Faz 3'te kullanılacak. MVP'de devrede değildir.
Prompt değişirse yeni dosya açılır (`v2-analiz.md`), bu dosya silinmez.
`predictions.prompt_version` alanına bu versiyon yazılır.

## Tasarım notları

Bu prompt kullanıcının mevcut promptundan türetilmiştir. Üç önemli fark var:

1. **Hesap yaptırılmıyor.** Bütün metrikler Python tarafında hesaplanır ve hazır
   verilir. LLM'in görevi yorumlamaktır, saymak değil. Kullanıcının orijinal
   promptundaki "hiçbir istatistiği kendiniz hesaplamayın" talimatı korunmuştur.

2. **Belirsizlik bildiriliyor.** Her metrik yanında örneklem büyüklüğü ve güven
   aralığı ile gelir. LLM'in "%35.7" gibi bir sayıyı kesin gerçek sanması engellenir.

3. **Çıktı zorunlu JSON.** Serbest metin değil. Şemaya uymayan cevap bir kez
   yeniden istenir, yine uymazsa kayıt atlanır.

"Oyun karakteri" katmanı **çıkarılmıştır.** Sadece skor verisinden "kontrollü oynuyor",
"maçı kilitliyor" gibi çıkarımlar yapılamaz; LLM bunları uydurur. Şut, topla oynama
veya xG verisi eklenirse katman geri konur.

---

## Sistem mesajı

```
Sen bir futbol maçı analistisin. Sana bir maç için önceden hesaplanmış
metrikler verilecek. Görevin bu metrikleri yorumlayarak olasılık dağılımı
üretmektir.

KURALLAR

1. Hiçbir istatistiği kendin hesaplama veya sayma. Bütün metrikler hazır
   verilmiştir. Yalnızca verilen sayıları kullan.

2. Her metriğin yanında örneklem büyüklüğü (n) ve güven aralığı vardır.
   Dar aralıklı metriklere daha çok, geniş aralıklı metriklere daha az güven.
   14 maçlık bir örneklemde %35.7 değerinin gerçek aralığı %16–%61 olabilir;
   böyle bir sayıyı kesin bilgi gibi kullanma.

3. Asla 0 veya 1 olasılık verme. En emin olduğun durumda bile 0.02–0.98
   aralığında kal.

4. Verilmeyen bilgiyi uydurma. Sakatlık, kadro, motivasyon, hava durumu
   bilgisi verilmediyse bunlar hakkında yorum yapma.

5. Yalnızca JSON döndür. Açıklama, giriş cümlesi, markdown işareti ekleme.
```

## Kullanıcı mesajı şablonu

```
MAÇ: {ev_takim} - {dep_takim}
LİG: {lig} | TARİH: {tarih}

--- HAZIR METRİKLER ---
{metrics_json}

--- ORTAK RAKİP ANALİZİ ---
Ortak rakip sayısı: {n_ortak}
{ortak_rakip_tablosu}

--- MODEL REFERANSI ---
İstatistiksel model şu olasılıkları üretti:
{baseline_probs}

Bu referanstan sapıyorsan gerekçesini "reasoning" alanında belirt.
Sapmak için yeterli sebep yoksa referansa yakın kal.
```

**Model referansı neden veriliyor:** LLM'in sıfırdan olasılık üretmesi zayıf sonuç
verir. Referans verilip "sapmak için gerekçe göster" denince, LLM'in katkısı
ölçülebilir hale gelir: sapmaları isabetli mi, yoksa gürültü mü?

Bu bir tasarım tercihidir ve test edilecektir. `v2`de referanssız versiyon
denenip karşılaştırılabilir.

## Zorunlu çıktı şeması

```json
{
  "markets": {
    "1x2":  {"home": 0.00, "draw": 0.00, "away": 0.00},
    "ou25": {"over": 0.00, "under": 0.00},
    "btts": {"yes": 0.00, "no": 0.00}
  },
  "confidence": 0,
  "key_factors": ["", ""],
  "deviation_from_baseline": "",
  "reasoning": ""
}
```

Kurallar:
- Her market içindeki olasılıklar toplamı 1.0 (± 0.01)
- `confidence`: 1-10 tam sayı
- `key_factors`: en fazla 3 madde, her biri tek cümle
- `deviation_from_baseline`: referanstan sapma gerekçesi, sapma yoksa boş
- `reasoning`: en fazla 3 cümle

## Ölçüm

Bu prompt ile üretilen tahminler `docs/04-evaluation.md` metrikleriyle
`poisson_dc` ve `common_opponent_v1` ile yan yana ölçülür.

Sorulacak sorular:
1. LLM baseline'ı yeniyor mu?
2. LLM'in baseline'dan saptığı maçlarda isabet artıyor mu azalıyor mu?
3. LLM'in `confidence` puanı gerçek isabetle ilişkili mi (kalibrasyon)?
4. Üç LLM'in uyuştuğu maçlar gerçekten daha mı isabetli?

Soru 2 en önemlisi. Sapmalar gürültüyse LLM katmanı para yakıyor demektir.
