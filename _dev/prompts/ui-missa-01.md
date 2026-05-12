# Spec técnica — Pipeline de extração e UI para app de acompanhamento de missa

## Contexto do projeto

Estou desenvolvendo um aplicativo que substitui o folheto de papel da missa por uma interface digital. O app baixa o PDF semanal do folheto (exemplo: `https://www.arqrio.com.br/app/painel/amissa/amissa.pdf`), extrai o conteúdo e o apresenta em telas sequenciais ("Canto de Entrada", "Primeira Leitura", "Salmo", etc.) que o fiel acompanha durante a celebração.

A pipeline atual quebra de várias formas que aparecem na UI final. Esta spec descreve o pipeline correto e os critérios de aceitação. Implemente exatamente como descrito; **não invente etapas adicionais** sem confirmar comigo.

## Problemas atuais que precisam ser eliminados

Na UI hoje aparecem todos estes artefatos, que **nunca** podem chegar à camada de apresentação:

1. Marcadores de markdown vazando como texto: `##`, `**`, `*`
2. Barras `/` separando versos (artefato do PDF que indica quebra de verso no folheto)
3. Hifenização de fim de linha não desfeita: `"Ale-luia"`, `"vence-dor"`
4. Palavras coladas no meio de outras: `"AleQue"` (resultado de `"Aleluia!"` + `"Que"` sem espaço)
5. Espaços perdidos entre palavras: `"CantodeEntrada"`, `"nósnocéu"`, `"JoséAlves"`
6. Créditos de autoria (`"Entrada: José Alves; Ofertas: D.R.;..."`) misturados dentro da letra do canto
7. Rubricas de postura (`"(De pé)"`, `"(Sentados)"`) renderizadas como texto corrido em vez de indicador visual
8. Refrão sem destaque visual, indistinguível das estrofes
9. Cada estrofe em um único parágrafo gigante, sem versos quebrados corretamente

## Arquitetura — visão geral

O pipeline tem **cinco etapas** estritamente sequenciais. Cada etapa tem entrada e saída bem definidas. A camada de UI só recebe JSON validado, **nunca** texto bruto.

```
[1] Download do PDF
      ↓
[2] Extração com metadados (PyMuPDF)
      ↓
[3] Limpeza determinística (regex)
      ↓
[4] Estruturação por LLM com schema rígido
      ↓
[5] Validação (Pydantic/Zod) — rejeita e re-processa se falhar
      ↓
[6] Renderização por componentes especializados
```

A regra inviolável: **se um campo de texto na saída final contém `/`, `##`, `**`, hífen órfão ou palavras coladas, a pipeline falhou e deve ser re-processada, não exibida.**

## Stack

- **Linguagem do backend de processamento**: Python 3.11+
- **Extração de PDF**: PyMuPDF (`pymupdf`) — preserva metadados de fonte, tamanho, flags de negrito/itálico, coordenadas
- **LLM de estruturação**: configurável (OpenAI / Anthropic / DeepSeek) via interface única
- **Validação**: Pydantic v2
- **UI**: (mantenha o framework que já está em uso — React/Flutter/SwiftUI; esta spec descreve o contrato JSON e os componentes lógicos)

## Etapa 1 — Download

Trivial. Baixar o PDF da URL configurada para um cache local, identificado por hash do conteúdo. Não re-processar se já existe em cache válido (TTL configurável, padrão 24h). Implementar com `requests` ou `httpx`.

## Etapa 2 — Extração com metadados

**Não use** `extract_text()` puro. Use `page.get_text("dict")` do PyMuPDF para obter, para cada span de texto:

- `text`: o conteúdo
- `font`: nome da fonte
- `size`: tamanho em pontos
- `flags`: bitfield (bit 4 = negrito, bit 1 = itálico) — usar a função utilitária abaixo
- `bbox`: coordenadas `(x0, y0, x1, y1)`
- `color`: cor RGB

Estruture cada span como:

