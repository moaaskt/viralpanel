from dataclasses import FrozenInstanceError
from pathlib import Path
import shutil
import subprocess

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from viralpanel.branding import (
    FontResolutionError,
    SafeZones9x16,
    ZuntoPalette,
    hex_to_ass_color,
    resolve_typography_font,
)
from viralpanel.database import Base
from viralpanel.models import Asset, Script, SourceVideo
from viralpanel.storage import StorageManager
from viralpanel.studio.avatar import (
    AudioReactiveAvatarAnimator,
    MockAvatarAnimator,
    ensure_default_avatar_image,
)
from viralpanel.studio.renderer import (
    ReactionCompositionSpec,
    ReactionVideoRenderer,
    StudioRenderRequest,
    build_reaction_filter_complex,
    calculate_stage_foreground_dimensions,
    classify_stage_strategy,
    has_video_stream,
    probe_video_dimensions,
)
from viralpanel.studio.service import StudioService
from viralpanel.studio.subtitles import (
    SubtitleJobConfig,
    build_cues_from_script,
    generate_subtitles,
    write_ass_subtitles,
)
from viralpanel.studio.voice import MockVoiceSynthesizer


def test_studio_render_request_dto():
    """Valida DTOs imutáveis ReactionCompositionSpec e StudioRenderRequest (D-03, D-04)."""
    spec = ReactionCompositionSpec()
    assert spec.target_width == 1080
    assert spec.target_height == 1920
    assert spec.fps == 24
    assert spec.video_codec == "libx264"
    assert spec.preset == "veryfast"
    assert spec.crf == 20
    assert spec.pix_fmt == "yuv420p"
    assert spec.audio_codec == "aac"
    assert spec.audio_bitrate == "192k"
    assert spec.single_pass is True
    assert spec.timeout_seconds == 180

    with pytest.raises(FrozenInstanceError):
        spec.preset = "slow"  # type: ignore

    req = StudioRenderRequest(
        run_id="run-123",
        source_video_path="/tmp/source.mp4",  # type: ignore
        avatar_video_path="/tmp/avatar.mp4",  # type: ignore
        voice_audio_path="/tmp/voice.wav",  # type: ignore
        ass_subtitle_path="/tmp/subs.ass",  # type: ignore
        output_path="/tmp/out.mp4",  # type: ignore
    )

    assert isinstance(req.source_video_path, Path)
    assert req.source_video_path == Path("/tmp/source.mp4")
    assert isinstance(req.avatar_video_path, Path)
    assert req.avatar_video_path == Path("/tmp/avatar.mp4")
    assert isinstance(req.voice_audio_path, Path)
    assert req.voice_audio_path == Path("/tmp/voice.wav")
    assert isinstance(req.ass_subtitle_path, Path)
    assert req.ass_subtitle_path == Path("/tmp/subs.ass")
    assert isinstance(req.output_path, Path)
    assert req.output_path == Path("/tmp/out.mp4")
    assert req.composition == spec
    assert req.voice_duration is None
    assert req.avatar_config is None

    with pytest.raises(FrozenInstanceError):
        req.run_id = "run-999"  # type: ignore


def test_ass_subtitles_generation(tmp_path):
    cues = build_cues_from_script(
        "Pare de esperar motivação. Comece agora com cinco minutos de foco.",
        total_duration=4.0,
        max_words_per_cue=4,
    )
    assert len(cues) >= 2
    ass_file = write_ass_subtitles(cues, tmp_path / "subs.ass")
    content = ass_file.read_text(encoding="utf-8")
    assert "[V4+ Styles]" in content
    assert "Dialogue:" in content


def test_studio_service_renders_vertical_9x16_reaction_video(tmp_path):
    eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    factory = sessionmaker(bind=eng, expire_on_commit=False)

    service = StudioService(
        voice_synthesizer=MockVoiceSynthesizer(min_duration=1.5, max_duration=3.0),
        avatar_animator=MockAvatarAnimator(width=240, height=240),
        storage=StorageManager(tmp_path),
    )

    with factory() as db:
        src = SourceVideo(url="https://www.tiktok.com/@creator/video/99", author="creator", score=95.0)
        db.add(src)
        db.flush()
        script = Script(
            source_video_id=src.id,
            hook="Pare de adiar seus objetivos.",
            script_text="Pare de adiar seus objetivos. Cinco minutos hoje valem mais que promessas amanhã.",
            version=1,
        )
        db.add(script)
        db.commit()

        final_asset = service.produce(db=db, run_id="run-studio-1", script=script)
        assert final_asset.asset_type == "final_video"
        assert final_asset.duration_seconds and final_asset.duration_seconds >= 1.4

        width, height = probe_video_dimensions(tmp_path / "runs" / "run-studio-1" / "assets" / "final_reaction_9x16.mp4")
        assert (width, height) == (1080, 1920)
        assert src.status == "produced"

        all_assets = db.scalars(select(Asset).where(Asset.script_id == script.id)).all()
        asset_types = {a.asset_type for a in all_assets}
        assert {"audio", "avatar", "final_video"}.issubset(asset_types)

        # Validação do arquivo captions.ass gerado em service.produce (D-01, D-05)
        captions_path = tmp_path / "runs" / "run-studio-1" / "assets" / "captions.ass"
        assert captions_path.exists(), "captions.ass deve ser gerado em service.produce"
        ass_content = captions_path.read_text(encoding="utf-8")

        # 1. Validar BorderStyle=3, MarginL=80, MarginR=440, MarginV=365 e cor de fundo &H000A0A0A&
        assert "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding" in ass_content
        assert (
            f",3,16,0,2,{SafeZones9x16.SUBTITLE_MARGIN_LEFT},"
            f"{SafeZones9x16.SUBTITLE_MARGIN_RIGHT},{SafeZones9x16.SUBTITLE_MARGIN_V},1"
        ) in ass_content, (
            f"Estilo Default deve conter BorderStyle=3, Outline=16, Alignment=2, MarginL={SafeZones9x16.SUBTITLE_MARGIN_LEFT}, MarginR={SafeZones9x16.SUBTITLE_MARGIN_RIGHT} e MarginV={SafeZones9x16.SUBTITLE_MARGIN_V}"
        )
        deep_black_ass = hex_to_ass_color(ZuntoPalette.DEEP_BLACK)  # &H000A0A0A&
        assert deep_black_ass in ass_content, f"Cor da caixa opaca {deep_black_ass} deve estar no cabeçalho ASS"
        assert "Dialogue: 0," in ass_content, "Eventos de diálogo devem estar presentes no arquivo ASS"


