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

Aşağıdakiler gerçek backfill-odds çalıştırmasının "eşleşmeyen örnekler"
logundan alındı (bkz. DB ↔ CSV formatındaki log satırları) - yönleri doğrulandı.
"""
MANUAL_ALIASES = [
    ("FIN", "Kooteepee", "KTP"),
    ("AUT", "WSG Wattens", "Tirol"),
    ("ROU", "Sepsi OSK Sfantu Gheorghe", "Sepsi Sf. Gheorghe"),
    ("POL", "Nieciecza", "Termalica B-B."),
    ("FIN", "EIF", "Ekenas"),  # Ekenäs IF
]
