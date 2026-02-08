# VisionTag 2.0
Plataforma de visão computacional para detecção de objetos com tags em português, com API versionada, CLI robusta e interface web moderna.

## Visão Geral
O VisionTag é voltado para produtos que precisam classificar elementos visuais com baixo atrito operacional:
- automação de catálogo (e-commerce)
- moderação e organização de mídia
- enriquecimento de metadados para pipelines de IA
- prototipagem rápida de features de visão computacional

## Arquitetura e Decisões Técnicas
O projeto foi refatorado para uma estrutura em camadas (Clean Architecture pragmática):
- `core`: contratos, exceções, modelos e configurações
- `services`: regras de negócio de extração e filtragem de tags
- `infrastructure`: adaptadores de IO e detector YOLO
- `interfaces`: API FastAPI, CLI e frontend web

Princípios aplicados:
- SOLID: separação de responsabilidades por camada
- DRY: centralização das regras de validação e filtragem
- compatibilidade retroativa: `visiontag.api:app` e `python -m visiontag.cli` preservados

## Stack
- Python 3.10+
- FastAPI + Uvicorn
- Ultralytics YOLOv8
- OpenCV + NumPy
- Frontend estático (HTML/CSS/JS)
- Testes com `unittest` + `fastapi.testclient`

## Estrutura do Projeto
```text
visiontag/
  core/
  services/
  infrastructure/
  interfaces/
    api/
    cli/
    web/static/
  api.py
  cli.py
  detector.py
tests/
README.md
requirements.txt
```

## Instalação
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## Execução
### API
```bash
uvicorn visiontag.api:app --host 0.0.0.0 --port 8000
```

Principais endpoints:
- `GET /health`
- `GET /api/v1/config`
- `POST /api/v1/detect`
- `POST /api/v1/detect/batch`
- `POST /detect` (compatibilidade legada)

UI web:
- acesse `http://localhost:8000/`

### CLI
Imagem única:
```bash
python -m visiontag.cli --source C:\caminho\imagem.jpg --include-details
```

Diretório (novo):
```bash
python -m visiontag.cli --source C:\dataset\imagens --recursive --pretty
```

Webcam:
```bash
python -m visiontag.cli --webcam 0 --show --stride 2
```

## Variáveis de Ambiente
- `VISIONTAG_MODEL` (default: `yolov8n.pt`)
- `VISIONTAG_API_KEY` (quando definido, exige header `X-API-Key`)
- `VISIONTAG_MAX_UPLOAD_MB` (default: `10`)
- `VISIONTAG_MAX_BATCH_FILES` (default: `10`)
- `VISIONTAG_DEFAULT_CONF` (default: `0.7`)
- `VISIONTAG_DEFAULT_MAX_TAGS` (default: `5`)
- `VISIONTAG_DEFAULT_MIN_AREA` (default: `0.01`)
- `VISIONTAG_DEFAULT_INCLUDE_PERSON` (default: `false`)
- `VISIONTAG_CORS_ORIGINS` (CSV opcional)

## Segurança, Performance e Qualidade
- validação forte de parâmetros e limites de entrada
- validação de tipo e tamanho de upload
- autenticação opcional por API key
- tratamento padronizado de erros e respostas
- logs de observabilidade com `request_id` e latência
- lock no detector para reduzir risco em concorrência de inferência
- testes automatizados para regras de negócio e API

## Exemplos de API
Detecção simples:
```bash
curl -X POST "http://localhost:8000/api/v1/detect?include_details=true" \
  -H "X-API-Key: SUA_CHAVE" \
  -F "file=@imagem.jpg"
```

Detecção em lote:
```bash
curl -X POST "http://localhost:8000/api/v1/detect/batch" \
  -H "X-API-Key: SUA_CHAVE" \
  -F "files=@img1.jpg" \
  -F "files=@img2.jpg"
```

## Testes
```bash
python -m unittest discover -s tests -v
```

## Deploy (Produção)
Sugestão mínima:
- containerizar com imagem Python slim
- executar `uvicorn visiontag.api:app --host 0.0.0.0 --port 8000 --workers 2`
- usar reverse proxy (Nginx/Traefik) com TLS
- configurar `VISIONTAG_API_KEY` e limites de upload
- monitorar logs e métricas de latência/erros

## Melhorias Futuras
- autenticação OAuth2/JWT para cenários multiusuário
- filas assíncronas para lotes grandes
- persistência de histórico de inferências
- suporte a modelos customizados e versionamento por tenant
- pipeline de CI/CD com lint, testes e scan de segurança

Autoria: Matheus Siqueira  
Website: https://www.matheussiqueira.dev/
