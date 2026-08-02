# ADR 0003 — Lig seçimi veriyle yapılır

Tarih: 2026-08-02
Durum: Kabul edildi

## Bağlam

Hangi liglerde tahmin yapmanın anlamlı olduğu baştan bilinemez. Veri kalitesi,
kadro devir hızı ve fiyatlama kalitesi ligden lige değişir.

## Karar

Geniş bir lig kümesiyle başlanır. `leagues.is_active` alanı ile ligler kod
değişikliği olmadan açılıp kapatılabilir. Kapatma kararı `docs/06-research-protocol.md`
içindeki eşiklere tabidir: lig başına en az 150-200 tahmin, ve karar kâr/zarara
değil Brier ile kalibrasyona göre.

Başlangıç kümesi: football-data.co.uk kapsamındaki ligler önceliklidir,
çünkü kapanış oranı arşivi ücretsiz mevcuttur (Norveç, İsveç, İrlanda,
Finlandiya, Danimarka, Polonya, Romanya, İsviçre, Avusturya ve diğerleri).

## Gerekçe

Geniş tarama istatistiksel katmanda neredeyse maliyetsizdir. Asıl maliyet
LLM katmanındadır ve o katman sadece filtreden geçen maçlara uygulanır.

## Sonuçlar

- Erken dönemde çok sayıda düşük kaliteli tahmin üretilir; bu beklenen durumdur.
- Lig eleme kararları için sabır gerekir; 20 maç sonra karar verilmez.
