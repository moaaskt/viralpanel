# Phase 8: Auditoria, Contratos e Diagnóstico de Causa Raiz - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-06
**Phase:** 08-Auditoria, Contratos e Diagnóstico de Causa Raiz
**Areas discussed:** Mapeamento de Contratos & Interfaces, Diagnóstico de Duplicação de Legendas, Diagnóstico de Assets e Formato do Avatar, Análise de Grafo e Passes FFmpeg

---

## Mapeamento de Contratos & Interfaces

| Option | Description | Selected |
|--------|-------------|----------|
| Manter assinatura atual de produce(db, run_id, script) -> Asset intacta, isolando melhor as responsabilidades internas | Preserva 100% da integração com tasks Celery e pipeline E2E | ✓ |
| Introduzir DTOs explícitos tipados para parâmetros entre StudioService e Renderer/Subtitles mantendo produce() compatível | Adiciona tipagem rígida nos módulos internos | |
| Refatorar para pipeline de compositores injetáveis | Arquitetura mais abstrata de composição | |

**User's choice:** Manter obrigatoriamente o contrato público atual `produce(db, run_id, script) -> Asset`. A integração existente com `tasks.py` e Celery deve continuar funcionando sem alterações na assinatura ou forma de chamada. A auditoria deve avaliar DTOs internos sem expor mudanças ao Celery. Sem compositores injetáveis sem necessidade comprovada.
**Notes:** Prioridade total em compatibilidade retroativa e zero regressão.

---

## Diagnóstico de Duplicação de Legendas

| Option | Description | Selected |
|--------|-------------|----------|
| Auditar ambas as fontes de risco: 1) Vídeo baixado com legendas queimadas de origem; 2) Passagem duplicada do filtro ass no FFmpeg | Abrange riscos externos e internos | ✓ |
| Focar primariamente na presença de legendas de origem no vídeo base baixado | Apenas análise do vídeo externo | |
| Focar primariamente no desacoplamento entre build_cues_from_script, write_ass_subtitles e o filtro no renderer.py | Apenas análise do código interno | |

**User's choice:** Auditar obrigatoriamente as duas fontes de risco (legendas embutidas no vídeo baixado e duplicidade de filtros/passagens no FFmpeg).
**Notes:** O relatório deve comprovar as causas com evidências, avaliar estratégias de crop/mascaramento e desacoplar o fluxo de legendas. Fase estritamente diagnóstica sem alteração de código.

---

## Diagnóstico de Assets e Formato do Avatar

| Option | Description | Selected |
|--------|-------------|----------|
| Inspeção técnica completa dos arquivos reais (creator_avatar.png e avatar.mp4): canais de cor, alfa, codecs, dimensões, padding branco hardcoded e FPS | Análise técnica aprofundada de formatos e render | ✓ |
| Focar primariamente na remoção do padding branco de borda quadrada que está hardcoded no renderer.py | Análise restrita ao padding | |
| Avaliar apenas dimensões e aspect ratio | Análise restrita a proporção | |

**User's choice:** Inspeção técnica completa dos assets reais (`creator_avatar.png` e `avatar.mp4`), verificando resolução, proporção, padding, canais de cor e canal alfa. Confirmar o efeito do padding branco (`pad=...color=white`) em `renderer.py` sem assumir que removê-lo é suficiente. Avaliar alternativas técnicas de transparência (WebM, ProRes, sequências PNG).
**Notes:** Não implementar alterações de assets nem filtros nesta fase.

---

## Análise de Grafo e Passes FFmpeg

| Option | Description | Selected |
|--------|-------------|----------|
| Identificar todos os passes e comandos FFmpeg atuais (fallback, avatar e final), mapear consumo/tempo e propor grafo single-pass | Mapeamento integral e proposta de consolidação | ✓ |
| Focar estritamente na análise do filter_complex do ReactionVideoRenderer | Análise pontual do filtro final | |
| Mapear opções de otimização de presets e codecs | Avaliação de hardware acceleration | |

**User's choice:** Mapear todos os comandos FFmpeg executados pelo pipeline (fundo fallback, avatar, composição final), identificar codecs, presets, pixel formats, FPS e reencodificações intermediárias desnecessárias. Propor arquitetura single-pass com codificação final única sempre que tecnicamente viável, garantindo rigorosamente 1080x1920 (9:16) em yuv420p.
**Notes:** Fase puramente diagnóstica; não modificar filtros ou presets agora.

---

## the agent's Discretion

Nenhuma área deixada para arbítrio genérico. Todas as diretrizes foram rigorosamente fixadas: foco em diagnóstico baseado em evidências, sem alteração de código durante a Phase 8.

## Deferred Ideas

- Implementação do novo motor de legendas ZUNTO! → Phase 10
- Implementação de recorte/transparência orgânica do avatar → Phase 11
- Refatoração do Video Composer em single-pass → Phase 12
- Validação técnica e visual E2E → Phase 13

