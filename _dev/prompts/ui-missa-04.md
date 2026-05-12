# Protocolo de Relatórios — adicionar ao projeto

> Cole este documento como mensagem para o DeepSeek **após** o prompt principal de reset. É uma instrução de protocolo, não substitui a spec do projeto.

---

## Por que isto existe

Você (DeepSeek) e eu (usuário) precisamos de um terceiro participante na conversa: o Claude, que faz a arquitetura e diagnóstico. Eu sou o canal entre vocês. Pra esse fluxo funcionar, todo relatório de progresso seu precisa estar em **arquivo de texto que eu possa copiar inteiro** e levar pra ele.

Não basta você descrever no chat do VS Code. O scroll some, o histórico se perde, e eu acabo passando um resumo enviesado da sua descrição para o Claude. Em vez disso: você escreve um arquivo `.md` formal e completo, eu mando pro Claude exatamente o que está lá, e ele responde com base em fatos, não na minha interpretação.

---

## Estrutura de pastas

Crie no projeto:

```
reports/
  INDEX.md                                     # sumário sempre atualizado
  2026-05-12_14h30_gate-00-reset.md           # cada relatório timestamped
  2026-05-12_14h45_gate-01-schema.md
  2026-05-12_15h00_gate-02-clean.md
  ...
```

**Convenção de nome do arquivo:**

```
YYYY-MM-DD_HHhMM_<contexto>.md
```

Onde `<contexto>` é um dos:

- `gate-NN-nome` para conclusão de gate (ex.: `gate-04-suite-criada`)
- `gate-NN-iter-MM-descricao` para iterações dentro de um gate (ex.: `gate-06-iter-03-conserto-ato-penitencial`)
- `bloqueio-descricao` quando você travar e precisar de orientação (ex.: `bloqueio-llm-sem-api-key`)

Use timestamp do momento real (não invente). Em shell: `date +%Y-%m-%d_%Hh%M`.

---

## Template do relatório

Todo relatório deve seguir **exatamente** este formato. Copie e preencha:

````markdown
# <Título descritivo do relatório>

**Data/hora:** YYYY-MM-DD HH:MM (TZ)
**Gate:** NN — <nome do gate>
**Iteração:** N (se aplicável, senão "única")
**Status:** ✅ verde | ⏳ em progresso | ❌ bloqueado

---

## 1. O que foi feito nesta iteração

Bullets curtos descrevendo as mudanças. Sem floreio.

- Criado `src/schema/missa.py` com 7 modelos Pydantic
- Adicionado validator `ARTEFATOS_PROIBIDOS` em `src/schema/validators.py`
- Etc.

---

## 2. Output do pytest

```
$ pytest tests/test_ascensao_2026.py -v --tb=short

============================= test session starts =============================
<COLAR OUTPUT COMPLETO AQUI, SEM EDITAR>
========================== 37 passed, 7 failed, 10 errors in 3.42s ==========
```

**Resumo numérico:** 37 passed, 7 failed, 10 errors (54 total)

---

## 3. Testes verdes (✅)

Lista bullet com nome completo de cada teste que passou:

- `TestMetadados::test_data`
- `TestMetadados::test_titulo`
- `TestCreditos::test_entrada`
- (etc.)

---

## 4. Testes vermelhos — FAILED (❌)

Para cada teste failed, este bloco:

### `TestSaudacao::test_terceiro_turno_completo`

**Mensagem do assert:**
```
AssertionError: assert 'A graça e a paz' == 'A graça e a paz daquele que é, que era e que vem, estejam convosco.'
```

**Esperado:**
```
"A graça e a paz daquele que é, que era e que vem, estejam convosco."
```

**Recebido:**
```
"A graça e a paz"
```

**Localização no código:** `tests/test_ascensao_2026.py:152`

---

### `<próximo teste failed>`

(repita o bloco)

---

## 5. Testes quebrados — ERROR (💥)

Para cada error, este bloco:

### `TestPrimeiraLeitura::test_tem_versiculos_numerados`

**Tipo da exceção:** `AttributeError`

**Mensagem:**
```
AttributeError: 'NoneType' object has no attribute 'versiculos'
```

**Stack trace (últimas 2 linhas):**
```
File "tests/test_ascensao_2026.py", line 234, in test_tem_versiculos_numerados
    assert len(leitura.versiculos) >= 11
```

**Hipótese:** O bloco "primeira_leitura" não está sendo criado pelo structurer, então o `next(...)` do fixture retorna `None`.

---

### `<próximo error>`

(repita o bloco)

---

## 6. Arquivos modificados/criados nesta iteração

- `src/schema/missa.py` (criado)
- `src/schema/validators.py` (criado)
- `tests/test_schema.py` (criado, 8 testes)
- `src/pipeline/clean.py` (modificado — linha 23: regex de hifenização)

---

## 7. Diagnóstico próprio

Em 3-6 linhas, sua hipótese do que está causando os problemas. **NÃO** conserte ainda — só diagnostique. Exemplo:

> Os erros do Ato Penitencial e da Primeira Leitura parecem ter causa comum:
> o `structurer.py` não está reconhecendo blocos que começam com número
> mas sem o padrão "1. Canto..." (ex.: "3. Ato Penitencial" e "6. Primeira
> Leitura (At 1,1-11) (Sentados)"). A regex atual em `_detectar_inicio_bloco`
> (linha 87) só captura títulos simples sem referência/postura inline.

---

## 8. Decisões pendentes / dúvidas para o arquiteto

Lista bullet de coisas que você não tem autonomia para decidir:

- Devo configurar chave de LLM (DeepSeek/OpenAI) ou refinar rule-based?
- Schema atual não tem campo para "comentário antes da leitura" (texto do L.
  antes da Primeira Leitura). Adiciono ou descarto?

---

## 9. Próxima ação proposta

O que eu **proponho** fazer no próximo passo, aguardando confirmação:

> Refatorar `structurer.py:_detectar_inicio_bloco` para aceitar títulos com
> referência inline `(At 1,1-11)` e postura `(Sentados)`. Aguardando autorização.

---

**AGUARDANDO ORIENTAÇÃO. NÃO VOU EXECUTAR A PRÓXIMA AÇÃO SEM RESPOSTA.**
````

---

## INDEX.md — sumário sempre atualizado

Toda vez que criar um relatório novo, **atualize** `reports/INDEX.md`. Formato:

```markdown
# Índice de Relatórios — App de Missa

Última atualização: YYYY-MM-DD HH:MM

## Status geral

- Gate atual: **6** (estruturação por LLM/rules)
- Testes: 37/54 verdes (68.5%)
- Bloqueios ativos: 1 (chave de API LLM)

## Histórico

| Data/hora | Gate | Iteração | Status | Arquivo |
|---|---|---|---|---|
| 2026-05-12 14:30 | 00 | única | ✅ | [gate-00-reset](2026-05-12_14h30_gate-00-reset.md) |
| 2026-05-12 14:45 | 01 | única | ✅ | [gate-01-schema](2026-05-12_14h45_gate-01-schema.md) |
| 2026-05-12 15:00 | 02 | única | ✅ | [gate-02-clean](2026-05-12_15h00_gate-02-clean.md) |
| 2026-05-12 15:20 | 03 | única | ✅ | [gate-03-extract](2026-05-12_15h20_gate-03-extract.md) |
| 2026-05-12 15:40 | 04 | única | ✅ | [gate-04-suite-criada](2026-05-12_15h40_gate-04-suite-criada.md) |
| 2026-05-12 16:00 | 06 | 01 | ⏳ | [gate-06-iter-01-inicial](2026-05-12_16h00_gate-06-iter-01-inicial.md) |
| 2026-05-12 16:45 | 06 | 02 | ⏳ | [gate-06-iter-02-pos-correcoes](2026-05-12_16h45_gate-06-iter-02-pos-correcoes.md) |

## Bloqueios ativos

- **2026-05-12 16:45** — Sem chave de API LLM, structurer rule-based parou em 37/54. Aguardando decisão do arquiteto.

## Decisões registradas

- **2026-05-12 14:30** — Stack: Python 3.11 + Pydantic v2 + PyMuPDF + pytest.
- **2026-05-12 15:40** — Suite de testes criada com 54 testes baseados no gabarito da Ascensão 2026.
```

---

## Regra de comportamento — leia 3 vezes

Toda vez que você completar uma etapa significativa (gate completo, iteração de conserto, ou bloqueio), você faz isto **nesta ordem exata**:

1. **PRIMEIRO** crie/atualize o arquivo `.md` em `reports/`. Sem exceção.
2. **DEPOIS** atualize `reports/INDEX.md`.
3. **POR ÚLTIMO** responda no chat do VS Code com apenas isto:

```
📄 Relatório salvo em: reports/2026-05-12_16h45_gate-06-iter-02-pos-correcoes.md

Resumo (3 linhas):
- 37/54 testes verdes (mesmo número da iteração anterior)
- 2 novos testes consertados, 2 novos quebrados (Saudação → Antífona)
- Bloqueio: structurer rule-based atingiu limite, preciso de orientação

Aguardando análise do arquiteto.
```

**Nada mais no chat.** Não cole o relatório completo lá. Não tente "ajudar" resumindo mais. Apenas o caminho do arquivo, o resumo de 3 linhas, e o pedido de orientação. Eu vou abrir o arquivo, copiar o conteúdo, e levar pro arquiteto.

---

## Quando criar relatório

Sempre que **qualquer** dessas coisas acontecer:

| Evento | Tipo de relatório |
|---|---|
| Gate começa | (não, espere o resultado) |
| Gate termina com pytest verde | `gate-NN-nome.md` |
| Gate termina com pytest parcial | `gate-NN-iter-MM-descricao.md` |
| Você fez uma iteração de conserto | `gate-NN-iter-MM-descricao.md` |
| Você travou e precisa orientação | `bloqueio-descricao.md` |
| O arquiteto pediu reanálise | `gate-NN-iter-MM-reanalise.md` |
| Mudou stack/arquitetura | `decisao-descricao.md` |

**Não crie** relatório para cada pequeno commit. Crie a cada **ponto de decisão** — momentos onde a próxima ação depende do arquiteto.

---

## Primeira ação concreta

Agora, antes de qualquer outra coisa:

1. Criar o diretório `reports/`.
2. Criar `reports/INDEX.md` com o cabeçalho inicial (sem entradas no histórico ainda — só estrutura).
3. Criar um primeiro relatório de status atual: `<timestamp>_estado-inicial.md` documentando onde o projeto está agora (37/54 verdes, etc.).
4. No chat, responder apenas com os 3 paths criados + 3 linhas de resumo.

Não tente consertar bugs, não rode pytest novamente, não toque em código de produção. Só estabeleça o sistema de relatórios e documente o estado atual.

---

## Confirmação

Sua próxima mensagem no chat deve ter, e apenas isto:

```
📄 Sistema de relatórios estabelecido:
- reports/INDEX.md
- reports/<timestamp>_estado-inicial.md

Estado atual documentado. Aguardando orientação do arquiteto sobre como
proceder com os 17 testes vermelhos (7 failed + 10 errors).
```

E me forneça, em mensagem separada se quiser, os caminhos absolutos dos arquivos criados, para eu poder abrir e copiar o conteúdo.
