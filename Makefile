.PHONY: ingest seed test backend frontend

ingest:
	python -m pipeline.ingest --mock-llm --sample

seed:
	python -m pipeline.ingest --mock-llm --sample --seed-only

test:
	cd backend && pytest

backend:
	cd backend && uvicorn app.main:app --reload

frontend:
	cd frontend && npm run dev