```python
@dataclass
class Span:
    text: str
    font: str
    size: float
    is_bold: bool
    is_italic: bool
    bbox: tuple[float, float, float, float]
    page: int
    color: int

def parse_flags(flags: int) -> tuple[bool, bool]:
    """Retorna (is_bold, is_italic) a partir do bitfield de flags do PyMuPDF."""
    is_italic = bool(flags & 2)
    is_bold = bool(flags & 16)
    return is_bold, is_italic
```

**Reconstrução de espaços perdidos**: PyMuPDF às vezes entrega spans contíguos sem o espaço entre eles. Ao concatenar spans de uma mesma linha, insira espaço entre dois spans se:

- O gap horizontal `(span_b.bbox[0] - span_a.bbox[2])` for maior que `0.25 * span_a.size`, **ou**
- `span_a.text` não termina em espaço e `span_b.text` não começa em espaço, **e** o caractere final de A e o inicial de B são alfabéticos

Esta heurística resolve o `"CantodeEntrada"`.

## Etapa 3 — Limpeza determinística

Antes de chamar a LLM, aplique estas regexes em ordem, ao texto reconstruído da etapa anterior:

```python
import re
import unicodedata

def limpar_texto(texto: str) -> str:
    # 1. Normaliza unicode (NFC) para evitar acentos decompostos
    texto = unicodedata.normalize("NFC", texto)

    # 2. Desfaz hifenização de quebra de linha: "Ale-\nluia" -> "Aleluia"
    texto = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", texto)

    # 3. Junta linhas que foram quebradas apenas por largura de coluna
    #    (linha terminando em letra minúscula ou vírgula + próxima começa em minúscula)
    texto = re.sub(
        r"([a-záéíóúâêôãõçà,;:])\s*\n\s*([a-záéíóúâêôãõçà])",
        r"\1 \2",
        texto,
    )

    # 4. Normaliza múltiplos espaços e tabs
    texto = re.sub(r"[ \t]+", " ", texto)

    # 5. Normaliza múltiplas quebras de linha (no máximo 2 = parágrafo)
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    # 6. Remove espaços no início/fim de cada linha
    texto = "\n".join(linha.strip() for linha in texto.split("\n"))

    return texto.strip()
```

**Importante**: a regra 3 é conservadora de propósito. Não junte se a linha anterior termina em `.`, `!`, `?` ou letra maiúscula — provavelmente é fim de frase legítimo.

## Etapa 4 — Estruturação por LLM com schema rígido

Esta é a etapa crítica. A LLM **não decide a estrutura** — ela preenche slots num schema fixo que reflete o Ordo Missae.

### Schema canônico (Pydantic)

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal

Postura = Literal["de_pe", "sentado", "ajoelhado", None]

class Creditos(BaseModel):
    """Créditos de autoria dos cantos. Sempre fora das letras."""
    entrada: str | None = None
    ofertas: str | None = None
    comunhao: str | None = None
    final: str | None = None
    observacoes: str | None = None

class Canto(BaseModel):
    tipo: Literal["canto"] = "canto"
    titulo: str                          # ex: "Canto de Entrada"
    postura: Postura = None
    refrao: list[str] = Field(default_factory=list)    # cada verso = 1 item
    estrofes: list[list[str]] = Field(default_factory=list)  # lista de estrofes, cada uma com versos
    creditos: Creditos | None = None

class Leitura(BaseModel):
    tipo: Literal["primeira_leitura", "segunda_leitura", "evangelho"]
    titulo: str                          # ex: "Primeira Leitura"
    referencia: str                      # ex: "At 1,1-11"
    introducao: str                      # ex: "Leitura dos Atos dos Apóstolos."
    texto: str                           # corpo da leitura, parágrafos separados por \n\n
    conclusao: str | None = None         # ex: "Palavra do Senhor."
    postura: Postura = None

class Salmo(BaseModel):
    tipo: Literal["salmo"] = "salmo"
    titulo: str = "Salmo Responsorial"
    referencia: str                      # ex: "Sl 46"
    refrao: list[str]                    # versos do refrão
    estrofes: list[list[str]]            # estrofes do salmo
    postura: Postura = "sentado"

class Aclamacao(BaseModel):
    tipo: Literal["aclamacao"] = "aclamacao"
    titulo: str = "Aclamação ao Evangelho"
    refrao: list[str]                    # geralmente ["Aleluia, aleluia, aleluia."]
    versiculo: str
    postura: Postura = "de_pe"

