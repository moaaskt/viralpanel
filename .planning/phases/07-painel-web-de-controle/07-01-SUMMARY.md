# Summary Plan 07-01: FastAPI REST API para Métricas, Esteira e Histórico

## O que foi feito
1. Atualizado `pyproject.toml` adicionando dependências:
   - `fastapi>=0.110.0`
   - `uvicorn>=0.28.0`
   - `httpx>=0.27.0` (dev)
2. Criado módulo `src/viralpanel/api/schemas.py` com esquemas Pydantic v2 para `PipelineRun`, `SourceVideo`, `Script`, `Asset`, `Publication`, `StatsResponse`, `HealthResponse` e `TriggerResponse`.
3. Criado módulo `src/viralpanel/api/routes.py` contendo endpoints:
   - `GET /api/health`
   - `GET /api/stats`
   - `GET /api/runs` e `GET /api/runs/{run_id}`
   - `POST /api/runs/trigger` (despacha tarefa Celery assíncrona)
   - `GET /api/videos` (com ordenação por score de viralidade e filtro de status)
   - `GET /api/scripts`
   - `GET /api/publications`
   - `GET /api/assets`
4. Criado módulo `src/viralpanel/api/app.py` configurando a aplicação FastAPI com middleware CORS aberto para desenvolvimento local e montagem de `/media` para servir arquivos de vídeo/áudio gerados pelo storage.
5. Criada suite de testes `tests/test_api.py` cobrindo 100% dos fluxos REST com SQLite em memória e mock de fila Celery. Todos os 42 testes da aplicação passam com sucesso.

