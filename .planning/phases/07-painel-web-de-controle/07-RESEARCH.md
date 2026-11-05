# Phase 7 Research: Painel Web de Controle

## Objetivo da Fase
Disponibilizar uma interface web moderna, sóbria e profissional (React + Chakra UI, sem cores neon) e uma API backend (FastAPI) para:
1. Visualizar o estado da esteira diária e das tarefas assíncronas do Celery (`DASH-01`).
2. Listar histórico de execuções de pipeline, vídeos descobertos/selecionados, roteiros gerados, mídias e publicações com métricas (`DASH-02`).
3. Respeitar a identidade visual limpa e profissional com Chakra UI, estritamente sem cores neon (`DASH-03`).
4. Permitir disparar a esteira diária manualmente através da interface web.

---

## 1. Arquitetura da Solução

### 1.1 Backend REST API (`src/viralpanel/api/`)
- **Framework**: FastAPI + Uvicorn + Pydantic v2.
- **Roteadores**:
  - `GET /api/health`: Status do backend, conexão com DB e Redis.
  - `GET /api/runs`: Lista as execuções de pipeline (`PipelineRun`) com status, timestamps e etapas.
  - `GET /api/runs/{run_id}`: Detalhes de uma execução com etapas concluídas/falhadas.
  - `POST /api/runs/trigger`: Dispara manualmente a task Celery `trigger_daily_pipeline`.
  - `GET /api/videos`: Lista vídeos fontes descobertos (`SourceVideo`) e selecionados com score de viralidade.
  - `GET /api/scripts`: Lista roteiros gerados (`Script`) com gancho, desenvolvimento e CTA.
  - `GET /api/publications`: Lista publicações efetuadas e agendadas (`Publication`) com plataformas (TikTok, Reels, Shorts), status e IDs externos.
  - `GET /api/stats`: Métricas agregadas (total de vídeos processados, taxa de sucesso, publicações por rede).
  - `StaticFiles / media`: Servir arquivos de mídia e preview para o player do painel.
- **CORS**: Configurado com `CORSMiddleware` para permitir o frontend local (portas 3000, 5173, etc).

### 1.2 Frontend Web (`frontend/`)
- **Build tool**: Vite + React 18 / TypeScript.
- **Design System**: Chakra UI v2 ou v3 com tema profissional configurado:
  - Paleta: Tons de Slate/Cinza/Navy/Azul corporativo sóbrio (`slate`, `blue.600`, `gray.700/800/900`).
  - Sem cores saturadas/neon (regra explícita em `AGENTS.md` e `DASH-03`).
- **Componentes**:
  - `Header` / `Navbar`: Status geral do sistema (Online, Celery status, última execução).
  - `StatsOverview`: Cards com totais (Vídeos coletados, Roteiros criados, Publicações realizadas, Taxa de aprovação).
  - `PipelineMonitor`: Tabela e visualização de pipelines ativos/recentes, botão "Disparar Esteira Manual", badge de status (`running`, `completed`, `failed`).
  - `VideoLibrary`: Lista e cards dos vídeos analisados com scores virais, roteiros gerados e mídias de preview.
  - `PublicationHistory`: Tabela de publicações por plataforma (TikTok, Instagram, YouTube) com status e links.

---

## 2. Dependências Necessárias
- **Python Backend**:
  - `fastapi>=0.110.0`
  - `uvicorn>=0.28.0`
- **Node / Frontend**:
  - `react`, `react-dom`
  - `@chakra-ui/react@2.8.2`, `@emotion/react`, `@emotion/styled`, `framer-motion`
  - `lucide-react` para ícones corporativos limpos
  - `vite`, `@vitejs/plugin-react`

---

## 3. Estratégia de Testes
- Backend:
  - `TestClient` do FastAPI (`httpx` ou `fastapi.testclient`).
  - Testes unitários para todos os endpoints em `tests/test_api.py`.
  - Garantir cobertura de DB fixtures e Celery mock para trigger.
- Frontend:
  - Teste de build do Vite (`npm run build`).
  - Validação estática de componentes.

