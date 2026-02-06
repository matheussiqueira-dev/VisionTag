# VisionTag

VisionTag é uma plataforma de visão computacional para detecção de objetos e geração de tags em português, projetada para uso em automações, triagem de conteúdo visual e sistemas de apoio operacional.

A solução foi evoluída para um padrão de produção com:
- API versionada e validada
- CLI com modo imagem, webcam e lote
- Interface web moderna e responsiva
- Respostas detalhadas (tags, bounding boxes e tempo de inferência)

## Visão Geral do Projeto

O fluxo principal do VisionTag:
1. Usuário envia imagem (UI web, CLI ou API).
2. O sistema valida o arquivo (tipo, tamanho e integridade).
3. O modelo YOLO processa a imagem com parâmetros ajustáveis.
4. As classes detectadas são traduzidas para português e normalizadas.
5. A aplicação retorna tags, detecções e métricas de inferência.

Público-alvo:
- Produtos que precisam de classificação visual rápida.
- Equipes de operação que demandam tagging automático.
- Desenvolvedores que querem integrar visão computacional com API simples.

## Tecnologias Utilizadas

- Python 3.10+
- FastAPI
- Uvicorn
- Ultralytics YOLOv8
- OpenCV
- NumPy
- HTML, CSS e JavaScript (UI web)

## Funcionalidades Principais

- Detecção de objetos com tags em português
- Exclusão opcional de `pessoa` para cenários mais restritos
- Filtros por confiança mínima, área mínima e máximo de tags
- Resposta detalhada com bounding boxes e confiança
- Endpoint batch para múltiplas imagens
- Endpoint de saúde (`/api/v1/health`) e catálogo de labels (`/api/v1/labels`)
- Interface web com:
  - Drag-and-drop
  - Pré-visualização da imagem
  - Ajuste de parâmetros em tempo real
  - Histórico local de análises
  - Métricas de inferência
- CLI com:
  - `--source` (imagem)
  - `--source-dir` (lote)
  - `--webcam` (stream)
  - `--details` e `--save-json`

## Instalação e Uso

### 1. Instalação

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Executar API + UI Web

```bash
uvicorn visiontag.api:app --host 0.0.0.0 --port 8000
```

Acesse:
- UI: `http://localhost:8000/`
- Swagger: `http://localhost:8000/docs`

### 3. Uso via CLI

Imagem única:
```bash
python -m visiontag.cli --source C:\caminho\imagem.jpg --details
```

Diretório (lote):
```bash
python -m visiontag.cli --source-dir C:\caminho\imagens --details --save-json output\relatorio.json
```

Webcam:
```bash
python -m visiontag.cli --webcam 0 --show --stride 2
```

### 4. Endpoints da API

- `POST /api/v1/detect`
- `POST /api/v1/detect/batch`
- `GET /api/v1/health`
- `GET /api/v1/labels`
- Compatibilidade legada: `POST /detect`

Exemplo de retorno (`/api/v1/detect`):

```json
{
  "tags": ["mesa", "livro"],
  "detections": [
    {
      "label": "mesa",
      "confidence": 0.92,
      "bbox": {"x1": 42.1, "y1": 90.3, "x2": 420.4, "y2": 310.6}
    }
  ],
  "total_detections": 1,
  "inference_ms": 84.77
}
```

## Variáveis de Ambiente

- `VISIONTAG_MODEL_PATH` (default: `yolov8n.pt`)
- `VISIONTAG_MAX_UPLOAD_MB` (default: `8`)
- `VISIONTAG_MAX_DIMENSION` (default: `1280`)
- `VISIONTAG_MAX_BATCH_FILES` (default: `10`)

## Estrutura do Projeto

```text
visiontag/
  __init__.py
  api.py
  cli.py
  detector.py
  labels_pt.py
  schemas.py
  utils.py
  static/
    index.html
    styles.css
    app.js
requirements.txt
README.md
```

## Boas Práticas Aplicadas

- Tipagem e contratos explícitos (schemas e dataclasses)
- Separação de responsabilidades (detecção, validação, API, UI)
- Validação defensiva de uploads (MIME, tamanho, corrupção)
- Cache de modelo para reduzir custo de inicialização
- Compatibilidade retroativa no endpoint legado
- Interface com foco em clareza visual, acessibilidade e responsividade

## Possíveis Melhorias Futuras

- Autenticação (JWT/API Key) e rate limiting
- Fila assíncrona para processamento massivo
- Persistência de histórico em banco (PostgreSQL)
- Exportação de relatórios CSV/Parquet
- Observabilidade com métricas Prometheus e tracing
- Suporte a múltiplos modelos e rotas de inferência por domínio

Autoria: Matheus Siqueira  
Website: https://www.matheussiqueira.dev/
