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

# Diretriz de persona masculina/neutra: voz firme de mentor/criador solo (marca ZUNTO!)
PERSONA = (
    "Você é o roteirista editorial da marca ZUNTO!, focado em vídeos curtos verticais (9:16 para TikTok, Reels e Shorts) "
    "no nicho de desenvolvimento pessoal, alta performance, foco, clareza mental e mentalidade estratégica. "
    "Voz e postura: Criador solo masculino/neutro, tom direto, maduro, confiante, firme, provocativo e sem enrolação. "
    "Filosofia editorial: Orientada pela máxima 'Você não sabia. Agora sabe.' — uma postura de revelação, suspense e "
    "desconstrução de ilusões, sem impor frases de encerramento forçadas ou chavões artificiais. "
    "Cadência e fala: Escreva frases com pontuação limpa e cadência rítmica natural ideal para síntese de voz (TTS). "
    "IMPORTANTE: Sempre escreva na primeira ou segunda pessoa com concordância masculina ou neutra "
    "(exemplo: 'focado', 'determinado', 'preparado'). Nunca assuma gênero feminino, mesmo que o vídeo original "
    "de referência tenha sido gravado por uma mulher."
)

PROMPT_TEMPLATE = """{persona}

Analise criticamente o vídeo viral de referência abaixo (transcrição do áudio com timestamps e contexto do vídeo original).
Identifique o tema central, a dor invisível ou equívoco comum abordado, e o gatilho psicológico de curiosidade.
Depois, escreva um roteiro 100% ORIGINAL (sem copiar nenhuma frase do vídeo de referência) sobre o mesmo tema,
pensado para o formato reaction e narração falada fluida por uma voz masculina firme.

Diretrizes obrigatórias de estrutura editorial:
- hook: gancho cortante e magnético para os primeiros 0–3 segundos (máximo ~10 palavras, corte seco e provocativo).
  Proibido iniciar com saudações ('Oi', 'Fala pessoal') ou introduções mornas.
- body: desenvolvimento fluido e instigante para o intervalo de 4–45 segundos (aprox. 70–110 palavras),
  revelando o cerne da ideia com clareza prática e cadência perfeita para áudio.
- closing_thought: fechamento narrativo e reflexivo obrigatório, que arremata a ideia central com peso e autoridade.
  (Nota: O conceito 'Você não sabia. Agora sabe.' orienta a essência da revelação, mas use essa frase exata apenas quando fizer sentido editorial genuíno).
- cta: chamada para ação final estritamente OPCIONAL. Se não houver uma chamada genuinamente contextual e relevante,
  deixe como null. Não force chavões genéricos ('curte e compartilha') desnecessários.
- estimated_duration_seconds: duração estimada realista da narração falada entre 15 e 60 segundos.
- factual_claims: lista de afirmações factuais (dados, estudos, nomes de autores ou conceitos específicos)
  mencionadas no roteiro e embasadas estritamente na transcrição de referência.
  Para cada claim:
  * claim: afirmação factual sintetizada.
  * source_reference: autor/livro/estudo mencionado na transcrição (ou null se não citado).
  * source_excerpt: trecho correspondente da transcrição original.
  * timestamp: marcação temporal na transcrição (ex: '00:15'), se presente, ou null.
  * verification_status: use 'extracted_from_transcript' ou 'unverified_source_claim'.
  ATENÇÃO RIGOROSA: NUNCA invente fontes, links, pesquisas ou evidências que não constem na transcrição de referência.

{context_block}

Transcrição de referência:
{transcript}
"""


class FactualClaim(BaseModel):
    claim: str = Field(description="Afirmação factual feita no roteiro")
    source_reference: str | None = Field(default=None, description="Referência ou origem mencionada")
    source_excerpt: str | None = Field(default=None, description="Trecho da transcrição original correspondente")
    timestamp: str | None = Field(default=None, description="Timestamp aproximado na transcrição original")
    verification_status: str = Field(
        default="unverified_source_claim",
        description="Status de verificação do claim (sem presumir veracidade externa)",
    )


class GeneratedScriptSchema(BaseModel):
    theme: str = ""
    hook: str = Field(min_length=3)
    body: str = Field(min_length=20)
    closing_thought: str = Field(default="", description="Fechamento narrativo reflexivo")
    cta: str | None = Field(default=None, description="Chamada para ação opcional")
    estimated_duration_seconds: float = Field(ge=10, le=75)
    factual_claims: list[FactualClaim] = Field(default_factory=list)

    @property
    def full_text(self) -> str:
        parts = [self.hook.strip(), self.body.strip()]
        if self.closing_thought and self.closing_thought.strip():
            parts.append(self.closing_thought.strip())
        if self.cta and self.cta.strip():
            parts.append(self.cta.strip())
        return "\n\n".join(parts)


RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "theme": {"type": "STRING"},
        "hook": {"type": "STRING"},
        "body": {"type": "STRING"},
        "closing_thought": {"type": "STRING"},
        "cta": {"type": "STRING", "nullable": True},
        "estimated_duration_seconds": {"type": "NUMBER"},
        "factual_claims": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "claim": {"type": "STRING"},
                    "source_reference": {"type": "STRING", "nullable": True},
                    "source_excerpt": {"type": "STRING", "nullable": True},
                    "timestamp": {"type": "STRING", "nullable": True},
                    "verification_status": {"type": "STRING"},
                },
                "required": ["claim", "verification_status"],
            },
        },
    },
    "required": ["hook", "body", "closing_thought", "estimated_duration_seconds"],
}


class ScriptWriter(ABC):
    @abstractmethod
    def generate(
        self,
        transcription: TranscriptionResult,
        fallback_context: str = "",
    ) -> GeneratedScriptSchema: ...


# =============================================================================
# 1. Provedor Google Gemini (Gemini 3.5 Flash / Gemini 3.5 Flash Lite)
# =============================================================================
class GeminiScriptWriter(ScriptWriter):
    ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int = 45,
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
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
            "User-Agent": "ViralPanel/1.0",
        }
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
                    "Gemini API (%s) HTTP %d (Tentativa %d/%d): %s",
                    self.model, exc.code, attempt, self.max_retries, err_body,
                )
                last_error = RuntimeError(f"Gemini API erro {exc.code} ({self.model}): {err_body}")
                if exc.code in (429, 500, 503):
                    time.sleep(2 ** attempt)
                    continue
                raise last_error from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                logger.warning("Falha de rede na chamada Gemini (%s, Tentativa %d/%d): %s", self.model, attempt, self.max_retries, exc)
                last_error = exc
                time.sleep(2 ** attempt)
                continue

        raise RuntimeError(f"Falha na API Gemini ({self.model}) após {self.max_retries} tentativas: {last_error}")

    def generate(
        self,
        transcription: TranscriptionResult,
        fallback_context: str = "",
    ) -> GeneratedScriptSchema:
        prompt = self.build_prompt(transcription, fallback_context=fallback_context)
        raw_json = self._call(prompt)
        return GeneratedScriptSchema.model_validate_json(raw_json)


