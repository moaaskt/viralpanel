# Phase 13: Validação Técnica Automatizada e Inspeção Audiovisual E2E - Discussion Log

**Date:** 2026-11-11
**Phase:** 13
**Status:** Completed

## Areas Discussed & Decisions

### 1. Estratégia de Inspeção Automatizada de Mídia
- **Opções apresentadas:**
  1. Módulo validador reutilizável (`MediaQualityValidator` com saída JSON estruturada de streams, codecs, resolução e fps).
  2. Testes pytest pontuais com chamadas ffprobe diretas.
  3. Validação mista (Integridade de Container + Amostragem de frames).
- **Seleção:** Módulo validador reutilizável (`MediaQualityValidator`).
- **Notas:** Permite uso em testes, CLI e tarefas automatizadas no futuro sem duplicar lógica de probe.

### 2. Conjunto de Dados de Teste & Execução da Esteira
- **Opções apresentadas:**
  1. CLI de Teste Integrado + Suíte Pytest E2E.
  2. Apenas Celery Task em modo real.
  3. Runner standalone independente.
- **Seleção:** CLI de Teste Integrado + Suíte Pytest E2E.
- **Notas:** Testa tanto o fluxo normal completo com vídeo fonte quanto o fluxo de fallback sem vídeo (apenas áudio), gravando saídas em `storage/inspection/`.

### 3. Protocolo e Evidências da Inspeção Visual Humana
- **Opções apresentadas:**
  1. Relatório em Markdown com checklist detalhado + arquivos salvos em `storage/inspection/`.
  2. Apenas pasta organizada de artefatos.
  3. Preview em HTML interativo com player lado a lado.
- **Seleção:** Relatório em Markdown com checklist detalhado + arquivos salvos em `storage/inspection/`.
- **Notas:** Fornece rastreabilidade no repositório com evidências claras para a validação perceptual dos 4 pilares ZUNTO!.

### 4. Critérios de Gate para Conclusão do Milestone
- **Opções apresentadas:**
  1. Gate cumulativo estrito (Automação 100% verde + Confirmação Humana Explícita).
  2. Gate técnico prioritário (apenas testes automatizados verdes).
- **Seleção:** Gate cumulativo estrito.
- **Notas:** Garante que o milestone v1.1 só seja finalizado após inspeção humana direta dos vídeos gerados.