def test_studio_service_produce_encapsulates_studio_render_request(tmp_path):
    """Valida que StudioService.produce instancia e delega via StudioRenderRequest (D-04, COMP-03)."""
    eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    factory = sessionmaker(bind=eng, expire_on_commit=False)

    received_requests: list[StudioRenderRequest] = []

    class SpyRenderer:
        def render_from_request(self, request: StudioRenderRequest) -> tuple[Path, float]:
            received_requests.append(request)
            request.output_path.parent.mkdir(parents=True, exist_ok=True)
            request.output_path.write_bytes(b"SPY_OUTPUT_VIDEO")
            return request.output_path, 3.5

    spy_renderer = SpyRenderer()
    service = StudioService(
        voice_synthesizer=MockVoiceSynthesizer(min_duration=2.0, max_duration=2.0),
        avatar_animator=MockAvatarAnimator(width=240, height=240),
        renderer=spy_renderer,  # type: ignore
        storage=StorageManager(tmp_path),
    )

    with factory() as db:
        src = SourceVideo(url="https://www.tiktok.com/@creator/video/101", author="creator", score=90.0)
        db.add(src)
        db.flush()
        script = Script(
            source_video_id=src.id,
            hook="Hook de teste",
            script_text="Texto do script de teste para validar o DTO tipado StudioRenderRequest.",
            version=1,
        )
        db.add(script)
        db.commit()

        final_asset = service.produce(db=db, run_id="run-spy-dto", script=script)

        # 1. Validação da delegação ao DTO StudioRenderRequest
        assert len(received_requests) == 1
        req = received_requests[0]
        assert isinstance(req, StudioRenderRequest)
        assert req.run_id == "run-spy-dto"
        assert req.source_video_path.name == "source.mp4"
        assert req.avatar_video_path.name == "avatar.mp4"
        assert req.voice_audio_path.name == "narration.wav"
        assert req.ass_subtitle_path.name == "captions.ass"
        assert req.output_path.name == "final_reaction_9x16.mp4"
        assert req.voice_duration == 2.0
        assert req.avatar_config == service.avatar_config
        assert req.composition == service.composition

        # 2. Validação dos contratos e persistência atômica
        assert final_asset.asset_type == "final_video"
        assert final_asset.duration_seconds == 3.5
        assert src.status == "produced"

        assets = db.scalars(select(Asset).where(Asset.script_id == script.id)).all()
        assert len(assets) == 3
        types = {a.asset_type for a in assets}
        assert types == {"audio", "avatar", "final_video"}


def test_reaction_renderer_single_ass_layer_and_path_escape(tmp_path, monkeypatch):
    """Garante camada única de legenda e escape blindado de caminhos no FFmpeg (T-10-04, SUB-02)."""
    captured_commands = []

    original_run = subprocess.run

    def mock_run(cmd, *args, **kwargs):
        captured_commands.append(cmd)
        # Se for ffprobe de dimensões/duração, retorna dummy
        if cmd[0] == "ffprobe":
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='{"streams":[{"width":1080,"height":1920}]}', stderr="")
        # Para ffmpeg, cria o arquivo de saída fake se aplicável
        out_file = Path(cmd[-1])
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_bytes(b"MOCKRENDER")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(shutil, "which", lambda x: "/usr/bin/" + x)

    renderer = ReactionVideoRenderer(width=1080, height=1920)

    # Cria caminhos fictícios com caracteres especiais (dois pontos e barras)
    source_vid = tmp_path / "source.mp4"
    source_vid.write_bytes(b"DUMMY_SOURCE")
    avatar_vid = tmp_path / "avatar.mp4"
    avatar_vid.write_bytes(b"DUMMY_AVATAR")
    audio_file = tmp_path / "audio.wav"
    audio_file.write_bytes(b"DUMMY_AUDIO")
    ass_file = tmp_path / "captions_zunto.ass"
    ass_file.write_text("[Script Info]\nTitle: Test\n", encoding="utf-8")
    output_vid = tmp_path / "output.mp4"

    # Força duration positiva
    monkeypatch.setattr("viralpanel.studio.renderer.probe_duration", lambda p: 3.0)
    monkeypatch.setattr("viralpanel.studio.renderer.has_video_stream", lambda p: True)

    out, dur = renderer.render(
        source_video_path=source_vid,
        avatar_video_path=avatar_vid,
        voice_audio_path=audio_file,
        ass_subtitle_path=ass_file,
        output_path=output_vid,
    )

    assert out == output_vid
    assert dur == 3.0

    # Localizar a chamada principal do FFmpeg
    ffmpeg_cmds = [c for c in captured_commands if c[0] == "ffmpeg" and "-filter_complex" in c]
    assert len(ffmpeg_cmds) == 1, "Deve haver exatamente 1 execução de FFmpeg com filter_complex"

    cmd = ffmpeg_cmds[0]
    filter_idx = cmd.index("-filter_complex") + 1
    filter_complex_str = cmd[filter_idx]

    # Validar camada única: o filtro ass= deve aparecer exatamente UMA vez com fontsdir obrigatório
    assert filter_complex_str.count("ass='") == 1, (
        f"Filtro ass='...' deve ocorrer exatamente 1 vez, sem duplicação de legendas. Encontrado: {filter_complex_str}"
    )
    assert "[composed]ass='" in filter_complex_str and ":fontsdir='" in filter_complex_str and filter_complex_str.endswith("'[vout]"), (
        "Legendas devem ser aplicadas na camada final sobre [composed] com fontsdir explícito"
    )

    # Validar escape de caminhos: dois pontos devem ser escapados como \\:
    escaped_expected = str(ass_file.resolve()).replace("\\", "/").replace(":", "\\:")
    assert f"ass='{escaped_expected}':fontsdir='" in filter_complex_str, (
        f"Caminho do arquivo ASS e fontsdir devem ser rigidamente escapados. Esperado ass='{escaped_expected}':fontsdir='...'"
    )

    # Validar remoção do pad retangular branco (Cenário 3 da auditoria) e overlay em safe zone calibrada
    assert "color=white" not in filter_complex_str, (
        "Filtro pad retangular branco (color=white) deve ser completamente removido de filter_complex"
    )
    expected_overlay = (
        f"overlay=W-w-{SafeZones9x16.AVATAR_MARGIN_RIGHT}:H-h-{SafeZones9x16.AVATAR_MARGIN_BOTTOM}:shortest=1"
    )
    assert expected_overlay in filter_complex_str, (
        f"Overlay do avatar deve estar posicionado na safe zone ({expected_overlay})"
    )


