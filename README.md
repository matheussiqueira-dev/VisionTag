# VisionTag

VisionTag é uma plataforma fullstack de detecção visual que combina backend robusto (FastAPI + YOLO) com frontend operacional de alto nível para análise de imagens em tempo real.

O projeto foi estruturado para cenários de produção com foco em:
- segurança,
- performance,
- observabilidade,
- UX/UI moderna,
- manutenção evolutiva.

## Visão Geral do Projeto

### Propósito
Transformar imagens em dados úteis para operações digitais, produtos e fluxos automatizados, retornando:
- tags em português,
- detecções com bounding box,
- métricas operacionais para governança técnica.

### Público-alvo
- times de operação e moderação;
- squads de produto com uso de visão computacional;
- engenharia que precisa de API + interface web pronta para uso.

### Fluxo principal
1. Usuário envia imagem por upload, URL, base64 ou lote.
2. Backend valida entrada e aplica políticas de segurança.
3. Serviço de detecção executa inferência YOLO com filtros configuráveis.
4. API retorna contrato tipado e rastreável.
5. Frontend renderiza resultado, insights, histórico local e painel operacional.

## Arquitetura e Decisões Técnicas

Arquitetura adotada: **monólito modular** com separação clara de camadas.

### Backend
- `visiontag/api.py`: camada HTTP, middleware, contratos, versionamento e composição de serviços.
- `visiontag/services/detection_service.py`: orquestração de inferência, cache e telemetria de análise.
- `visiontag/services/admin_service.py`: agregação de métricas e visão administrativa.
- `visiontag/detector.py`: domínio de inferência e filtros de detecção.
- `visiontag/security.py`: autenticação por API key, autorização por escopo e rate limit.
- `visiontag/remote_fetch.py`: download remoto com hardening SSRF.
- `visiontag/errors.py`: taxonomia de erros e respostas padronizadas.
- `visiontag/telemetry.py`: snapshot operacional, percentis de latência e trilha recente.

### Frontend
- `visiontag/static/js/app.js`: estado, fluxo da aplicação e eventos.
- `visiontag/static/js/ui.js`: renderização e manipulação de DOM.
- `visiontag/static/js/api.js`: cliente HTTP para endpoints versionados.
- `visiontag/static/js/storage.js`: persistência local de histórico/preferências/presets.
- `visiontag/static/js/helpers.js`: utilitários puros (debounce, insights, formatação).
- `visiontag/static/styles.css`: design system via tokens e estados visuais.

### Decisões arquiteturais-chave
- inferência executada com `asyncio.to_thread` para preservar o event loop;
- timeout de inferência configurável (`VISIONTAG_INFERENCE_TIMEOUT_SECONDS`);
- concorrência controlada por semáforos (inferência e fetch remoto);
- contratos Pydantic explícitos para estabilidade de integração;
- cache de resultados por hash de payload + opções;
- observabilidade com `X-Request-ID`, latência média/p95/p99 e distribuição por status class.

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
- JavaScript ES Modules

### Qualidade
- Pytest

## Funcionalidades Principais

### API de Detecção
- `POST /api/v1/detect` (upload único)
- `POST /api/v1/detect/batch` (lote por arquivos)
- `POST /api/v1/detect/url` (imagem remota)
- `POST /api/v1/detect/url/batch` (lote por URLs)
- `POST /api/v1/detect/base64` (payload base64)
- `POST /detect` (compatibilidade legada)

### API Operacional/Admin
- `GET /api/v1/health`
- `GET /api/v1/labels`
- `GET /api/v1/metrics`
- `GET /api/v1/admin/runtime`
- `GET /api/v1/admin/recent`
- `GET /api/v1/admin/overview`
- `GET /api/v1/admin/cache`
- `DELETE /api/v1/admin/cache`

### Frontend (UX/UI)
- análise única, lote por arquivos e lote por URLs;
- presets rápidos + presets personalizados persistentes;
- filtros avançados (confiança, área mínima, include/exclude labels);
- insights visuais de detecção (KPIs e distribuição por label);
- histórico local com busca;
- exportação JSON;
- painel operacional consolidado (métricas, runtime e atividade recente);
- controles de acessibilidade (alto contraste e modo compacto);
- atalhos de teclado para produtividade.

## Segurança, Performance e Confiabilidade

### Segurança
- autenticação por `X-API-Key` ou `Authorization: Bearer`;
- autorização por escopos (`detect`, `admin`);
- rate limit com retorno de `Retry-After` em `429`;
- validação forte de uploads e payload base64;
- proteção SSRF para URLs remotas:
  - bloqueio de hosts locais/privados/reservados,
  - restrição de portas (80/443),
  - validação de redirecionamentos,
  - validação de resolução DNS.

### Performance e Escalabilidade
- pipeline de inferência com timeout e concorrência controlada;
- processamento concorrente em lotes;
- cache com TTL e capacidade máxima configuráveis;
- compressão GZip opcional para respostas.

### Confiabilidade e Observabilidade
- erros padronizados com `error.code`, `request_id` e `details`;
- percentis p95/p99 de latência;
- métricas por rota e por classe de status (`2xx`, `4xx`, `5xx`);
- trilha recente de análises para suporte operacional.

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
    admin_service.py
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
  test_admin_service.py
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

### Execução local
```bash
uvicorn visiontag.api:app --host 0.0.0.0 --port 8000
```

Acessos:
- Frontend: `http://localhost:8000/`
- Docs OpenAPI: `http://localhost:8000/docs`

### Deploy
```bash
uvicorn visiontag.api:app --host 0.0.0.0 --port 8000 --workers 1
```

Observação: para cargas elevadas de inferência, prefira escala horizontal com tuning de concorrência por instância.

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
- `VISIONTAG_MAX_CONCURRENT_REMOTE_FETCH`
- `VISIONTAG_INFERENCE_TIMEOUT_SECONDS`
- `VISIONTAG_AUTH_REQUIRED`
- `VISIONTAG_DEFAULT_API_KEY`
- `VISIONTAG_API_KEYS` (ex.: `key1:detect|admin,key2:detect`)
- `VISIONTAG_RATE_LIMIT_PER_MINUTE`
- `VISIONTAG_CORS_ORIGINS`
- `VISIONTAG_ENABLE_GZIP`
- `VISIONTAG_LOG_LEVEL`

## Testes e Qualidade

```bash
python -m pytest -q
python -m compileall visiontag tests
node --check visiontag/static/js/app.js
node --check visiontag/static/js/ui.js
node --check visiontag/static/js/api.js
```

## Boas Práticas Adotadas

- separação de responsabilidades e baixo acoplamento;
- contratos de API estáveis e tipados;
- validação defensiva de entradas;
- observabilidade operacional embutida;
- UI orientada a produtividade com acessibilidade prática;
- código legível, testável e evolutivo.

## Melhorias Futuras

- integração nativa com Prometheus/OpenTelemetry;
- fila assíncrona para processamento massivo;
- persistência de auditoria em banco;
- testes e2e de interface (Playwright);
- suporte multi-tenant com políticas de quota por chave.

Autoria: Matheus Siqueira  
Website: https://www.matheussiqueira.dev/
