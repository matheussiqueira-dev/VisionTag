.PHONY: install dev test lint run-api help

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --cov=visiontag --cov-report=term-missing

test-fast:
	pytest tests/ -v -x

lint:
	python -m py_compile visiontag/*.py && echo "Syntax OK"

run-api:
	uvicorn visiontag.api:app --host 0.0.0.0 --port 8000 --reload

help:
	@echo "Comandos disponíveis:"
	@echo "  make install   - Instala o pacote"
	@echo "  make dev       - Instala com dependências de desenvolvimento"
	@echo "  make test      - Executa testes com cobertura"
	@echo "  make test-fast - Executa testes (para no primeiro erro)"
	@echo "  make lint      - Verifica sintaxe"
	@echo "  make run-api   - Inicia a API em modo desenvolvimento"