class Oracao(BaseModel):
    tipo: Literal["oracao"] = "oracao"
    titulo: str                          # ex: "Oração da Coleta", "Pai Nosso"
    texto: str
    resposta: str | None = None          # ex: "Amém."
    postura: Postura = None

class Dialogo(BaseModel):
    """Para partes alternadas tipo P:/T: (Presidente/Todos), L:/T: (Leitor/Todos)."""
    tipo: Literal["dialogo"] = "dialogo"
    titulo: str
    turnos: list[dict[str, str]]         # [{"falante": "P", "texto": "..."}, {"falante": "T", "texto": "..."}]
    postura: Postura = None

Bloco = Canto | Leitura | Salmo | Aclamacao | Oracao | Dialogo

class Missa(BaseModel):
    data: str                            # ISO 8601 "2026-05-17"
    titulo_celebracao: str               # ex: "Ascensão do Senhor"
    tempo_liturgico: str | None = None
    cor_liturgica: str | None = None
    observacoes: str | None = None       # ex: "60º Dia Mundial das Comunicações Sociais"
    blocos: list[Bloco]                  # ordem sequencial da celebração
```

### Validadores que rejeitam artefatos

Adicione validadores que **rejeitam** qualquer string contaminada:

```python
ARTEFATOS_PROIBIDOS = re.compile(r"(##|\*\*|^\*|\s/\s|/$|^/|\b\w+-$|\bAleQue\b)")

def validar_limpo(texto: str) -> str:
    if ARTEFATOS_PROIBIDOS.search(texto):
        raise ValueError(f"Texto contém artefato proibido: {texto[:80]!r}")
    return texto

# Aplicar como field_validator em todos os campos de texto livre
# Exemplo em Canto:
class Canto(BaseModel):
    # ...campos...

    @field_validator("titulo", "refrao", "estrofes", mode="after")
    @classmethod
    def sem_artefatos(cls, v):
        if isinstance(v, str):
            return validar_limpo(v)
        if isinstance(v, list):
            for item in v:
                if isinstance(item, str):
                    validar_limpo(item)
                elif isinstance(item, list):
                    for s in item:
                        validar_limpo(s)
        return v
```

### System prompt para a LLM

Use exatamente este system prompt na chamada de estruturação:

```
Você recebe texto bruto extraído de um folheto de missa católica em português.
Sua única tarefa é preencher o schema JSON fornecido. Não invente conteúdo.

REGRAS OBRIGATÓRIAS:

1. NUNCA inclua os caracteres "/", "##", "**" ou "*" no conteúdo dos campos.
   Esses são artefatos de extração e devem ser removidos ou interpretados:
   - "/" em folhetos separa versos. Cada verso vira um item separado no array.
   - "##" e "**" são markdown vazado. Ignore.

2. NUNCA retorne palavras hifenizadas por quebra de linha.
   "Ale-luia" → "Aleluia". "vence-dor" → "vencedor".
   Se ver "AleQue", "AleNão", etc., é provavelmente duas palavras coladas
   após uma "Aleluia!" perdida — reconstrua: "AleQue" → "Aleluia! Que".

3. SEPARE rigorosamente conteúdos diferentes:
   - Letras de cantos vão em "refrao" e "estrofes".
   - Créditos de autoria ("Entrada: Fulano; Ofertas: Beltrano") vão em "creditos",
     NUNCA dentro das letras.
   - Rubricas de postura entre parênteses ("(De pé)", "(Sentados)", "(Ajoelhados)")
     viram o campo "postura" com valores "de_pe", "sentado", "ajoelhado",
     NUNCA dentro do texto.
   - Rubricas de instrução longa ("O sacerdote diz...") ficam em campo separado
     ou são omitidas se não couberem no schema.

4. ESTRUTURA DE CANTOS E SALMOS:
   - "refrao" é a parte que se repete entre estrofes. No folheto geralmente
     está em negrito ou marcada com "R." ou "REFRÃO:".
   - "estrofes" é uma lista de listas: cada estrofe é uma lista de versos.
   - Cada verso é UM item do array. Não concatene versos com "/".

