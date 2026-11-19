import json
import shutil
import subprocess
from dataclasses import FrozenInstanceError
from pathlib import Path
import pytest

from viralpanel.branding import SafeZones9x16, ZuntoPalette
from viralpanel.studio.avatar import (
    AudioReactiveAvatarAnimator,
    AvatarConfig,
    MockAvatarAnimator,
    ensure_default_avatar_image,
)
from viralpanel.studio.voice import MockVoiceSynthesizer


def test_avatar_config_defaults_and_immutability():
    """Valida DTO AvatarConfig tipado, imutável e com defaults calibrados em SafeZones9x16."""
    config = AvatarConfig()
    assert config.avatar_image_path is None
    assert config.size == SafeZones9x16.AVATAR_SIZE == 260
    assert config.crop_mode == "circle_alpha"
    assert config.border_color == ZuntoPalette.IMPACT_YELLOW == "#FACC15"
    assert config.border_width == 6
    assert config.overlay_x_expr == f"W-w-{SafeZones9x16.AVATAR_MARGIN_RIGHT}" == "W-w-140"
    assert config.overlay_y_expr == f"H-h-{SafeZones9x16.AVATAR_MARGIN_BOTTOM}" == "H-h-300"
    assert config.enable_waveform is False
    assert config.waveform_color == "#FACC15@0.85"

    with pytest.raises(FrozenInstanceError):
        config.size = 360

    custom = AvatarConfig(
        avatar_image_path=Path("assets/custom.png"),
        size=280,
        crop_mode="native_rgba",
        border_color="#FFFFFF",
        border_width=2,
        overlay_x_expr="W-w-60",
        overlay_y_expr="H-h-300",
        enable_waveform=False,
        waveform_color="#FFFFFF@0.5",
    )
    assert custom.size == 280
    assert custom.border_width == 2
    assert custom.enable_waveform is False


def test_mock_avatar_animator_matches_voice_duration(tmp_path):
    voice_path = tmp_path / "voice.wav"
    avatar_path = tmp_path / "avatar.mp4"

    _, voice_dur = MockVoiceSynthesizer().synthesize("Disciplina constrói liberdade todos os dias.", voice_path)
    out_path, avatar_dur = MockAvatarAnimator().generate_avatar_video(voice_path, avatar_path)

    assert out_path.exists()
    assert abs(avatar_dur - voice_dur) < 0.5


def test_ensure_default_avatar_image_creates_file(tmp_path):
    target = tmp_path / "avatar.png"
    result = ensure_default_avatar_image(target)
    assert result.exists()
    assert result.stat().st_size > 0


def test_audio_reactive_avatar_animator(tmp_path):
    voice_path = tmp_path / "voice.wav"
    avatar_path = tmp_path / "reactive_avatar.mp4"
    img_path = tmp_path / "img.png"
    ensure_default_avatar_image(img_path)

    _, voice_dur = MockVoiceSynthesizer().synthesize("Foco diário.", voice_path)
    animator = AudioReactiveAvatarAnimator(default_avatar_image=img_path)
    out_path, dur = animator.generate_avatar_video(voice_path, avatar_path)

    assert out_path.exists()
    assert dur > 0


def test_avatar_video_codec_and_pixel_format(tmp_path):
    """Valida metadados de codec 'png' e pix_fmt 'rgba' em avatar.mp4 per AVTR-03."""
    if not shutil.which("ffprobe") or not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg/ffprobe não disponíveis no ambiente")

    voice_path = tmp_path / "voice.wav"
    avatar_path = tmp_path / "avatar.mp4"
    img_path = tmp_path / "img.png"
    ensure_default_avatar_image(img_path)

    MockVoiceSynthesizer().synthesize("Teste codec e formato.", voice_path)
    animator = AudioReactiveAvatarAnimator(default_avatar_image=img_path)
    out_path, dur = animator.generate_avatar_video(voice_path, avatar_path)

    assert out_path.exists()
    assert dur > 0

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name,pix_fmt",
        "-of",
        "json",
        str(out_path),
    ]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    probe_data = json.loads(proc.stdout)
    assert "streams" in probe_data and len(probe_data["streams"]) > 0
    stream = probe_data["streams"][0]

    assert stream["codec_name"] == "png"
    assert stream["pix_fmt"] == "rgba"


