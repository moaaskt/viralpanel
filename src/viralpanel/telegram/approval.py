from pathlib import Path

from viralpanel.telegram.client import BaseTelegramClient


def build_approval_inline_keyboard(run_id: str) -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "Aprovar ✅", "callback_data": f"approve:{run_id}"},
                {"text": "Rejeitar ❌", "callback_data": f"reject:{run_id}"},
            ]
        ]
    }


def parse_approval_callback_data(callback_data: str) -> tuple[str, str]:
    """Retorna (action, run_id) onde action é 'approve' ou 'reject'."""
    if ":" not in callback_data:
        raise ValueError(f"callback_data inválido: {callback_data}")
    action, run_id = callback_data.split(":", 1)
    if action not in ("approve", "reject") or not run_id:
        raise ValueError(f"Ação de callback inválida: {callback_data}")
    return action, run_id


def send_approval_request(
    client: BaseTelegramClient,
    run_id: str,
    video_path: Path,
    hook: str = "",
    score: float | None = None,
) -> dict:
    score_str = f"{score:.1f}" if score is not None else "N/A"
    caption = (
        f"🎥 <b>Preview — Aprovação Supervisionada</b>\n"
        f"• <b>Run ID:</b> <code>{run_id}</code>\n"
        f"• <b>Gancho:</b> {hook or 'N/A'}\n"
        f"• <b>Viral Score:</b> {score_str}\n\n"
        f"Deseja aprovar a publicação deste vídeo nas redes?"
    )
    markup = build_approval_inline_keyboard(run_id)
    return client.send_video(video_path=video_path, caption=caption, reply_markup=markup)

