# Phase 14: Context & Background
## Formalização da Coleta e Scraper (Retrospectiva)

**Data de Elaboração:** 13 de Novembro de 2026  
**Fase:** 14 — Formalização da Coleta e Scraper (Retrospectiva)  
**Status:** Planejamento Retrospectivo Formal  
**Requisitos Vinculados:** `DISC-04`, `DISC-05`  

---

## 1. Contexto Histórico e Justificativa

Durante o ciclo de transição e auditoria do projeto ZUNTO! (anteriormente ViralPanel), uma sequência de 12 commits (`c77a44c`..`10229d6`) foi incorporada diretamente à branch `developer` para sanar problemas operacionais imediatos no módulo de coleta (Playwright/TikTok scraper), download de mídia (`yt-dlp`), deduplicação de candidatos e alinhamento temático editorial:

1. `c77a44c`: Ajuste de restrição do PyAV (`av>=19.0.2,<20.0.0`) para compatibilidade com Python 3.14.
2. `88d8aaa`: Alinhamento de tópicos de discovery e seed accounts para a linha editorial ZUNTO! (ciência, tecnologia, mistério).
3. `133571c`: Atualização dos identificadores oficiais dos modelos Gemini (`gemini-2.5-flash`) e Groq (`llama-3.3-70b-versatile`).
4. `d482cf2`: Sincronização dos identificadores oficiais no `.env.example`.
5. `455a1d8`: Atualização dos defaults de `DiscoverySettings` para o nicho de ciência/tecnologia/mistério.
6. `e848edb`: Implementação de verificação cross-platform do `yt-dlp` e normalização canônica de URLs do TikTok.
7. `5e99225`: Deduplicação canônica de URLs equivalentes e filtro de score estritamente positivo (`score > 0.0`).
8. `a9c4945`: Resiliência de download no `MediaDownloader` com sobrescrita limpa (`--force-overwrites`) e `get_ytdlp_cmd`.
9. `2628e09`: Limpeza de arquivos de mídia órfãos em `ScriptingService` em caso de `InsufficientSpeechError`.
10. `746a598`: Eliminação de fallback silencioso para `MockPublisher` / `MockGeminiScriptWriter` quando `PIPELINE_MOCK_MODE=false`.
11. `9c27de6`: Atualização de asserções de testes para hashtags e nicho ZUNTO!.
12. `10229d6`: Adição da suíte de regressão `tests/test_phase14_recovery.py` (10 testes cobrindo todas as correções).

Como essas alterações foram aplicadas diretamente no repositório antes de sua formalização no GSD, a presente fase atua com **finalidade retrospectiva**: catalogar, validar e vincular formalmente todo o trabalho aos requisitos rastreáveis do projeto, sem fabricar histórico fictício e garantindo que o GSD reflita com precisão o commit HEAD real.

---

## 2. Decisões Consolidadas e Implementadas

### D-DISC-01: Normalização Canônica de URLs do TikTok (`DISC-04`)
- **Implementação:** `normalize_tiktok_url()` em `src/viralpanel/discovery/tiktok.py`.
- **Comportamento:** Converte variantes móveis (`https://m.tiktok.com/v/...`), URLs com parâmetros de rastreamento (`?is_copy_url=1`), URLs curtas sem autor no path e IDs numéricos avulsos no formato canônico estável: `https://www.tiktok.com/@{author}/video/{video_id}`.

### D-DISC-02: Deduplicação e Filtro de Score Estritamente Positivo (`DISC-04`)
- **Implementação:** `DiscoveryService.collect_and_rank()` e `select_best_candidate()` em `src/viralpanel/discovery/service.py`.
- **Comportamento:** Mantém conjunto `seen_urls` normalizado durante a coleta, evitando duplicatas no banco de dados. Exige explicitamente `score > 0.0` para que qualquer candidato seja elegível a processamento pelo pipeline diário.

### D-DISC-03: Comando `yt-dlp` Cross-Platform Tolerante a Falhas (`DISC-05`)
- **Implementação:** `get_ytdlp_cmd()` em `src/viralpanel/discovery/tiktok.py` e `src/viralpanel/media/downloader.py`.
- **Comportamento:** Inspeciona `shutil.which("yt-dlp")`. Caso o binário isolado não esteja no PATH (cenário frequente em ambientes Windows ou containers enxutos), recorre automaticamente a `[sys.executable, "-m", "yt_dlp"]`. Se a biblioteca não estiver disponível, lança `RuntimeError` informativo em vez de falha silenciosa.

### D-DISC-04: Limpeza Atômica de Arquivos em Retentativas (`DISC-05`)
- **Implementação:** `MediaDownloader.fetch()` em `src/viralpanel/media/downloader.py` e `ScriptingService.process()` em `src/viralpanel/scripting/service.py`.
- **Comportamento:** Na troca de candidatos dentro do mesmo `run_id`, arquivos antigos (`source.mp4`, `audio.wav`) são limpos antes do novo download com flag `--force-overwrites`. Em caso de erro de fala insuficiente (`InsufficientSpeechError`), os arquivos de mídia associados são imediatamente removidos do disco e o vídeo é marcado como `skipped_no_speech`.

### D-DISC-05: Travas contra Mocks Silenciosos
- **Implementação:** `FallbackScriptWriter` em `src/viralpanel/scripting/gemini.py`.
- **Comportamento:** Se `PIPELINE_MOCK_MODE=false` e as chaves de API estiverem ausentes, o construtor lança `RuntimeError` imediato em vez de instanciar `MockGeminiScriptWriter`.

---

## 3. Escopo e Fronteiras da Fase

### O que está no escopo da Phase 14:
- Auditoria e catalogação dos 12 commits de recuperação.
- Vinculação formal aos requisitos `DISC-04` e `DISC-05`.
- Execução e verificação da suíte `tests/test_phase14_recovery.py` e `tests/test_discovery_scoring.py`.
- Atualização e alinhamento dos artefatos GSD (`ROADMAP.md`, `REQUIREMENTS.md`, `14-01-PLAN.md`).

### O que está FORA de escopo (Non-Goals):
- Nenhuma alteração em código de aplicação (`src/`).
- Nenhuma alteração em testes existentes (`tests/`).
- Nenhuma alteração em migrações Alembic (escopo exclusivo da Phase 15).
- Não encerra a Phase 13 nem o Milestone v1.1.
- Não avança para as Phases 15 a 18.
