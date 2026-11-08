# Validation Strategy: Phase 12 — Refatoração do Video Composer FFmpeg e Integração

## Verification Dimensions

### Dimension 1: Composição Integrada Single-Pass e Eliminação de Fallback em Disco (`COMP-01`)
- **Verificação**: `ReactionVideoRenderer` executa a composição em passe único sem gerar arquivos temporários `source_visual_bg.mp4` em disco. Quando `source_video` não possui stream de vídeo, o fundo escuro é gerado inline via lavfi (`color=c=#0f172a:s=1080x1920:r=24:d=...`).
- **Asserção**: Validação de que nenhum arquivo `source_visual_bg.mp4` é criado no sistema de arquivos durante a execução.
- **Comando automatizado**: `./.venv/bin/pytest tests/test_studio_renderer.py -k "test_single_pass_composition_no_disk_fallback" -v`

### Dimension 2: Parâmetros Técnicos de Saída e Qualidade Visual (`COMP-02`, `BRND-01`, `BRND-02`)
- **Verificação**: O vídeo final gerado possui resolução exata 1080x1920 (aspect ratio 9:16), codec de vídeo `h264` (`pix_fmt yuv420p`), codec de áudio `aac` (192k) e taxa de quadros 24 fps, codificado com `preset=veryfast` e `crf=20`.
- **Asserção**: Inspeção de propriedades de formato e stream via `ffprobe` e asserção de linha de comando FFmpeg.
- **Comando automatizado**: `./.venv/bin/pytest tests/test_studio_renderer.py -k "test_reaction_renderer_output_specs_and_encoding_flags" -v`

### Dimension 3: DTOs Tipados e Preservação de Contratos Celery/Studio (`COMP-03`)
- **Verificação**: `ReactionVideoRenderer` aceita instâncias de `StudioRenderRequest` e chamadas legadas com argumentos nomeados/posicionais. `StudioService.produce` preserva a criação dos 3 registros `Asset` (`audio`, `avatar`, `final_video`) vinculados ao `script.id` e o status `script.source_video.status = "produced"`.
- **Asserção**: Criação íntegra dos registros de banco de dados e compatibilidade com o pipeline de tarefas Celery.
- **Comando automatizado**: `./.venv/bin/pytest tests/test_studio_renderer.py tests/test_celery_tasks.py -k "test_studio_service_renders_vertical_9x16_reaction_video or test_task_records_run_and_is_idempotent" -v`

### Dimension 4: Ausência de Regressões Globais
- **Verificação**: Execução integral da suíte de testes do repositório (86+ testes) com 100% de sucesso.
- **Comando automatizado**: `./.venv/bin/pytest tests/ -v`
