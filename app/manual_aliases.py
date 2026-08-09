"""Hiçbir kuralla çözülemeyen takım ismi eşleştirmeleri.

Bunlar tamamen farklı takma adlar/fonetik yazımlar (örn. "Kooteepee" ↔ "KTP") -
normalizasyon veya kısaltma açılımıyla genel olarak yakalanamaz, elle girilir.

`backfill-odds` her çalıştığında bu listeyi `team_aliases`'a yükler
(ON CONFLICT DO NOTHING - tekrar tekrar çalıştırmak güvenli).

Yeni bir tane bulursan: `backfill-odds`'un logladığı "eşleşmeyen örnekler"
listesine bak, buraya ekle, tekrar çalıştır.

Format: (fd_code, "teams.name'deki gerçek isim (API-Football)", "football-data.co.uk'teki ham isim")

Not: "UCD" ↔ "UC Dublin" buraya eklenmedi - boşluksuz önek kontrolü ("ucd" <->
"ucdublin", skor 0.95) bunu zaten kural olarak çözüyor.

UYARI: Aşağıdaki kayıt gerçek veriye karşı doğrulanmadı (bu ortamda erişim
yok). Hangi tarafın API-Football hangi tarafın football-data olduğundan emin
olamadığım için yön yanlış olabilir - `real_name` sütunu teams.name ile
eşleşmezse backfill-odds "takım bulunamadı" diye loglar, o zaman iki sütunu
yer değiştir.
"""
MANUAL_ALIASES = [
    ("FIN", "KTP", "Kooteepee"),
]
