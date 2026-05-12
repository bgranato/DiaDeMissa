# Prompt corretivo — App de Missa (DeepSeek / VS Code)

> Cole este documento inteiro como mensagem para o DeepSeek. Ele substitui qualquer instrução anterior sobre o mesmo projeto.

---

## 1. Diagnóstico do que está errado agora

A UI atual mostra artefatos que **não podem existir** em nenhuma tela do app:

| Artefato visível | Exemplo na tela | Origem |
|---|---|---|
| Barras `/` no meio dos versos | `"Aleluia! / O Jesus que subiu..."` | Separador de verso do folheto, não foi traduzido em quebra |
| Hifenização de quebra de linha | `"Ale-luia"`, `"vence-dor"` | Hifens de fim de linha do PDF não foram desfeitos |
| Palavras coladas | `"AleQue"`, `"CantodeEntrada"` | Espaços perdidos na extração do PDF |
| Créditos misturados na letra | `"...nós no céu. Entrada: José Alves; Ofertas: D.R.;..."` | Bloco de créditos da página de abertura colado no Canto |
| Postura como texto | `"Canto de Entrada (De pé)"` | `(De pé)` deveria ser metadado, não texto |
| Estrofes sem numeração | Quatro estrofes apresentadas como parágrafos soltos | Numeração `1.`, `2.`, `3.`, `4.` do folheto foi perdida ou jogada dentro do texto |
| Refrão indistinguível das estrofes | Cor amarela aplicada mas vaza pro meio dos créditos | Cosmética CSS sobre texto bruto contaminado |

**Você até agora aplicou CSS sobre texto bruto.** Isso é maquiagem. O problema acontece **antes da UI**, no parsing. Nenhum ajuste de fonte, cor, peso ou espaçamento vai resolver enquanto a string que chega no componente continuar contaminada.

A partir daqui, **nenhuma alteração visual** será aceita antes do pipeline de parsing estar implementado e validado por testes.

---

## 2. O princípio fundamental que você precisa internalizar

**Metadado disfarçado de texto.**

O folheto de missa é impresso em tinta monocromática. Tudo que é estrutura — postura, numeração de estrofe, falante de diálogo, número de versículo, referência bíblica, marcação de refrão — está representado como **texto inline** porque tinta não tem outra forma de mostrar.

No app, isso vira componente. A regra é:

```
Folheto: "1. Ó varões galileus..."
           ↓ parsing
JSON:    estrofes[0] = ["Ó varões galileus..."]   (sem "1." dentro)
           ↓ render
UI:      <Estrofe numero={1}> Ó varões galileus... </Estrofe>
```

O `"1."` **some como string** e **renasce como índice + elemento visual**. Não é "manter" nem "apagar" — é **transformar**.

Tudo no folheto que parece texto mas é estrutura precisa passar por essa tradução. A tabela completa:

| No folheto | Vira (JSON) | Renderiza (UI) |
|---|---|---|
| `"1. Canto de Entrada (De pé)"` | `titulo: "Canto de Entrada"`, `postura: "de_pe"`, `ordem: 1` | Título + chip "De pé" no topo |
| `"REFRÃO: O Senhor foi preparar..."` | `refrao: ["O Senhor foi preparar..."]` | Bloco destacado com label "REFRÃO" |
| `"1. Ó varões..."` (estrofe) | Item 0 do array `estrofes` | Card com badge numérico "1" |
| `"verso A / verso B"` | `["verso A", "verso B"]` | Duas linhas separadas, sem `/` |
| `"P. Em nome do Pai..."` | `turnos: [{falante: "P", texto: "..."}]` | Indentação + label "P" |
| `"(At 1,1-11)"` | `referencia: "At 1,1-11"` | Badge abaixo do título |
| `"¹⁷O Deus de nosso Senhor..."` | `versiculos: [{numero: 17, texto: "..."}]` | Número 17 em sobrescrito cinza |
| `"Ale-\nluia"` (quebra de linha) | `"Aleluia"` | `"Aleluia"` |

---

## 3. Regras de transformação — exemplos concretos

Para cada padrão abaixo, **input** é o que chega do extrator de PDF, **output** é o que deve estar no JSON.

### 3.1 Barras separadoras de verso

```
INPUT:  "Ó varões galileus, que estais no céu a olhar? Aleluia! / O Jesus que subiu ao céu deve, depois voltar! Aleluia!"

OUTPUT: [
  "Ó varões galileus, que estais no céu a olhar? Aleluia!",
  "O Jesus que subiu ao céu deve, depois voltar! Aleluia!"
]
```

