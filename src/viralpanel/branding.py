"""Módulo Central de Identidade Visual e Safe Zones da marca ZUNTO!.

Fonte única de verdade para constantes visuais, cores oficiais, safe zones 9:16
e conversão de cores para legendas e composição FFmpeg.
"""
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Final, Literal


class FontResolutionError(RuntimeError):
    """Lançada quando nenhuma fonte homologada for encontrada ou configurável para o libass."""


@dataclass(frozen=True)
class ResolvedFont:
    """Contrato formal da fonte tipográfica resolvida para o pipeline audiovisual."""

    font_path: Path
    fonts_dir: Path
    font_name: str
    variant: Literal["montserrat", "dejavu_sans"]


@dataclass(frozen=True)
class ZuntoPalette:
    """Paleta de cores oficial da marca ZUNTO!."""

    DEEP_BLACK: Final[str] = "#0A0A0A"     # Preto profundo (fundo, caixas opacas)
    IMPACT_YELLOW: Final[str] = "#FACC15"  # Amarelo de alto impacto (destaques, bordas, ênfases)
    PURE_WHITE: Final[str] = "#FFFFFF"     # Branco puro (texto primário, legendas)
    DARK_NEUTRAL: Final[str] = "#1A1A1A"   # Cinza escuro neutro (cards, detalhes secundários)


@dataclass(frozen=True)
class ZuntoTypography:
    """Especificações tipográficas para resolução base 1080x1920."""

    PRIMARY_FONT: Final[str] = "Montserrat"
    FALLBACK_FONT: Final[str] = "DejaVu Sans"
    SUBTITLE_FONT_SIZE: Final[int] = 64
    TITLE_FONT_SIZE: Final[int] = 84
    SUBTITLE_MAX_CHARS_PER_LINE: Final[int] = 28
    SUBTITLE_MAX_LINES: Final[int] = 2


@dataclass(frozen=True)
class SafeZones9x16:
    """Referências defensivas conservadoras configuráveis de safe zone em 1080x1920.

    Projetadas para maximizar compatibilidade entre variações de interface do
    TikTok, Instagram Reels e YouTube Shorts (iOS/Android e diferentes proporções de tela).
    """

    WIDTH: Final[int] = 1080
    HEIGHT: Final[int] = 1920

    # Margens de segurança da UI mobile (referências defensivas conservadoras configuráveis)
    TOP_MARGIN: Final[int] = 220       # Evitar ícones de busca, abas 'Seguindo/Para Você'
    BOTTOM_MARGIN: Final[int] = 340    # Evitar descrição, áudio giratório e barra de navegação
    RIGHT_MARGIN: Final[int] = 140     # Evitar botões de like, comentários, salvar e compartilhar
    LEFT_MARGIN: Final[int] = 48       # Margem lateral esquerda segura base

    # Zonas calibradas de legendas no terço inferior (Phase 13.2)
    # MarginL=80, MarginR=440 confinam texto em X in [80, 640] e caixa com padding<=656px
    SUBTITLE_MARGIN_V: Final[int] = 420
    SUBTITLE_MARGIN_RIGHT: Final[int] = 440
    SUBTITLE_MARGIN_LEFT: Final[int] = 80
    SUBTITLE_Y_MIN: Final[int] = 1340
    SUBTITLE_Y_MAX: Final[int] = 1500

    # Avatar Reaction: Canto inferior direito livre da coluna de botões (X<=940) e barra (Y<=1620)
    # Bounding box: X in [680, 940], Y in [1360, 1620]
    AVATAR_SIZE: Final[int] = 260
    AVATAR_MARGIN_RIGHT: Final[int] = 140
    AVATAR_MARGIN_BOTTOM: Final[int] = 300

    # Palco Cinematic Backdrop (foreground + plano de fundo desfocado)
    STAGE_FG_Y_TOP: Final[int] = 240
    STAGE_FG_MAX_H: Final[int] = 900
    STAGE_BACKDROP_BLUR: Final[str] = "20:5"
    STAGE_BACKDROP_BRIGHTNESS: Final[float] = -0.15
    STAGE_BACKDROP_CONTRAST: Final[float] = 0.9


@dataclass(frozen=True)
class BrandGuidelines:
    """Diretrizes editoriais e slogan da marca ZUNTO!."""

    BRAND_NAME: Final[str] = "ZUNTO!"
    SLOGAN: Final[str] = "Você não sabia. Agora sabe."
    TONE_OF_VOICE: Final[str] = "Direto, maduro, confiante, provocativo e livre de clichês motivacionais rasos."


_HEX_CHARS = set("0123456789abcdefABCDEF")


