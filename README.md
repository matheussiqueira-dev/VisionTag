# VisionTag Backend

Backend de visão computacional para detecção de objetos com tags em português, preparado para uso em produção com foco em segurança, observabilidade, escalabilidade e contratos de API consistentes.

## Visão Geral do Backend

O domínio principal do sistema é transformar imagens em metadados acionáveis:
- detecção de objetos,
- tradução de classes para português,
- resposta estruturada para integrações operacionais.

Fluxo de negócio principal:
1. Cliente envia imagem (single ou batch).
2. API valida tipo, tamanho e integridade.
3. Serviço de detecção processa via YOLO.
4. Resultado é filtrado por regras (confiança, área, inclusão/exclusão de labels).
5. API retorna contrato estruturado com tags, detecções e métricas.

## Arquitetura Adotada

A arquitetura segue modelo modular monolítico com separação por camadas:

- `api.py`: camada HTTP (roteamento, middleware, contratos).
- `services/`: aplicação e regras de orquestração (`DetectionService`, cache, provider).
- `detector.py`: domínio de inferência e normalização de opções.
- `security.py`: autenticação por API key, autorização por escopo e rate limiting.
- `errors.py`: exceções de domínio e handlers globais padronizados.
- `telemetry.py`: métricas operacionais em memória.
- `config.py`: configuração centralizada via ambiente.
- `schemas.py`: contratos Pydantic para request/response.
- `utils.py`: utilitários transversais (imagem, labels, sanitização).

Decisões arquiteturais principais:
- lazy loading do modelo para reduzir custo de startup;
- cache de inferência com TTL para reduzir latência em payloads repetidos;
- middleware com `request_id`, headers de segurança e métricas por request;
- autenticação/escopo desacoplados da camada HTTP.

## Tecnologias Utilizadas

- Python 3.10+
- FastAPI
- Uvicorn
- Pydantic v2
- Ultralytics YOLOv8
- OpenCV
- NumPy
- Pytest

## Segurança e Confiabilidade

Implementações aplicadas:
- Autenticação por `X-API-Key` (ou `Authorization: Bearer ...`).
- Autorização por escopo (`detect`, `admin`).
- Rate limit em janela deslizante por identidade/cliente.
- Validação defensiva de upload:
  - MIME permitido,
  - limite de tamanho,
  - arquivo vazio e corrupção.
- Headers de segurança:
  - `X-Content-Type-Options`,
  - `X-Frame-Options`,
  - `Referrer-Policy`,
  - `Permissions-Policy`,
  - `Content-Security-Policy`.
- Tratamento global de exceções com payload padronizado (`error.code`, `error.message`, `request_id`).
- Telemetria de requests, erros, latência média, detecções e cache hits.

## Novas Features Implementadas

1. Filtro avançado por labels
- parâmetros `include_labels` e `exclude_labels` no contrato de detecção.
- impacto: permite cenários de negócio específicos (ex.: monitorar apenas classes críticas).

2. Cache de inferência com TTL
- cache por hash do payload + opções de detecção.
- campo `cached` no retorno.
- impacto: menor latência e menor custo computacional em entradas repetidas.

3. Endpoints administrativos
- métricas operacionais (`/api/v1/metrics`),
- runtime settings (`/api/v1/admin/runtime`),
- gestão de cache (`/api/v1/admin/cache`).
- impacto: suporte a operação, troubleshooting e governança em produção.

## API e Contratos

### Endpoints principais
- `POST /api/v1/detect`
- `POST /api/v1/detect/batch`
- `GET /api/v1/health`
- `GET /api/v1/labels`

### Endpoints administrativos (escopo `admin`)
- `GET /api/v1/metrics`
- `GET /api/v1/admin/runtime`
- `GET /api/v1/admin/cache`
- `DELETE /api/v1/admin/cache`

### Compatibilidade legada
- `POST /detect` (retorna apenas `tags`)

### Parâmetros de detecção
- `conf`
- `max_tags`
- `min_area`
- `include_person`
- `include_labels`
- `exclude_labels`

## Setup e Execução

### 1. Instalação

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Rodar aplicação

```bash
uvicorn visiontag.api:app --host 0.0.0.0 --port 8000
```

Acessos:
- API docs: `http://localhost:8000/docs`
- UI local: `http://localhost:8000/`

## Variáveis de Ambiente

- `VISIONTAG_APP_NAME`
- `VISIONTAG_APP_VERSION`
- `VISIONTAG_MODEL_PATH`
- `VISIONTAG_MAX_UPLOAD_MB`
- `VISIONTAG_MAX_DIMENSION`
- `VISIONTAG_MAX_BATCH_FILES`
- `VISIONTAG_CACHE_TTL_SECONDS`
- `VISIONTAG_CACHE_MAX_ITEMS`
- `VISIONTAG_AUTH_REQUIRED`
- `VISIONTAG_DEFAULT_API_KEY`
- `VISIONTAG_API_KEYS` (formato: `key1:detect|admin,key2:detect`)
- `VISIONTAG_RATE_LIMIT_PER_MINUTE`
- `VISIONTAG_LOG_LEVEL`

## Estrutura do Projeto

```text
visiontag/
  __init__.py
  api.py
  cli.py
  config.py
  detector.py
  errors.py
  labels_pt.py
  logging_config.py
  schemas.py
  security.py
  telemetry.py
  utils.py
  services/
    __init__.py
    detection_service.py
  static/
    index.html
    styles.css
    js/
      app.js
      api.js
      constants.js
      helpers.js
      storage.js
      ui.js
tests/
  test_api_backend.py
  test_detection_service.py
  test_security.py
  test_utils.py
requirements.txt
requirements-dev.txt
```

## Testes e Qualidade

Execução:

```bash
python -m pytest -q
python -m compileall visiontag tests
```

Cobertura atual inclui:
- contratos da API,
- autenticação/autorização,
- rate limiting,
- cache de detecção,
- utilitários de imagem e sanitização.

## Boas Práticas e Padrões Aplicados

- SOLID e separação por responsabilidade.
- DRY para validações e contratos compartilhados.
- Tipagem explícita e contratos Pydantic.
- Tratamento padronizado de erros com rastreabilidade.
- Observabilidade orientada a operação.
- Código preparado para evolução incremental.

## Melhorias Futuras

- Persistência de telemetria em Prometheus/OpenTelemetry.
- Autenticação com rotação de chaves e storage externo (Vault/KMS).
- Filas assíncronas para processamento massivo.
- Testes de carga e SLOs formais de latência.
- Política de quotas por tenant e auditoria por consumidor.

Autoria: Matheus Siqueira  
Website: https://www.matheussiqueira.dev/
