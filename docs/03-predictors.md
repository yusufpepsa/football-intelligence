# 03 — Predictor Sözleşmesi

## Neden bu dosya var

Projenin cevaplamaya çalıştığı asıl soru: "hangi yöntem daha iyi tahmin yapıyor?"
Bu soru ancak bütün yöntemler aynı arayüzden geçip aynı tabloda ölçülürse cevaplanır.

Bu yüzden tek bir kural var ve istisnası yoktur: **tahmin üreten her şey `Predictor`dur.**
İstatistiksel model de, LLM de, kullanıcının elle kurduğu kural seti de.

LLM özel muamele görmez. Ayrı bir kayıt yolu, ayrı bir tablo, ayrı bir metrik yoktur.

## Arayüz

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class Prediction:
    market: str                  # "1x2" | "ou25" | "btts" | "ht_1x2"
    probabilities: dict[str, float]
    predicted_at: datetime       # UTC
    input_snapshot: dict         # modele giden verinin tamamı
    sample_size: int | None = None
    notes: str | None = None     # kısa gerekçe, opsiyonel

class Predictor(ABC):
    name: str                    # "poisson_dc", "elo", "claude", ...
    version: str                 # "1.0.0" — mantık değişirse artar
    prompt_version: str | None = None   # sadece LLM için

    @abstractmethod
    def supported_markets(self) -> list[str]: ...

    @abstractmethod
    def predict(self, ctx: MatchContext) -> list[Prediction]: ...
```

`MatchContext`, predictor'ün görebileceği her şeyi içerir ve **maç başlangıcından
önce bilinen veriyle sınırlıdır**. İçine sonuç, kapanış oranı veya maç sonrası
istatistik konulmaz. Bu, sızıntıya karşı tek savunma hattıdır.

## Çıktı doğrulaması

Her `Prediction` veritabanına yazılmadan önce şu kontrollerden geçer.
Herhangi biri başarısızsa kayıt reddedilir, hata loglanır, sistem devam eder.

1. `probabilities` değerlerinin toplamı 1.0 ± 0.001
2. Her olasılık 0 < p < 1 aralığında (tam 0 veya 1 kabul edilmez)
3. `market` için beklenen anahtarlar eksiksiz
   - `1x2` → home, draw, away
   - `ou25` → over, under
   - `btts` → yes, no
4. `predicted_at` < `fixture.kickoff_utc`
5. `input_snapshot` boş değil ve JSON'a serileşiyor
6. Aynı (fixture, name, version, market) için kayıt yoksa

Kural 2 önemli: bir model "%100 kesin" derse log loss sonsuza gider ve tek bir
hata bütün ölçümü bozar. LLM'ler bunu yapmaya eğilimlidir. Olasılıklar
[0.001, 0.999] aralığına kırpılır.

## MVP predictor'ları

### `poisson_dc` — Dixon-Coles

Ana baseline. Her takım için hücum ve savunma gücü katsayısı, artı ev avantajı.
Skor dağılımı üretir; 1X2, alt/üst ve KG olasılıkları aynı dağılımdan türetilir.
Düşük skorlu sonuçlar için Dixon-Coles düzeltmesi uygulanır.

Zaman ağırlığı: eski maçlar üstel olarak azalan ağırlık alır.
Yarılanma süresi lig bazında ayarlanabilir, varsayılan 180 gün.
Alt liglerde kadro devir hızı yüksek olduğu için bu değer düşürülebilir —
ancak bunu tahminle değil, backtest ile belirle.

### `elo`

İkinci baseline. Basit, hızlı, şaşırtıcı derecede iyi. Karşılaştırma için gerekli.
Gol farkını hesaba katan versiyon kullanılır. Sadece 1X2 üretir.

### `market_baseline` (Faz 2)

Kapanış oranından vig çıkarılarak elde edilen olasılık. Yenilmesi hedeflenen sınır.
Ölçümde referans olarak kullanılır, tahmin olarak değil.

### LLM predictor'ları (Faz 3)

`gpt5`, `claude`, `gemini`. Aynı `MatchContext`ten üretilen JSON'u alır,
olasılık döndürür. Birbirlerinin çıktısını görmezler, geçmiş tahminleri okumazlar.

LLM çıktısı serbest metin değil, zorunlu JSON şemasıdır. Şemaya uymayan cevap
bir kez yeniden istenir, yine uymazsa kayıt atlanır ve `unmatched` sayacı artar.

## Feature üretimi

Predictor'lar ham veriyi değil, `features/` modülünün ürettiği metrikleri kullanır.

MVP'de üretilecekler:

| Metrik | Not |
|---|---|
| Son N maç gol ortalaması (attığı/yediği) | N varsayılan 15 |
| Ev / deplasman ayrımı | ayrı hesaplanır |
| Rakip gücü düzeltmesi | gol oranları rakip kalitesine göre normalize edilir |
| Küçültme (shrinkage) | takım oranı lig ortalamasına doğru çekilir |
| Örneklem büyüklüğü | her metriğin yanında taşınır |
| Dinlenme günü | son maçtan bu yana geçen gün |

**Küçültme neden zorunlu:** 14 maçlık örneklemde bir takımın "üst 2.5 oranı %85.7"
gibi görünmesi normaldir ve büyük ölçüde gürültüdür. Ham oran yerine lig ortalaması
ile ağırlıklı ortalaması kullanılır. Ağırlık örneklem büyüklüğünden gelir.
Bu düzeltme yapılmazsa model küçük örneklem gürültüsünü sinyal sanır.

**Rakip gücü neden zorunlu:** "28 gol attı" ifadesi kime karşı atıldığı bilinmeden
anlamsızdır. Her rakibe bir güç katsayısı atanır ve gol oranları buna göre düzeltilir.

## Yeni predictor ekleme

1. `predictors/` altına yeni sınıf, `Predictor`dan türetilmiş
2. `name` ve `version` belirle
3. `supported_markets` tanımla
4. Kayıt listesine ekle (`predictors/registry.py`)
5. Backtest çalıştır, sonucu `docs/adr/` altına kısa bir not olarak yaz

Adım 5 atlanmaz. Aksi halde altı ay sonra o predictor'ün neden eklendiği bilinmez.