5. PARA DIÁLOGOS (P:/T:, L:/T:, V:/R:):
   - Use o bloco "dialogo" com turnos alternados.
   - "falante" recebe a sigla exata do folheto ("P", "T", "L", "V", "R").

6. SE NÃO TIVER CERTEZA de um campo, retorne null. NUNCA invente.

7. PRESERVE acentuação portuguesa correta. Corrija obviamente errados
   ("nao" → "não", "voce" → "você") mas não altere o sentido.

8. ORDEM dos blocos deve seguir a ordem da celebração no folheto.

Retorne APENAS o JSON válido conforme o schema, sem texto antes ou depois,
sem cercas de markdown ```json.
```

### Estratégia de retry

Se a validação Pydantic falhar (artefato detectado ou schema inválido), faça **até 2 retries** alimentando o erro de volta para a LLM:

```python
async def estruturar_com_retry(texto_limpo: str, max_tentativas: int = 3) -> Missa:
    erro_anterior = None
    for tentativa in range(max_tentativas):
        prompt_user = texto_limpo
        if erro_anterior:
            prompt_user = (
                f"Sua tentativa anterior falhou com erro:\n{erro_anterior}\n\n"
                f"Corrija e retorne o JSON válido para o texto:\n\n{texto_limpo}"
            )
        try:
            resposta_json = await chamar_llm(SYSTEM_PROMPT, prompt_user)
            return Missa.model_validate_json(resposta_json)
        except (ValueError, ValidationError) as e:
            erro_anterior = str(e)
    raise RuntimeError(f"Falha após {max_tentativas} tentativas: {erro_anterior}")
```

## Etapa 5 — Cache e versionamento

Salve o JSON validado em disco indexado pelo hash do PDF. Se uma nova execução produzir o mesmo hash, devolva o JSON cacheado. Estruture o cache assim:

```
cache/
  pdfs/
    <hash>.pdf
  estruturado/
    <hash>.json
    <hash>.meta.json        # data de processamento, versão do schema, modelo LLM usado
```

## Componentes de UI — contrato visual

A UI recebe um objeto `Missa` validado e renderiza um componente por bloco, navegado sequencialmente com botões "Anterior" / "Próximo". Cada tipo de bloco tem um componente próprio.

### Princípios visuais

- **Postura** sempre como chip/indicador no topo do card, nunca como texto: ícone + "De pé" / "Sentado" / "Ajoelhado"
- **Refrão** com destaque tipográfico distinto das estrofes (peso maior, cor de destaque sutil, ou borda lateral)
- **Versos** como linhas independentes, nunca separados por `/`
- **Estrofes** numeradas e visualmente separadas (espaçamento ou divisor sutil)
- **Créditos** em texto pequeno secundário, no rodapé do card, jamais misturados na letra
- **Referências bíblicas** (`At 1,1-11`) como badge ou subtítulo, abaixo do título
- **Diálogos** com indentação e cor por falante

### Componentes lógicos por tipo

```
<Canto>
├── Header: título + chip de postura
├── Refrão (destacado)
├── Estrofes (lista numerada de versos)
└── Footer: créditos (texto pequeno cinza)

<Leitura>
├── Header: título + badge de referência + chip de postura
├── Introdução (itálico discreto)
├── Texto (corpo principal, parágrafos)
└── Conclusão (separada, com peso)

<Salmo>
├── Header: título + badge de referência
├── Refrão fixo (sempre visível, destacado)
└── Estrofes (alternadas com indicação visual de "responder com refrão")

<Aclamacao>
├── Refrão (Aleluia destacado)
└── Versículo

<Oracao>
├── Header: título + chip de postura
├── Texto
└── Resposta (destacada, ex: "Amém.")

<Dialogo>
└── Turnos alternados com indentação e label do falante (P/T/L)
```

## Critérios de aceitação — testes obrigatórios

Implemente estes testes. Eles **devem passar** para o pipeline ser considerado pronto:

1. **Sem artefatos de markdown**: percorra recursivamente todos os campos de texto de uma `Missa` validada e garanta que nenhum contém `##`, `**`, `*`, `/` isolada, hífen no final de palavra, ou padrão `[a-z][A-Z][a-z]` (palavra colada típica).

