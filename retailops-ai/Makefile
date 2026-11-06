.PHONY: init seed api dashboard test docker-up docker-down
init:
	python -m retailops.bootstrap
seed:
	python -m retailops.generate_data --out data/sample
	python -m retailops.ingest --dir data/sample
api:
	uvicorn retailops.api:app --reload
dashboard:
	streamlit run dashboard/app.py
test:
	python -m pytest -q
docker-up:
	docker compose up --build
docker-down:
	docker compose down