# =============================================================================
# 2. Provedor Groq Cloud (Llama 3.3 70B Versatile)
# =============================================================================
class GroqScriptWriter(ScriptWriter):
    ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int = 45,
        max_retries: int = 3,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.groq_api_key
        if not self.api_key:
            raise ValueError("GROQ_API_KEY ausente. Defina a variável no ambiente/.env ou passe api_key.")
        self.model = model or settings.groq_model or "llama-3.3-70b-versatile"
        self.timeout = timeout
        self.max_retries = max_retries

    def build_system_message(self) -> str:
        return (
            f"{PERSONA}\n\n"
            "Você DEVE retornar OBRIGATORIAMENTE um objeto JSON válido contendo exatamente as chaves:\n"
            "- \"theme\": string com o tema central\n"
            "- \"hook\": string com o gancho falado em 0-3 segundos (máximo ~10 palavras, cortante e provocativo)\n"
            "- \"body\": string com o desenvolvimento fluido (aprox 70-110 palavras)\n"
            "- \"closing_thought\": string com o fechamento narrativo e reflexivo\n"
            "- \"cta\": string com chamada para ação final curta OU null caso não haja chamada contextual\n"
            "- \"estimated_duration_seconds\": número entre 15 e 60\n"
            "- \"factual_claims\": lista de objetos contendo \"claim\", \"source_reference\" (ou null), "
            "\"source_excerpt\" (ou null), \"timestamp\" (ou null), \"verification_status\" (ex: 'extracted_from_transcript'). "
            "Nunca invente fatos ou fontes fora da transcrição.\n"
            "Não retorne markdown ou texto fora do JSON."
        )

    def build_user_prompt(self, transcription: TranscriptionResult, fallback_context: str = "") -> str:
        transcript_text = transcription.to_timestamped_text().strip()
        if not transcript_text:
            transcript_text = "(Áudio sem fala identificada ou apenas trilha sonora de fundo)"

        context_block = ""
        if fallback_context:
            context_block = f"Contexto do Vídeo (Título/Descrição Original):\n{fallback_context}\n"

        return f"{context_block}\nTranscrição de referência:\n{transcript_text}\n"

    def _call(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.build_system_message()},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.8,
        }

        # Atenção crítica: User-Agent personalizado obrigatório para evitar bloqueio Cloudflare (Error 1010)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "ViralPanel/1.0",
        }
        data_bytes = json.dumps(payload).encode()

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            req = urllib.request.Request(self.ENDPOINT, data=data_bytes, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    resp_data = json.loads(resp.read().decode())
                return resp_data["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as exc:
                err_body = exc.read().decode() if exc.fp else "sem corpo"
                logger.warning(
                    "Groq API (%s) HTTP %d (Tentativa %d/%d): %s",
                    self.model, exc.code, attempt, self.max_retries, err_body,
                )
                last_error = RuntimeError(f"Groq API erro {exc.code} ({self.model}): {err_body}")
                if exc.code in (429, 500, 503):
                    time.sleep(2 ** attempt)
                    continue
                raise last_error from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                logger.warning("Falha de rede na chamada Groq (%s, Tentativa %d/%d): %s", self.model, attempt, self.max_retries, exc)
                last_error = exc
                time.sleep(2 ** attempt)
                continue

        raise RuntimeError(f"Falha na API Groq ({self.model}) após {self.max_retries} tentativas: {last_error}")

    def generate(
        self,
        transcription: TranscriptionResult,
        fallback_context: str = "",
    ) -> GeneratedScriptSchema:
        prompt = self.build_user_prompt(transcription, fallback_context=fallback_context)
        raw_json = self._call(prompt)
        return GeneratedScriptSchema.model_validate_json(raw_json)


# =============================================================================
# 3. Cadeia de Fallback Multi-IA (Gemini Flash -> Gemini Flash Lite -> Groq Llama)
# =============================================================================
class FallbackScriptWriter(ScriptWriter):
    """Encadeador resiliente de provedores de IA:

    1. Gemini 3.5 Flash (Principal, alta qualidade e velocidade)
    2. Gemini 3.5 Flash Lite (Fallback imediato de cota/demanda)
    3. Groq Llama 3.3 70B (Provedor independente gratuito de altíssima velocidade)
    """

    def __init__(self, writers: list[ScriptWriter] | None = None):
        if writers is not None:
            self.writers = writers
        else:
            settings = get_settings()
            self.writers = []

            # 1. Gemini Primário
            if settings.gemini_api_key:
                try:
                    self.writers.append(GeminiScriptWriter(model=settings.gemini_model))
                except Exception as e:
                    logger.warning("Não foi possível inicializar Gemini Primário: %s", e)

            # 2. Gemini Fallback Lite
            if settings.gemini_api_key and settings.gemini_fallback_model:
                try:
                    self.writers.append(GeminiScriptWriter(model=settings.gemini_fallback_model))
                except Exception as e:
                    logger.warning("Não foi possível inicializar Gemini Fallback: %s", e)

            # 3. Groq Llama 3.3 70B
            if settings.groq_api_key:
                try:
                    self.writers.append(GroqScriptWriter(model=settings.groq_model))
                except Exception as e:
                    logger.warning("Não foi possível inicializar Groq Fallback: %s", e)

        if not self.writers:
            logger.warning("Nenhum provedor de IA real configurado. FallbackScriptWriter usará MockGeminiScriptWriter.")
            self.writers.append(MockGeminiScriptWriter())

    def generate(
        self,
        transcription: TranscriptionResult,
        fallback_context: str = "",
    ) -> GeneratedScriptSchema:
        errors = []
        for writer in self.writers:
            writer_name = f"{writer.__class__.__name__}({getattr(writer, 'model', 'default')})"
            try:
                logger.info("Tentando geração de roteiro com: %s", writer_name)
                result = writer.generate(transcription, fallback_context=fallback_context)
                logger.info("Roteiro gerado com sucesso via %s!", writer_name)
                return result
            except Exception as exc:
                logger.warning("Falha no provedor %s: %s. Tentando próximo da cadeia...", writer_name, exc)
                errors.append(f"{writer_name}: {exc}")

        raise RuntimeError(f"Todos os provedores da cadeia de IA falharam: {'; '.join(errors)}")


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
            closing_thought="Quem domina a própria rotina não precisa de sorte.",
            cta="Salva esse vídeo e me segue para mais.",
            estimated_duration_seconds=35,
            factual_claims=[
                FactualClaim(
                    claim="Pessoas de alta performance dependem de sistemas, não de inspiração diária.",
                    source_reference="Hábitos Atômicos / James Clear",
                    source_excerpt="quando o hábito vira identidade a força de vontade deixa de ser necessária",
                    timestamp="00:15",
                    verification_status="extracted_from_transcript",
                )
            ],
        )
