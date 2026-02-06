# VisionTag Frontend

Frontend profissional para análise de imagens com foco em usabilidade, acessibilidade, performance e operação em tempo real. A interface consome a API do VisionTag para detecção visual e oferece fluxo completo para modo único, lote e URL remota.

## Visão Geral do Frontend

O frontend do VisionTag foi projetado para equipes que precisam de produtividade operacional sem abrir mão de qualidade visual.

Objetivos principais:
- reduzir tempo de análise visual;
- melhorar previsibilidade dos fluxos de detecção;
- entregar feedback claro de status, resultados e saúde operacional.

Público-alvo:
- analistas de operação;
- squads de produto e engenharia;
- times que validam modelos de visão computacional em ambiente real.

## Stack e Tecnologias Utilizadas

- HTML5 semântico
- CSS3 com design tokens e componentes reutilizáveis
- JavaScript ES Modules (arquitetura modular sem framework)
- Integração com API REST (`/api/v1/*`)
- Persistência local com `localStorage`

## Funcionalidades Principais

- Upload de imagem única e lote
- Análise por URL remota
- Parâmetros avançados de inferência (confiança, área mínima, include/exclude labels)
- Presets rápidos e presets personalizados persistidos localmente
- Histórico local com busca
- Exportação de relatório JSON
- Painel operacional (overview admin, runtime, atividade recente e limpeza de cache)
- Atalhos de teclado para fluxo rápido
- Controles de acessibilidade:
  - alto contraste
  - modo compacto
- Insights visuais de detecção (KPIs + distribuição por label)

## Arquitetura Frontend

Estrutura modular:

```text
visiontag/static/
  index.html
  styles.css
  js/
    app.js        # estado, orquestração e eventos
    ui.js         # renderização e manipulação de DOM
    api.js        # cliente HTTP da API
    storage.js    # persistência local
    helpers.js    # utilitários puros (formatação, insights, debounce)
    constants.js  # constantes e chaves da aplicação
```

Padrões adotados:
- separação de responsabilidades por módulo;
- funções puras para transformação de dados;
- renderização incremental por estado;
- persistência de preferências sem armazenar segredos sensíveis (API key não persiste).

## UI/UX e Design System

### Diretrizes aplicadas
- hierarquia visual clara e alta legibilidade;
- feedback contínuo de estado (loading, sucesso, erro);
- consistência tipográfica e de espaçamento;
- componentes reutilizáveis para listas, chips, cards e painéis.

### Tokens visuais
- paleta semântica com variáveis CSS (`:root`);
- estados de interação (hover/focus/disabled);
- modo de alto contraste por atributo `data-contrast`;
- densidade visual ajustável por `data-density`.

### Acessibilidade (boas práticas WCAG)
- skip-link para conteúdo principal;
- foco visível em elementos interativos;
- áreas com `aria-live` para feedback dinâmico;
- navegação por teclado e atalhos;
- suporte a `prefers-reduced-motion`.

## Setup e Execução

### Pré-requisitos
- Python 3.10+
- Backend VisionTag em execução local

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

### Rodar aplicação
```bash
uvicorn visiontag.api:app --host 0.0.0.0 --port 8000
```

Acessar:
- Frontend: `http://localhost:8000/`
- API Docs: `http://localhost:8000/docs`

## Build e Qualidade

Validações executadas no frontend:

```bash
node --check visiontag/static/js/app.js
node --check visiontag/static/js/ui.js
node --check visiontag/static/js/helpers.js
node --check visiontag/static/js/storage.js
```

Validação da suíte do projeto:

```bash
python -m pytest -q
```

## Boas Práticas Adotadas

- estado centralizado com fluxo previsível;
- renderização desacoplada do transporte HTTP;
- persistência local com limites e saneamento;
- debounce em busca para melhor responsividade;
- foco em acessibilidade e UX operacional;
- nomenclatura clara e manutenção simples.

## Melhorias Futuras

- testes e2e de interface (Playwright);
- internacionalização (i18n);
- gráficos avançados de operação;
- tema claro/escuro completo com preferências do sistema;
- PWA para uso offline parcial.

Autoria: Matheus Siqueira  
Website: https://www.matheussiqueira.dev/
