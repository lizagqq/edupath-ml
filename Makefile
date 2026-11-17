PYTHON ?= python3
.PHONY: build test evaluate api ui fallback
build:
	$(PYTHON) scripts/build_project.py
test:
	$(PYTHON) -m unittest discover -s tests -v
evaluate:
	$(PYTHON) scripts/evaluate_system.py
api:
	$(PYTHON) -m uvicorn src.api.app:app --reload --host 127.0.0.1 --port 8000
ui:
	$(PYTHON) -m streamlit run ui/app.py
fallback:
	$(PYTHON) scripts/smoke_server.py