Regra: split por ` / ` (com espaços), trim de cada item. Nunca deixe o `/` sobreviver no texto.

### 3.2 Numeração de estrofes

```
INPUT:  "1. Ó varões galileus, que estais no céu a olhar?"

OUTPUT: índice 0 do array, com texto "Ó varões galileus, que estais no céu a olhar?"
```

Regex de remoção: `^\d+\.\s*` no início do primeiro verso de cada estrofe. O número não pode aparecer dentro da string.

### 3.3 Postura entre parênteses

```
INPUT:  "Canto de Entrada (De pé)"
        "Primeira Leitura (At 1,1-11) (Sentados)"
        "Profissão de Fé (De pé)"

OUTPUT: titulo: "Canto de Entrada",   postura: "de_pe"
        titulo: "Primeira Leitura",   referencia: "At 1,1-11",   postura: "sentado"
        titulo: "Profissão de Fé",    postura: "de_pe"
```

Valores válidos de `postura`: `"de_pe"`, `"sentado"`, `"ajoelhado"`, ou `null`. Mapeamento:

- `(De pé)` → `"de_pe"`
- `(Sentados)`, `(Sentado)` → `"sentado"`
- `(Ajoelhados)`, `(Ajoelhado)` → `"ajoelhado"`

### 3.4 Hifenização de fim de linha

```
INPUT:  "Ale-\nluia"
        "vence-\ndor"
        "comuni-\ncação"

OUTPUT: "Aleluia"
        "vencedor"
        "comunicação"
```

Regex: `r"(\w+)-\s*\n\s*(\w+)"` → `r"\1\2"`. Aplicar **antes** de qualquer outra regex de junção de linhas.

### 3.5 Palavras coladas (espaços perdidos pelo extrator)

```
INPUT:  "CantodeEntrada"
        "AleQue"
        "JoséAlves"
        "Entrada:JoséAlves;Ofertas:D.R."

OUTPUT: "Canto de Entrada"
        "Aleluia! Que"   (reconstrução contextual)
        "José Alves"
        "Entrada: José Alves; Ofertas: D.R."
```

Solução estrutural (não regex reativa): trocar o método de extração. Use `page.get_text("dict")` do PyMuPDF e, ao concatenar spans contíguos, insira espaço quando:

- O gap horizontal entre dois spans for maior que `0.25 * fontsize` do span anterior, **ou**
- Detectar transição `minúscula→maiúscula` no meio de um span (caso de "AleQue").

### 3.6 Refrão vs estrofes vs créditos

Olhe esta sequência exata do PDF (Ascensão do Senhor, 17/05/2026):

```
[Bloco de abertura — está na primeira página, ANTES de "Ritos Iniciais"]
Entrada: José Alves; Ofertas: D.R.; Comunhão: Pe. José Weber; Final: Antífona Mariana / Liturgia das Horas.

[Bloco "Ritos Iniciais"]
1. Canto de Entrada (De pé)
REFRÃO: O Senhor foi preparar / um lugar para nós no céu.
1. Ó varões galileus, que estais no céu a olhar? Aleluia! / O Jesus que subiu ao céu deve, depois voltar! Aleluia!
2. Entre cantos e hinos triunfais se eleva o Senhor! Aleluia! / Cante a terra e o mar também: Cristo é vencedor! Aleluia!
3. Glorioso, à direita do Pai, sentou-se Jesus! Aleluia! / Que nos foi preparar no céu, reino de eterna luz! Aleluia!
4. Ó Jesus, nosso Rei e Senhor, que subis para o céu! Aleluia! / Não deixeis os cristãos a sós: dai-nos o dom de Deus! Aleluia!
```

Três regiões **estruturalmente diferentes**:

1. **Créditos da missa** (autoria dos cantos): pertencem ao objeto `Missa`, não a nenhum canto específico. Vivem em `missa.creditos_cantos`.
2. **Refrão**: termina em `"nós no céu."`. Vai em `canto.refrao`.
3. **Estrofes numeradas 1–4**: cada uma com dois versos separados por `/`. Vão em `canto.estrofes`.

O parser **nunca** pode juntar essas três regiões. O REFRÃO termina quando bate uma linha começando com `^\d+\.` (início de estrofe). Os créditos terminam quando bate `Ritos Iniciais`.

### 3.7 Diálogos P./T./L.

