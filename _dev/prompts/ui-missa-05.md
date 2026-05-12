# Plano de Correção — 17 testes vermelhos → verde

> Cole este documento como mensagem para o DeepSeek. Ele dá continuidade ao trabalho atual (não é reset).

---

## Contexto

Estado atual segundo relatório `ui-missa-03.md`:
- ✅ 37/54 testes verdes
- ❌ 7 FAILED (bugs de detalhe)
- 💥 10 ERROR (parsers faltantes: Ato Penitencial, Leituras)

Estratégia confirmada: **continuar rule-based**. LLM não vai entrar agora. Todos os 17 vermelhos são padrões fixos que regex resolve, e LLM teria custo permanente e não-determinismo indesejado para conteúdo litúrgico.

Você vai trabalhar em **duas fases**, cada uma com seu próprio relatório:

- **Fase A:** consertar os 7 FAILED (mudanças pequenas em arquivos existentes)
- **Fase B:** implementar os parsers faltantes (Ato Penitencial e Leituras)

Não execute as duas fases de uma vez. Faça Fase A, salve relatório, espere autorização. Só então Fase B.

---

## Ajuste de schema/gabarito ANTES de tudo

Há uma correção no gabarito que precisa entrar primeiro: o refrão era para ser **lista de versos** (igual estrofes), não string única. Isto resolve naturalmente o "REFRÃO: O Senhor foi preparar" + "/" issue.

**Modificar `tests/fixtures/amissa_ascensao_2026.expected.json`:**

Trocar:
```json
"refrao": ["O Senhor foi preparar um lugar para nós no céu."]
```

Por:
```json
"refrao": [
  "O Senhor foi preparar",
  "um lugar para nós no céu."
]
```

**Modificar o teste `TestCantoEntrada::test_refrao_exato` em `tests/test_ascensao_2026.py`:**

Trocar:
```python
def test_refrao_exato(self, canto):
    assert canto.refrao == ["O Senhor foi preparar um lugar para nós no céu."]
```

Por:
```python
def test_refrao_exato(self, canto):
    assert canto.refrao == [
        "O Senhor foi preparar",
        "um lugar para nós no céu.",
    ]
```

Faça essas duas mudanças **agora**, antes de começar a Fase A.

---

# FASE A — Consertar os 7 FAILED

## Bug A1 — Crédito "Final" perdendo "Horas"

**Sintoma:**
```
Esperado: "Antífona Mariana / Liturgia das Horas"
Recebido: "Antífona Mariana / Liturgia das"
```

**Causa:** A regex que extrai créditos está cortando em `;` ou `\n`, mas o campo `Final:` é o último da lista e o valor cruza quebra de linha (`"Antífona Mariana / Liturgia das\nHoras."`).

**Solução em `src/pipeline/structure.py`** (procure a função que extrai créditos):

```python
def extrair_creditos(texto: str) -> dict:
    """
    Extrai bloco de créditos. No PDF aparece como:
    "Entrada: José Alves; Ofertas: D.R.; Comunhão: Pe. José Weber; 
     Final: Antífona Mariana / Liturgia das Horas."
    
    O bloco pode cruzar múltiplas linhas. Termina em "." seguido de \n\n
    ou no início da próxima seção ("Ritos Iniciais").
    """
    # Captura tudo desde "Entrada:" até "."+ fim de parágrafo ou próxima seção
    match = re.search(
        r"Entrada:\s*(.+?)(?=\n\n|Ritos Iniciais|\Z)",
        texto,
        re.DOTALL,
    )
    if not match:
        return {}
    
    bloco = match.group(0).replace("\n", " ")
    bloco = re.sub(r"\s+", " ", bloco).strip().rstrip(".")
    
    # Agora parse por ";" — cada parte é "Campo: valor"
    creditos = {}
    for parte in bloco.split(";"):
        if ":" not in parte:
            continue
        chave, valor = parte.split(":", 1)
        chave = chave.strip().lower()
        valor = valor.strip()
        # Mapeia variações do português
        mapa = {
            "entrada": "entrada",
            "ofertas": "ofertas",
            "comunhão": "comunhao",
            "final": "final",
        }
        if chave in mapa:
            creditos[mapa[chave]] = valor
    
    return creditos
```

**Teste para guardar a correção:**

```python
# tests/test_clean.py — adicionar
def test_creditos_capturam_final_completo():
    from src.pipeline.structure import extrair_creditos
    texto = """Entrada: José Alves; Ofertas: D.R.; Comunhão: Pe. José Weber; 
Final: Antífona Mariana / Liturgia das Horas.

Ritos Iniciais
"""
    creditos = extrair_creditos(texto)
    assert creditos["final"] == "Antífona Mariana / Liturgia das Horas"
```

---

## Bug A2 — Postura do Canto de Entrada é None

**Sintoma:**
```
Esperado: postura == "de_pe"
Recebido: postura == None
```

