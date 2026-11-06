import json
import logging
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from viralpanel.config import get_settings
from viralpanel.media.transcriber import TranscriptionResult

logger = logging.getLogger(__name__)

PERSONA = (
    "Você é um roteirista de vídeos curtos virais (TikTok/Reels/Shorts) no nicho de "
    "desenvolvimento pessoal e motivação, em português do Brasil. Tom direto, humano e confiante."
)

PROMPT_TEMPLATE = """{persona}

Analise o conteúdo do vídeo viral de referência abaixo (transcrição do áudio com timestamps e contexto do vídeo original).
Identifique o tema central, o gatilho do gancho e a estrutura de retenção.
Depois escreva um roteiro 100% ORIGINAL (sem copiar frases) sobre o mesmo tema, para narração em formato reaction.

Regras obrigatórias:
- hook: gancho de alta retenção falado em 0–3s (máx. ~10 palavras, impacto imediato).
- body: desenvolvimento fluido falado entre 4–45s (aprox. 70–110 palavras, persuasivo e prático).
- cta: chamada para ação final curta.
- estimated_duration_seconds entre 15 e 60.

{context_block}

Transcrição de referência:
{transcript}
"""


class GeneratedScriptSchema(BaseModel):
    theme: str = ""
    hook: str = Field(min_length=3)
    body: str = Field(min_length=20)
    cta: str = Field(min_length=3)
    estimated_duration_seconds: float = Field(ge=10, le=75)

    @property
    def full_text(self) -> str:
        return f"{self.hook}\n\n{self.body}\n\n{self.cta}"


RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "theme": {"type": "STRING"},
        "hook": {"type": "STRING"},
        "body": {"type": "STRING"},
        "cta": {"type": "STRING"},
        "estimated_duration_seconds": {"type": "NUMBER"},
    },
    "required": ["hook", "body", "cta", "estimated_duration_seconds"],
}


class ScriptWriter(ABC):
    @abstractmethod
    def generate(
        self,
        transcription: TranscriptionResult,
        fallback_context: str = "",
    ) -> GeneratedScriptSchema: ...


class GeminiScriptWriter(ScriptWriter):
    ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int = 60,
        max_retries: int = 3,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY ausente. Defina a variável no ambiente/.env ou passe api_key no construtor."
            )
        self.model = model or settings.gemini_model or "gemini-3.5-flash"
        self.timeout = timeout
        self.max_retries = max_retries

    def build_prompt(self, transcription: TranscriptionResult, fallback_context: str = "") -> str:
        transcript_text = transcription.to_timestamped_text().strip()
        if not transcript_text:
            transcript_text = "(Áudio sem fala identificada ou apenas trilha sonora de fundo)"

        context_block = ""
        if fallback_context:
            context_block = f"Contexto do Vídeo (Título/Descrição Original):\n{fallback_context}\n"

        return PROMPT_TEMPLATE.format(
            persona=PERSONA,
            context_block=context_block,
            transcript=transcript_text,
        )

    def _call(self, prompt: str) -> str:
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.8,
                "responseMimeType": "application/json",
                "responseSchema": RESPONSE_SCHEMA,
            },
        }

        url = self.ENDPOINT.format(model=self.model)
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}
        data_bytes = json.dumps(payload).encode()

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    resp_data = json.loads(resp.read().decode())
                return resp_data["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as exc:
                err_body = exc.read().decode() if exc.fp else "sem corpo de resposta"
                logger.warning(
                    "Gemini API HTTP %d (Tentativa %d/%d): %s",
                    exc.code, attempt, self.max_retries, err_body,
                )
                last_error = RuntimeError(f"Gemini API erro {exc.code}: {err_body}")
                if exc.code in (429, 500, 503):
                    time.sleep(2 ** attempt)
                    continue
                raise last_error from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                logger.warning("Falha de rede na chamada Gemini (Tentativa %d/%d): %s", attempt, self.max_retries, exc)
                last_error = exc
                time.sleep(2 ** attempt)
                continue

        raise RuntimeError(f"Falha na API Gemini após {self.max_retries} tentativas: {last_error}")

    def generate(
        self,
        transcription: TranscriptionResult,
        fallback_context: str = "",
    ) -> GeneratedScriptSchema:
        prompt = self.build_prompt(transcription, fallback_context=fallback_context)
        raw_json = self._call(prompt)
        return GeneratedScriptSchema.model_validate_json(raw_json)


class MockGeminiScriptWriter(ScriptWriter):
    def generate(
        self,
        transcription: TranscriptionResult,
        fallback_context: str = "",
    ) -> GeneratedScriptSchema:
        return GeneratedScriptSchema(
            theme="disciplina vs motivação",
            hook="Pare de esperar motivação. Ela não vem.",
            body=(
                "A verdade é que as pessoas que você admira não acordam inspiradas todos os dias. "
                "Elas criaram sistemas. Um horário fixo, uma tarefa pequena, uma regra simples: "
                "nunca falhar dois dias seguidos. Quando o hábito vira identidade, a força de vontade "
                "deixa de ser necessária. Comece hoje com algo ridículo de tão pequeno."
            ),
            cta="Salva esse vídeo e me segue para mais.",
            estimated_duration_seconds=35,
        )
