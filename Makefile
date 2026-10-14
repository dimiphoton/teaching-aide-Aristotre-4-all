VENV ?= backend/.venv
PY := $(VENV)/bin/python

.PHONY: venv test dev-diag

venv:
	python3 -m venv $(VENV)
	$(PY) -m pip install -e "backend[dev]"

test:
	cd backend && ../$(PY) -m pytest -q

# Diagnostic du matériel simulé (aucun périphérique requis)
dev-diag:
	ARISTOTE_MOCK=1 $(PY) -m aristote.cli diag printer
