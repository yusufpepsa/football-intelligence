# 002 — Model Katmanı (Hafta 2)

## Amaç

Geçmiş sezon verisinden (Hafta 1'de biriktirilen ~8.000 maç + kapanış oranı) özellik
üretip, `Predictor` sözleşmesine uyan iki istatistiksel yöntem (Dixon-Coles Poisson,
Elo) ile olasılık üretmek ve bunları kapanış oranından türetilen piyasa referansına
karşı ölçülebilir şekilde karşılaştırmak.

## Kapsam

**Yapılacak**

- `Predictor` arayüzü ve `Prediction` dataclass'ı (`docs/03-predictors.md`), çıktı
  doğrulaması (6 kural: olasılık toplamı, aralık, market anahtarları, zaman,
  input_snapshot, tekillik).
- `app/features.py`: son N maç formu (N=15 varsayılan), ev/deplasman ayrımı, rakip
  gücü düzeltmesi, küçültme (shrinkage), örneklem büyüklüğünün taşınması, dinlenme
  günü.
- `poisson_dc`: Dixon-Coles, zaman ağırlıklı (yarılanma 180 gün varsayılan, lig
  bazında ayarlanabilir), skor matrisinden `docs/07-markets.md` formülleriyle
  1x2/ou25/btts türetilir.
- `elo`: gol farkını hesaba katan versiyon, sadece 1x2.
- `app/evaluation.py`: Brier, log loss, kalibrasyon (10 kova), `docs/04-evaluation.md`
  v1.0 formülleri.
- `market_baseline`: kapanış oranından (`odds_snapshots`, kaynak
  `football_data_avg`) oransal yöntemle vig çıkarılmış olasılık. `docs/03-predictors.md`
  gereği bu bir öneri değil, karşılaştırma referansıdır.
- `python -m app.cli backtest`: geçmiş sezonlar üzerinde `poisson_dc`, `elo`,
  `market_baseline`'ı **aynı maç kümesinde** çalıştırır, `metrics_snapshots`'a yazar,
  özet tablo basar.

**Yapılmayacak**

- LLM katmanı (Faz 3).
- Karar katmanı, edge hesabı, öneri (oran MVP'de yok).
- `common_opponent` predictor'ı (ayrı bir spec — `specs/001` zaten var, bu hafta
  kapsamı dışında, istenirse ayrı ele alınır).
- Web arayüzü.
- `market_baseline`'ın canlı/güncel oran akışı — sadece geçmiş kapanış oranı.

## Veri

**Okunan:** `fixtures` (kickoff_utc, goller, sezon), `teams`, `leagues.is_active`,
`odds_snapshots` (source=`football_data_avg`, market=`1x2`, is_closing=true).

**Yazılan:** `predictions`, `metrics_snapshots`.

`predictions` şu an tamamen boş — bu hafta ilk satırlar buraya yazılacak.
`predictions` tablosu **değişmez** kaydı zaten uyguluyor (trigger:
`predicted_at < kickoff_utc`); backtest de canlı tahmin de aynı validasyon ve aynı
tabloyu kullanır — hiçbir predictor'e (bu ikisi dahil) özel yol yoktur.

## Kabul kriterleri

1. `Predictor` ABC + `Prediction` dataclass `docs/03-predictors.md` ile birebir.
2. Çıktı doğrulamasının 6 kuralı da ayrı ayrı test edilmiş (en az bir "reddedilmeli"
   testi her kural için).
3. `poisson_dc` ve `elo` deterministik: aynı girdi → aynı çıktı.
4. `backtest`, `poisson_dc` + `elo` + `market_baseline`'ı **ortak maç kümesi**
   üzerinde karşılaştırır (`docs/04-evaluation.md`: "İki predictor karşılaştırılırken
   aynı maç kümesi kullanılır").
5. Rapor: her predictor/market için `n`, Brier, kalibrasyon durumu; `n<100` ise
   soluk/"henüz yorumlanamaz" etiketiyle.
6. Küçültme (shrinkage) olmadan üretilmiş bir özellik seti ile karşılaştırıldığında
   (backtest sırasında) küçültmenin Brier'i gerçekten iyileştirdiği gösterilir —
   yoksa uygulanmasının gerekçesi yok demektir (`docs/03-predictors.md`'nin kendi
   uyarısı).

## Riskler

- **Veri sızıntısı (en kritik):** `MatchContext`, bir maç için SADECE o maçın
  `kickoff_utc`'sinden ÖNCEKİ verilerle kurulmalı. Backtest binlerce geçmiş maçı
  aynı anda işleyeceği için, "son N maç formu" hesaplanırken yanlışlıkla gelecekteki
  bir maçın dahil edilmesi kolay bir hatadır ve sonuçları sessizce anlamsız kılar.
  Feature üretim kodu bunu test etmeli (bilerek gelecekteki bir maçı değiştirip
  metriğin değişmediğini doğrulayan bir test).
- **Küçük örneklem / lig devir hızı:** Sezon başında ve yeni yükselen takımlarda
  form verisi çok az olur, küçültme bunu telafi eder ama parametre (ağırlık
  eğrisi) backtest ile bulunmalı, tahminle değil.
- **Zaman ağırlığı ve küçültme parametreleri lig bazında farklı olabilir**
  (`docs/03-predictors.md`: "alt liglerde kadro devir hızı yüksek... bunu tahminle
  değil, backtest ile belirle"). Bu hafta içinde TEK bir varsayılan (180 gün
  yarılanma) ile başlanacak, lig bazında ayarlama backtest sonuçlarına göre Hafta
  3+'a bırakılacak.
- **market_baseline'ın veri kapsamı sınırlı:** `backfill-odds` sonrası kapanış oranı
  kapsamı ligden lige değişiyor (bkz. `report` çıktısı, %20-100 arası). `market_baseline`
  ile karşılaştırma sadece oranı olan maçlarla sınırlı olacak — bu, "ortak maç
  kümesi" kuralının (Kabul kriteri 4) `poisson_dc`/`elo` için de otomatik olarak
  aynı alt kümeye indirgenmesi gerektiği anlamına gelir.

## Bilinmeyenler — onay gerekiyor

Kod yazmadan önce netleşmesi gereken üç nokta:

1. **Backtest'te `predicted_at` nasıl simüle edilecek?** Gerçek zamanda tahmin
   üretmiyoruz, geçmişe bakıyoruz. Öneri: `predicted_at = kickoff_utc - 1 saat`
   (kural: `predicted_at < kickoff_utc` sağlanır, ve "maç başlamadan hemen önce
   üretilmiş gibi" davranır). Başka bir değer mi istersin (örn. maçtan 1 gün önce)?
2. **`market_baseline` için hangi oran kaynağı?** `odds_snapshots`'ta hem
   `football_data_avg` hem `football_data_max` var. Öneri: `football_data_avg`
   (piyasa ortalaması gerçek konsensüsü daha iyi yansıtır, `max` uç bir değerdir).
   Onaylıyor musun?
3. **Backtest sonuçları `docs/adr/`'a yazılsın mı?** `docs/03-predictors.md`,
   "Yeni predictor ekleme" adım 5'te bunu zorunlu tutuyor ("Adım 5 atlanmaz").
   Poisson-DC ve Elo bu hafta ilk kez eklendiği için bu kurala tabi — backtest
   bitince kısa bir ADR (örn. `0004-poisson-dc-elo-ilk-backtest.md`) yazılacak,
   onaylıyor musun?

Bu üçü netleşince kod yazmaya başlarım.