def test_empirical_reference_frame_ass_rendering(tmp_path):
    """Validação geométrica empírica: renderiza frame 1080x1920 com FFmpeg/libass e analisa pixels da caixa opaca.

    Metadados & Governança (D-01, SUB-01, Phase 13 Delegation):
    ----------------------------------------------------------
    - Demonstra que a posição efetiva da caixa opaca (#0A0A0A) depende de:
      * Alignment = 2 (alinhamento inferior central no padrão ASS)
      * PlayResY = 1920 (espaço de coordenadas vertical)
      * FontSize = 64px
      * Outline / box_padding = 16px (em BorderStyle=3 funciona como padding da caixa)
      * MarginV = 365px (distância nominal a partir da base inferior)
    - Inspeciona empiricamente a presença de pixels da caixa opaca (#0A0A0A) na região segura
      (Y ≈ 1080px a 1280px) sobre fundo contrastante magenta.
    - Delegação Formal: A comprovação visual definitiva perante as interfaces dinâmicas dos apps móveis
      (TikTok, Instagram Reels e YouTube Shorts) e variações de hard-subs de vídeos de terceiros
      fica formalmente delegada à inspeção audiovisual da Phase 13.
    """
    if shutil.which("ffmpeg") is None:
        pytest.skip("FFmpeg não disponível para teste empírico de renderização")

    # Verificar se o ffmpeg suporta o filtro ass
    proc_check = subprocess.run(["ffmpeg", "-filters"], capture_output=True, text=True)
    if "ass" not in proc_check.stdout:
        pytest.skip("FFmpeg sem suporte a libass (filtro ass ausente)")

    resolved_font = resolve_typography_font()
    ass_path = tmp_path / "reference_zunto.ass"
    job_cfg = SubtitleJobConfig(
        script_text="Você não sabia. Agora sabe.",
        total_duration=3.0,
        output_path=ass_path,
        margin_v=SafeZones9x16.SUBTITLE_MARGIN_V,
        font_size=64,
        box_padding=16,
        resolved_font=resolved_font,
    )
    generate_subtitles(job_cfg)
    assert ass_path.exists()

    escaped_ass = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    escaped_fontsdir = str(resolved_font.fonts_dir).replace("\\", "/").replace(":", "\\:")
    raw_frame_path = tmp_path / "ref_frame_1080x1920.raw"

    # Renderiza 1 frame de referência 1080x1920 sobre fundo magenta (RGB: 255, 0, 255)
    render_cmd = [
        "ffmpeg",
        "-y",
        "-f", "lavfi",
        "-i", "color=c=magenta:s=1080x1920:d=0.1",
        "-vf", f"ass='{escaped_ass}':fontsdir='{escaped_fontsdir}'",
        "-vframes", "1",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        str(raw_frame_path),
    ]

    subprocess.run(render_cmd, check=True, capture_output=True)
    assert raw_frame_path.exists()

    raw_bytes = raw_frame_path.read_bytes()
    expected_size = 1080 * 1920 * 3  # 6.220.800 bytes
    assert len(raw_bytes) == expected_size, f"Tamanho do raw frame deve ser {expected_size} bytes"

    def get_pixel_rgb(x: int, y: int) -> tuple[int, int, int]:
        idx = (y * 1080 + x) * 3
        return raw_bytes[idx], raw_bytes[idx + 1], raw_bytes[idx + 2]

    # 1. Regiões fora da safe zone de legendas devem preservar o fundo magenta (R≈255, G≈0, B≈255)
    top_r, top_g, top_b = get_pixel_rgb(540, 500)
    assert top_r > 200 and top_g < 30 and top_b > 200, "Topo deve permanecer fundo magenta"

    bot_r, bot_g, bot_b = get_pixel_rgb(540, 1700)
    assert bot_r > 200 and bot_g < 30 and bot_b > 200, "Base inferior deve permanecer fundo magenta"

    # 2. Inspecionar empiricamente a presença da caixa opaca ZUNTO! (#0A0A0A) no terço inferior (Y 1400..1580, X 80..656)
    dark_box_pixels = 0
    for y in range(SafeZones9x16.SUBTITLE_Y_MIN, SafeZones9x16.SUBTITLE_Y_MAX + 1):
        for x in range(SafeZones9x16.SUBTITLE_MARGIN_LEFT, 657):
            r, g, b = get_pixel_rgb(x, y)
            if r <= 25 and g <= 25 and b <= 25:
                dark_box_pixels += 1

    assert dark_box_pixels > 1000, (
        f"A caixa opaca ZUNTO! (#0A0A0A) deve estar presente na faixa SafeZone Y {SafeZones9x16.SUBTITLE_Y_MIN}-{SafeZones9x16.SUBTITLE_Y_MAX}. Encontrados {dark_box_pixels} pixels."
    )


