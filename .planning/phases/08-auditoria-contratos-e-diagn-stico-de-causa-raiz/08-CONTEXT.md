# Phase 8: Auditoria, Contratos e Diagnóstico de Causa Raiz - Context

**Gathered:** 2026-11-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Esta fase é estritamente diagnóstica e analítica. Ela entrega o mapeamento exaustivo dos contratos e interfaces atuais entre `tasks.py`, `StudioService`, `subtitles.py`, `avatar.py` e `renderer.py`, além do diagnóstico conclusivo e baseado em evidências das causas raiz da duplicação de legendas, artefatos visuais do avatar (borda quadrada) e gargalos/ineficiências nos comandos e filtros FFmpeg. Nenhuma alteração de código ou implementação de correção deve ser executada durante esta fase.

</domain>

<decisions>
## Implementation Decisions

### Contratos & Interfaces
- **D-01:** Manter obrigatoriamente o contrato público atual: `StudioService.produce(db, run_id, script) -> Asset`. A integração existente com `tasks.py` e Celery deve continuar funcionando sem alterações na assinatura ou forma de chamada — **Reversibility:** one-way — quebrar essa assinatura exigiria alterar a task Celery e invalidaria os testes do pipeline E2E v1.0.
- **D-02:** A auditoria deve avaliar a introdução de DTOs explícitos e tipados para comunicação interna entre `StudioService`, `ReactionVideoRenderer` e `subtitles.py`, visando clareza e baixo acoplamento interno sem expor mudanças para o Celery.
- **D-03:** Não introduzir arquitetura de compositores injetáveis complexa nesta etapa sem evidência concreta de necessidade; priorizar compatibilidade retroativa, responsabilidades bem delineadas e zero regressão.

### Diagnóstico de Duplicação de Legendas
- **D-04:** Auditar obrigatoriamente as duas fontes de risco de duplicação: 1) Vídeos baixados que já possuem legendas incorporadas (burned-in captions) na imagem original; 2) Aplicação duplicada do filtro ASS no FFmpeg ou sobreposição com outros elementos do pipeline de composição.
- **D-05:** Diferenciar no relatório técnico causas confirmadas por evidências de meras hipóteses teóricas.
- **D-06:** Analisar o fluxo de dados entre `build_cues_from_script`, `write_ass_subtitles` e o filtro ASS em `renderer.py`, identificando responsabilidades e oportunidades de desacoplamento.
- **D-07:** Avaliar estratégias para lidar com legendas preexistentes do vídeo baixado (como crop, mascaramento ou posicionamento dinâmico de legendas ZUNTO!), sem implementar nada antes de comprovar necessidade.

### Diagnóstico de Assets e Formato do Avatar
- **D-08:** Realizar inspeção técnica profunda dos arquivos reais: `assets/creator_avatar.png` e os arquivos de vídeo de avatar gerados (`avatar.mp4`), verificando resolução, proporção, padding interno, canais de cor e existência real de canal alfa (transparência).
- **D-09:** Verificar e documentar o impacto do padding branco hardcoded (`pad=...color=white`) presente na linha 128 de `renderer.py` e comprovar se ele é a causa única ou parcial da aparência de caixa quadrada.
- **D-10:** Não assumir antecipadamente que a simples remoção do padding branco ou que o uso de uma máscara estática resolverá o problema. Avaliar alternativas técnicas viáveis de transparência (ex: WebM com alpha, ProRes 4444, sequências PNG ou keying) e compatibilidade com FFmpeg.
- **D-11:** Mapear posicionamento e safe zones verticais 9:16 para evitar que o avatar cubra legendas ou o centro do vídeo original.

### Grafo e Passes FFmpeg
- **D-12:** Mapear todos os comandos e passes FFmpeg atualmente executados: geração de fundo visual fallback (`color=c=#0f172a`), geração/animação de avatar e composição final no `ReactionVideoRenderer`.
- **D-13:** Identificar para cada comando os arquivos de I/O, codecs, presets (`ultrafast`), pixel format (`yuv420p`), FPS e reencodificações intermediárias desnecessárias.
- **D-14:** Elaborar a proposta de arquitetura de composição single-pass (concentrando os filtros e a composição em uma única codificação final sempre que tecnicamente viável), preservando rigorosamente a saída vertical 9:16 em 1080x1920 e a sincronização A/V.

