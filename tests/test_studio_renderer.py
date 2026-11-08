from pathlib import Path
import shutil
import subprocess

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from viralpanel.branding import SafeZones9x16, ZuntoPalette, hex_to_ass_color
from viralpanel.database import Base
from viralpanel.models import Asset, Script, SourceVideo
from viralpanel.storage import StorageManager
from viralpanel.studio.avatar import MockAvatarAnimator
from viralpanel.studio.renderer import ReactionVideoRenderer, probe_video_dimensions
from viralpanel.studio.service import StudioService
from viralpanel.studio.subtitles import (
    SubtitleJobConfig,
    build_cues_from_script,
    generate_subtitles,
    write_ass_subtitles,
)
from viralpanel.studio.voice import MockVoiceSynthesizer


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

        # 1. Validar BorderStyle=3, MarginV=640 e cor de fundo &H000A0A0A& (preto profundo ZUNTO!)
        assert "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding" in ass_content
        # Linha de estilo: ...3,16,0,2,80,80,640,1
        assert ",3,16,0,2,80,80,640,1" in ass_content, (
            "Estilo Default deve conter BorderStyle=3, Outline=16, Alignment=2 e MarginV=640"
        )
        deep_black_ass = hex_to_ass_color(ZuntoPalette.DEEP_BLACK)  # &H000A0A0A&
        assert deep_black_ass in ass_content, f"Cor da caixa opaca {deep_black_ass} deve estar no cabeçalho ASS"
        assert "Dialogue: 0," in ass_content, "Eventos de diálogo devem estar presentes no arquivo ASS"


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

    # Validar camada única: o filtro ass= deve aparecer exatamente UMA vez
    assert filter_complex_str.count("ass='") == 1, (
        f"Filtro ass='...' deve ocorrer exatamente 1 vez, sem duplicação de legendas. Encontrado: {filter_complex_str}"
    )
    assert "[composed]ass='" in filter_complex_str and "'[vout]" in filter_complex_str, (
        "Legendas devem ser aplicadas na camada final sobre o vídeo composto [composed]"
    )

    # Validar escape de caminhos: dois pontos devem ser escapados como \\:
    escaped_expected = str(ass_file.resolve()).replace("\\", "/").replace(":", "\\:")
    assert f"ass='{escaped_expected}'" in filter_complex_str, (
        f"Caminho do arquivo ASS deve ser rigidamente escapado. Esperado ass='{escaped_expected}'"
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
      * MarginV = 640px (distância nominal a partir da base inferior)
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

    ass_path = tmp_path / "reference_zunto.ass"
    job_cfg = SubtitleJobConfig(
        script_text="Você não sabia. Agora sabe.",
        total_duration=3.0,
        output_path=ass_path,
        margin_v=SafeZones9x16.SUBTITLE_MARGIN_V,  # 640
        font_size=64,
        box_padding=16,
    )
    generate_subtitles(job_cfg)
    assert ass_path.exists()

    escaped_ass = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    raw_frame_path = tmp_path / "ref_frame_1080x1920.raw"

    # Renderiza 1 frame de referência 1080x1920 sobre fundo magenta (RGB: 255, 0, 255)
    render_cmd = [
        "ffmpeg",
        "-y",
        "-f", "lavfi",
        "-i", "color=c=magenta:s=1080x1920:d=0.1",
        "-vf", f"ass='{escaped_ass}'",
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

    bot_r, bot_g, bot_b = get_pixel_rgb(540, 1600)
    assert bot_r > 200 and bot_g < 30 and bot_b > 200, "Base inferior deve permanecer fundo magenta"

    # 2. Inspecionar empiricamente a presença da caixa opaca ZUNTO! (#0A0A0A) na faixa SafeZone (Y 1080 a 1280)
    # Procuramos pixels escuros da caixa opaca (R, G, B <= 25)
    dark_box_pixels = 0
    for y in range(SafeZones9x16.SUBTITLE_Y_MIN, SafeZones9x16.SUBTITLE_Y_MAX + 1):
        for x in range(300, 781):
            r, g, b = get_pixel_rgb(x, y)
            if r <= 25 and g <= 25 and b <= 25:
                dark_box_pixels += 1

    assert dark_box_pixels > 1000, (
        f"A caixa opaca ZUNTO! (#0A0A0A) deve estar presente na faixa SafeZone Y 1080-1280. Encontrados {dark_box_pixels} pixels."
    )


