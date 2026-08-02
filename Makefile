.PHONY: setup migrate fetch predict backfill report serve test

setup:      ## bağımlılıklar + veritabanı kurulumu
	python -m venv .venv && .venv/bin/pip install -U pip && .venv/bin/pip install -r requirements.txt
	.venv/bin/alembic upgrade head

migrate:    ## şema güncelleme
	.venv/bin/alembic upgrade head

seed:       ## ligleri ve geçmiş veriyi ilk kez yükle
	.venv/bin/python -m app.cli seed

fetch:      ## günün maçlarını çek
	.venv/bin/python -m app.cli fetch

predict:    ## bekleyen maçlar için tahmin üret
	.venv/bin/python -m app.cli predict

backfill:   ## sonuçları ve kapanış oranlarını geçmiş tahminlere işle
	.venv/bin/python -m app.cli backfill

backtest:   ## geçmiş sezonlar üzerinde model testi
	.venv/bin/python -m app.cli backtest

report:     ## ölçüm tablosunu yazdır
	.venv/bin/python -m app.cli report

serve:      ## arayüzü başlat (http://localhost:8000)
	.venv/bin/uvicorn app.main:app --reload

test:
	.venv/bin/pytest -q
