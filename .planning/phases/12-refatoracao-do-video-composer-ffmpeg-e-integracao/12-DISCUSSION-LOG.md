# Phase 12: Refatoração do Video Composer FFmpeg e Integração - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-08
**Phase:** 12-refatoracao-do-video-composer-ffmpeg-e-integracao
**Areas discussed:** Unificação de grafo e artefato avatar.mp4, Fallback visual sem arquivo temporário, Parâmetros de encoding e qualidade CRF, DTO StudioRenderRequest

---

## 1. Unificação do grafo e artefato avatar.mp4 perante Single-Pass

| Option | Description | Selected |
|--------|-------------|----------|
| Manter avatar.mp4 (PNG/RGBA) para persistir o Asset no banco e compor no grafo final em passe de codificação única | Preserva contratos com Celery e PostgreSQL sem passes adicionais | ✓ |
| Dois passos físicos com intermediários arbitrários | Não atende plenamente o conceito de single-pass | |
| Eliminar avatar.mp4 do banco e do disco | Quebraria a tabela de Assets e os contratos do v1.0 | |

**User's choice:** Manter geração de avatar.mp4 (com PNG/RGBA) para preservar o Asset no banco e compor diretamente no grafo final em passe único.
**Notes:** O single-pass refere-se a evitar reencodificações intermediárias desnecessárias na composição final.

---

## 2. Tratamento do fallback visual quando source não tem vídeo

| Option | Description | Selected |
|--------|-------------|----------|
| Gerar fundo escuro inline via entrada lavfi (`color=c=#0f172a:s=1080x1920`) direto no filter_complex | Elimina completamente o arquivo source_visual_bg.mp4 em disco | ✓ |
| Manter arquivo físico intermediário source_visual_bg.mp4 | Gasto desnecessário de I/O em disco | |

**User's choice:** Gerar fundo de fallback diretamente como entrada lavfi no comando principal.
**Notes:** Menos I/O de disco, maior velocidade e simplificação arquitetural.

---

## 3. Parâmetros de encoding e qualidade CRF

| Option | Description | Selected |
|--------|-------------|----------|
| `preset="veryfast"`, `crf=20`, áudio `aac 192k`, `fps=24` | Equilíbrio ideal entre tempo de renderização e alta fidelidade visual 1080x1920 | ✓ |
| `preset="ultrafast"` | Menor eficiência de compressão | |
| `preset="medium"`, `crf=18` | Muito lento para automação diária | |

**User's choice:** `preset="veryfast"`, `crf=20`, áudio `aac 192k`, `fps=24`.
**Notes:** Alta qualidade visual para TikTok/Reels/Shorts sem sobrecarregar a máquina.

---

## 4. DTO StudioRenderRequest e contratos de interface

| Option | Description | Selected |
|--------|-------------|----------|
| Adotar DTO StudioRenderRequest internamente, mantendo assinatura de render() retrocompatível | Preserva 100% dos testes e callers existentes sem atrito | ✓ |
| Mudar assinatura pública de render() exclusivamente para DTO | Quebraria testes legados e chamadas diretas | |

**User's choice:** Adotar DTO internamente mantendo assinatura pública com kwargs compatíveis.
**Notes:** Evolução limpa e segura sem quebrar o pipeline.

---

## the agent's Discretion

- Organização interna do método de renderização com overload ou factory method.
- Timeout de subprocesso FFmpeg (120s).

## Deferred Ideas

- Nenhuma ideia adiada nesta fase.
