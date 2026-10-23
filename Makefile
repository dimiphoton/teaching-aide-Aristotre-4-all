VENV ?= backend/.venv
PY := $(VENV)/bin/python

.PHONY: venv test dev-diag frontend dev eval eval-offline eval-compare

venv:
	python3 -m venv $(VENV)
	$(PY) -m pip install -e "backend[dev]"

# Diagnostic du matériel simulé (aucun périphérique requis)
dev-diag:
	ARISTOTE_MOCK=1 $(PY) -m aristote.cli diag printer

frontend:
	cd frontend && npm ci --no-audit --no-fund && npm run build

# Kiosque simulé sur http://127.0.0.1:8000 (interface compilée requise : make frontend)
dev:
	ARISTOTE_MOCK=1 ARISTOTE_CONFIG=backend/config.dev.toml $(PY) -m aristote.cli serve

test:
	cd backend && ../$(PY) -m pytest -q
	$(PY) -m pytest -q eval/tests

CONFIG ?= eval/configs/exemple.toml
eval:
	$(PY) -m eval.run --config $(CONFIG)

eval-offline:
	$(PY) -m eval.run --offline

eval-compare:
	$(PY) -m eval.report $(A) $(B) -o eval/results/comparaison.md