def test_avatar_reaction_overlay_pixel_transparency_and_no_white_box(tmp_path):
    """Renderiza composição real 1080x1920 sobre fundo magenta e valida transparência e anel amarelo per AVTR-01, AVTR-02 e BRND-01."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("FFmpeg não disponível para teste empírico de composição")

    # 1. Gera áudio de narração mock e avatar com recorte circular em canal alfa
    voice_path = tmp_path / "voice_sample.wav"
    MockVoiceSynthesizer(min_duration=1.5, max_duration=2.0).synthesize("Você não sabia. Agora sabe.", voice_path)

    img_path = tmp_path / "creator_avatar.png"
    ensure_default_avatar_image(img_path)

    avatar_video_path = tmp_path / "avatar_circular.mp4"
    animator = AudioReactiveAvatarAnimator(default_avatar_image=img_path)
    animator.generate_avatar_video(voice_path, avatar_video_path)
    assert avatar_video_path.exists()

    # 2. Gera vídeo base com fundo magenta puro (#FF00FF / RGB: 255, 0, 255)
    source_video_path = tmp_path / "source_magenta.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f", "lavfi",
            "-i", "color=c=magenta:s=1080x1920:r=24:d=2.0",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(source_video_path),
        ],
        check=True,
        capture_output=True,
    )

    # 3. Gera legenda ASS em safe zone
    ass_path = tmp_path / "subtitles_zunto.ass"
    job_cfg = SubtitleJobConfig(
        script_text="Você não sabia. Agora sabe.",
        total_duration=2.0,
        output_path=ass_path,
        margin_v=SafeZones9x16.SUBTITLE_MARGIN_V,
    )
    generate_subtitles(job_cfg)

    # 4. Executa composição com ReactionVideoRenderer
    final_output_path = tmp_path / "final_reaction_composed.mp4"
    renderer = ReactionVideoRenderer(width=1080, height=1920)
    out_file, duration = renderer.render(
        source_video_path=source_video_path,
        avatar_video_path=avatar_video_path,
        voice_audio_path=voice_path,
        ass_subtitle_path=ass_path,
        output_path=final_output_path,
    )
    assert out_file == final_output_path
    assert final_output_path.exists()

    # 5. Extrai o primeiro frame do vídeo composto em rawvideo rgb24 (1080x1920)
    raw_frame_path = tmp_path / "composed_frame_1080x1920.raw"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i", str(final_output_path),
            "-vframes", "1",
            "-f", "rawvideo",
            "-pix_fmt", "rgb24",
            str(raw_frame_path),
        ],
        check=True,
        capture_output=True,
    )
    assert raw_frame_path.exists()

    raw_bytes = raw_frame_path.read_bytes()
    expected_size = 1080 * 1920 * 3  # 6.220.800 bytes
    assert len(raw_bytes) == expected_size, f"Tamanho do raw frame deve ser {expected_size} bytes"

    def get_pixel_rgb(x: int, y: int) -> tuple[int, int, int]:
        idx = (y * 1080 + x) * 3
        return raw_bytes[idx], raw_bytes[idx + 1], raw_bytes[idx + 2]

    # Amostragem no quadrante calibrado do avatar (X in [680, 940], Y in [1360, 1620], size=260):
    box_x0 = SafeZones9x16.WIDTH - SafeZones9x16.AVATAR_SIZE - SafeZones9x16.AVATAR_MARGIN_RIGHT  # 680
    box_y0 = SafeZones9x16.HEIGHT - SafeZones9x16.AVATAR_SIZE - SafeZones9x16.AVATAR_MARGIN_BOTTOM  # 1360
    box_x1 = box_x0 + SafeZones9x16.AVATAR_SIZE  # 940
    box_y1 = box_y0 + SafeZones9x16.AVATAR_SIZE  # 1620
    cx = box_x0 + SafeZones9x16.AVATAR_SIZE // 2  # 810
    cy = box_y0 + SafeZones9x16.AVATAR_SIZE // 2  # 1490

    # a) Canto superior esquerdo do bounding box do avatar: DEVE ser magenta puro
    r, g, b = get_pixel_rgb(box_x0 + 10, box_y0 + 10)
    assert r > 200 and g < 30 and b > 200, (
        f"Canto superior esquerdo do avatar deve ser transparente (fundo magenta). Obtido: RGB({r}, {g}, {b})"
    )

    # b) Canto inferior externo da área do avatar: DEVE ser magenta puro (sem fundo opaco na onda sonora)
    r, g, b = get_pixel_rgb(box_x0 + 10, box_y1 - 10)
    assert r > 200 and g < 30 and b > 200, (
        f"Canto inferior externo do avatar deve ser transparente (fundo magenta). Obtido: RGB({r}, {g}, {b})"
    )

    # c) Ponto onde ficava a antiga moldura retangular no canto (box_x0, box_y0): NÃO deve ser branco puro
    r, g, b = get_pixel_rgb(box_x0, box_y0)
    assert not (r > 240 and g > 240 and b > 240), (
        f"Ponto ({box_x0}, {box_y0}) não deve ser branco puro. Obtido: RGB({r}, {g}, {b})"
    )
    assert r > 200 and g < 30 and b > 200, (
        f"Ponto ({box_x0}, {box_y0}) deve ser fundo magenta devido à transparência dos cantos. Obtido: RGB({r}, {g}, {b})"
    )

    # d) Continuidade do anel circular ZUNTO! (#FACC15): amostragem em 4 pontos cardeais
    border_samples = [
        (cx, box_y0 + 2, "topo"),
        (cx, box_y1 - 3, "base"),
        (box_x0 + 2, cy, "lateral esquerda"),
        (box_x1 - 3, cy, "lateral direita"),
    ]
    for x, y, desc in border_samples:
        br, bg, bb = get_pixel_rgb(x, y)
        assert br > 210 and bg > 170 and bb < 70, (
            f"Anel amarelo ZUNTO! (#FACC15) no {desc} ({x}, {y}) deve ter amarelo contínuo. Obtido: RGB({br}, {bg}, {bb})"
        )

    # e) Centro do avatar: NÃO deve ser magenta puro (exibe a figura do avatar)
    cr, cg, cb = get_pixel_rgb(cx, cy)
    assert not (cr > 200 and cg < 30 and cb > 200), (
        f"Centro do avatar não deve ser magenta puro. Obtido: RGB({cr}, {cg}, {cb})"
    )


def test_single_pass_composition_no_disk_fallback(tmp_path):
    """Garante que a composição single-pass não cria source_visual_bg.mp4 em disco (COMP-01, D-02)."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("FFmpeg não disponível")

    # 1. Cria áudio de voz sintético
    voice_path = tmp_path / "voice_sample.wav"
    MockVoiceSynthesizer(min_duration=1.5, max_duration=2.0).synthesize("Teste single pass.", voice_path)

    # 2. Cria avatar circular sintético rápido
    avatar_video_path = tmp_path / "avatar_simple.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "color=c=yellow:s=240x240:r=24:d=1.5",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(avatar_video_path),
        ],
        check=True,
        capture_output=True,
    )

    # 3. Legendas ASS
    ass_path = tmp_path / "subtitles.ass"
    job_cfg = SubtitleJobConfig(
        script_text="Teste single pass.",
        total_duration=1.5,
        output_path=ass_path,
        margin_v=SafeZones9x16.SUBTITLE_MARGIN_V,
    )
    generate_subtitles(job_cfg)

    # 4. Source video sem stream de vídeo (arquivo vazio de áudio / sem vídeo)
    source_video = tmp_path / "source_no_video.mp4"
    source_video.write_bytes(b"DUMMY_AUDIO_ONLY_NO_VIDEO")
    assert not has_video_stream(source_video)

    out_file = tmp_path / "output_single_pass.mp4"
    request = StudioRenderRequest(
        run_id="run-sp-1",
        source_video_path=source_video,
        avatar_video_path=avatar_video_path,
        voice_audio_path=voice_path,
        ass_subtitle_path=ass_path,
        output_path=out_file,
    )

    renderer = ReactionVideoRenderer()
    rendered_path, dur = renderer.render_from_request(request)

    assert rendered_path == out_file
    assert out_file.exists()
    assert dur >= 1.4

    # Assegurar explicitamente que nenhum arquivo source_visual_bg.mp4 foi criado em disco
    assert not (source_video.parent / "source_visual_bg.mp4").exists()
    assert not (tmp_path / "source_visual_bg.mp4").exists()


