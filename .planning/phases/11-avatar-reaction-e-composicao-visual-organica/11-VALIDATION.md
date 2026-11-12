# Validation Strategy: Phase 11 — Avatar Reaction e Composição Visual Orgânica

## Verification Dimensions

### Dimension 1: Recorte Circular e Transparência Nativa (`AVTR-01`, `AVTR-03`)
- **Verificação**: Presença de máscara circular programática com canal alfa suave em `AudioReactiveAvatarAnimator`, eliminando cantos opacos mesmo para imagens de entrada `rgb24`.
- **Asserção de Pixels (Rawvideo RGBA)**: Em frame amostrado de `avatar.mp4`, verificar que os 4 cantos externos do envelope 300x300 possuem canal alfa igual a 0 (`A == 0`).
- **Codec e Formato**: Confirmar via `ffprobe` que `avatar.mp4` intermediário utiliza codec de vídeo `png` em `pix_fmt rgba`.
- **Comando automatizado**: `./.venv/bin/pytest tests/test_studio_avatar.py -k "test_audio_reactive_avatar_animator_circular_alpha" -v`

### Dimension 2: Moldura Circular e Identidade Visual ZUNTO! (`BRND-01`, `BRND-02`)
- **Verificação**: Presença de anel circular de 4px na cor Amarelo de Impacto ZUNTO! (`#FACC15`), contorno suave acompanhando a curvatura do círculo.
- **Asserção de Borda**: Amostrar pixels no raio da borda ($r \approx 148\text{px}$) e confirmar presença da cor `#FACC15` ($R=250, G=204, B=21$).
- **Sincronização SafeZones**: Confirmar que `SafeZones9x16` em `src/viralpanel/branding.py` expõe `AVATAR_SIZE=300`, `AVATAR_MARGIN_RIGHT=54` e `AVATAR_MARGIN_BOTTOM=320`.
- **Comando automatizado**: `./.venv/bin/pytest tests/test_branding.py tests/test_studio_avatar.py -k "test_safe_zones_9x16_constants or test_avatar_border" -v`

### Dimension 3: Confinamento da Onda Sonora Reativa e Transparência de Fundo (`AVTR-01`, `BRND-01`)
- **Verificação**: A onda sonora gerada pelo `showwaves` deve utilizar a cor ZUNTO! (`#FACC15@0.85`), estar geometricamente contida no interior do círculo e possuir fundo transparente (`A == 0` nos pixels onde não há traço sonoro). Teste empírico sobre imagem-base de cor sólida valida que os pixels ao redor da forma de onda preservam a imagem de fundo sem gerar retângulo opaco/preto.
- **Comando automatizado**: `./.venv/bin/pytest tests/test_studio_avatar.py -k "test_showwaves_alpha_transparency or test_audio_reactive_avatar_animator" -v`

### Dimension 4: Composição Visual 9:16 no Renderer (`AVTR-01`, `AVTR-02`)
- **Verificação**: Remoção de `pad=...:color=white` no `ReactionVideoRenderer`. Sobreposição PIP configurada em `W-w-54:H-h-320` com `size=300`, posicionada na faixa vertical canônica $Y=1300\dots1600\text{px}$ e preservação total da transparência sobre o vídeo de fundo.
- **Asserção de Composição e Continuidade**: Frame composto 1080x1920 sobre fundo magenta contrastante deve manter os cantos do envelope do avatar com a cor do fundo de vídeo (magenta R=254-255, G=0, B=253-255), continuidade da borda anelar amarela (#FACC15) e ausência de caixa opaca na região da onda.
- **Comando automatizado**: `./.venv/bin/pytest tests/test_studio_renderer.py -k "test_reaction_renderer_avatar_composition" -v`

### Dimension 5: Integridade de Regressão e Contratos Legados
- **Verificação**: Compatibilidade estrita de `BaseAvatarAnimator`, `AudioReactiveAvatarAnimator`, `MockAvatarAnimator` e `StudioService.produce(db, run_id, script) -> Asset`.
- **Comando automatizado**: `./.venv/bin/pytest tests/ -v`

