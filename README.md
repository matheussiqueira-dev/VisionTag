# VisionTag Backend

API de detecção visual orientada a produção, com contratos versionados, segurança por escopo, telemetria operacional e pipeline de inferência com controle de concorrência.

## Visão Geral do Backend

O backend do VisionTag transforma imagens em metadados estruturados (tags e bounding boxes) para fluxos de produto e operação.

Casos de uso:
- análise de imagem única;
- análise em lote;
- análise por URL remota;
- análise por payload base64;
- observabilidade e gestão operacional via endpoints administrativos.

## Arquitetura Adotada

Arquitetura: **monólito modular** com responsabilidades separadas por camada.

- `visiontag/api.py`: camada HTTP, contratos, middlewares e versionamento.
- `visiontag/services/detection_service.py`: orquestração de detecção, cache e telemetria.
- `visiontag/detector.py`: domínio de inferência YOLO e filtros de detecção.
- `visiontag/security.py`: autenticação, autorização por escopo e rate limiting.
- `visiontag/remote_fetch.py`: fetch remoto com hardening SSRF.
- `visiontag/telemetry.py`: métricas operacionais e trilha recente de análises.
- `visiontag/errors.py`: taxonomia de erros e handlers padronizados.

### Decisões Técnicas Relevantes

- inferência executada em thread (`asyncio.to_thread`) para não bloquear o event loop;
- limite de concorrência por semáforo (`max_concurrent_inference`);
- timeout de inferência configurável (`inference_timeout_seconds`);
- contratos explícitos com Pydantic para respostas e requests;
- cache por hash de payload + opções (TTL e capacidade configuráveis);
- rastreabilidade via `X-Request-ID`.

## Tecnologias Utilizadas

- Python 3.10+
- FastAPI
- Pydantic v2
- Uvicorn
- Ultralytics YOLOv8
- OpenCV
- NumPy
- httpx
- Pytest

## Endpoints da API

### Core de Detecção
- `POST /api/v1/detect` (multipart upload)
- `POST /api/v1/detect/batch` (multipart múltiplo)
- `POST /api/v1/detect/url` (URL remota)
- `POST /api/v1/detect/base64` (payload base64)
- `POST /detect` (legado)

### Catálogo e Saúde
- `GET /api/v1/health`
- `GET /api/v1/labels`

### Operação/Admin
- `GET /api/v1/metrics`
- `GET /api/v1/admin/runtime`
- `GET /api/v1/admin/recent`
- `GET /api/v1/admin/overview`
- `GET /api/v1/admin/cache`
- `DELETE /api/v1/admin/cache`

## Segurança e Confiabilidade

### Autenticação e Autorização
- API key via `X-API-Key` ou `Authorization: Bearer`.
- Escopos suportados:
  - `detect`
  - `admin`
- Rate limit por identidade com janela deslizante.
- Header `Retry-After` em resposta `429`.

### Hardening de Entrada
- validação de tipo e tamanho de upload;
- validação de payload base64 (incluindo Data URL);
- proteção SSRF em URL remota:
  - bloqueio de hosts locais e IPs privados/reservados;
  - validação de portas (80/443);
  - validação de cadeia de redirecionamentos;
  - resolução DNS com bloqueio de destino interno.

### Tratamento de Erros
- erros de domínio padronizados (`error.code`, `request_id`, `details`);
- timeout de inferência com erro explícito (`processing_timeout`);
- fallback seguro para exceções não tratadas.

## Observabilidade

Métricas disponíveis:
- total de requests, erros, detecções e cache hits;
- latência média, p95 e p99;
- requests por rota;
- requests por classe de status (`2xx`, `4xx`, `5xx`);
- visão consolidada em `/api/v1/admin/overview`.

## Setup e Execução

### Pré-requisitos
- Python 3.10+

### Instalação
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Execução
```bash
uvicorn visiontag.api:app --host 0.0.0.0 --port 8000
```

### Acessos
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

## Configuração por Variáveis de Ambiente

- `VISIONTAG_APP_NAME`
- `VISIONTAG_APP_VERSION`
- `VISIONTAG_MODEL_PATH`
- `VISIONTAG_MAX_UPLOAD_MB`
- `VISIONTAG_MAX_REMOTE_IMAGE_MB`
- `VISIONTAG_REMOTE_FETCH_TIMEOUT_SECONDS`
- `VISIONTAG_MAX_DIMENSION`
- `VISIONTAG_MAX_BATCH_FILES`
- `VISIONTAG_CACHE_TTL_SECONDS`
- `VISIONTAG_CACHE_MAX_ITEMS`
- `VISIONTAG_MAX_CONCURRENT_INFERENCE`
- `VISIONTAG_INFERENCE_TIMEOUT_SECONDS`
- `VISIONTAG_AUTH_REQUIRED`
- `VISIONTAG_DEFAULT_API_KEY`
- `VISIONTAG_API_KEYS` (ex.: `key1:detect|admin,key2:detect`)
- `VISIONTAG_RATE_LIMIT_PER_MINUTE`
- `VISIONTAG_CORS_ORIGINS`
- `VISIONTAG_ENABLE_GZIP`
- `VISIONTAG_LOG_LEVEL`

## Estrutura do Projeto

```text
visiontag/
  api.py
  config.py
  detector.py
  errors.py
  logging_config.py
  remote_fetch.py
  schemas.py
  security.py
  telemetry.py
  utils.py
  services/
    detection_service.py
tests/
  test_api_backend.py
  test_detection_service.py
  test_remote_fetch.py
  test_security.py
  test_utils.py
```

## Boas Práticas e Padrões

- SOLID/DRY na separação de responsabilidades;
- contratos de API tipados e versionados;
- validação defensiva de entradas;
- telemetria operacional embutida;
- tratamento padronizado de falhas;
- testes automatizados para contratos e segurança.

## Testes

```bash
python -m pytest -q
```

## Melhorias Futuras

- métricas nativas em formato Prometheus/OpenTelemetry;
- fila assíncrona para processamento massivo;
- trilha de auditoria persistida em banco;
- rotação de segredos integrada (Vault/KMS);
- testes de carga com perfis de concorrência.

Autoria: Matheus Siqueira  
Website: https://www.matheussiqueira.dev/
