# Phase 11: Avatar Reaction e Composição Visual Orgânica - Context

**Gathered:** 2026-11-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Esta fase entrega o avatar reaction visualmente orgânico, eliminando de forma definitiva o problema de "adesivo/imagem quadrada" diagnosticado na Phase 8 (08-AUDIT-REPORT.md Seção 3).
Ela refatora a preparação e animação do avatar em `src/viralpanel/studio/avatar.py`, além de definir o DTO `AvatarConfig` (ou `AvatarJobConfig`) e as regras de composição de canal alfa e borda circular para consumo pelo `ReactionVideoRenderer`.

Entregas:
1. Eliminação do fundo retangular opaco: aplicação de máscara circular programática com canal alfa em memória (`yuva420p` / `rgba`), aceitando qualquer imagem fonte (RGB opaco ou RGBA nativo) sem forçar o usuário a ter um PNG pré-cortado.
2. Contorno circular sutil: borda refinada de 3px a 4px no Amarelo de Impacto ZUNTO! (`#FACC15`), harmonizada com a paleta oficial centralizada em `branding.py`.
3. Calibração de dimensão e safe zone: diâmetro calibrado em 300px (ou parametrizável entre 280–320px) posicionado no canto inferior direito (`X=W-w-54`, `Y=H-h-320`), ocupando a faixa vertical segura $Y = 1300\dots1600\text{px}$ (para $H=1920$ e $h=300$, $1920 - 300 - 320 = 1300$), sem colidir com as legendas ZUNTO! ($Y \approx 1080\dots1280\text{px}$) nem com os botões nativos das plataformas (TikTok, Reels, Shorts).
4. Onda sonora reativa (`showwaves`) integrada: visualizador de áudio contido organicamente na base interna do círculo, estilizado na cor ZUNTO! (`#FACC15@0.85`), sem vazar para fora da máscara circular.
5. Preservação de contratos legados da v1.0: `BaseAvatarAnimator`, `AudioReactiveAvatarAnimator`, `MockAvatarAnimator` e a geração de `avatar.mp4` para manter intactos os 3 registros `Asset` do `StudioService`.

Fora de escopo: unificação de todos os passes no grafo single-pass definitivo (Phase 12), inspeção audiovisual em telas físicas (Phase 13).

</domain>

<decisions>
## Implementation Decisions

### 1. Técnica de Recorte e Transparência
- **D-01:** Máscara circular programática via filtros nativos do FFmpeg (`format=yuva420p`, gerador de máscara circular ou expressão alfa) aplicada diretamente sobre a imagem de entrada.
  - **Reversibility:** costly — define o pipeline de renderização do avatar e sua transparência.
  - O sistema aceita qualquer imagem base (seja o PNG padrão `creator_avatar.png` que é `rgb24` opaco, ou fotos reais de criadores em JPG/PNG), gerando transparência nos cantos externos sem exigir intervenção manual.
  - Tratamento conjunto dos cenários mapeados na auditoria: substitui o `format=yuv420p` e os pads retangulares opacos por composição preservando canal alfa (`yuva420p` / `movflags=faststart` ou stream com alfa).

### 2. Moldura e Identidade Visual ZUNTO!
- **D-02:** Borda circular sutil de 3px a 4px na cor oficial `ZuntoPalette.IMPACT_YELLOW` (`#FACC15`), consumida diretamente de `src/viralpanel/branding.py`.
  - **Reversibility:** reversible — parâmetro visual do contorno.
  - Elimina a antiga moldura branca retangular rígida de 6px (`pad=...:color=white`).
  - O contorno acompanha perfeitamente a curvatura do círculo, criando acabamento profissional e destacando o apresentador sobre qualquer tipo de vídeo de fundo.

### 3. Dimensão e Safe Zone no Layout 9:16 (1080x1920)
- **D-03:** Dimensão calibrada em 300px de diâmetro, posicionada no canto inferior direito em `X=W-w-54`, `Y=H-h-320` (faixa vertical $Y = 1300\dots1600\text{px}$, pois $1920 - 300 - 320 = 1300$).
  - **Reversibility:** reversible — coordenadas do overlay.
  - Respeita rigorosamente a Safe Zone do `SafeZones9x16` de `branding.py`.
  - Isola espacialmente o avatar: a faixa $Y=1080\dots1280\text{px}$ fica reservada para as legendas ZUNTO!, a faixa $Y=1300\dots1600\text{px}$ para o avatar PIP (garantindo 20px de respiro abaixo das legendas), e a margem inferior de 320px ($Y > 1600\text{px}$) permanece livre para a interface de título/som do TikTok/Reels/Shorts.

### 4. Onda Sonora Reativa (Showwaves) Integrada
- **D-04:** Onda sonora mantida e refinada na cor ZUNTO! Amarelo de Impacto (`#FACC15@0.85`), confinada geometricamente dentro da máscara circular.
  - **Reversibility:** reversible — filtro de áudio/vídeo.
  - Evita que a onda apareça verde ou desbotada (problema detectado na auditoria pela conversão prematura para yuv420p).
  - A onda sonora reage dinamicamente à amplitude da narração, fornecendo feedback visual de fala sem quebrar a harmonia do círculo.

### 5. DTO e Preservação de Contratos
- **D-05:** Criar o DTO `AvatarConfig` (ou `AvatarJobConfig`) em `avatar.py`, preservando as interfaces `BaseAvatarAnimator.generate_avatar_video(audio_path, output_path, avatar_image_path) -> tuple[Path, float]`.
  - **Reversibility:** costly — contrato entre StudioService e AvatarAnimator.
  - Mantém compatibilidade com `MockAvatarAnimator` e com as tasks Celery.

### the agent's Discretion
- Expressão exata do grafo FFmpeg para gerar a máscara circular e a borda suave (ex.: `geq=r='...':a='if(lte(hypot(X-W/2,Y-H/2),R),255,0)'` ou composição via `lavfi color` + `maskedmerge` / `drawbox`).
- Ajuste fino da espessura da borda entre 3px e 4px para nitidez ideal em 1080x1920 sem serrilhamento.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Auditoria e Diagnósticos
- `.planning/phases/08-auditoria-contratos-e-diagn-stico-de-causa-raiz/08-AUDIT-REPORT.md` — Seção 3 (Diagnóstico de Assets e Formato do Avatar Reaction, distinção dos 4 cenários de caixa quadrada) e Seção 1.5 (DTO AvatarConfig).

### Brand & Safe Zones
- `src/viralpanel/branding.py` — Paleta oficial ZUNTO! (`IMPACT_YELLOW="#FACC15"`, `DEEP_BLACK="#0A0A0A"`), `SafeZones9x16` (`AVATAR_SIZE=340`, `AVATAR_X="W-w-54"`, `AVATAR_Y="H-h-320"`).

### Módulos do Studio
- `src/viralpanel/studio/avatar.py` — Implementação atual de `ensure_default_avatar_image`, `AudioReactiveAvatarAnimator` e `MockAvatarAnimator`.
- `src/viralpanel/studio/renderer.py` — Consumo de `avatar_path` e filtros de overlay PIP.
- `tests/test_studio_avatar.py` — Suíte de testes existente do avatar.

</canonical_refs>

