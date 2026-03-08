.PHONY: test test-unit test-integration test-e2e lint format run clean

test:
	conda run -n civilization_simulator pytest tests/ -v

test-unit:
	conda run -n civilization_simulator pytest tests/unit/ -v

test-integration:
	conda run -n civilization_simulator pytest tests/integration/ -v

test-e2e:
	conda run -n civilization_simulator pytest tests/e2e/ -v

lint:
	conda run -n civilization_simulator ruff check src/ tests/

format:
	conda run -n civilization_simulator ruff format src/ tests/

run:
	conda run -n civilization_simulator python scripts/run_simulation.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .ruff_cache *.egg-info