def test_avatar_circular_alpha_and_yellow_border_pixels(tmp_path):
    """Renderiza 1 frame de avatar.mp4 em rawvideo rgba e inspeciona pixels numéricos per D-01, AVTR-01 e BRND-01."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg não disponível no ambiente")

    voice_path = tmp_path / "voice.wav"
    avatar_path = tmp_path / "avatar.mp4"
    img_path = tmp_path / "img.png"
    ensure_default_avatar_image(img_path)

    MockVoiceSynthesizer().synthesize("Análise empírica de pixels do avatar.", voice_path)
    animator = AudioReactiveAvatarAnimator(default_avatar_image=img_path)
    animator.generate_avatar_video(voice_path, avatar_path)

    raw_path = tmp_path / "frame.raw"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(avatar_path),
            "-vframes",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            str(raw_path),
        ],
        check=True,
        capture_output=True,
    )

    size = SafeZones9x16.AVATAR_SIZE
    center = size // 2
    raw_bytes = raw_path.read_bytes()
    assert len(raw_bytes) == size * size * 4

    def get_rgba(x: int, y: int) -> tuple[int, int, int, int]:
        offset = (y * size + x) * 4
        return tuple(raw_bytes[offset : offset + 4])

    # 1. Quatro cantos externos do bounding box possuem Alpha == 0 (transparência total)
    corners = [(10, 10), (size - 10, 10), (10, size - 10), (size - 10, size - 10)]
    for pt in corners:
        rgba = get_rgba(*pt)
        assert rgba[3] == 0, f"Canto {pt} deveria ter alfa 0, obteve: {rgba}"

    # 2. Pontos na borda anelar circular possuem Alpha > 200 e cor amarela ZUNTO! (#FACC15: R > 220, G > 180, B < 60)
    border_points = [(center, 2), (center, size - 3), (2, center), (size - 3, center)]
    for pt in border_points:
        r, g, b, a = get_rgba(*pt)
        assert a > 200, f"Borda {pt} deveria ter alfa > 200, obteve: {a}"
        assert r > 220 and g > 180 and b < 60, f"Borda {pt} deveria ser amarela #FACC15, obteve R={r}, G={g}, B={b}"

    # 3. Centro do avatar é opaco (alpha == 255)
    center_rgba = get_rgba(center, center)
    assert center_rgba[3] == 255, f"Centro deveria ter alfa 255, obteve: {center_rgba[3]}"

    # 4. Cantos inferiores externos mantêm Alpha == 0
    lower_outside = [(15, size - 40), (size - 15, size - 40)]
    for pt in lower_outside:
        rgba = get_rgba(*pt)
        assert rgba[3] == 0, f"Canto inferior externo {pt} deveria ter alfa 0, obteve: {rgba}"


def test_showwaves_background_transparency(tmp_path):
    """Comprova empiricamente que o modo legado showwaves (isolado) não produz fundo opaco ou retângulo preto per D-04."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg não disponível no ambiente")

    size = SafeZones9x16.AVATAR_SIZE
    center = size // 2
    blue_img = tmp_path / "solid_blue.png"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=blue:s={size}x{size}:d=0.1",
            "-frames:v",
            "1",
            "-update",
            "1",
            str(blue_img),
        ],
        check=True,
        capture_output=True,
    )

    audio_path = tmp_path / "voice.wav"
    MockVoiceSynthesizer().synthesize("Confinamento e transparência do showwaves.", audio_path)

    animator = AudioReactiveAvatarAnimator(config=AvatarConfig(enable_waveform=True, avatar_image_path=blue_img))
    avatar_out = tmp_path / "blue_avatar.mp4"
    animator.generate_avatar_video(audio_path, avatar_out, avatar_image_path=blue_img)

    raw_path = tmp_path / "blue_frame.raw"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(avatar_out),
            "-vframes",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            str(raw_path),
        ],
        check=True,
        capture_output=True,
    )

    raw_bytes = raw_path.read_bytes()
    assert len(raw_bytes) == size * size * 4

    def get_rgba(x: int, y: int) -> tuple[int, int, int, int]:
        offset = (y * size + x) * 4
        return tuple(raw_bytes[offset : offset + 4])

    # Amostrar linha vertical central na região da onda (Y = size - 100 .. size - 20)
    # Pixels onde não há traço sonoro preservam o azul e alfa intactos (sem caixa preta opaca)
    wave_sample_ys = [size - 95, size - 85, size - 75, size - 65, size - 55, size - 45, size - 35, size - 25]
    for y in wave_sample_ys:
        r, g, b, a = get_rgba(center, y)
        assert a == 255, f"Pixel em ({center}, {y}) teve alfa degradado: {a}"
        assert not (r == 0 and g == 0 and b == 0), f"Pixel em ({center}, {y}) tornou-se preto indesejado"
        is_blue = (b > 200 and r < 50 and g < 50)
        is_yellow = (r > 150 and g > 120)
        assert is_blue or is_yellow, f"Pixel em ({center}, {y}) tem cor inesperada: R={r}, G={g}, B={b}"


