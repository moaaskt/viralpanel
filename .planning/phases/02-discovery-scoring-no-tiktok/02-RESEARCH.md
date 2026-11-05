# Phase 2 Research: Discovery & Scoring no TikTok

## 1. Contexto e Objetivos
O objetivo da Fase 2 é implementar a ingestão e classificação dos 30 vídeos mais virais no TikTok no nicho de desenvolvimento pessoal / motivação.
Requisitos:
- **DISC-01**: Busca de 30 vídeos candidatos por hashtags e termos configuráveis.
- **DISC-02**: Extração de metadados completos (views, likes, comments, shares, data de postagem).
- **DISC-03**: Interface abstrata de coleta (`BaseDiscoveryScraper`), permitindo múltiplos backends (ex: mock, Playwright, yt-dlp / API) sem acoplamento.
- **SCOR-01**: Cálculo de score de viralidade parametrizável via YAML (ponderação de views, likes/views ratio, comments/views ratio, shares/views ratio e velocidade por hora).
- **SCOR-02**: Seleção e persistência do melhor candidato não processado no banco de dados (`SourceVideo`).

## 2. Padrões de Arquitetura & Design
1. **Interface Abstrata de Scraping (`viralpanel/discovery/base.py`)**:
   - `ScrapedVideoMetadata`: dataclass/Pydantic com url, platform, author, title, views, likes, comments, shares, posted_at.
   - `BaseScraper(ABC)`: método `discover_trending(limit: int = 30) -> list[ScrapedVideoMetadata]`.
2. **Implementações**:
   - `MockDiscoveryScraper` para testes unitários deterministicos e offline.
   - `TikTokPlaywrightScraper` / `YtDlpMetadataExtractor` para execução real em produção.
3. **Mecanismo de Scoring (`viralpanel/discovery/scoring.py`)**:
   - Carrega fórmula e pesos de `config/scoring.yaml` (ou fallback padrão).
   - `calculate_viral_score(video_metadata: ScrapedVideoMetadata, config: ScoringConfig) -> float`.
   - Considera: engajamento relativo `(likes + 2*comments + 3*shares) / views`, velocidade temporal de visualizações por hora decorrida desde a postagem.
4. **Integração com Celery & Persistência (`viralpanel/discovery/service.py`)**:
   - Serviço que orquestra a coleta, calcula os scores de todos os 30 itens, salva/atualiza na tabela `source_videos`, e seleciona o item de maior score que ainda tem status `'pending'`.