def test_reaction_renderer_output_specs_and_encoding_flags(tmp_path, monkeypatch):
    """Valida argumentos de codificação de alta fidelidade e mapeamento FFmpeg (COMP-02, D-03)."""
    captured_commands = []

    def mock_run(cmd, *args, **kwargs):
        captured_commands.append(cmd)
        if cmd[0] == "ffprobe":
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout='{"streams":[{"width":1080,"height":1920}]}', stderr=""
            )
        out_file = Path(cmd[-1])
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_bytes(b"MOCKRENDER")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(shutil, "which", lambda x: "/usr/bin/" + x)

    source_vid = tmp_path / "source_audio.mp4"
    source_vid.write_bytes(b"NO_VIDEO")
    avatar_vid = tmp_path / "avatar.mp4"
    avatar_vid.write_bytes(b"AVATAR")
    audio_file = tmp_path / "audio.wav"
    audio_file.write_bytes(b"AUDIO")
    ass_file = tmp_path / "subs.ass"
    ass_file.write_text("[Script Info]\n", encoding="utf-8")
    output_vid = tmp_path / "output.mp4"

    monkeypatch.setattr("viralpanel.studio.renderer.probe_duration", lambda p: 2.5)
    monkeypatch.setattr("viralpanel.studio.renderer.has_video_stream", lambda p: False)

    req = StudioRenderRequest(
        run_id="run-enc-test",
        source_video_path=source_vid,
        avatar_video_path=avatar_vid,
        voice_audio_path=audio_file,
        ass_subtitle_path=ass_file,
        output_path=output_vid,
        composition=ReactionCompositionSpec(
            preset="veryfast",
            crf=20,
            pix_fmt="yuv420p",
            video_codec="libx264",
            audio_codec="aac",
            audio_bitrate="192k",
        ),
    )

    renderer = ReactionVideoRenderer()
    renderer.render_from_request(req)

    # Encontrar comando do ffmpeg com filter_complex
    ffmpeg_cmds = [c for c in captured_commands if c[0] == "ffmpeg" and "-filter_complex" in c]
    assert len(ffmpeg_cmds) == 1, "Deve haver exatamente 1 execução de FFmpeg"
    cmd = ffmpeg_cmds[0]

    # Flags de codificação obrigatórias
    assert "-preset" in cmd and cmd[cmd.index("-preset") + 1] == "veryfast"
    assert "-crf" in cmd and cmd[cmd.index("-crf") + 1] == "20"
    assert "-pix_fmt" in cmd and cmd[cmd.index("-pix_fmt") + 1] == "yuv420p"
    assert "-c:v" in cmd and cmd[cmd.index("-c:v") + 1] == "libx264"
    assert "-c:a" in cmd and cmd[cmd.index("-c:a") + 1] == "aac"
    assert "-b:a" in cmd and cmd[cmd.index("-b:a") + 1] == "192k"
    assert "-shortest" in cmd

    # Mapeamento audiovisual
    vout_idx = cmd.index("-map")
    assert cmd[vout_idx + 1] == "[vout]"
    a2_idx = cmd.index("-map", vout_idx + 2)
    assert cmd[a2_idx + 1] == "2:a"

    # lavfi inline quando has_video_stream é False
    assert "-f" in cmd and cmd[cmd.index("-f") + 1] == "lavfi"
    lavfi_input = cmd[cmd.index("-f") + 3]
    assert lavfi_input.startswith("color=c=#0f172a:s=1080x1920:r=24:d=2.5")


