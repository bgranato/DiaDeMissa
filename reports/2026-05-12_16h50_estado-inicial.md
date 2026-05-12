# Estado Inicial — Gate 5, Iteração 1

**Data/hora:** 2026-05-12 16:50 (BRT)
**Gate:** 05 — Estruturação por regras
**Iteração:** 1 (primeira)
**Status:** ⏳ em progresso

---

## 1. O que foi feito

- Reset completo do projeto (`_archive_20260512/`)
- Schema Pydantic com 11 modelos (Canto, Leitura, Salmo, Aclamacao, Antifona, Oracao, Dialogo, Turno, Versiculo, Creditos, PalavraDoDia, Missa)
- Validadores com 9 padrões de artefatos proibidos
- Pipeline de extração (PyMuPDF com reconstrução de espaços por gap horizontal)
- Pipeline de limpeza (6 regexes: hifenização, junção de linhas, separação de siglas, normalização)
- Structurer rule-based com detecção de Canto, Saudação e Antífona
- Suíte de testes com 54 testes baseados no gabarito da Ascensão 2026

---

## 2. Output do pytest

```
$ pytest tests/test_ascensao_2026.py -v --tb=short

============================= test session starts =============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0
rootdir: .../backend
plugins: anyio-4.12.1
collected 54 items

tests/test_ascensao_2026.py  ... 37 passed, 7 failed, 10 errors in 1.84s
========================== 37 passed, 7 failed, 10 errors in 1.84s ==========
```

**Resumo numérico:** 37 passed, 7 failed, 10 errors (54 total)

---

## 3. Testes verdes (37)

- `TestMetadados::test_data`
- `TestMetadados::test_titulo`
- `TestMetadados::test_categoria`
- `TestMetadados::test_ano_liturgico`
- `TestMetadados::test_observacoes_mencionam_dia_das_comunicacoes`
- `TestCreditos::test_entrada`
- `TestCreditos::test_ofertas`
- `TestCreditos::test_comunhao`
- `TestCantoEntrada::test_tipo`
- `TestCantoEntrada::test_quantidade_estrofes`
- `TestCantoEntrada::test_primeira_estrofe_exata`
- `TestCantoEntrada::test_nenhum_verso_contem_barra`
- `TestCantoEntrada::test_nenhum_verso_contem_numero_estrofe`
- `TestCantoEntrada::test_creditos_nao_estao_no_canto`
- `TestSaudacao::test_tipo`
- `TestSaudacao::test_quatro_turnos`
- `TestSaudacao::test_sequencia_falantes`
- `TestSaudacao::test_primeiro_turno`
- `TestSaudacao::test_segundo_turno`
- `TestSaudacao::test_terceiro_turno_completo`
- `TestSaudacao::test_quarto_turno`
- `TestSaudacao::test_nenhum_turno_orfao`
- `TestSaudacao::test_nenhum_turno_tem_sigla_no_texto`
- `TestAntifonaEntrada::test_tipo`
- `TestAntifonaEntrada::test_e_bloco_independente`
- `TestPalavraDoDia::test_vem_do_evangelho_da_ascensao`
- `TestPalavraDoDia::test_nao_e_frase_generica_aleatoria`
- `TestPalavraDoDia::test_tema_central`
- `TestInvariantesGlobais::test_zero_markdown`
- `TestInvariantesGlobais::test_zero_hifens_orfaos`
- `TestInvariantesGlobais::test_zero_palavras_mutiladas`
- `TestInvariantesGlobais::test_zero_palavras_coladas`
- `TestInvariantesGlobais::test_zero_postura_como_texto`
- `TestInvariantesGlobais::test_zero_siglas_falante_em_texto_de_dialogo`
- `TestInvariantesGlobais::test_ordem_sequencial`
- `TestInvariantesGlobais::test_todos_blocos_tem_titulo`
- `TestIdempotencia::test_processar_duas_vezes_produz_mesmo_resultado`

---

## 4. Testes vermelhos — FAILED (7)

### `TestCreditos::test_final`

**Mensagem do assert:**
```
AssertionError: assert 'Antífona Mariana / Liturgia das' == 'Antífona Mariana / Liturgia das Horas'
```

**Esperado:**
```
"Antífona Mariana / Liturgia das Horas"
```

**Recebido:**
```
"Antífona Mariana / Liturgia das"
```

**Localização:** `tests/test_ascensao_2026.py:52`

---

### `TestCantoEntrada::test_postura`

**Mensagem do assert:**
```
AssertionError: assert None == 'de_pe'
```

**Esperado:** `'de_pe'`
**Recebido:** `None`
**Localização:** `tests/test_ascensao_2026.py:64`

---

### `TestCantoEntrada::test_refrao_exato`

**Mensagem do assert:**
```
AssertionError: assert ['REFRÃO: O Senhor foi preparar', 'um lugar para nós no céu.'] == ['O Senhor foi preparar um lugar para nós no céu.']
```

**Esperado:** `["O Senhor foi preparar um lugar para nós no céu."]`
**Recebido:** `["REFRÃO: O Senhor foi preparar", "um lugar para nós no céu."]`
**Localização:** `tests/test_ascensao_2026.py:67`

---

### `TestCantoEntrada::test_quarta_estrofe_exata`

**Mensagem do assert:**
```
AssertionError: assert ['Ó Jesus, nosso Rei...', 'Aleluia!', 'Não deixeis...'] == ['Ó Jesus, nosso Rei... Aleluia!', 'Não deixeis... Aleluia!']
```

**Esperado:** 2 versos (/"Aleluia!" unido ao verso anterior)
**Recebido:** 3 itens no array (verso quebrado)
**Localização:** `tests/test_ascensao_2026.py:79`

