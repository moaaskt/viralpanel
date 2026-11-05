from viralpanel.telegram.client import BaseTelegramClient, MockTelegramClient


class TelegramNotifier:
    """Formata e envia notificações estruturadas de observabilidade do pipeline."""

    def __init__(self, client: BaseTelegramClient | None = None):
        self.client = client or MockTelegramClient()

    def notify_pipeline_started(self, run_id: str, run_date: str) -> dict:
        text = (
            f"🚀 <b>ViralPanel — Pipeline Iniciado</b>\n"
            f"• <b>Run ID:</b> <code>{run_id}</code>\n"
            f"• <b>Data:</b> {run_date}"
        )
        return self.client.send_message(text=text)

    def notify_stage_completed(self, run_id: str, stage: str, details: dict | None = None) -> dict:
        details_lines = ""
        if details:
            formatted = [f"  - <b>{k}:</b> {v}" for k, v in details.items() if v is not None]
            if formatted:
                details_lines = "\n" + "\n".join(formatted)
        text = (
            f"✅ <b>Etapa Concluída: {stage.upper()}</b>\n"
            f"• <b>Run ID:</b> <code>{run_id}</code>"
            f"{details_lines}"
        )
        return self.client.send_message(text=text)

    def notify_error(self, run_id: str, stage: str, error_message: str) -> dict:
        text = (
            f"🚨 <b>Erro na Pipeline — Etapa: {stage.upper()}</b>\n"
            f"• <b>Run ID:</b> <code>{run_id}</code>\n"
            f"• <b>Erro:</b> <code>{error_message}</code>"
        )
        return self.client.send_message(text=text)

    def notify_pipeline_success(self, run_id: str, summary: dict) -> dict:
        text = (
            f"🎬 <b>Pipeline Finalizado com Sucesso!</b>\n"
            f"• <b>Run ID:</b> <code>{run_id}</code>\n"
            f"• <b>Vídeo Selecionado:</b> {summary.get('selected_video_url', 'N/A')}\n"
            f"• <b>Score:</b> {summary.get('selected_video_score', 'N/A')}\n"
            f"• <b>Status Aprovação:</b> {summary.get('approval_status', 'N/A')}"
        )
        return self.client.send_message(text=text)
