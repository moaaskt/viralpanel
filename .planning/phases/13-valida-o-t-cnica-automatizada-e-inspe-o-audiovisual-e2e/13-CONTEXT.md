# Phase 13: Validação Técnica Automatizada e Inspeção Audiovisual E2E - Context

**Gathered:** 2026-11-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Esta fase entrega a validação técnica e perceptual final do milestone v1.1 — ZUNTO! Visual Engine. Ela garante que todas as melhorias introduzidas nas fases anteriores (Fase 8 à 12: diagnóstico de causas-raiz, roteirização com branding ZUNTO!, motor de legendas desacoplado, recorte orgânico do avatar sem borda branca e composição single-pass 1080x1920 no FFmpeg) sejam comprovadas de ponta a ponta sem regressões.

Entregas:
1. Validador técnico automatizado (`MediaQualityValidator`) baseado em FFprobe para inspeção programática de dimensões (1080x1920), aspect ratio (9:16), taxa de quadros (24 fps), codecs (H.264/AAC), duração e integridade de streams.
2. CLI de teste integrado (`validate-e2e`) e suíte de testes E2E executando cenários reais e com fallback de áudio sem falhas.
3. Pasta dedicada de artefatos de inspeção (`storage/inspection/`) acompanhada por relatório estruturado em Markdown (`INSPECTION-REPORT.md`) com checklist dos critérios visuais críticos.
4. Gate cumulativo formal para conclusão do Milestone v1.1: 100% dos testes técnicos aprovados cumulativamente com a validação humana explícita dos vídeos renderizados.

Fora de escopo: Adição de novas funcionalidades audiovisuais, novos filtros ou alterações no motor de publicação (escopo já fechado nas fases anteriores).

</domain>

<decisions>
## Implementation Decisions

### 1. Estratégia de Inspeção Automatizada de Mídia
- **D-01:** Implementar um módulo reutilizável `MediaQualityValidator` (em `src/viralpanel/studio/validator.py`) que invoca `ffprobe` com saída JSON estruturada, validando especificações técnicas exatas:
  - Resolução: exatos 1080x1920
  - Aspect ratio: 9:16
  - Video stream: codec `h264`, pixel format `yuv420p`, frame rate 24 fps
  - Audio stream: codec `aac`, taxa de amostragem mínima 44100Hz
  - Sincronismo/Duração: coerência entre streams e integridade do container MP4
  — **Reversibility:** reversible — componente utilitário modular e testável.

### 2. Conjunto de Dados de Teste & Execução da Esteira
- **D-02:** Disponibilizar comando CLI integrado (`python -m viralpanel.cli validate-e2e` ou equivalente) combinado com suíte de testes `pytest tests/test_e2e_inspection.py`.
  - O fluxo executa no mínimo dois cenários fim a fim:
    a) Cenário Completo: Vídeo fonte com imagem/áudio + avatar circular orgânico ZUNTO! + legendas ASS ZUNTO!.
    b) Cenário Fallback: Áudio puro (sem stream de vídeo de fundo) ativando o background lavfi `#0f172a` inline single-pass sem gerar arquivos temporários espúrios.
  - Os artefatos gerados são salvos isoladamente em `storage/inspection/`.
  — **Reversibility:** reversible — script de orquestração de testes e CLI utilitário.

### 3. Protocolo e Evidências da Inspeção Visual Humana
- **D-03:** Gerar relatório estruturado em Markdown (`.planning/phases/13-valida-o-t-cnica-automatizada-e-inspe-o-audiovisual-e2e/INSPECTION-REPORT.md` e espelho em `storage/inspection/README.md`) contendo:
  - Metadados técnicos apurados pelo `MediaQualityValidator` para cada vídeo gerado.
  - Checklist dos 4 pilares visuais ZUNTO!:
    1. Ausência total de moldura branca ao redor do avatar circular.
    2. Canal alfa e borda amarela de impacto (#FFDE59) preservados e posicionados em Safe Zone (Y=1300..1600).
    3. Ausência definitiva de duplicação de legendas (apenas camada ASS estilizada ZUNTO! em MarginV=640).
    4. Harmonia estética global e legibilidade do texto e do background.
  — **Reversibility:** reversible — documentação de auditoria e evidências.

### 4. Critérios de Gate para Conclusão do Milestone
- **D-04:** Adotar gate cumulativo estrito: o milestone v1.1 só é formalmente aprovado e concluído quando:
  1. Todos os testes automatizados da suíte (unitários, integração e E2E) estiverem 100% verdes.
  2. Todos os critérios do `MediaQualityValidator` passarem sem ressalvas.
  3. O usuário inspecionar visualmente os vídeos em `storage/inspection/` e fornecer aprovação explícita.
  — **Reversibility:** costly — estabelece o critério de transição de milestone para release do sistema.

### the agent's Discretion
- Parametrização fina de timeouts do `ffprobe` e `ffmpeg` durante a geração de teste (ex: timeout de 180s para renderização).
- Formatação das mensagens no terminal e estrutura de logs durante o comando de validação.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Brand & Safe Zones
- `src/viralpanel/branding.py` — `SafeZones9x16`, cores ZUNTO! (`BRAND_YELLOW_HEX = "#FFDE59"`), margens de avatar e legendas.

### Video Composer & Pipeline
- `src/viralpanel/studio/renderer.py` — `ReactionVideoRenderer`, `StudioRenderRequest`, `ReactionCompositionSpec` e grafo de composição single-pass.
- `src/viralpanel/studio/service.py` — `StudioService.produce`, orquestração dos assets (`audio`, `avatar`, `final_video`).
- `src/viralpanel/studio/subtitles.py` — Geração e formatação de legendas ASS estilo ZUNTO!.
- `src/viralpanel/studio/avatar.py` — Geração de avatar circular com recorte PNG e canal alfa.

### Requisitos e Roadmap
- `.planning/REQUIREMENTS.md` — Requisitos QUAL-01 e QUAL-02 do milestone v1.1.
- `.planning/ROADMAP.md` — Seção da Phase 13.

</canonical_refs>