def test_static_avatar_omits_showwaves_from_ffmpeg_command(tmp_path, monkeypatch):
    """Comprova que o padrão enable_waveform=False omite completamente showwaves do comando FFmpeg."""
    captured_cmds: list[list[str]] = []

    def mock_run(cmd, *args, **kwargs):
        captured_cmds.append(cmd)
        out = Path(cmd[-1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"MOCKAVATAR")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(shutil, "which", lambda x: "/usr/bin/" + x)
    monkeypatch.setattr("viralpanel.studio.avatar.probe_duration", lambda p: 2.0)

    img_path = tmp_path / "avatar_src.png"
    img_path.write_bytes(b"PNG")
    audio_path = tmp_path / "voice.wav"
    audio_path.write_bytes(b"WAV")
    out_path = tmp_path / "avatar.mp4"

    animator = AudioReactiveAvatarAnimator(default_avatar_image=img_path)
    assert animator.config.enable_waveform is False
    animator.generate_avatar_video(audio_path, out_path)

    ffmpeg_cmds = [c for c in captured_cmds if c[0] == "ffmpeg" and "-filter_complex" in c]
    assert len(ffmpeg_cmds) == 1
    fc = ffmpeg_cmds[0][ffmpeg_cmds[0].index("-filter_complex") + 1]
    assert "showwaves" not in fc
    assert "[1:a]" not in fc
    assert "format=rgba,geq=" in fc
    assert fc.endswith("[vout]")


def test_static_avatar_has_zero_temporal_pixel_variation(tmp_path):
    """Comprova via Frame-Difference em t=0.2s e t=1.2s que o avatar estático possui diff == 0 bytes."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg não disponível no ambiente")

    voice_path = tmp_path / "voice.wav"
    MockVoiceSynthesizer(min_duration=2.0, max_duration=2.0).synthesize(
        "Mascote ZUNTO estático sem visualizador de frequência.", voice_path
    )

    img_path = tmp_path / "avatar_src.png"
    ensure_default_avatar_image(img_path)
    avatar_out = tmp_path / "static_avatar.mp4"

    animator = AudioReactiveAvatarAnimator(default_avatar_image=img_path)
    assert animator.config.enable_waveform is False
    animator.generate_avatar_video(voice_path, avatar_out)
    assert avatar_out.exists()

    size = SafeZones9x16.AVATAR_SIZE
    expected_bytes = size * size * 4

    frames: list[bytes] = []
    for idx, ts in enumerate((0.2, 1.2)):
        raw_path = tmp_path / f"frame_{idx}.raw"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{ts:.2f}",
                "-i",
                str(avatar_out),
                "-vframes",
                "1",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgba",
                str(raw_path),
            ],
            check=True,
            capture_output=True,
        )
        raw_bytes = raw_path.read_bytes()
        assert len(raw_bytes) == expected_bytes
        frames.append(raw_bytes)

    diff = sum(abs(a - b) for a, b in zip(frames[0], frames[1]))
    assert diff == 0, f"Avatar estático apresentou variação temporal entre t=0.2s e t=1.2s: diff={diff}"