### Diretriz Obrigatória do Milestone
- **D-15:** FASE EXCLUSIVAMENTE DIAGNÓSTICA. Não modificar assets, não aplicar patches rápidos, não alterar código de produção e não criar dependências sem justificativa. O produto desta fase é um relatório técnico estruturado de auditoria com propostas para as fases subsequentes.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisitos e Roadmap
- `.planning/REQUIREMENTS.md` — Requisitos SUB-01, AVTR-01 e COMP-01
- `.planning/ROADMAP.md` — Escopo, metas e critérios de sucesso da Phase 8

### Código-Fonte em Auditoria
- `src/viralpanel/studio/service.py` — Orquestração de estúdio (`StudioService.produce`)
- `src/viralpanel/studio/renderer.py` — Renderização FFmpeg (`ReactionVideoRenderer`, `filter_complex`)
- `src/viralpanel/studio/subtitles.py` — Geração e formatação de legendas ASS (`build_cues_from_script`, `write_ass_subtitles`)
- `src/viralpanel/studio/avatar.py` — Geração e animação do avatar (`AudioReactiveAvatarAnimator`, `ensure_default_avatar_image`)
- `src/viralpanel/tasks.py` — Ponto de integração com Celery (`_run_pipeline`, task assíncrona)

### Assets
- `assets/creator_avatar.png` — Asset padrão de imagem do avatar do criador

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets & Diagnósticos Identificados
- `ReactionVideoRenderer` (`src/viralpanel/studio/renderer.py`):
  - Linha 127-128: `pad={self.avatar_size + 12}:{self.avatar_size + 12}:6:6:color=white` insere explicitamente uma borda branca de 6px ao redor do avatar, resultando no visual quadrado se o avatar não preencher um círculo ou se tiver fundo opaco.
  - Linha 130: `ass='{escaped_ass}'` aplica o filtro de legenda diretamente no stream composto.
  - Linha 101-119: Criação de `source_visual_bg.mp4` via comando subprocess separado quando o vídeo fonte não tem stream de vídeo (passe adicional).
- `subtitles.py` (`src/viralpanel/studio/subtitles.py`):
  - Utiliza estilo ASS padrão (`DejaVu Sans,62,&H00FFFFFF`) com margin vertical 480.
  - Converte texto puro em cues proporcionais à duração do áudio (`build_cues_from_script`).
- `tasks.py` (`src/viralpanel/tasks.py`):
  - Injeta `StudioService` em `_run_pipeline` chamando `studio_service.produce(db, run.id, script)`.

### Integration Points
- `StudioService.produce` recebe `Script` e `run_id`, cria paths no storage (`storage.get_run_dir`), gera narração, avatar, legendas e chama o renderer, persistindo 3 instâncias de `Asset` (`audio`, `avatar`, `final_video`).

</code_context>

<specifics>
## Specific Ideas

- O relatório de auditoria deve ser estruturado em seções claras:
  1. Mapeamento de Contratos e Interfaces (diagrama de chamadas, DTOs propostos)
  2. Diagnóstico de Causa Raiz de Legendas Duplicadas (vídeo fonte vs filtros FFmpeg)
  3. Diagnóstico de Assets e Recorte do Avatar (inspeção dos arquivos reais, alternativas de transparência)
  4. Mapeamento do Grafo FFmpeg e Proposta Single-Pass
- Todas as conclusões devem ser acompanhadas de comandos de inspeção (`ffprobe`, `file`, etc.) e evidências concretas.

</specifics>

<deferred>
## Deferred Ideas

- Implementação do novo motor de legendas ZUNTO! → Phase 10
- Implementação da transparência orgânica do avatar → Phase 11
- Refatoração do grafo FFmpeg single-pass → Phase 12
- Validação audiovisual E2E → Phase 13

</deferred>

---

*Phase: 8-Auditoria, Contratos e Diagnóstico de Causa Raiz*
*Context gathered: 2026-11-06*

