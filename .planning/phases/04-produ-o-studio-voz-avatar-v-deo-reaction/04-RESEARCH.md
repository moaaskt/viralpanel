# Phase 4 Research: Produção Studio (Voz, Avatar & Vídeo Reaction)

## 1. Contexto & Requisitos
- **PROD-01**: Módulo de síntese de voz (TTS) gera áudio narrado com voz clonada do criador utilizando XTTS v2 / Voice Studio através de interface modular abstrata (`BaseVoiceSynthesizer`).
- **PROD-02**: Módulo gerador de avatar sincroniza movimentos do avatar virtual do criador (SadTalker / LivePortrait / Wav2Lip ou mock/vídeo de overlay pré-renderizado) com a narração gerada.
- **PROD-03**: Módulo de composição via FFmpeg gera o vídeo final vertical 9:16 (1080x1920) em formato reaction (vídeo de referência ao fundo/topo, avatar do criador em overlay com borda/recorte e legendas sincronizadas queimadas com filtro `drawtext` ou `subtitles`).

## 2. Decisões Técnicas e Arquitetura
1. **Síntese de Voz Modular (`src/viralpanel/studio/voice.py`)**:
   - `BaseVoiceSynthesizer(ABC)` com método `synthesize(text: str, output_path: Path, speaker_wav: Path | None = None) -> Path`.
   - `XTTSVoiceSynthesizer` para inferência local com XTTS v2 (ou chamada a servidor de voz / microserviço).
   - `MockVoiceSynthesizer` gerando áudio sintético com tom/duração aproximada via FFmpeg lavfi `sine` ou `flite` para testes rápidos sem depender de GPU.
2. **Avatar Reaction Sincronizado (`src/viralpanel/studio/avatar.py`)**:
   - `BaseAvatarAnimator(ABC)` com método `generate_avatar_video(audio_path: Path, output_path: Path) -> Path`.
   - `SadTalkerAvatarAnimator` / `LivePortraitAnimator` que recebe uma imagem de referência do criador e sincroniza lábios com o áudio narrado.
   - `MockAvatarAnimator` gerando vídeo sintético em loop do avatar com FFmpeg para testes e ambientes sem GPU.
3. **Pipeline de Renderização Reaction 9:16 (`src/viralpanel/studio/renderer.py`)**:
   - `ReactionVideoRenderer`:
     - Resolução padrão: 1080x1920 (9:16 vertical, padrão TikTok/Reels/Shorts).
     - Layout:
       - Vídeo de referência redimensionado e centralizado no topo ou fundo.
       - Avatar do criador posicionado em overlay (canto inferior direito ou PIP com moldura arredondada).
       - Legendas animadas / sincronizadas via arquivo SRT/ASS gerado automaticamente a partir da transcrição/timing do roteiro.
       - Mixagem de áudio: voz clonada em destaque (0dB) + áudio do vídeo original atenuado (-14dB) para criar ambientação autêntica de reaction.
4. **Integração no Celery (`src/viralpanel/tasks.py`)**:
   - Etapa diária: avança para stage="production" -> gera voz -> anima avatar -> renderiza vídeo final 9:16 -> persiste em `Asset(asset_type="final_video")`.
