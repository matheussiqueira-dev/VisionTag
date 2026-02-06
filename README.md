# VisionTag

VisionTag é uma plataforma fullstack de visão computacional para detecção de objetos com tags em português, construída para cenários reais de operação com foco em segurança, performance, UX e governança técnica.

## Visão Geral do Projeto

O sistema resolve o problema de classificação visual rápida e estruturada para produtos e operações que precisam transformar imagens em metadados úteis.

Público-alvo:
- times de operação e moderação de conteúdo;
- squads de produto que integram visão computacional em fluxos de negócio;
- engenharia que precisa de API + interface pronta para uso e validação.

Fluxo principal:
1. Upload de imagem, lote de imagens ou URL remota.
2. Validação de entrada e política de segurança.
3. Inferência YOLO com filtros de domínio.
4. Retorno com tags, detecções, métricas e sinalização de cache.
5. Histórico e exploração operacional via UI.

## Arquitetura e Decisões Técnicas

Arquitetura adotada: monólito modular com separação clara entre camadas.

### Backend
- `api.py`: camada HTTP, middleware, contratos e versionamento.
- `services/`: orquestração de aplicação, cache e provider de detecção.
- `detector.py`: domínio de inferência e regras de filtragem.
- `security.py`: autenticação por API key, autorização por escopo e rate-limit.
- `errors.py`: exceções de domínio e handlers globais.
- `telemetry.py`: métricas operacionais e trilha recente de análises.
- `remote_fetch.py`: fetch seguro de imagem remota com proteção SSRF.

### Frontend
- UI modular em ES Modules (`static/js/*`) com separação de estado, API, utilitários e render.
- Design system com tokens, estados e componentes reutilizáveis.
- Fluxos para análise única, lote, URL remota e painel operacional.

Decisões-chave:
- cache de inferência com TTL para reduzir latência em payload repetido;
- semáforo de concorrência para proteger inferência em pico;
- contratos versionados e explicitamente tipados (Pydantic);
- observabilidade embutida com `request_id`, métricas e erros padronizados;
- UX orientada a produtividade (atalhos, presets e persistência de preferências).

## Stack e Tecnologias

### Backend
- Python 3.10+
- FastAPI
- Uvicorn
- Pydantic v2
- Ultralytics YOLOv8
- OpenCV
- NumPy
- httpx

### Frontend
- HTML5 semântico
- CSS3 com design tokens
- JavaScript modular (ES Modules)

### Qualidade
- Pytest

## Funcionalidades Principais

### Frontend
- análise por imagem única, lote e URL;
- presets de inferência;
- filtros de confiança visual;
- delta de tags entre análises;
- histórico local pesquisável;
- exportação JSON;
- atalho de teclado e modal de ajuda;
- painel operacional para métricas (escopo admin).

### Backend
- `POST /api/v1/detect`
- `POST /api/v1/detect/batch`
- `POST /api/v1/detect/url`
- `GET /api/v1/health`
- `GET /api/v1/labels`
- `GET /api/v1/metrics` (admin)
- `GET /api/v1/admin/runtime` (admin)
- `GET /api/v1/admin/cache` (admin)
- `DELETE /api/v1/admin/cache` (admin)
- compatibilidade legada: `POST /detect`

## Segurança, Performance e Confiabilidade

- autenticação por `X-API-Key` ou `Authorization: Bearer`;
- autorização por escopo (`detect`, `admin`);
- rate limit por janela deslizante;
- validação defensiva de uploads (tipo, tamanho, corrupção);
- proteção SSRF para detecção por URL;
- headers de segurança e CSP;
- cache de inferência com flag `cached`;
- middleware com `X-Request-ID`;
- telemetria de requests, erros, latência, cache hits e trilha recente.

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
  remote_fetch.py
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
  test_remote_fetch.py
  test_security.py
  test_utils.py
requirements.txt
requirements-dev.txt
README.md
```

## Instalação, Execução e Deploy

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

### Executar localmente

```bash
uvicorn visiontag.api:app --host 0.0.0.0 --port 8000
```

Acessos:
- Frontend: `http://localhost:8000/`
- Swagger/OpenAPI: `http://localhost:8000/docs`

### Deploy (produção)

```bash
uvicorn visiontag.api:app --host 0.0.0.0 --port 8000 --workers 1
```

Observação: para workloads intensos de inferência, priorize escala horizontal por instância com controle de concorrência por processo.

## Configuração via Ambiente

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
- `VISIONTAG_AUTH_REQUIRED`
- `VISIONTAG_DEFAULT_API_KEY`
- `VISIONTAG_API_KEYS` (`key1:detect|admin,key2:detect`)
- `VISIONTAG_RATE_LIMIT_PER_MINUTE`
- `VISIONTAG_CORS_ORIGINS`
- `VISIONTAG_ENABLE_GZIP`
- `VISIONTAG_LOG_LEVEL`

## Testes e Qualidade

```bash
python -m pytest -q
python -m compileall visiontag tests
```

Cobertura atual contempla:
- contratos de API;
- segurança (auth/escopo/rate-limit);
- serviço de detecção e cache;
- validações de URL remota;
- utilitários centrais.

## Boas Práticas Adotadas

- separação de responsabilidades por camada;
- princípios SOLID e DRY;
- contratos explícitos de API;
- tratamento padronizado de erros;
- observabilidade básica embutida;
- UI com design system e acessibilidade prática.

## Melhorias Futuras

- pipeline assíncrono para processamento massivo;
- integração com Prometheus/OpenTelemetry;
- rotação e gestão externa de segredos (Vault/KMS);
- testes e2e de interface (Playwright);
- persistência de auditoria e histórico em banco.

Autoria: Matheus Siqueira  
Website: https://www.matheussiqueira.dev/