```
INPUT:  P. Em nome do Pai e do Filho e do Espírito Santo.
        T. Amém.
        P. A graça e a paz daquele que é...
        T. Bendito seja Deus...

OUTPUT: {
  "tipo": "dialogo",
  "titulo": "Saudação",
  "turnos": [
    {"falante": "P", "texto": "Em nome do Pai e do Filho e do Espírito Santo."},
    {"falante": "T", "texto": "Amém."},
    {"falante": "P", "texto": "A graça e a paz daquele que é..."},
    {"falante": "T", "texto": "Bendito seja Deus..."}
  ]
}
```

A sigla nunca fica na string. `P.` no início vira `falante: "P"`. Falantes válidos: `P` (Presidente/sacerdote), `T` (Todos), `L` (Leitor), `V` (Versículo), `R` (Resposta).

### 3.8 Versículos bíblicos numerados

```
INPUT:  "¹No meu primeiro livro, ó Teófilo, já tratei de tudo... ²até ao dia em que foi levado..."

OUTPUT: versiculos: [
  {"numero": 1, "texto": "No meu primeiro livro, ó Teófilo, já tratei de tudo..."},
  {"numero": 2, "texto": "até ao dia em que foi levado..."}
]
```

Regex: capturar grupos `(\d+)([^\d]+)` após o início da leitura. Renderize o número em sobrescrito menor e cinza, como nas Bíblias impressas.

---

## 4. JSON-alvo verificado — Ascensão do Senhor, 17/05/2026

Este é o gabarito. O resultado do seu pipeline executado sobre `https://www.arqrio.com.br/app/painel/amissa/amissa.pdf` **deve** produzir este JSON (campos parciais mostrados, foco no Canto de Entrada e estrutura geral):

```json
{
  "data": "2026-05-17",
  "ano_liturgico": "A",
  "titulo_celebracao": "Ascensão do Senhor",
  "categoria": "Solenidade",
  "observacoes": "60º Dia Mundial das Comunicações Sociais. Ano Jubilar Arquidiocesano.",
  "creditos_cantos": {
    "entrada": "José Alves",
    "ofertas": "D.R.",
    "comunhao": "Pe. José Weber",
    "final": "Antífona Mariana / Liturgia das Horas"
  },
  "palavra_do_dia": {
    "texto": "Eis que estou convosco todos os dias, até o fim do mundo.",
    "referencia": "Mt 28,20"
  },
  "blocos": [
    {
      "tipo": "canto",
      "ordem": 1,
      "titulo": "Canto de Entrada",
      "postura": "de_pe",
      "refrao": [
        "O Senhor foi preparar um lugar para nós no céu."
      ],
      "estrofes": [
        [
          "Ó varões galileus, que estais no céu a olhar? Aleluia!",
          "O Jesus que subiu ao céu deve, depois voltar! Aleluia!"
        ],
        [
          "Entre cantos e hinos triunfais se eleva o Senhor! Aleluia!",
          "Cante a terra e o mar também: Cristo é vencedor! Aleluia!"
        ],
        [
          "Glorioso, à direita do Pai, sentou-se Jesus! Aleluia!",
          "Que nos foi preparar no céu, reino de eterna luz! Aleluia!"
        ],
        [
          "Ó Jesus, nosso Rei e Senhor, que subis para o céu! Aleluia!",
          "Não deixeis os cristãos a sós: dai-nos o dom de Deus! Aleluia!"
        ]
      ]
    },
    {
      "tipo": "dialogo",
      "ordem": 2,
      "titulo": "Saudação",
      "turnos": [
        {"falante": "P", "texto": "Em nome do Pai e do Filho e do Espírito Santo."},
        {"falante": "T", "texto": "Amém."},
        {"falante": "P", "texto": "A graça e a paz daquele que é, que era e que vem, estejam convosco."},
        {"falante": "T", "texto": "Bendito seja Deus, que nos reuniu no amor de Cristo."}
      ]
    },
    {
      "tipo": "leitura",
      "ordem": 6,
      "categoria": "primeira_leitura",
      "titulo": "Primeira Leitura",
      "referencia": "At 1,1-11",
      "postura": "sentado",
      "introducao": "Leitura dos Atos dos Apóstolos.",
      "versiculos": [
        {"numero": 1, "texto": "No meu primeiro livro, ó Teófilo, já tratei de tudo o que Jesus fez e ensinou, desde o começo,"},
        {"numero": 2, "texto": "até ao dia em que foi levado para o céu, depois de ter dado instruções pelo Espírito Santo, aos apóstolos que tinha escolhido."}
      ],
      "conclusao": "Palavra do Senhor.",
      "resposta": "Graças a Deus."
    }
  ]
}
```