2. **Refrão e estrofes separados**: para qualquer bloco do tipo `canto` ou `salmo`, `refrao` é não-vazio E `estrofes` é não-vazio E nenhum item de `estrofes` contém o texto completo do refrão.

3. **Créditos fora das letras**: nenhum item de `refrao` ou `estrofes` contém os tokens `"Entrada:"`, `"Ofertas:"`, `"Comunhão:"`, `"Final:"`.

4. **Postura como enum**: o campo `postura` é `None` ou um dos valores literais permitidos, nunca uma string livre como `"(De pé)"`.

5. **Versos atômicos**: nenhum item de array de versos contém `\n` ou ` / `.

6. **Idempotência de cache**: processar o mesmo PDF duas vezes retorna o mesmo JSON byte-a-byte (depois de re-serializar).

7. **Teste de regressão visual**: o snapshot do PDF de exemplo (`https://www.arqrio.com.br/app/painel/amissa/amissa.pdf`) deve produzir um JSON que, comparado ao snapshot anterior, só difere em campos esperados (data, leituras do dia). A estrutura geral (presença de Canto de Entrada, Salmo, Evangelho, etc.) deve ser estável.

## Organização do código

```
src/
  pipeline/
    download.py          # etapa 1
    extract.py           # etapa 2 (PyMuPDF + reconstrução de espaços)
    clean.py             # etapa 3 (regexes)
    structure.py         # etapa 4 (LLM + retry)
    cache.py             # etapa 5
  schema/
    missa.py             # modelos Pydantic
    validators.py        # ARTEFATOS_PROIBIDOS e helpers
  llm/
    base.py              # interface abstrata
    deepseek.py          # implementação
    prompts.py           # SYSTEM_PROMPT como constante
  api/
    main.py              # endpoint que retorna Missa(json) dado uma URL de PDF
tests/
  fixtures/
    amissa_ascensao_2026.pdf
    amissa_ascensao_2026.expected.json
  test_clean.py
  test_schema_validators.py
  test_pipeline_e2e.py
```

## Tarefas para você (Deepseek)

Execute na ordem, **um passo por vez**, esperando minha confirmação antes de prosseguir para o próximo:

1. Crie a estrutura de pastas conforme acima.
2. Implemente `schema/missa.py` e `schema/validators.py` com todos os modelos Pydantic e o validador `ARTEFATOS_PROIBIDOS`. Escreva testes unitários para os validadores antes de prosseguir.
3. Implemente `pipeline/download.py` com cache por hash.
4. Implemente `pipeline/extract.py` usando PyMuPDF com a heurística de reconstrução de espaços. Inclua teste com o PDF de exemplo verificando que `"CantodeEntrada"` não aparece na saída.
5. Implemente `pipeline/clean.py` com as regexes documentadas. Testes unitários cobrindo: de-hifenização, junção de linhas quebradas, normalização de espaços.
6. Implemente `llm/base.py` (interface) e `llm/deepseek.py` (implementação), com o `SYSTEM_PROMPT` em `llm/prompts.py`.
7. Implemente `pipeline/structure.py` com a estratégia de retry.
8. Escreva o teste end-to-end `test_pipeline_e2e.py` usando o PDF de exemplo. Todos os 7 critérios de aceitação devem passar.
9. Só depois disso, ajuste os componentes de UI para consumir o novo schema.

## Restrições importantes

- **Não** introduza dependências fora desta lista sem confirmar: `pymupdf`, `pydantic`, `httpx`, `pytest`, e o SDK da LLM escolhida.
- **Não** "melhore" o schema adicionando campos que não estão na spec sem confirmar.
- **Não** mude os nomes dos campos do schema — a UI depende deles.
- **Sempre** prefira falhar (raise) a produzir saída contaminada. É melhor mostrar "erro ao processar o folheto desta semana" do que mostrar `"## REFRÃO / nósnocéu"` para um fiel durante a missa.

Quando terminar cada etapa, me mostre o diff dos arquivos criados/modificados e o resultado dos testes. Não avance sem meu OK.
