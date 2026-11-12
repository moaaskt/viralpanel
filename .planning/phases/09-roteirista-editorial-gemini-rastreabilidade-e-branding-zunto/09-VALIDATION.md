# Validation Strategy: Phase 9 — Roteirista Editorial Gemini, Rastreabilidade e Branding ZUNTO!

## Verification Dimensions

### Dimension 1: Identidade Visual e Branding ZUNTO! (`BRND-01`, `BRND-02`)
- **Verificação**: Presença e integridade de `src/viralpanel/branding.py` com `ZuntoPalette`, `ZuntoTypography`, `SafeZones9x16`, `BrandGuidelines` e função `hex_to_ass_color`.
- **Asserção de Cor BGR**: Garantir que `hex_to_ass_color("#FACC15") == "&H0015CCFA&"` e `hex_to_ass_color("#0A0A0A") == "&H000A0A0A&"`.
- **Comando automatizado**: `.venv/bin/pytest tests/test_branding.py -v`

### Dimension 2: Qualidade Editorial do Roteirista Gemini (`SCRP-01`)
- **Verificação**: Prompt e persona atualizados para gancho nos primeiros 0-3s, desenvolvimento dinâmico e separação de `closing_thought` (obrigatório) e `cta` (opcional).
- **Asserção de Full Text**: `GeneratedScriptSchema.full_text` deve conter `closing_thought` e omitir blocos de CTA quando `cta` for `None` ou vazio, sem gerar linhas em branco órfãs.
- **Comando automatizado**: `.venv/bin/pytest tests/test_gemini_scripting.py -k "test_generated_script_schema" -v`

### Dimension 3: Rastreabilidade Factual de Fontes (`SCRP-02`)
- **Verificação**: Modelo `FactualClaim` e parsing de lista de claims no retorno do Gemini; persistência dos dados no campo `metadata_json` da entidade `Script`.
- **Asserção de Persistência**: Ao processar um vídeo no `ScriptingService`, o `Script` persistido deve conter `metadata_json["factual_claims"]` estruturado.
- **Comando automatizado**: `.venv/bin/pytest tests/test_gemini_scripting.py -k "test_factual_claims" -v`

### Dimension 4: Ausência de Regressão no Pipeline e Testes
- **Verificação**: Execução de toda a suíte de testes do projeto garantindo retrocompatibilidade total.
- **Comando automatizado**: `.venv/bin/pytest tests/test_gemini_scripting.py tests/test_models.py tests/test_branding.py -v`

