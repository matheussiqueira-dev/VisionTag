<div align="center">

# VisionTag

**Detecção de objetos em tempo real com tags em português**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-ultralytics-purple)](https://github.com/ultralytics/ultralytics)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## Visão Geral

**VisionTag** é um sistema de visão computacional que analisa imagens, vídeos e streams de webcam em tempo real, identificando objetos com alta confiança e retornando **tags em português**. Construído sobre [YOLOv8](https://github.com/ultralytics/ultralytics) e [FastAPI](https://fastapi.tiangolo.com/), oferece uma interface de linha de comando e uma API REST.

### Destaques

- Detecção via YOLOv8 com limiar de confiança configurável
- Saída em JSON com tags e metadados de detecção (confiança + bbox)
- Suporte a imagens, vídeos e webcam via CLI
- Exportação de imagem/vídeo anotados com `--output`
- API REST com endpoints `/detect`, `/health` e `/info`
- Configuração por variáveis de ambiente
- Testes unitários e de integração com `pytest`

---

## Arquitetura

```
visiontag/
├── config.py      # VisionTagConfig: defaults, validação e env vars
├── detector.py    # VisionTagger: lógica de detecção YOLOv8
├── labels_pt.py   # Mapeamento COCO → português (80 classes)
├── cli.py         # Entrypoint de linha de comando
└── api.py         # API REST com FastAPI

tests/
├── test_config.py
├── test_labels.py
├── test_detector.py
└── test_api.py
```

---

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/matheussiqueira-dev/VisionTag.git
cd VisionTag

# 2. Crie e ative o ambiente virtual
python -m venv .venv
# Linux/Mac:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# 3. Instale o pacote
pip install -e .

# Para desenvolvimento (inclui pytest, httpx, coverage):
pip install -e ".[dev]"
```

> O modelo `yolov8n.pt` (~6 MB) é baixado automaticamente na primeira execução.

---

## Uso — CLI

### Imagem

```bash
python -m visiontag.cli --source foto.jpg
# {"tags": ["cadeira", "mesa", "laptop"]}
```

### Salvar imagem anotada

```bash
python -m visiontag.cli --source foto.jpg --output resultado.jpg
```

### Vídeo

```bash
python -m visiontag.cli --source video.mp4 --show --output saida.mp4
```

### Webcam

```bash
python -m visiontag.cli --webcam 0 --show --stride 3
# Pressione 'q' para sair
```

### Opções disponíveis

| Flag | Padrão | Descrição |
|------|--------|-----------|
| `--source PATH` | — | Caminho para imagem ou vídeo |
| `--webcam IDX` | — | Índice da webcam (ex: `0`) |
| `--model` | `yolov8n.pt` | Modelo YOLOv8 a usar |
| `--conf` | `0.7` | Confiança mínima (0–1) |
| `--max-tags` | `5` | Número máximo de tags |
| `--min-area` | `0.01` | Área mínima do bbox relativa à imagem |
| `--include-person` | `false` | Incluir "pessoa" nas tags |
| `--show` | `false` | Exibir janela com preview e bboxes |
| `--output PATH` | — | Salvar imagem/vídeo anotado |
| `--stride N` | `1` | Processar a cada N frames |
| `--print-every` | `false` | Emitir JSON mesmo sem mudança |
| `--log-level` | `INFO` | Nível de log |

---

## Uso — API REST

### Iniciar servidor

```bash
uvicorn visiontag.api:app --host 0.0.0.0 --port 8000
# Ou com reload automático:
make run-api
```

### Endpoints

#### `POST /detect`

Detecta objetos em uma imagem enviada como `multipart/form-data`.

```bash
curl -X POST http://localhost:8000/detect \
  -F "file=@foto.jpg"
```

**Resposta:**

```json
{
  "tags": ["cadeira", "mesa"],
  "detections": [
    {"tag": "cadeira", "confidence": 0.9312, "bbox": [10.0, 20.0, 150.0, 300.0]},
    {"tag": "mesa",    "confidence": 0.8741, "bbox": [0.0,  180.0, 640.0, 480.0]}
  ]
}
```

#### `GET /health`

```bash
curl http://localhost:8000/health
# {"status": "ok", "uptime_seconds": 42.3}
```

#### `GET /info`

```bash
curl http://localhost:8000/info
# {"model": "yolov8n.pt", "conf_threshold": 0.7, "max_tags": 5, ...}
```

Documentação interativa disponível em `http://localhost:8000/docs`.

---

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `VISIONTAG_MODEL` | `yolov8n.pt` | Modelo YOLOv8 |
| `VISIONTAG_CONF` | `0.7` | Confiança mínima |
| `VISIONTAG_MAX_TAGS` | `5` | Máximo de tags |
| `VISIONTAG_MIN_AREA` | `0.01` | Área mínima do bbox |
| `VISIONTAG_INCLUDE_PERSON` | `0` | `1` para incluir pessoas |
| `VISIONTAG_MAX_UPLOAD_MB` | `10` | Limite de upload da API (MB) |
| `VISIONTAG_LOG_LEVEL` | `INFO` | Nível de log |

---

## Testes

```bash
make test
# ou
pytest tests/ -v --cov=visiontag --cov-report=term-missing
```

---

## Requisitos

- Python 3.10+
- Dependências: `fastapi`, `uvicorn`, `ultralytics`, `opencv-python`, `numpy`

---

<div align="center">

Desenvolvido por **Matheus Siqueira** · [matheussiqueira.dev](https://www.matheussiqueira.dev/)

</div>