A escolha de `palavra_do_dia` segue a regra: pegar três candidatos do JSON (fim do Evangelho, refrão do Salmo, versículo da Aclamação) e a LLM escolhe o mais sintetizante. Para esta missa, é o final do Evangelho de Mateus 28,20.

---

## 5. Suite de testes — pytest

Crie o arquivo `tests/test_ascensao_2026.py` exatamente assim. Estes testes **devem passar** antes de qualquer ajuste de UI.

```python
import re
import pytest
from pathlib import Path
from src.pipeline import processar_pdf

PDF_URL = "https://www.arqrio.com.br/app/painel/amissa/amissa.pdf"
PDF_FIXTURE = Path("tests/fixtures/amissa_ascensao_2026.pdf")

@pytest.fixture(scope="module")
def missa():
    return processar_pdf(PDF_FIXTURE)


def test_metadados_da_celebracao(missa):
    assert missa.data == "2026-05-17"
    assert missa.titulo_celebracao == "Ascensão do Senhor"
    assert missa.categoria == "Solenidade"
    assert missa.ano_liturgico == "A"


def test_creditos_vivem_fora_dos_cantos(missa):
    assert missa.creditos_cantos.entrada == "José Alves"
    assert missa.creditos_cantos.ofertas == "D.R."
    assert missa.creditos_cantos.comunhao == "Pe. José Weber"
    assert missa.creditos_cantos.final == "Antífona Mariana / Liturgia das Horas"


def test_canto_de_entrada_estrutura_exata(missa):
    canto = missa.blocos[0]
    assert canto.tipo == "canto"
    assert canto.titulo == "Canto de Entrada"
    assert canto.postura == "de_pe"
    assert canto.refrao == ["O Senhor foi preparar um lugar para nós no céu."]
    assert len(canto.estrofes) == 4
    assert canto.estrofes[0] == [
        "Ó varões galileus, que estais no céu a olhar? Aleluia!",
        "O Jesus que subiu ao céu deve, depois voltar! Aleluia!",
    ]
    assert canto.estrofes[3] == [
        "Ó Jesus, nosso Rei e Senhor, que subis para o céu! Aleluia!",
        "Não deixeis os cristãos a sós: dai-nos o dom de Deus! Aleluia!",
    ]


def test_zero_artefatos_em_qualquer_texto(missa):
    """Percorre TODOS os campos de texto da missa e garante zero contaminação."""
    PROIBIDOS = [
        (r"\s/\s",        "barra separadora de verso"),
        (r"^/|/$",        "barra no início ou fim"),
        (r"##|\*\*",      "markdown vazado"),
        (r"\w+-\s*\n",    "hifenização de quebra de linha"),
        (r"[a-záéíóú][A-ZÁÉÍÓÚ][a-záéíóú]", "palavra colada (camelCase)"),
        (r"^\d+\.\s",     "numeração de estrofe dentro do texto"),
        (r"\(De pé\)|\(Sentados?\)|\(Ajoelhados?\)", "postura como texto"),
        (r"Entrada:\s*\w+;\s*Ofertas:", "créditos vazando para letra"),
    ]
    for caminho, texto in _todos_os_textos(missa):
        for padrao, descricao in PROIBIDOS:
            assert not re.search(padrao, texto), (
                f"Artefato '{descricao}' encontrado em {caminho}:\n  {texto!r}"
            )


def test_postura_e_enum(missa):
    VALIDAS = {"de_pe", "sentado", "ajoelhado", None}
    for bloco in missa.blocos:
        if hasattr(bloco, "postura"):
            assert bloco.postura in VALIDAS, (
                f"Postura inválida em {bloco.titulo}: {bloco.postura!r}"
            )


def test_palavra_do_dia_sintetiza_celebracao(missa):
    """A frase de destaque deve vir do Evangelho do dia, não de outra liturgia."""
    pd = missa.palavra_do_dia
    assert pd.referencia.startswith("Mt 28"), (
        f"Palavra do dia da Ascensão deve vir de Mt 28, veio de: {pd.referencia}"
    )
    assert "todos os dias" in pd.texto.lower()


def _todos_os_textos(obj, caminho="missa"):
    """Walker recursivo que yielda (caminho, string) para todo campo de texto."""
    if isinstance(obj, str):
        yield caminho, obj
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            yield from _todos_os_textos(item, f"{caminho}[{i}]")
    elif hasattr(obj, "__dict__"):
        for k, v in obj.__dict__.items():
            yield from _todos_os_textos(v, f"{caminho}.{k}")
    elif hasattr(obj, "model_dump"):
        for k, v in obj.model_dump().items():
            yield from _todos_os_textos(v, f"{caminho}.{k}")
```

