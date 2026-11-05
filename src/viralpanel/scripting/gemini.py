import json
import urllib.request
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from viralpanel.config import get_settings
from viralpanel.media.transcriber import TranscriptionResult

PERSONA = (
    "Você é um roteirista de vídeos curtos virais (TikTok/Reels/Shorts) no nicho de "
    "desenvolvimento pessoal e motivação, em português do Brasil. Tom direto, humano e confiante."
)

PROMPT_TEMPLATE = """{persona}

Analise a transcrição de um vídeo viral de referência abaixo. Identifique o tema central,
o gatilho do gancho e a estrutura de retenção. Depois escreva um roteiro 100% ORIGINAL
(sem copiar frases) sobre o mesmo tema, para narração em formato reaction.

Regras obrigatórias:
- hook: gancho de alta retenção falado em 0–3s (máx. ~10 palavras).
- body: desenvolvimento fluido falado entre 4–45s (aprox. 70–110 palavras).
- cta: chamada para ação final curta.
- estimated_duration_seconds entre 15 e 60.

Transcrição de referência (com timestamps):
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
    def generate(self, transcription: TranscriptionResult) -> GeneratedScriptSchema: ...


class GeminiScriptWriter(ScriptWriter):
    ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int = 60,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY ausente. Defina a variável no ambiente/.env ou passe api_key no construtor."
            )
        self.model = model or settings.gemini_model or "gemini-2.5-flash"
        self.timeout = timeout

    def build_prompt(self, transcription: TranscriptionResult) -> str:
        return PROMPT_TEMPLATE.format(persona=PERSONA, transcript=transcription.to_timestamped_text())

    def _call(self, prompt: str) -> str:
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.9,
                "responseMimeType": "application/json",
                "responseSchema": RESPONSE_SCHEMA,
            },
        }
        req = urllib.request.Request(
            self.ENDPOINT.format(model=self.model),
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read())
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def generate(self, transcription: TranscriptionResult) -> GeneratedScriptSchema:
        raw = self._call(self.build_prompt(transcription))
        return GeneratedScriptSchema.model_validate_json(raw)


class MockGeminiScriptWriter(ScriptWriter):
    def generate(self, transcription: TranscriptionResult) -> GeneratedScriptSchema:
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

