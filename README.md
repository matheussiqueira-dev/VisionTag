# VisionTag

VisionTag é uma plataforma fullstack de detecção visual com foco em qualidade de engenharia, segurança operacional e experiência de uso. O projeto combina API versionada com interface web moderna para análise de imagem única, lote e URL remota.

## Visão Geral

### Propósito
Transformar imagens em dados acionáveis (tags e detecções) para fluxos de produto, operação, moderação e automação.

### Público-alvo
- Times de produto e operações que precisam de classificação visual rápida.
- Equipes de engenharia que desejam API robusta com frontend pronto para uso.
- Cenários de validação técnica e prototipação com YOLOv8.

### Fluxo principal
1. Usuário envia imagem local, lote ou URL remota.
2. Backend valida entrada (tipo, tamanho e políticas de segurança).
3. Inferência executa com filtros configuráveis.
4. API retorna contrato estruturado com detecções e métricas.
5. Frontend apresenta resultado, histórico local e painel operacional.

## Arquitetura e Decisões Técnicas

Arquitetura adotada: **monólito modular** com separação clara por responsabilidades.

- `visiontag/api.py`: camada HTTP, contratos, middlewares e endpoints versionados.
- `visiontag/services/detection_service.py`: orquestração de detecção, cache e telemetria.
- `visiontag/detector.py`: domínio de inferência YOLO e regras de filtragem.
- `visiontag/security.py`: autenticação, autorização por escopo e rate limiting.
- `visiontag/remote_fetch.py`: fetch remoto seguro com proteção SSRF.
- `visiontag/telemetry.py`: métricas operacionais e trilha recente de análises.
- `visiontag/static/*`: frontend modular (estado, API client, renderização e UX).

Decisões-chave implementadas:
- Inferência síncrona movida para `asyncio.to_thread` no backend para evitar bloqueio do event loop.
- Processamento de lote com concorrência controlada por semáforo (`max_concurrent_inference`).
- Endpoint consolidado `GET /api/v1/admin/overview` para dashboard operacional completo.
- Cache de inferência com TTL e limite de itens.
- Segurança por API key + escopos (`detect`, `admin`) e rate limit por janela deslizante.

## Tecnologias Utilizadas

### Backend
- Python 3.10+
- FastAPI
- Pydantic v2
- Uvicorn
- Ultralytics YOLOv8
- OpenCV
- NumPy
- httpx

### Frontend
- HTML5 semântico
- CSS3 com design tokens e estados reutilizáveis
- JavaScript ES Modules

### Qualidade
- Pytest

## Funcionalidades Principais

### API
- `POST /api/v1/detect` (imagem única)
- `POST /api/v1/detect/batch` (lote)
- `POST /api/v1/detect/url` (imagem por URL)
- `GET /api/v1/health`
- `GET /api/v1/labels`
- `GET /api/v1/metrics` (admin)
- `GET /api/v1/admin/runtime` (admin)
- `GET /api/v1/admin/recent` (admin)
- `GET /api/v1/admin/overview` (admin, consolidado)
- `GET /api/v1/admin/cache` (admin)
- `DELETE /api/v1/admin/cache` (admin)
- `POST /detect` (compatibilidade legada)

### Frontend
- Modo imagem única e lote.
- Análise por URL remota.
- Presets de inferência.
- Filtros de labels (`include_labels` e `exclude_labels`).
- Histórico local pesquisável e exportação JSON.
- Painel operacional com visão consolidada:
  - métricas,
  - runtime,
  - atividade recente,
  - limpeza de cache via UI.
- Atalhos de teclado e feedback visual de status.

## Segurança, Performance e Escalabilidade

### Segurança
- Autenticação por `X-API-Key` ou `Authorization: Bearer`.
- Autorização por escopos.
- Rate limit por identidade.
- Validação rígida de upload.
- Proteção contra SSRF no fetch remoto (incluindo cadeia de redirecionamentos).
- Headers de segurança e CSP.

### Performance
- Inferência executada fora do loop assíncrono (`to_thread`).
- Lote processado em paralelo com limite configurável.
- Cache de resultados por hash de payload + opções.
- Compressão HTTP opcional (`GZipMiddleware`).

### Manutenibilidade
- Contratos tipados e versionados.
- Separação por camadas com baixo acoplamento.
- Testes cobrindo API, segurança, serviço e utilitários.

## Instalação e Uso

### Pré-requisitos
- Python 3.10+

### Setup
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Executar
```bash
uvicorn visiontag.api:app --host 0.0.0.0 --port 8000
```

Acessos:
- Frontend: `http://localhost:8000/`
- Docs: `http://localhost:8000/docs`

### Testes
```bash
python -m pytest -q
```

## Configuração por Ambiente

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
- `VISIONTAG_API_KEYS` (ex.: `key1:detect|admin,key2:detect`)
- `VISIONTAG_RATE_LIMIT_PER_MINUTE`
- `VISIONTAG_CORS_ORIGINS`
- `VISIONTAG_ENABLE_GZIP`
- `VISIONTAG_LOG_LEVEL`

## Estrutura do Projeto

```text
visiontag/
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
README.md
requirements.txt
requirements-dev.txt
```

## Boas Práticas Adotadas

- SOLID e DRY na organização de responsabilidades.
- Contratos explícitos de API com validação forte.
- Tratamento padronizado de erros.
- Observabilidade com métricas, request ID e trilha recente.
- Interface acessível, responsiva e orientada a operação.

## Possíveis Melhorias Futuras

- Métricas Prometheus/OpenTelemetry nativas.
- Fila assíncrona para processamento massivo.
- Persistência de auditoria em banco.
- Testes e2e de frontend (Playwright).
- Deploy com autoscaling horizontal e gateway dedicado.

Autoria: Matheus Siqueira  
Website: https://www.matheussiqueira.dev/