---

## 6. Ordem de execução — hard gates

Você vai executar nesta ordem. **Não pule etapas. Não avance sem o teste da etapa anterior passar verde.**

### Gate 1 — Schema e validators
- [ ] Criar `src/schema/missa.py` com todos os modelos Pydantic (Canto, Leitura, Salmo, Aclamacao, Oracao, Dialogo, Missa).
- [ ] Criar `src/schema/validators.py` com `ARTEFATOS_PROIBIDOS` rejeitando os 8 padrões da lista de testes.
- [ ] Criar `tests/test_validators.py` que tenta criar um Canto com `"/"` no texto e verifica que `ValidationError` é levantado.
- [ ] Rodar `pytest tests/test_validators.py -v` e me mostrar o output.

### Gate 2 — Limpeza determinística
- [ ] Criar `src/pipeline/clean.py` com as funções `desfazer_hifenizacao`, `juntar_linhas_quebradas`, `normalizar_espacos`.
- [ ] Criar `tests/test_clean.py` com casos: `"Ale-\nluia"` → `"Aleluia"`, etc.
- [ ] Rodar `pytest tests/test_clean.py -v` e me mostrar o output.

### Gate 3 — Extração com metadados
- [ ] Criar `src/pipeline/extract.py` usando PyMuPDF com reconstrução de espaços por gap horizontal.
- [ ] Criar `tests/test_extract.py` que processa o PDF de fixture e verifica: `"CantodeEntrada"` **não** aparece, `"AleQue"` **não** aparece.
- [ ] Rodar `pytest tests/test_extract.py -v` e me mostrar o output.

### Gate 4 — Estruturação por LLM
- [ ] Criar `src/llm/prompts.py` com `SYSTEM_PROMPT` (use a versão da spec original).
- [ ] Criar `src/pipeline/structure.py` com retry até 3 tentativas, alimentando o erro de validação de volta para a LLM.
- [ ] Garantir que o resultado é validado por Pydantic antes de ser retornado.

### Gate 5 — Teste end-to-end
- [ ] Baixar o PDF para `tests/fixtures/amissa_ascensao_2026.pdf`.
- [ ] Rodar `pytest tests/test_ascensao_2026.py -v`.
- [ ] **Todos os 6 testes devem passar.** Me mostre o output.

### Gate 6 — Só agora, ajustes de UI
- [ ] Atualizar o componente `<Canto>` para renderizar `refrao` e `estrofes` separadamente, com numeração 1–4 vindo do índice do array.
- [ ] Atualizar `<Leitura>` para renderizar `versiculos[].numero` em sobrescrito.
- [ ] Atualizar `<Dialogo>` para renderizar `turnos` com indentação e label do falante.
- [ ] Postura sempre como chip visual no topo, nunca dentro do título.

---

## 7. Regras inegociáveis

1. **Antes de tocar em qualquer arquivo de UI, rode `pytest` e me mostre a saída completa.** Se um teste falhar, conserte o pipeline; **não** conserte na UI.

2. **Nunca** adicione lógica de limpeza de string dentro do componente de UI. Se você se pegar escrevendo `text.replace("/", "")` num arquivo `.jsx`/`.tsx`/`.dart`/`.swift`, pare imediatamente — o problema é no pipeline anterior.

3. **Nunca** invente campos do schema. Se um folheto tem algo que não cabe no schema, me pergunte antes de adicionar.

4. **Falha é preferível a saída contaminada.** Se a LLM não conseguir estruturar o folheto após 3 retries, lance exceção e mostre "Erro ao carregar folheto" ao usuário. É infinitamente melhor que mostrar `"## REFRÃO / nósnocéu / AleQue"` durante a missa.

5. **Idempotência.** Processar o mesmo PDF duas vezes deve produzir o mesmo JSON byte-a-byte (modulo timestamps).

---

## 8. Por onde você começa

Sua próxima resposta deve ser **apenas o Gate 1**: criar `src/schema/missa.py`, `src/schema/validators.py` e `tests/test_validators.py`, rodar `pytest tests/test_validators.py -v` e me mostrar o resultado.

Não crie nada além disso. Não toque em UI. Não toque em extração. Não toque em pipeline. Só schema + validators + teste do schema.

Quando eu vir `pytest` verde no Gate 1, eu autorizo o Gate 2.