def test_karaoke_subtitles_rendered_pixel_inspection(tmp_path: Path):
    """Renderiza clipe com FFmpeg libass e comprova deslocamento de amarelo, pausa em branco e caixa opaca contínua."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("FFmpeg não disponível para inspeção visual de legendas")

    proc_check = subprocess.run(["ffmpeg", "-filters"], capture_output=True, text=True)
    if "ass" not in proc_check.stdout:
        pytest.skip("FFmpeg sem suporte ao filtro libass (ass)")

    resolved_font = resolve_typography_font()
    ass_path = tmp_path / "karaoke_pixels.ass"
    job_cfg = SubtitleJobConfig(
        script_text="Você não sabia.",
        total_duration=2.0,
        output_path=ass_path,
        resolved_font=resolved_font,
        word_timestamps=[
            {"word": "Você", "start": 0.1, "end": 0.5, "duration": 0.4},
            {"word": "não", "start": 0.6, "end": 1.0, "duration": 0.4},
            {"word": "sabia.", "start": 1.4, "end": 1.9, "duration": 0.5},
        ],
    )
    generate_subtitles(job_cfg)
    assert ass_path.exists()

    escaped_ass = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    escaped_fontsdir = str(resolved_font.fonts_dir).replace("\\", "/").replace(":", "\\:")
    clip_mp4 = tmp_path / "karaoke_clip.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f", "lavfi",
            "-i", "color=c=magenta:s=1080x1920:r=24:d=2.0",
            "-vf", f"ass='{escaped_ass}':fontsdir='{escaped_fontsdir}'",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", "24",
            str(clip_mp4),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    assert clip_mp4.exists()

    def _inspect_frame(ts: float) -> dict:
        raw_path = tmp_path / f"frame_{ts:.1f}.raw"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss", f"{ts:.2f}",
                "-i", str(clip_mp4),
                "-vframes", "1",
                "-f", "rawvideo",
                "-pix_fmt", "rgb24",
                str(raw_path),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        raw_bytes = raw_path.read_bytes()
        assert len(raw_bytes) == 1080 * 1920 * 3

        yellow_xs: list[int] = []
        white_count = 0
        dark_box_count = 0
        # Região Safe Zone calibrada das legendas no terço inferior (Y ~ 1400..1580, X ~ 80..656)
        for y in range(SafeZones9x16.SUBTITLE_Y_MIN, SafeZones9x16.SUBTITLE_Y_MAX + 1):
            for x in range(SafeZones9x16.SUBTITLE_MARGIN_LEFT, 657):
                idx = (y * 1080 + x) * 3
                r, g, b = raw_bytes[idx], raw_bytes[idx + 1], raw_bytes[idx + 2]
                if r <= 25 and g <= 25 and b <= 25:
                    dark_box_count += 1
                elif r > 180 and g > 140 and b < 90 and (r - b) > 100:
                    yellow_xs.append(x)
                elif r > 190 and g > 190 and b > 190:
                    white_count += 1

        # Agrupa coordenadas X de pixels amarelos separadas por mais de 35px para checar exclusividade de 1 palavra
        clusters = 0
        if yellow_xs:
            sorted_x = sorted(set(yellow_xs))
            clusters = 1
            for k in range(1, len(sorted_x)):
                if sorted_x[k] - sorted_x[k - 1] > 35:
                    clusters += 1

        return {
            "yellow_count": len(yellow_xs),
            "yellow_cx": (sum(yellow_xs) / len(yellow_xs)) if yellow_xs else None,
            "yellow_clusters": clusters,
            "white_count": white_count,
            "dark_box_count": dark_box_count,
        }

    f_word1 = _inspect_frame(0.3)
    f_word2 = _inspect_frame(0.8)
    f_pause = _inspect_frame(1.2)
    f_word3 = _inspect_frame(1.6)

    for label, stats in [("t=0.3s", f_word1), ("t=0.8s", f_word2), ("t=1.2s(pausa)", f_pause), ("t=1.6s", f_word3)]:
        assert stats["dark_box_count"] > 1000, f"Caixa preta ausente/instável em {label}: {stats}"
        assert stats["white_count"] > 100, f"Texto branco ausente em {label}: {stats}"

    for label, stats in [("Você", f_word1), ("não", f_word2), ("sabia.", f_word3)]:
        assert stats["yellow_count"] > 40, f"Palavra ativa '{label}' sem destaque amarelo: {stats}"
        assert stats["yellow_clusters"] == 1, f"Esperado apenas 1 aglomerado amarelo em '{label}': {stats}"

    assert f_pause["yellow_count"] == 0, f"Pausa t=1.2s deve estar 100% em branco (zero amarelo): {f_pause}"
    assert f_word1["yellow_cx"] < f_word2["yellow_cx"] < f_word3["yellow_cx"], (
        f"Centroide amarelo deve avançar para a direita: {f_word1['yellow_cx']} < {f_word2['yellow_cx']} < {f_word3['yellow_cx']}"
    )


def _probe_filter_output_dimensions(width: int, height: int, scale_filter: str) -> tuple[int, int]:
    """Executa o filtro de escala em um frame lavfi real e extrai dimensões via showinfo."""
    proc = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=red:s={width}x{height}:d=0.1",
            "-vf",
            f"{scale_filter},showinfo",
            "-frames:v",
            "1",
            "-f",
            "null",
            "-",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    for line in proc.stderr.splitlines():
        if "showinfo" in line and "s:" in line:
            for token in line.split():
                if token.startswith("s:"):
                    w_str, h_str = token[2:].split("x")
                    return int(w_str), int(h_str)
    raise AssertionError(f"showinfo não retornou dimensões para {width}x{height}: {proc.stderr}")


def test_reaction_renderer_invokes_font_resolution_and_injects_fontsdir(tmp_path, monkeypatch):
    """ReactionVideoRenderer.render_from_request invoca resolve_typography_font e injeta :fontsdir."""
    from viralpanel.branding import ResolvedFont

    font_file = tmp_path / "custom_fonts" / "Montserrat-Bold.ttf"
    font_file.parent.mkdir(parents=True, exist_ok=True)
    font_file.write_bytes(b"DUMMY_TTF")
    resolved = ResolvedFont(
        font_path=font_file.resolve(),
        fonts_dir=font_file.parent.resolve(),
        font_name="Montserrat",
        variant="montserrat",
    )

    resolve_calls = 0

    def spy_resolve():
        nonlocal resolve_calls
        resolve_calls += 1
        return resolved

    captured_cmds: list[list[str]] = []

    def mock_run(cmd, *args, **kwargs):
        captured_cmds.append(cmd)
        if cmd[0] == "ffprobe":
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout='{"streams":[{"width":1280,"height":720}]}', stderr=""
            )
        out = Path(cmd[-1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"MP4")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("viralpanel.studio.renderer.resolve_typography_font", spy_resolve)
    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(shutil, "which", lambda x: "/usr/bin/" + x)
    monkeypatch.setattr("viralpanel.studio.renderer.probe_duration", lambda p: 2.0)
    monkeypatch.setattr("viralpanel.studio.renderer.has_video_stream", lambda p: True)

    src = tmp_path / "src.mp4"
    src.write_bytes(b"SRC")
    avatar = tmp_path / "avatar.mp4"
    avatar.write_bytes(b"AVT")
    voice = tmp_path / "voice.wav"
    voice.write_bytes(b"WAV")
    ass = tmp_path / "subs.ass"
    ass.write_text("[Script Info]\n", encoding="utf-8")
    out = tmp_path / "out.mp4"

    req = StudioRenderRequest(
        run_id="run-fontsdir",
        source_video_path=src,
        avatar_video_path=avatar,
        voice_audio_path=voice,
        ass_subtitle_path=ass,
        output_path=out,
    )
    ReactionVideoRenderer().render_from_request(req)

    assert resolve_calls == 1
    ffmpeg_cmds = [c for c in captured_cmds if c[0] == "ffmpeg" and "-filter_complex" in c]
    assert len(ffmpeg_cmds) == 1
    fc = ffmpeg_cmds[0][ffmpeg_cmds[0].index("-filter_complex") + 1]
    escaped_fontsdir = str(resolved.fonts_dir).replace("\\", "/").replace(":", "\\:")
    assert f":fontsdir='{escaped_fontsdir}'[vout]" in fc


def test_build_reaction_filter_complex_enforces_fontsdir_fail_closed():
    """build_reaction_filter_complex rejeita fonts_dir None ou vazio com FontResolutionError."""
    spec = ReactionCompositionSpec()
    for bad_dir in (None, "", "   "):
        with pytest.raises(FontResolutionError, match="fonts_dir"):
            build_reaction_filter_complex(
                composition=spec,
                avatar_size=SafeZones9x16.AVATAR_SIZE,
                escaped_ass="C\\:/tmp/subs.ass",
                source_width=1280,
                source_height=720,
                has_video=True,
                fonts_dir=bad_dir,
            )


def test_aspect_ratio_boundary_0_75(tmp_path):
    """Testa fronteira AR=0.75: 0.749 e 0.750 (Portrait direto sem split), 0.751 (Square confinado com split)."""
    spec = ReactionCompositionSpec()
    fonts_dir = tmp_path

    # 0.749 -> Portrait
    assert classify_stage_strategy(749, 1000) == "portrait"
    fc_0749 = build_reaction_filter_complex(spec, 260, "sub.ass", 749, 1000, True, fonts_dir)
    assert "split=2" not in fc_0749
    assert "boxblur=" not in fc_0749
    assert ":fontsdir='" in fc_0749

    # 0.750 -> Portrait (fronteira inclusiva <= 0.75)
    assert classify_stage_strategy(750, 1000) == "portrait"
    fc_0750 = build_reaction_filter_complex(spec, 260, "sub.ass", 750, 1000, True, fonts_dir)
    assert "split=2" not in fc_0750
    assert "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[bg]" in fc_0750

    # 0.751 -> Square/4:5 confinado com split + boxblur
    assert classify_stage_strategy(751, 1000) == "square"
    fc_0751 = build_reaction_filter_complex(spec, 260, "sub.ass", 751, 1000, True, fonts_dir)
    assert "split=2[raw_bg][raw_fg]" in fc_0751
    assert f"boxblur={SafeZones9x16.STAGE_BACKDROP_BLUR}" in fc_0751
    assert f"overlay=(W-w)/2:{SafeZones9x16.STAGE_FG_Y_TOP}[stage]" in fc_0751
    assert ":fontsdir='" in fc_0751

    if shutil.which("ffmpeg"):
        fg_clause = fc_0751.split("[raw_fg]")[-1].split("[fg]")[0]
        w, h = _probe_filter_output_dimensions(751, 1000, fg_clause)
        assert w % 2 == 0 and h % 2 == 0
        assert w <= 1080 and h <= 900


def test_aspect_ratio_boundary_1_20(tmp_path):
    """Testa fronteira AR=1.20 (1080x900): confinamento por altura (1.199), match exato (1.200) e largura (1.201)."""
    spec = ReactionCompositionSpec()
    fonts_dir = tmp_path

    for src_w, src_h in ((1199, 1000), (1200, 1000), (1201, 1000)):
        strategy, fg_w, fg_h = calculate_stage_foreground_dimensions(src_w, src_h)
        assert strategy == "square"
        assert fg_w % 2 == 0 and fg_h % 2 == 0
        assert fg_w <= 1080 and fg_h <= 900
        fc = build_reaction_filter_complex(spec, 260, "sub.ass", src_w, src_h, True, fonts_dir)
        assert f"overlay=(W-w)/2:{SafeZones9x16.STAGE_FG_Y_TOP}[stage]" in fc
        assert ":fontsdir='" in fc

    _, w_1199, h_1199 = calculate_stage_foreground_dimensions(1199, 1000)
    _, w_1200, h_1200 = calculate_stage_foreground_dimensions(1200, 1000)
    _, w_1201, h_1201 = calculate_stage_foreground_dimensions(1201, 1000)
    assert (w_1199, h_1199) == (1078, 900)
    assert (w_1200, h_1200) == (1080, 900)
    assert h_1201 < 900 and w_1201 <= 1080

    if shutil.which("ffmpeg"):
        for src_w, src_h in ((1199, 1000), (1200, 1000), (1201, 1000)):
            fc = build_reaction_filter_complex(spec, 260, "sub.ass", src_w, src_h, True, fonts_dir)
            fg_clause = fc.split("[raw_fg]")[-1].split("[fg]")[0]
            pw, ph = _probe_filter_output_dimensions(src_w, src_h, fg_clause)
            assert pw % 2 == 0 and ph % 2 == 0
            assert pw <= 1080 and ph <= 900
            if (src_w, src_h) == (1200, 1000):
                assert (pw, ph) == (1080, 900)


def test_aspect_ratio_boundary_1_25(tmp_path):
    """Testa fronteira AR=1.25: 1.249 (Square confinado) vs 1.250 e 1.251 (Landscape 100% largura + backdrop)."""
    spec = ReactionCompositionSpec()
    fonts_dir = tmp_path

    # 1.249 -> Square/híbrido confinado
    assert classify_stage_strategy(1249, 1000) == "square"
    fc_1249 = build_reaction_filter_complex(spec, 260, "sub.ass", 1249, 1000, True, fonts_dir)
    assert "min(1080,trunc(900*a/2)*2)" in fc_1249

    # 1.250 e 1.251 -> Landscape backdrop com escala direta 1080:-2:flags=lanczos
    for src_w, src_h in ((1250, 1000), (1251, 1000)):
        strategy, fg_w, fg_h = calculate_stage_foreground_dimensions(src_w, src_h)
        assert strategy == "landscape"
        assert fg_w == 1080
        assert fg_h % 2 == 0 and fg_h <= 864
        fc = build_reaction_filter_complex(spec, 260, "sub.ass", src_w, src_h, True, fonts_dir)
        assert "split=2[raw_bg][raw_fg]" in fc
        assert "[raw_fg]scale=1080:-2:flags=lanczos[fg]" in fc
        assert f"boxblur={SafeZones9x16.STAGE_BACKDROP_BLUR}" in fc
        assert f"eq=brightness={SafeZones9x16.STAGE_BACKDROP_BRIGHTNESS}:contrast={SafeZones9x16.STAGE_BACKDROP_CONTRAST}" in fc
        assert ":fontsdir='" in fc

    if shutil.which("ffmpeg"):
        for src_w, src_h in ((1249, 1000), (1250, 1000), (1251, 1000)):
            fc = build_reaction_filter_complex(spec, 260, "sub.ass", src_w, src_h, True, fonts_dir)
            fg_clause = fc.split("[raw_fg]")[-1].split("[fg]")[0]
            pw, ph = _probe_filter_output_dimensions(src_w, src_h, fg_clause)
            assert pw == 1080 and ph % 2 == 0 and ph <= 864


def test_build_reaction_filter_complex_lavfi(tmp_path):
    """Quando has_video=False, utiliza lavfi inline sem split e injeta :fontsdir."""
    spec = ReactionCompositionSpec()
    fc = build_reaction_filter_complex(spec, 260, "sub.ass", 1080, 1920, False, tmp_path)
    assert "split=2" not in fc
    assert "boxblur=" not in fc
    assert "[0:v]setsar=1[bg]" in fc
    assert "[bg][pip]overlay=W-w-140:H-h-300" in fc
    assert ":fontsdir='" in fc


def test_reaction_renderer_renders_cinematic_backdrop_e2e(tmp_path):
    """Renderiza clipe 16:9 real de 2s comprovando 1080x1920, A/V válidos e 100% da largura sem crop."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("FFmpeg/ffprobe não disponíveis")

    # Cria vídeo 16:9 (1280x720) com faixa lateral esquerda vermelha, centro verde e faixa direita azul
    # Se houvesse crop central destrutivo 9:16 (405x720), as laterais vermelha e azul desapareceriam!
    source_16x9 = tmp_path / "source_16x9.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=green:s=1280x720:r=24:d=2.0",
            "-vf",
            "drawbox=x=0:y=0:w=120:h=720:color=red:t=fill,drawbox=x=1160:y=0:w=120:h=720:color=blue:t=fill",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(source_16x9),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )

    voice_path = tmp_path / "voice.wav"
    MockVoiceSynthesizer(min_duration=2.0, max_duration=2.0).synthesize(
        "Você não sabia. Agora sabe.", voice_path
    )

    img_path = tmp_path / "avatar_src.png"
    ensure_default_avatar_image(img_path)
    avatar_path = tmp_path / "avatar.mp4"
    AudioReactiveAvatarAnimator(default_avatar_image=img_path).generate_avatar_video(
        voice_path, avatar_path
    )

    ass_path = tmp_path / "subs.ass"
    generate_subtitles(
        SubtitleJobConfig(
            script_text="Você não sabia. Agora sabe.",
            total_duration=2.0,
            output_path=ass_path,
            resolved_font=resolve_typography_font(),
        )
    )

    output_mp4 = tmp_path / "cinematic_output.mp4"
    req = StudioRenderRequest(
        run_id="run-cinematic-e2e",
        source_video_path=source_16x9,
        avatar_video_path=avatar_path,
        voice_audio_path=voice_path,
        ass_subtitle_path=ass_path,
        output_path=output_mp4,
        voice_duration=2.0,
    )

    out_path, dur = ReactionVideoRenderer().render_from_request(req)
    assert out_path == output_mp4 and output_mp4.exists()
    assert dur >= 1.8

    import json
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,width,height,sample_aspect_ratio",
            "-of",
            "json",
            str(output_mp4),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    streams = json.loads(probe.stdout)["streams"]
    video_streams = [s for s in streams if s["codec_type"] == "video"]
    audio_streams = [s for s in streams if s["codec_type"] == "audio"]
    assert len(video_streams) == 1 and len(audio_streams) == 1
    assert (video_streams[0]["width"], video_streams[0]["height"]) == (1080, 1920)
    assert video_streams[0].get("sample_aspect_ratio") == "1:1"

    # Verifica em frame bruto que as bordas extremas do foreground 16:9 (Y=240..847 -> centro Y=540)
    # preservam vermelho à esquerda (X=20) e azul à direita (X=1060), provando 0% crop horizontal!
    raw_path = tmp_path / "e2e_frame.rgb"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            "0.5",
            "-i",
            str(output_mp4),
            "-vframes",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            str(raw_path),
        ],
        check=True,
        capture_output=True,
    )
    raw = raw_path.read_bytes()

    def px(x: int, y: int) -> tuple[int, int, int]:
        i = (y * 1080 + x) * 3
        return raw[i], raw[i + 1], raw[i + 2]

    left_r, left_g, left_b = px(20, 540)
    center_r, center_g, center_b = px(540, 540)
    right_r, right_g, right_b = px(1060, 540)
    assert left_r > 180 and left_g < 60, f"Borda esquerda do 16:9 foi cortada! RGB={left_r, left_g, left_b}"
    assert center_g > 100 and center_r < 60, f"Centro do 16:9 incorreto! RGB={center_r, center_g, center_b}"
    assert right_b > 180 and right_r < 60, f"Borda direita do 16:9 foi cortada! RGB={right_r, right_g, right_b}"






