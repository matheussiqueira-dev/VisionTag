# VisionTag

Sistema simples de visao computacional para detectar objetos e retornar tags em portugues.

**Requisitos**
1. Python 3.10+

**Instalacao**
1. `python -m venv .venv`
2. `.venv\\Scripts\\activate`
3. `pip install -r requirements.txt`

**Uso (arquivo)**
1. `python -m visiontag.cli --source C:\\caminho\\imagem.jpg`

Saida:
```json
{"tags":["caderno","mesa"]}
```

**Uso (webcam)**
1. `python -m visiontag.cli --webcam 0 --show`

Para sair, pressione `q` na janela.

Quando `--show` esta ativo, o video exibido inclui boxes e o nome do objeto.

**API**
1. `uvicorn visiontag.api:app --host 0.0.0.0 --port 8000`
2. `POST /detect` com arquivo no campo `file`

**Padroes**
1. Confianca minima: `0.7`
2. Maximo de tags: `5`
3. Objetos pequenos: ignora bbox com area < `1%` da imagem
4. Pessoas: ignoradas por padrao (use `--include-person`)

**Observacoes**
1. O modelo `yolov8n.pt` sera baixado na primeira execucao.
