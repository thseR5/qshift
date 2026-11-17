BOOTSTRAP_PYTHON ?= python3.11
PYTHON ?= .venv/bin/python
PIP = $(PYTHON) -m pip

.PHONY: setup run run-whatsapp-pilot whatsapp-test migrate test lint eval eval-live eval-forensics diagnose-generation demo webhook-demo client-demo studio clean-demo
setup:
	$(BOOTSTRAP_PYTHON) -m venv .venv
	$(PIP) install -e '.[dev]'

run:
	$(PYTHON) -m uvicorn qshift.api.main:app --reload

run-whatsapp-pilot:
	$(PYTHON) -m uvicorn qshift.whatsapp_pilot:create_app --factory --host 127.0.0.1 --port 8765 --no-access-log

whatsapp-test:
	$(PYTHON) scripts/whatsapp_test.py

migrate:
	$(PYTHON) -m alembic upgrade head

test:
	$(PYTHON) -m pytest --cov=qshift.engine --cov=qshift.approval --cov-report=term-missing

lint:
	$(PYTHON) -m ruff check qshift tests evals scripts
	$(PYTHON) -m mypy qshift/engine qshift/approval

eval:
	$(PYTHON) -m evals.run_eval

eval-live:
	$(PYTHON) -m evals.run_live_eval

eval-forensics:
	$(PYTHON) -m evals.run_forensics

diagnose-generation:
	$(PYTHON) -m evals.run_generation_diagnostics

demo:
	$(PYTHON) -m qshift.demo

webhook-demo:
	$(PYTHON) -m qshift.whatsapp_rehearsal

client-demo:
	$(PYTHON) -m qshift.simulated_client_demo --port $(or $(PORT),8078)

studio:
	$(PYTHON) -m qshift.studio_server

clean-demo:
	rm -f qshift.db
	rm -rf demo-output