**Causa:** O `(De pé)` está no título do bloco no PDF (`"1. Canto de Entrada (De pé)"`), mas após extração e limpeza, ele pode ter ficado em linha separada ou junto com o REFRÃO. O parser está olhando só a primeira linha do bloco e perdendo o marcador.

**Solução:** Buscar postura em uma **janela** de 1-3 linhas após o título, não só na linha do título.

```python
POSTURAS = {
    "de pé": "de_pe",
    "sentado": "sentado",
    "sentados": "sentado",
    "ajoelhado": "ajoelhado",
    "ajoelhados": "ajoelhado",
}

def extrair_postura(linhas_bloco: list[str], janela: int = 3) -> str | None:
    """
    Procura "(De pé)", "(Sentados)", etc. nas primeiras N linhas do bloco.
    Retorna o valor normalizado para o enum Postura.
    """
    contexto = " ".join(linhas_bloco[:janela])
    match = re.search(r"\(([^)]+)\)", contexto)
    if not match:
        return None
    candidato = match.group(1).strip().lower()
    return POSTURAS.get(candidato)
```

**Importante:** Depois de extrair a postura, **remova** a marcação `(De pé)` do texto do título e das linhas de conteúdo. Senão o invariante `test_zero_postura_como_texto` quebra.

```python
def remover_marcacao_postura(texto: str) -> str:
    return re.sub(r"\s*\((De pé|Sentados?|Ajoelhados?)\)\s*", " ", texto).strip()
```

---

## Bug A3 — Refrão tem prefixo "REFRÃO:" e versos errados

**Sintoma:**
```
Recebido: ["REFRÃO: O Senhor foi preparar", "um lugar para nós no céu."]
Esperado: ["O Senhor foi preparar", "um lugar para nós no céu."]
```

**Causa:** O prefixo `REFRÃO:` não foi removido do primeiro verso.

**Solução** no parser de Canto:

```python
def extrair_refrao(linhas: list[str]) -> list[str]:
    """
    Encontra a linha com 'REFRÃO:' e retorna os versos do refrão como lista.
    Versos são separados por " / " (com espaços).
    """
    refrao_linha = None
    for i, linha in enumerate(linhas):
        if re.match(r"^\s*REFRÃO:", linha, re.IGNORECASE):
            # Junta com próxima linha se o refrão quebra de linha (sem ser numeração de estrofe)
            blob = linha
            j = i + 1
            while j < len(linhas) and not re.match(r"^\s*\d+\.\s", linhas[j]):
                blob += " " + linhas[j]
                j += 1
                if j >= i + 3:  # limite de segurança
                    break
            refrao_linha = blob
            break
    
    if not refrao_linha:
        return []
    
    # Remove prefixo "REFRÃO:"
    texto = re.sub(r"^\s*REFRÃO:\s*", "", refrao_linha, flags=re.IGNORECASE)
    
    # Normaliza espaços (sem "/" ainda)
    texto = re.sub(r"\s+", " ", texto).strip()
    
    # Split por " / " (com espaços) — separador de verso
    versos = [v.strip() for v in re.split(r"\s*/\s*", texto) if v.strip()]
    return versos
```

---

## Bug A4 — Quarta estrofe quebrada em 3 itens

**Sintoma:**
```
Esperado: 2 versos
Recebido: 3 itens — "Aleluia!" sozinho como item separado
```

**Causa:** Splitter está quebrando por `\n` ou por `!`, não apenas por ` / `.

**No PDF original:**
```
4. Ó Jesus, nosso Rei e Senhor, que subis para o céu! 
Aleluia! / Não deixeis os cristãos a sós: dai-nos o dom 
de Deus! Aleluia!
```

O `Aleluia!` da segunda linha **pertence ao primeiro verso**, mas o splitter o tratou como item independente.

**Solução:** primeiro normalize o bloco inteiro juntando linhas quebradas, **depois** divida por ` / `:

```python
def parse_estrofe(bloco: str) -> list[str]:
    """
    Recebe o texto bruto de uma estrofe (já sem o "N." inicial) e retorna 
    lista de versos separados por " / ".
    """
    # 1. Junta linhas quebradas em parágrafo único
    blob = re.sub(r"\s*\n\s*", " ", bloco)
    blob = re.sub(r"\s+", " ", blob).strip()
    
    # 2. Divide APENAS por " / " (com espaços obrigatórios em volta)
    versos = [v.strip() for v in re.split(r"\s+/\s+", blob) if v.strip()]
    
    return versos
```

**Verifique:** o splitter nunca deve dividir por `!`, `?`, `.`, `\n` ou `/` sem espaços. Só por ` / ` exato.

---

## Bug A5 + A6 — Antífona da Entrada: referência não extraída e dentro do texto

**Sintoma:**
```
referencia: None
texto: "(At 1,11) Homens da Galileia..."
```

**Causa:** O parser de Antífona não extrai `(Referência)` para campo separado.

**Solução:** ao detectar um bloco do tipo Antífona, separar referência do texto:

```python
def parse_antifona(linhas: list[str]) -> dict:
    """
    Antífona da Entrada (At 1,11)
    Homens da Galileia, por que ficais aqui, parados, olhando para o céu? 
    Esse Jesus virá do mesmo modo como o vistes partir para o céu, aleluia.
    """
    # Primeira linha tem o título e possivelmente a referência
    titulo_linha = linhas[0]
    
    # Extrai referência entre parênteses
    ref_match = re.search(r"\(([^)]+)\)", titulo_linha)
    referencia = ref_match.group(1).strip() if ref_match else None
    
    # Título limpo (sem referência)
    titulo = re.sub(r"\s*\([^)]+\)\s*", " ", titulo_linha).strip()
    
    # Texto: junta linhas seguintes em parágrafo
    texto = " ".join(linhas[1:])
    texto = re.sub(r"\s+", " ", texto).strip()
    
    # Se a referência ficou dentro do texto, remove
    texto = re.sub(r"^\s*\([^)]+\)\s*", "", texto)
    
    return {
        "tipo": "antifona",
        "titulo": titulo,
        "referencia": referencia,
        "texto": texto,
    }
```

---

## Bug A7 — Invariante global rejeita "/" legítimo nos créditos

**Sintoma:**
```
'Antífona Mariana / Liturgia das' contém /
```

**Causa:** O nome do hino "Antífona Mariana / Liturgia das Horas" tem `/` legítimo (indica alternativa litúrgica entre dois cantos). Mas o teste `test_zero_barras_separadoras` é global e rejeita qualquer `/`.

**Solução:** o teste precisa ignorar o campo `creditos_cantos`, onde `/` é semanticamente diferente.

**Modificar `tests/test_ascensao_2026.py`, classe `TestInvariantesGlobais`:**

```python
def test_zero_barras_separadoras(self, missa):
    """
    Nenhum texto pode conter ' / ' como separador de verso.
    Exceção: creditos_cantos, onde '/' indica alternativa litúrgica
    (ex.: 'Antífona Mariana / Liturgia das Horas').
    """
    for caminho, texto in self._walk_strings(missa):
        if "creditos_cantos" in caminho:
            continue  # créditos podem ter "/" legítimo
        assert " / " not in texto, f"{caminho}: {texto!r}"
```

Aplique o mesmo padrão (skip de `creditos_cantos`) em qualquer outro invariante que envolva `/`.

---

## Critério de conclusão da Fase A

Após implementar os 7 consertos acima, rodar `pytest tests/test_ascensao_2026.py -v` e:

- ✅ Os 7 FAILED devem ficar verdes
- ✅ Nenhum dos 37 testes que já passavam pode regredir
- 💥 Os 10 ERRORS de Ato Penitencial e Leitura **continuam** vermelhos — não tente consertá-los aqui

**Esperado ao final da Fase A:** 44/54 verdes, 0 failed, 10 errors.

Quando atingir isso, **PARE**. Crie o relatório e aguarde autorização para Fase B.

---

# FASE B — Implementar parsers faltantes

**NÃO INICIE A FASE B ANTES DA AUTORIZAÇÃO.**

(Detalhes da Fase B serão enviados após a Fase A estar verde. O escopo será: parser genérico de diálogos para Ato Penitencial e parser de Leituras com versículos numerados.)

---

# PROTOCOLO DE RELATÓRIO — Fase A

Quando completar a Fase A (ou ficar bloqueado), crie:

`reports/<timestamp>_gate-06-iter-fase-a.md`

Conteúdo conforme template estabelecido. Atualize também `reports/INDEX.md`.

Resposta no chat: apenas caminho do arquivo + 3 linhas de resumo. Não cole conteúdo no chat.

---

# CHECKLIST DE EXECUÇÃO

Marque conforme avança (mentalmente, não precisa responder até o final):

- [ ] 0. Ajuste de schema/gabarito (refrão como lista de 2 versos)
- [ ] A1. Crédito Final completo
- [ ] A2. Postura do Canto detectada
- [ ] A3. Refrão sem prefixo "REFRÃO:"
- [ ] A4. Estrofe 4 com 2 versos, não 3
- [ ] A5+A6. Antífona com referência separada
- [ ] A7. Invariante global pula creditos_cantos
- [ ] Rodar pytest
- [ ] 44/54 verdes confirmado, 0 failed, 10 errors
- [ ] Criar relatório
- [ ] Atualizar INDEX.md
- [ ] Responder no chat com path + 3 linhas

**Não execute Fase B. Aguarde autorização.**

---

# REGRAS QUE NÃO MUDAM

1. Pytest verde é o único critério de progresso.
2. Nada de `.replace()` na UI. Conserto vai sempre no pipeline.
3. Se um conserto da Fase A quebrar algo que já passava, **reverta e me reporte** — não continue empilhando bugs.
4. Não tente "otimizar" outras coisas no caminho. Só os 7 itens listados.
5. Falha é melhor que saída contaminada.

Boa Fase A.
