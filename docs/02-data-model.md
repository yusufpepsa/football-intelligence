# 02 — Veri Modeli

## Prensip

Veritabanı bu projenin asıl ürünüdür. Kod yeniden yazılabilir, veri geri gelmez.
Şema, "altı ay sonra bu tahmini neden ürettiğimizi ve iyi olup olmadığını
cevaplayabilir miyiz" sorusuna göre tasarlanmıştır.

Üç kural:

1. **Tahmin kayıtları değişmez.** Yazıldıktan sonra sadece sonuç ve kapanış oranı
   alanları doldurulur. Olasılık, model adı, prompt versiyonu güncellenmez.
2. **Girdi saklanır.** Her tahminin yanında o tahmine giren verinin tam kopyası ve
   hash'i durur.
3. **Zaman kaydedilir.** `predicted_at` olmadan hiçbir tahmin geçerli değildir.

## Tablolar

### leagues
```
id              serial pk
name            text            -- "Eliteserien"
country         text            -- "Norway"
api_football_id int unique
fd_code         text            -- football-data.co.uk kodu, örn "NOR"
is_active       bool default true   -- veriyle kapatılır/açılır
created_at      timestamptz
```

`is_active` lig eleme mekanizmasıdır. Kapatmak için kod değişikliği gerekmez.

### teams
```
id              serial pk
league_id       int fk
name            text
api_football_id int unique
created_at      timestamptz
```

### team_aliases
```
id          serial pk
team_id     int fk
source      text        -- "football_data" | "api_football" | "manual"
alias       text
unique(source, alias)
```

İsim eşleştirme için. Yeni bir eşleşmeyen isim çıktığında buraya elle eklenir.

### fixtures
```
id                serial pk
league_id         int fk
home_team_id      int fk
away_team_id      int fk
kickoff_utc       timestamptz not null
season            text
status            text          -- scheduled | finished | postponed | cancelled
api_football_id   int unique
home_goals        int null
away_goals        int null
home_goals_ht     int null
away_goals_ht     int null
created_at        timestamptz
updated_at        timestamptz
index(kickoff_utc), index(league_id, kickoff_utc)
```

### predictions
Projenin kalbi. Buraya yazılan satır bir daha değişmez.

```
id                serial pk
fixture_id        int fk
predictor_name    text not null   -- "poisson_dc" | "elo" | "gpt5" | "claude" | ...
predictor_version text not null   -- "1.0.3"
prompt_version    text null       -- sadece LLM için, örn "v2"
market            text not null   -- "1x2" | "ou25" | "btts" | "ht_1x2"
probabilities     jsonb not null  -- {"home":0.42,"draw":0.28,"away":0.30}
predicted_at      timestamptz not null
input_snapshot    jsonb not null  -- modele giden verinin tamamı
input_hash        text not null   -- sha256(input_snapshot)
sample_size       int null        -- kaç maçlık veriye dayanıyor
notes             text null       -- LLM'in kısa gerekçesi

-- sonradan doldurulan alanlar
actual_outcome    text null       -- "home" | "over" | "yes" ...
settled_at        timestamptz null
closing_odds      jsonb null      -- {"home":2.35,"draw":3.40,"away":3.10}
closing_source    text null       -- "football_data_avg"

created_at        timestamptz
unique(fixture_id, predictor_name, predictor_version, market)
index(predicted_at), index(predictor_name, market)
```

`probabilities` toplamı 1.0 olmalıdır (tolerans 0.001). Yazmadan önce doğrulanır.

`predicted_at >= fixtures.kickoff_utc` ise INSERT reddedilir. Bu kontrol veritabanı
seviyesinde trigger veya uygulama seviyesinde zorunlu doğrulama olarak uygulanır.

### odds_snapshots
MVP'de sadece backfill ile dolar. İleride canlı oran kaynağı eklenirse aynı tabloya yazar.

```
id            serial pk
fixture_id    int fk
source        text        -- "football_data_avg" | "iddaa_manual" | ...
market        text
odds          jsonb       -- {"home":2.35,...}
captured_at   timestamptz -- oranın geçerli olduğu an
is_closing    bool
created_at    timestamptz
index(fixture_id, source, market)
```

### bets
Sadece kullanıcı bir öneriyi kabul ettiğinde yazılır. MVP'de kağıt üstü.

```
id            serial pk
prediction_id int fk
stake         numeric(10,2)
odds_taken    numeric(6,3)
is_paper      bool default true
placed_at     timestamptz
result        text null     -- won | lost | void
pnl           numeric(10,2) null
```

### metrics_snapshots
Haftalık hesaplanan ölçüm tablosu. Geçmiş anlık görüntüler silinmez.

```
id              serial pk
computed_at     timestamptz
predictor_name  text
market          text
league_id       int null    -- null = tüm ligler
n               int         -- gözlem sayısı
brier           numeric
log_loss        numeric
calibration     jsonb       -- kova kova: {"0.5-0.6":{"n":40,"actual":0.55}}
roi_vs_closing  numeric null
```

`n` her zaman raporlanır. `n` olmadan gösterilen yüzde yalan söyler.

### unmatched_fixtures
```
id          serial pk
source      text
raw_home    text
raw_away    text
raw_date    date
seen_at     timestamptz
resolved    bool default false
```

Eşleşmeyen kayıtlar sessizce atılmaz. Raporda sayısı gösterilir.

## Şema değişikliği

Alembic migration ile. Elle SQL çalıştırılmaz. `predictions` tablosunda mevcut bir
sütunun anlamı değiştirilmez — yeni sütun eklenir, eskisi bırakılır.

## Neden bazı şeyler yok

- **Model karşılaştırma tablosu yok.** Karşılaştırma `predictions` üstünde sorgu ile yapılır.
  Türetilmiş veriyi ayrı tabloda tutmak tutarsızlık üretir.
- **Kullanıcı tablosu yok.** Tek kullanıcı.
- **Feature'lar ayrı tabloda değil.** `input_snapshot` içinde saklanıyor, çünkü asıl
  soru "bu tahmin hangi veriyle yapıldı" ve cevabın tahminle aynı satırda olması gerekiyor.
