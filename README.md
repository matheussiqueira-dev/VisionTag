# VisionTag Frontend

Frontend profissional do VisionTag para operação de detecção visual com foco em produtividade, clareza de informação e escalabilidade de código.

A interface foi reestruturada para suportar fluxo real de uso com:
- análise de imagem única e em lote,
- filtros avançados de inferência,
- histórico local pesquisável,
- exportação de relatório,
- arquitetura frontend modular,
- persistência de preferências e atalhos de produtividade.

## Visão Geral do Frontend

O frontend atende dois cenários principais:
1. Operação rápida (imagem única): upload, ajuste de parâmetros e leitura imediata das tags/detecções.
2. Operação em volume (lote): envio de múltiplas imagens, visão consolidada de resultados e rastreabilidade local.

Público-alvo:
- times operacionais e analistas de conteúdo visual;
- squads de produto que integram visão computacional no fluxo de negócio;
- desenvolvedores que precisam de uma UI pronta para validar inferência da API.

## Stack e Tecnologias Utilizadas

- HTML5 semântico
- CSS3 com design tokens e layout responsivo
- JavaScript modular (ES Modules)
- FastAPI servindo assets estáticos
- API VisionTag (`/api/v1/detect`, `/api/v1/detect/batch`)

## Arquitetura Frontend

Estrutura atual:

```text
visiontag/static/
  index.html
  styles.css
  js/
    app.js
    api.js
    constants.js
    helpers.js
    storage.js
    ui.js
```

Responsabilidades por módulo:
- `app.js`: orquestra fluxo da aplicação, eventos, estado global e casos de uso.
- `api.js`: camada de comunicação HTTP com tratamento de erro.
- `ui.js`: renderização de UI, atualizações de DOM e estado visual.
- `storage.js`: persistência de histórico e preferências no `localStorage`.
- `helpers.js`: utilitários de formatação, transformação e normalização.
- `constants.js`: contratos e limites do frontend.

## Refactor e Otimizações Aplicadas

- Quebra de script monolítico em módulos reutilizáveis.
- Estado de interface centralizado para reduzir inconsistências de renderização.
- Reuso de componentes visuais via classes e tokens.
- Uso de `URL.createObjectURL` para preview mais eficiente de imagem.
- Cancelamento de requisição concorrente com `AbortController`.
- Renderização defensiva com `textContent` e criação de nós DOM para reduzir risco de injeção.
- Melhorias de UX de feedback (status pill, loading state, mensagens contextualizadas).
- Persistência de preferências do usuário (modo e parâmetros).
- Atalhos globais para acelerar fluxos operacionais.
- Comparativo entre análises com delta de tags.

## UI/UX e Design System

### Diretrizes implementadas
- Hierarquia visual forte (hero, controles, resultados e histórico).
- Sistema de cores com contraste elevado e tokens semânticos.
- Tipografia dedicada para UI e métricas técnicas.
- Microinterações em botões, dropzone e transições de estado.
- Responsividade completa para desktop, tablet e mobile.

### Acessibilidade (WCAG orientada)
- Estrutura semântica com landmarks (`header`, `main`, `aside`, `section`).
- `skip-link` para navegação por teclado.
- `aria-live` para feedback de status.
- Estados de foco visíveis.
- Compatibilidade com `prefers-reduced-motion`.

## Funcionalidades Implementadas

- Modo alternável: imagem única e lote.
- Upload por clique e drag-and-drop.
- Preview imediato de imagem e fila visual de arquivos.
- Ajustes de inferência na UI:
  - confiança mínima,
  - máximo de tags,
  - área mínima,
  - inclusão de pessoa.
- Filtro visual de confiança pós-processamento.
- Presets de inferência (balanceado, alta precisão e sensível).
- Resultado detalhado:
  - tags,
  - delta entre análise anterior e atual,
  - tabela de detecções,
  - métricas operacionais.
- Visão de resultado por arquivo em análise de lote.
- Busca e limpeza de histórico local.
- Exportação de relatório JSON.
- Cópia rápida de tags para clipboard.
- Atalhos de teclado:
  - `Ctrl + Enter` para analisar
  - `Ctrl + K` para buscar no histórico
  - `Ctrl + B` para alternar modo
  - `?` para abrir a ajuda de atalhos

## Setup e Execução

## Pré-requisitos
- Python 3.10+

## Instalação

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## Rodar aplicação

```bash
uvicorn visiontag.api:app --host 0.0.0.0 --port 8000
```

Acessos:
- Frontend: `http://localhost:8000/`
- Swagger/OpenAPI: `http://localhost:8000/docs`

## Build

O frontend atual é servido como assets estáticos (sem etapa de build obrigatória).

## Boas Práticas Adotadas

- separação de responsabilidades por módulo;
- contratos de API explícitos no consumo frontend;
- componentes e tokens reutilizáveis;
- feedback de erro/sucesso padronizado;
- foco em legibilidade, manutenção e evolução incremental.

## Melhorias Futuras

- testes automatizados de UI (Playwright);
- internacionalização (i18n);
- modo de comparação entre análises;
- paginação/virtualização para lotes muito grandes;
- telemetria de UX (eventos e funis de uso).

Autoria: Matheus Siqueira  
Website: https://www.matheussiqueira.dev/