---

### `TestAntifonaEntrada::test_referencia`

**Mensagem do assert:**
```
AssertionError: assert None == 'At 1,11'
```

**Esperado:** `'At 1,11'`
**Recebido:** `None` (referência dentro do texto: "(At 1,11)")
**Localização:** `tests/test_ascensao_2026.py:147`

---

### `TestAntifonaEntrada::test_texto_completo`

**Mensagem do assert:**
```
AssertionError: assert '(At 1,11) Homens da Galileia...' == 'Homens da Galileia...'
```

**Esperado:** texto sem "(At 1,11)"
**Recebido:** texto com "(At 1,11)" prefixado
**Localização:** `tests/test_ascensao_2026.py:150`

---

### `TestInvariantesGlobais::test_zero_barras_separadoras`

**Mensagem do assert:**
```
AssertionError: ' / ' in 'Antífona Mariana / Liturgia das'
```

**Esperado:** sem " / "
**Recebido:** crédito `final` contém "Antífona Mariana / Liturgia das"
**Localização:** `tests/test_ascensao_2026.py:243`

---

## 5. Testes quebrados — ERROR (10)

### `TestAtoPenitencial::test_tem_rubrica_de_silencio`

**Tipo:** `StopIteration`
**Mensagem:** Nenhum bloco com `titulo == "Ato Penitencial"`
**Stack:**
```
File "tests/test_ascensao_2026.py:165", in ato
    return next(b for b in missa.blocos if b.titulo == "Ato Penitencial")
```

### `TestAtoPenitencial::test_alterna_padre_assembleia`

Mesmo `StopIteration` — Ato Penitencial não detectado.

### `TestPrimeiraLeitura::test_referencia`

**Tipo:** `StopIteration`
**Mensagem:** Nenhum bloco com `categoria == "primeira_leitura"`
**Stack:**
```
File "tests/test_ascensao_2026.py:182", in leitura
    return next(b for b in missa.blocos if hasattr(b, "categoria") and b.categoria == "primeira_leitura")
```

### `TestPrimeiraLeitura::test_postura` (idem)
### `TestPrimeiraLeitura::test_introducao` (idem)
### `TestPrimeiraLeitura::test_conclusao` (idem)
### `TestPrimeiraLeitura::test_resposta` (idem)
### `TestPrimeiraLeitura::test_tem_versiculos_numerados` (idem)
### `TestPrimeiraLeitura::test_versiculos_em_ordem` (idem)
### `TestPrimeiraLeitura::test_numero_nao_aparece_no_texto` (idem)

Todos os 8 errors de Ato Penitencial e Primeira Leitura são `StopIteration`: blocos não foram implementados no structurer rule-based.

---

## 6. Arquivos do pipeline

```
backend/app/pipeline/__init__.py
backend/app/pipeline/clean.py
backend/app/pipeline/extract.py
backend/app/pipeline/structure.py
backend/app/schema/__init__.py
backend/app/schema/missa.py
backend/app/schema/validators.py
backend/app/llm/__init__.py
backend/app/llm/base.py
backend/app/llm/deepseek.py
backend/app/llm/prompts.py
backend/tests/test_schema.py (11)
backend/tests/test_clean.py (10)
backend/tests/test_extract.py (5)
backend/tests/test_ascensao_2026.py (54)
backend/tests/fixtures/amissa_ascensao_2026.expected.json
backend/tests/fixtures/amissa_ascensao_2026.pdf
```

---

## 7. Diagnóstico próprio

Os 10 errors têm causa comum: o structurer rule-based (`structure.py`) implementa apenas detecção para `Canto de Entrada`, `Saudação`, `Antífona da Entrada` e seus blocos adjacentes. Blocos como `Ato Penitencial`, `Primeira Leitura`, `Salmo Responsorial`, `Segunda Leitura`, `Evangelho`, `Profissão de Fé`, `Oração dos Fiéis`, `Canto das Ofertas`, `Oração Eucarística`, `Pai Nosso`, `Canto de Comunhão` e `Bênção Final` não têm detecção alguma.

Os 7 failed concentram-se em 3 áreas:
1. **Canto de Entrada** — postura não extraída, refrão com prefixo "REFRÃO:", estrofe 4 quebrada em vez de unir versos com "/"
2. **Antífona** — referência bíblica não separada do texto
3. **Créditos** — regex `Final:` corta antes de "Horas" por causa do ";"

---

## 8. Decisões pendentes

- **LLM vs rule-based:** Sem chave de API, o structurer rule-based precisa ser expandido para cobrir todos os ~22 blocos. Isso é viável mas trabalhoso (~novos 15 blocos para implementar). Com LLM, todos seriam resolvidos de uma vez.
- **Barra nos créditos:** `"Antífona Mariana / Liturgia das Horas"` tem "/" legítimo. O validador `ARTEFATOS_PROIBIDOS` rejeita, mas o dado é correto. Precisa de exceção para campo `creditos_cantos.final`.

---

## 9. Próxima ação proposta

Expandir structurer rule-based para cobrir os blocos faltantes: Ato Penitencial (turnos com rubrica), Primeira Leitura (versículos numerados), Salmo Responsorial, Segunda Leitura, Evangelho, Profissão de Fé, Oração dos Fiéis, Canto das Ofertas, Oração Eucarística, Pai Nosso, Canto de Comunhão, Bênção Final. Ou, alternativamente, configurar chave DeepSeek/OpenAI para estruturação via LLM.

---

**AGUARDANDO ORIENTAÇÃO. NÃO VOU EXECUTAR A PRÓXIMA AÇÃO SEM RESPOSTA.**
