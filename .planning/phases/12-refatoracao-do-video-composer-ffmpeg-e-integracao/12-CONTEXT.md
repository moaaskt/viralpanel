# Phase 12: Refatoração do Video Composer FFmpeg e Integração - Context

**Gathered:** 2026-11-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Esta fase entrega a refatoração do Video Composer (`ReactionVideoRenderer`) e sua integração com o pipeline do `StudioService`. Ela implementa o requisito de **Single-Pass**: composição integrada em grafo único e codificação única sempre que viável, eliminando reencodificações intermediárias desnecessárias e arquivos temporários redundantes em disco (como `source_visual_bg.mp4`), gerando o vídeo vertical final 9:16 em 1080x1920 com fidelidade visual ZUNTO!, sincronização audiovisual estrita e 100% de retrocompatibilidade com Celery, PostgreSQL e o pipeline de publicação da v1.0.

Entregas:
1. Eliminação do passe intermediário de fallback: quando `source_video` não possui stream de vídeo, o fallback visual é gerado inline via lavfi (`color=c=#0f172a:s=1080x1920:r=24:d=...`) como input do grafo FFmpeg, sem criar `source_visual_bg.mp4` em disco.
2. Composição integrada e preservação de contratos: preserva o registro do `Asset(asset_type="avatar")` gerando `avatar.mp4` em PNG/RGBA (ou permitindo composição in-memory quando aplicável), e executa a codificação final do vídeo 1080x1920 com `libx264` (`yuv420p`), `preset=veryfast`, `crf=20`, áudio `aac` 192k e `fps=24`.
3. Preservação de contratos Celery / StudioService: `StudioService.produce(db, run_id, script) -> Asset` mantém intacta a sua assinatura e a criação dos 3 registros `Asset` (`audio`, `avatar`, `final_video`) vinculados ao `script.id` e o status `produced`.
4. DTO interno tipado `StudioRenderRequest`: introduzido para encapsular insumos de renderização internamente entre `StudioService` e `ReactionVideoRenderer`, mantendo a assinatura pública de `render()` compatível via kwargs / argumentos nomeados.

Fora de escopo: testes perceptuais manuais de visualização em dispositivos móveis (escopo da Phase 13).

</domain>

<decisions>
## Implementation Decisions

### 1. Grafo Integrado Single-Pass e Intermediário de Avatar
- **D-01:** Manter a geração física do artefato `avatar.mp4` (codec `png`, `pix_fmt rgba`) para assegurar a persistência do `Asset(asset_type="avatar")` no banco e compatibilidade com Celery, enquanto a composição do vídeo final consome esse stream de avatar com canal alfa direto no grafo único em conjunto com o vídeo base e legendas ASS.
  - **Reversibility:** costly — define o contrato de persistência de assets no banco e pipelines downstream.
  - O pipeline de composição final ocorre em uma única codificação para disco (`final_reaction_9x16.mp4`), sem passes intermediários de filtros adicionais.

### 2. Eliminação do Arquivo Intermediário de Fallback
- **D-02:** Tratar ausência de stream de vídeo no `source_video` gerando o fundo escuro diretamente via input lavfi (`-f lavfi -i color=c=#0f172a:s=1080x1920:r=24:d={duration}`) no comando principal do FFmpeg.
  - **Reversibility:** reversible — simplificação interna do `ReactionVideoRenderer`.
  - Elimina completamente o subprocesso preliminar que criava `source_visual_bg.mp4` em disco, economizando I/O e tempo de CPU.

### 3. Parâmetros de Encoding e Qualidade Visual
- **D-03:** Adotar `preset="veryfast"`, `crf=20`, áudio `aac` com bitrate `192k` e `fps=24` para a codificação de saída `libx264` (`yuv420p`).
  - **Reversibility:** reversible — parâmetros de linha de comando FFmpeg.
  - O `crf=20` com `veryfast` oferece equilíbrio ideal entre alta fidelidade visual (sem degradação de blocos na resolução 1080x1920) e renderização ágil em ambiente de produção com criador solo.

### 4. DTO Interno e Contratos Públicos Retrocompatíveis
- **D-04:** Adotar `StudioRenderRequest` como DTO interno em `src/viralpanel/studio/renderer.py`, mantendo a assinatura pública de `render(...)` com parâmetros nomeados retrocompatíveis.
  - **Reversibility:** reversible — interface de serviço.
  - O método `render` pode aceitar `StudioRenderRequest` ou os parâmetros primitivos legados (`source_video_path`, `avatar_video_path`, `voice_audio_path`, `ass_subtitle_path`, `output_path`), encapsulando-os sem quebrar nenhum teste existente da v1.0.

### 5. Camadas do Grafo e Sincronização Audiovisual
- **D-05:** Ordem estrita das camadas no grafo:
  1. `[0:v]` Fundo (vídeo de origem escalado/recortado para 1080x1920 ou fundo lavfi).
  2. `[1:v]` Avatar reaction circular com transparência nativa posicionado em `W-w-54:H-h-320` ($Y=1300\dots1600\text{px}$).
  3. `[composed]ass='...'[vout]` Legendas ZUNTO! aplicadas sobre o vídeo composto com caixa opaca em `MarginV=640` ($Y \approx 1080\dots1280\text{px}$).
  4. Stream de áudio da locução `voice_audio_path` mapeado como trilha principal de áudio sincronizada (`-map [vout] -map 2:a -shortest`).

### the agent's Discretion
- Estruturação do método `render_from_request(request: StudioRenderRequest)` vs overload de `render()`.
- Timeout de subprocesso FFmpeg calibrado (ex.: 120s para vídeos longos em veryfast).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Auditoria e Diagnósticos
- `.planning/phases/08-auditoria-contratos-e-diagn-stico-de-causa-raiz/08-AUDIT-REPORT.md` — Seção 1.4 (Passe e Grafo FFmpeg Atual) e Seção 1.5 (DTOs StudioRenderRequest e ReactionCompositionSpec).

### Brand & Safe Zones
- `src/viralpanel/branding.py` — SafeZones9x16 (`AVATAR_SIZE=300`, `AVATAR_MARGIN_RIGHT=54`, `AVATAR_MARGIN_BOTTOM=320`, `SUBTITLE_MARGIN_V=640`).

### Módulos do Studio
- `src/viralpanel/studio/renderer.py` — `ReactionVideoRenderer`, filtros de scale/crop/overlay/ass e execução de subprocesso FFmpeg.
- `src/viralpanel/studio/service.py` — `StudioService.produce`, orquestração dos 3 assets e status `produced`.
- `tests/test_studio_renderer.py` — Suíte de testes de renderização.

</canonical_refs>
