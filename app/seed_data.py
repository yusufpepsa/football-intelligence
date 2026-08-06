"""specs/000-veri-katmani.md Adım 2 — başlangıç lig listesi.

Bu eşleştirme elle yapılır ve bir kez yapılır (bkz. docs/02-data-model.md).

UYARI: api_football_id değerleri bu oturumda API-Football'un /leagues uç
noktasına karşı doğrulanamadı (anahtar bu ortamda yok). `make seed`
ardından `make fetch` çalıştırılınca bir lig boş veya yanlış maç
döndürürse önce buradaki id'yi kontrol et (specs/000-veri-katmani.md
"Riskler" bölümü).
"""

# API-Football'da sezonu takvim yılına göre değil temmuz-haziran arası
# sayan ligler. fetch sırasında API'ye gönderilecek `season` parametresini
# hesaplamak için kullanılır (docs/02-data-model.md'ye yazılmaz).
CROSS_YEAR_SEASON_LEAGUES = {119, 106, 283, 207, 218}  # Danimarka, Polonya, Romanya, İsviçre, Avusturya

LEAGUES = [
    {"name": "Eliteserien", "country": "Norway", "api_football_id": 103, "fd_code": "NOR"},
    {"name": "Allsvenskan", "country": "Sweden", "api_football_id": 113, "fd_code": "SWE"},
    {"name": "Premier Division", "country": "Ireland", "api_football_id": 357, "fd_code": "IRL"},
    {"name": "Veikkausliiga", "country": "Finland", "api_football_id": 244, "fd_code": "FIN"},
    {"name": "Superliga", "country": "Denmark", "api_football_id": 119, "fd_code": "DNK"},
    {"name": "Ekstraklasa", "country": "Poland", "api_football_id": 106, "fd_code": "POL"},
    {"name": "Liga I", "country": "Romania", "api_football_id": 283, "fd_code": "ROU"},
    {"name": "Super League", "country": "Switzerland", "api_football_id": 207, "fd_code": "SWZ"},
    {"name": "Bundesliga", "country": "Austria", "api_football_id": 218, "fd_code": "AUT"},
]
