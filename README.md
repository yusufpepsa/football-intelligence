# Football Intelligence Platform

Futbol maçları için tahmin üreten ve o tahminlerin gerçekten işe yarayıp
yaramadığını ölçen bir platform.

## Nereden başlamalı

| Kim | Ne okumalı |
|---|---|
| Kullanıcı | `KURULUM.md` — hesap açma, anahtar alma, ilk çalıştırma |
| Claude Code | `CLAUDE.md` — kurallar ve yönlendirme tablosu |
| İlk iş | `specs/000-veri-katmani.md` |

## Dosya haritası

```
CLAUDE.md                 Claude Code için kurallar. Kısa tutulur.
KURULUM.md                Kullanıcı için adım adım kurulum
Makefile                  Bütün komutlar
.env.example              Anahtar şablonu

docs/
  01-architecture.md      Katmanlar, veri akışı, kaynaklar
  02-data-model.md        Veritabanı şeması
  03-predictors.md        Tahmin yöntemi sözleşmesi
  04-evaluation.md        Metrik tanımları (dondurulmuş)
  05-mvp-plan.md          3 haftalık plan, kabul kriterleri
  06-research-protocol.md İstatistiksel disiplin kuralları
  07-markets.md           Marketlerin türetilmesi
  prompts/                LLM promptları, versiyonlu
  adr/                    Mimari kararlar ve gerekçeleri

specs/
  000-veri-katmani.md     Hafta 1
  001-common-opponent-predictor.md
```

## Temel fikir

Tahmin üretmek kolaydır. Üretilen tahminin işe yarayıp yaramadığını bilmek zordur.
Bu proje ikincisi üzerine kuruludur.

Her tahmin, üretildiği anın verisiyle ve zaman damgasıyla saklanır. Sonuçlar ve
kapanış oranları haftalık olarak geriye dönük işlenir. Böylece 3 ay sonra
"bu yöntem gerçekten işe yarıyor mu" sorusu cevaplanabilir.

Bütün tahmin yöntemleri — istatistiksel modeller, kullanıcının ortak rakip
yöntemi, LLM'ler — aynı arayüzden geçer ve aynı tabloda ölçülür.
