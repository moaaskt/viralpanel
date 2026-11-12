# Validation Strategy: Phase 8 — Auditoria, Contratos e Diagnóstico de Causa Raiz

## Verification Dimensions

### Dimension 1: Contratos e Interfaces de Estúdio
- **Verificação**: Mapeamento exaustivo de chamadas de `StudioService.produce(db, run_id, script)` a partir de `tasks.py` e Celery.
- **Evidência**: Documentar a assinatura pública intacta, os parâmetros de entrada e os valores retornados (`Asset` final), além da especificação conceitual de DTOs tipados internos.
- **Comando automatizado**: `python -c "from viralpanel.studio.service import StudioService; import inspect; print(inspect.signature(StudioService.produce))"`

### Dimension 2: Diagnóstico de Causa Raiz de Legendas Duplicadas
- **Verificação**: Identificação precisa e baseada em evidências das duas fontes de risco: 1) Hard subs preexistentes em vídeos fonte baixados do TikTok; 2) Ausência de duplicação interna do filtro ASS no FFmpeg (`renderer.py` executa apenas uma passagem).
- **Evidência**: Comparação técnica entre vídeos baixados com legendas embutidas vs vídeos limpos, e validação de que o filtro `ass` é chamado uma única vez no `filter_complex`.

### Dimension 3: Diagnóstico de Formato de Avatar e Borda Quadrada
- **Verificação**: Inspeção direta dos metadados de imagem e vídeo de avatar via `ffprobe` e `file`.
- **Evidência**: Comprovação de que `assets/creator_avatar.png` é `rgb24` (opaco), de que `renderer.py` aplica `pad=...color=white` criando moldura branca quadrada, e de que `avatar.mp4` é gerado em `yuv420p` descartando alfa.
- **Comando automatizado**: `ffprobe -v error -select_streams v:0 -show_entries stream=pix_fmt,width,height -of json assets/creator_avatar.png`

### Dimension 4: Mapeamento de Grafo FFmpeg e Proposta Single-Pass
- **Verificação**: Mapeamento de todos os passes FFmpeg executados no pipeline atual (fundo fallback, avatar intermediário, render final).
- **Evidência**: Proposta arquitetural de grafo integrado single-pass para a Phase 12, eliminando reencodificações intermediárias e garantindo saída Full HD 1080x1920 (9:16) em yuv420p.

### Dimension 5: Integridade do Código e Ausência de Regressão
- **Verificação**: Garantia de que nenhum código de produção foi alterado indevidamente durante a fase diagnóstica.
- **Comando automatizado**: `pytest tests/test_studio_renderer.py tests/test_subtitles.py`