def hex_to_ass_color(hex_color: str, alpha_hex: str = "00") -> str:
    """Converte cor Hex (#RRGGBB ou #RRGGBBAA) para formato ASS BGR (&HAABBGGRR&).

    Args:
        hex_color: String contendo cor hexadecimal (ex: "#FACC15", "FACC15", "#FACC1580").
        alpha_hex: Canal alpha opcional de 2 dígitos em hexadecimal (padrão "00" = opaco no ASS).

    Returns:
        String formatada no padrão ASS BGR com delimitadores: &HAABBGGRR&.

    Raises:
        ValueError: Caso o formato hexadecimal seja inválido ou contenha caracteres não-hexadecimais.
    """
    cleaned = hex_color.strip().lstrip("#")
    if not cleaned or not all(c in _HEX_CHARS for c in cleaned):
        raise ValueError(
            f"Formato de cor Hex inválido: {hex_color!r}. Esperado #RRGGBB ou #RRGGBBAA com caracteres válidos."
        )

    if len(cleaned) == 6:
        r, g, b = cleaned[0:2], cleaned[2:4], cleaned[4:6]
        raw_a = alpha_hex.strip().lstrip("&Hh")
        if len(raw_a) == 2 and all(c in _HEX_CHARS for c in raw_a):
            a = raw_a
        else:
            a = "00"
    elif len(cleaned) == 8:
        r, g, b, a = cleaned[0:2], cleaned[2:4], cleaned[4:6], cleaned[6:8]
    else:
        raise ValueError(
            f"Formato de cor Hex inválido: {hex_color!r}. Esperado comprimento de 6 ou 8 dígitos hexadecimais."
        )

    return f"&H{a.upper()}{b.upper()}{g.upper()}{r.upper()}&"


def _infer_font_metadata(font_path: Path) -> tuple[str, Literal["montserrat", "dejavu_sans"]]:
    """Infere família ASS e variante homologada a partir do arquivo TTF."""
    if "dejavu" in font_path.name.lower():
        return ZuntoTypography.FALLBACK_FONT, "dejavu_sans"
    return ZuntoTypography.PRIMARY_FONT, "montserrat"


def _build_font_candidates(
    custom_font_path: Path | str | None = None,
) -> list[tuple[Path, str, Literal["montserrat", "dejavu_sans"]]]:
    """Constrói a lista ordenada de caminhos homologados para resolução tipográfica."""
    candidates: list[tuple[Path, str, Literal["montserrat", "dejavu_sans"]]] = []
    seen: set[str] = set()

    def _add(path: Path, font_name: str, variant: Literal["montserrat", "dejavu_sans"]) -> None:
        key = os.path.normcase(os.path.abspath(str(path)))
        if key not in seen:
            seen.add(key)
            candidates.append((path, font_name, variant))

    # 1. Caminho customizado explícito
    if custom_font_path is not None and str(custom_font_path).strip():
        custom_p = Path(custom_font_path)
        c_name, c_var = _infer_font_metadata(custom_p)
        _add(custom_p, c_name, c_var)

    # 2. Ativo versionado no repositório (assets/fonts/Montserrat-Bold.ttf)
    repo_root = Path(__file__).resolve().parents[2]
    _add(
        repo_root / "assets" / "fonts" / "Montserrat-Bold.ttf",
        ZuntoTypography.PRIMARY_FONT,
        "montserrat",
    )
    _add(
        Path.cwd() / "assets" / "fonts" / "Montserrat-Bold.ttf",
        ZuntoTypography.PRIMARY_FONT,
        "montserrat",
    )

    # 3. Instalação local Windows
    _add(
        Path("C:/Windows/Fonts/Montserrat-Bold.ttf"),
        ZuntoTypography.PRIMARY_FONT,
        "montserrat",
    )
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        _add(
            Path(local_app_data) / "Microsoft" / "Windows" / "Fonts" / "Montserrat-Bold.ttf",
            ZuntoTypography.PRIMARY_FONT,
            "montserrat",
        )

    # 4. Instalação Linux
    _add(
        Path("/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf"),
        ZuntoTypography.PRIMARY_FONT,
        "montserrat",
    )
    _add(
        Path.home() / ".local" / "share" / "fonts" / "Montserrat-Bold.ttf",
        ZuntoTypography.PRIMARY_FONT,
        "montserrat",
    )

    # 5. Fallback homologado DejaVuSans-Bold
    _add(
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ZuntoTypography.FALLBACK_FONT,
        "dejavu_sans",
    )
    _add(
        Path("C:/Windows/Fonts/DejaVuSans-Bold.ttf"),
        ZuntoTypography.FALLBACK_FONT,
        "dejavu_sans",
    )

    return candidates


def resolve_typography_font(custom_font_path: Path | str | None = None) -> ResolvedFont:
    """Resolve a fonte tipográfica homologada segundo ordem estrita de prioridade.

    Política fail-closed: se nenhum arquivo TTF homologado for encontrado em disco,
    levanta FontResolutionError detalhando caminhos verificados e instrução de
    provisionamento explícito. Nunca retorna None e nunca delega silenciosamente.
    """
    candidates = _build_font_candidates(custom_font_path=custom_font_path)
    searched_paths: list[str] = []

    for candidate_path, font_name, variant in candidates:
        searched_paths.append(str(candidate_path))
        if candidate_path.is_file():
            resolved_path = candidate_path.resolve()
            return ResolvedFont(
                font_path=resolved_path,
                fonts_dir=resolved_path.parent,
                font_name=font_name,
                variant=variant,
            )

    raise FontResolutionError(
        "Nenhuma fonte tipográfica homologada (Montserrat-Bold.ttf ou DejaVuSans-Bold.ttf) "
        f"foi encontrada. Caminhos pesquisados: {', '.join(searched_paths)}. "
        "Provisione explicitamente as fontes no ambiente antes de renderizar: "
        "sudo apt-get install -y fonts-dejavu-core fonts-montserrat"
    )
