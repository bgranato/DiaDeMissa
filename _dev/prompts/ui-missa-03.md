# RESET TOTAL — App de Missa, reimplementação por TDD

> Cole este documento inteiro como **primeira mensagem** de uma conversa **nova** com o DeepSeek. Não continue conversas anteriores — elas têm hábitos contaminados.

---

## 0. Leia isto antes de tudo

Você (DeepSeek) trabalhou neste projeto antes. Você falhou repetidamente. A cada iteração de "consertar a UI", você quebrou duas outras coisas. As últimas telas mostram bugs piores que as primeiras: títulos colados com falas, turnos órfãos sem texto, palavras mutiladas (`"ífona"` em vez de `"Antífona"`), markdown literal (`**Antífona:**`) vazando, blocos litúrgicos diferentes aglutinados no mesmo card.

A causa raiz não é técnica. É de método: você esteve fazendo mudanças sem testes que pudessem provar regressão. Cada "correção" foi um chute.

**Isso para agora.**

A partir desta mensagem, você opera por **Test-Driven Development estrito**:

1. Nenhum arquivo de produção é criado, modificado ou deletado sem que **primeiro exista um teste que justifique a mudança**.
2. Nenhum gate é considerado completo sem `pytest -v` verde, com output **mostrado a mim** copiado e colado, antes de avançar.
3. Quando um teste falha, você conserta **a etapa do pipeline onde o problema está**, nunca remenda a UI ou faz `replace` cosmético.
4. Se você se pegar escrevendo `.replace("/", "")` ou similar dentro de um arquivo de UI, **pare imediatamente** — o problema está no parser, suba a stack.

Se você violar qualquer um desses quatro princípios, eu rejeito a mudança e te peço para reverter.

---

## 1. Reset do projeto

Primeira ação concreta sua, antes de qualquer código:

```bash
# Cria pasta de arquivo
mkdir -p _archive_$(date +%Y%m%d)

# Move TUDO que existe relacionado ao parsing e UI antiga
mv src _archive_$(date +%Y%m%d)/src_old 2>/dev/null || true
mv tests _archive_$(date +%Y%m%d)/tests_old 2>/dev/null || true
mv components _archive_$(date +%Y%m%d)/components_old 2>/dev/null || true

# Cria estrutura nova
mkdir -p src/schema src/pipeline src/llm src/api
mkdir -p tests/fixtures
mkdir -p components

# Baixa o PDF de referência como fixture
curl -o tests/fixtures/amissa_ascensao_2026.pdf \
  "https://www.arqrio.com.br/app/painel/amissa/amissa.pdf"
```

Me mostre o `ls -la` da nova estrutura e o tamanho do PDF baixado antes de prosseguir.

---

## 2. Filosofia: metadado disfarçado de texto

O folheto de missa é impresso em tinta monocromática. Toda estrutura — postura corporal, numeração de estrofes, falante de diálogos, número de versículo, referência bíblica, marcação de refrão — está representada como **texto inline** porque tinta não tem outra dimensão.

No app, isso vira componente visual. A regra única é:

```
folheto:  "1. Canto de Entrada (De pé)"
            ↓ pipeline de parsing
JSON:     { ordem: 1, titulo: "Canto de Entrada", postura: "de_pe" }
            ↓ pipeline de renderização
UI:       [chip "De pé"]  Canto de Entrada
```

O `"1."` e o `"(De pé)"` **morrem como string** e **renascem como elementos visuais**. Tabela completa:

| Folheto | JSON (parsing) | UI (renderização) |
|---|---|---|
| `1. Canto de Entrada (De pé)` | `ordem`, `titulo`, `postura` | Chip de postura no topo |
| `REFRÃO: ...` | `refrao: [...]` | Bloco destacado com label |
| `1. Ó varões...` (estrofe) | índice 0 de `estrofes` | Card com badge numérico |
| `verso A / verso B` | `["verso A", "verso B"]` | Linhas separadas, sem `/` |
| `P.Em nome...` (com ou sem espaço) | `{falante: "P", texto: "Em nome..."}` | Badge "P" + texto indentado |
| `(At 1,1-11)` | `referencia: "At 1,1-11"` | Badge abaixo do título |
| `¹⁷O Deus...` | `versiculos: [{numero:17, texto:"O Deus..."}]` | Número sobrescrito cinza |
| `Antífona da Entrada` (vem solta) | **Bloco próprio**, separado | Tela própria, não no card anterior |
| `Ale-\nluia` (quebra hifenizada) | `"Aleluia"` | `"Aleluia"` |

**Regra inegociável: o resultado final na UI nunca pode conter `/`, `##`, `**`, `Ale-luia`, `AleQue`, palavras coladas, ou siglas de falante como texto.**

---

## 3. O gabarito — JSON-alvo verificado

Eu li o PDF (`https://www.arqrio.com.br/app/painel/amissa/amissa.pdf`) e estruturei manualmente o resultado esperado. Seu pipeline, ao processar esse PDF, deve produzir **exatamente** este JSON.

Salve isto como `tests/fixtures/amissa_ascensao_2026.expected.json`:

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
      "refrao": ["O Senhor foi preparar um lugar para nós no céu."],
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
      "postura": "de_pe",
      "turnos": [
        {"falante": "P", "texto": "Em nome do Pai e do Filho e do Espírito Santo."},
        {"falante": "T", "texto": "Amém."},
        {"falante": "P", "texto": "A graça e a paz daquele que é, que era e que vem, estejam convosco."},
        {"falante": "T", "texto": "Bendito seja Deus, que nos reuniu no amor de Cristo."}
      ]
    },
    {
      "tipo": "antifona",
      "ordem": 3,
      "titulo": "Antífona da Entrada",
      "referencia": "At 1,11",
      "texto": "Homens da Galileia, por que ficais aqui, parados, olhando para o céu? Esse Jesus virá do mesmo modo como o vistes partir para o céu, aleluia."
    },
    {
      "tipo": "dialogo",
      "ordem": 4,
      "titulo": "Ato Penitencial",
      "turnos": [
        {"falante": "P", "texto": "Irmãos e irmãs, reconheçamos os nossos pecados, para celebrarmos dignamente os santos mistérios."},
        {"falante": "rubrica", "texto": "Momento de silêncio."},
        {"falante": "P", "texto": "Senhor, que subindo ao céu vos tornastes Rei do universo e Senhor dos séculos, tende piedade de nós."},
        {"falante": "T", "texto": "Senhor, tende piedade de nós."},
        {"falante": "P", "texto": "Cristo, que na vossa ascensão levastes cativo o cativeiro, tende piedade de nós."},
        {"falante": "T", "texto": "Cristo, tende piedade de nós."},
        {"falante": "P", "texto": "Senhor, que voltando à casa do Pai abristes o céu para nós, tende piedade de nós."},
        {"falante": "T", "texto": "Senhor, tende piedade de nós."},
        {"falante": "P", "texto": "Deus todo-poderoso tenha compaixão de nós, perdoe os nossos pecados e nos conduza à vida eterna."},
        {"falante": "T", "texto": "Amém."}
      ]
    },
    {
      "tipo": "leitura",
      "ordem": 7,
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

**Observação importante:** o JSON acima mostra os primeiros blocos completos. O folheto inteiro tem ~22 blocos. Os outros seguem o mesmo padrão (Salmo Responsorial, Segunda Leitura, Aclamação ao Evangelho, Evangelho, Profissão de Fé, Oração dos Fiéis, Canto das Ofertas, Oração Eucarística, Pai Nosso, Canto de Comunhão, Antífona da Comunhão, Bênção Final, Antífona Mariana). Os testes verificam estruturas gerais para esses; os primeiros blocos têm verificação exata.

---

## 4. O schema (Pydantic v2)

`src/schema/missa.py`:

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Annotated, Union
import re

Postura = Literal["de_pe", "sentado", "ajoelhado", None]
Falante = Literal["P", "T", "L", "V", "R", "rubrica"]

# Padrões proibidos em qualquer campo de texto
ARTEFATOS = [
    (r"\s/\s",                              "barra separadora não traduzida"),
    (r"^/|/$",                              "barra no início/fim"),
    (r"##|^\*\*|\*\*$",                     "markdown vazado"),
    (r"\w+-\s*\n",                          "hifenização de quebra de linha"),
    (r"[a-záéíóúâêôãõç][A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]",
                                            "palavras coladas (camelCase)"),
    (r"^\s*\d+\.\s",                        "numeração de estrofe dentro do texto"),
    (r"\(De pé\)|\(Sentados?\)|\(Ajoelhados?\)",
                                            "postura como texto"),
    (r"^[PTLVR]\.\s*",                      "sigla de falante dentro do texto"),
    (r"Entrada:\s*\w+;\s*Ofertas:",         "créditos vazando para letra"),
]

def validar_texto_limpo(texto: str) -> str:
    if not isinstance(texto, str):
        return texto
    for padrao, descricao in ARTEFATOS:
        if re.search(padrao, texto):
            raise ValueError(f"Artefato '{descricao}' em: {texto[:80]!r}")
    return texto

TextoLimpo = Annotated[str, field_validator("*", mode="after")(validar_texto_limpo)]


class Creditos(BaseModel):
    entrada: str | None = None
    ofertas: str | None = None
    comunhao: str | None = None
    final: str | None = None


class PalavraDoDia(BaseModel):
    texto: str
    referencia: str


class BlocoBase(BaseModel):
    ordem: int
    titulo: str
    postura: Postura = None


class Canto(BlocoBase):
    tipo: Literal["canto"] = "canto"
    refrao: list[str] = Field(default_factory=list)
    estrofes: list[list[str]] = Field(default_factory=list)

    @field_validator("refrao", "estrofes", mode="after")
    @classmethod
    def sem_artefatos(cls, v):
        if isinstance(v, list):
            for item in v:
                if isinstance(item, str):
                    validar_texto_limpo(item)
                elif isinstance(item, list):
                    for s in item:
                        validar_texto_limpo(s)
        return v


class Versiculo(BaseModel):
    numero: int
    texto: str

    @field_validator("texto", mode="after")
    @classmethod
    def texto_limpo(cls, v):
        return validar_texto_limpo(v)


class Leitura(BlocoBase):
    tipo: Literal["leitura"] = "leitura"
    categoria: Literal["primeira_leitura", "segunda_leitura", "evangelho"]
    referencia: str
    introducao: str
    versiculos: list[Versiculo] = Field(default_factory=list)
    conclusao: str | None = None
    resposta: str | None = None


class Salmo(BlocoBase):
    tipo: Literal["salmo"] = "salmo"
    referencia: str
    refrao: list[str]
    estrofes: list[list[str]]


class Aclamacao(BlocoBase):
    tipo: Literal["aclamacao"] = "aclamacao"
    referencia: str
    refrao: list[str]
    versiculo: str


class Antifona(BlocoBase):
    tipo: Literal["antifona"] = "antifona"
    referencia: str | None = None
    texto: str


class Oracao(BlocoBase):
    tipo: Literal["oracao"] = "oracao"
    texto: str
    resposta: str | None = None


class Turno(BaseModel):
    falante: Falante
    texto: str

    @field_validator("texto", mode="after")
    @classmethod
    def texto_limpo(cls, v):
        return validar_texto_limpo(v)


class Dialogo(BlocoBase):
    tipo: Literal["dialogo"] = "dialogo"
    turnos: list[Turno]


Bloco = Union[Canto, Leitura, Salmo, Aclamacao, Antifona, Oracao, Dialogo]


class Missa(BaseModel):
    data: str  # ISO 8601
    ano_liturgico: Literal["A", "B", "C"]
    titulo_celebracao: str
    categoria: str  # "Solenidade", "Festa", "Memória", "Domingo Comum", etc.
    observacoes: str | None = None
    creditos_cantos: Creditos
    palavra_do_dia: PalavraDoDia
    blocos: list[Bloco]
```

---

## 5. A suíte de testes — `tests/test_ascensao_2026.py`

Este arquivo é a **spec executável**. Todo teste aqui deve passar antes do projeto ser considerado pronto.

```python
import json
import re
from pathlib import Path

import pytest

from src.pipeline import processar_pdf
from src.schema.missa import Missa

PDF_FIXTURE = Path("tests/fixtures/amissa_ascensao_2026.pdf")
JSON_GABARITO = Path("tests/fixtures/amissa_ascensao_2026.expected.json")


@pytest.fixture(scope="module")
def missa() -> Missa:
    return processar_pdf(PDF_FIXTURE)


@pytest.fixture(scope="module")
def gabarito() -> dict:
    return json.loads(JSON_GABARITO.read_text(encoding="utf-8"))


# ===== METADADOS DA CELEBRAÇÃO =====

class TestMetadados:
    def test_data(self, missa):
        assert missa.data == "2026-05-17"

    def test_titulo(self, missa):
        assert missa.titulo_celebracao == "Ascensão do Senhor"

    def test_categoria(self, missa):
        assert missa.categoria == "Solenidade"

    def test_ano_liturgico(self, missa):
        assert missa.ano_liturgico == "A"

    def test_observacoes_mencionam_dia_das_comunicacoes(self, missa):
        assert "Comunicações Sociais" in (missa.observacoes or "")


# ===== CRÉDITOS DOS CANTOS (fora dos blocos) =====

class TestCreditos:
    def test_entrada(self, missa):
        assert missa.creditos_cantos.entrada == "José Alves"

    def test_ofertas(self, missa):
        assert missa.creditos_cantos.ofertas == "D.R."

    def test_comunhao(self, missa):
        assert missa.creditos_cantos.comunhao == "Pe. José Weber"

    def test_final(self, missa):
        assert missa.creditos_cantos.final == "Antífona Mariana / Liturgia das Horas"


# ===== CANTO DE ENTRADA =====

class TestCantoEntrada:
    @pytest.fixture
    def canto(self, missa):
        return next(b for b in missa.blocos if b.titulo == "Canto de Entrada")

    def test_tipo(self, canto):
        assert canto.tipo == "canto"

    def test_postura(self, canto):
        assert canto.postura == "de_pe"

    def test_refrao_exato(self, canto):
        assert canto.refrao == ["O Senhor foi preparar um lugar para nós no céu."]

    def test_quantidade_estrofes(self, canto):
        assert len(canto.estrofes) == 4

    def test_primeira_estrofe_exata(self, canto):
        assert canto.estrofes[0] == [
            "Ó varões galileus, que estais no céu a olhar? Aleluia!",
            "O Jesus que subiu ao céu deve, depois voltar! Aleluia!",
        ]

    def test_quarta_estrofe_exata(self, canto):
        assert canto.estrofes[3] == [
            "Ó Jesus, nosso Rei e Senhor, que subis para o céu! Aleluia!",
            "Não deixeis os cristãos a sós: dai-nos o dom de Deus! Aleluia!",
        ]

    def test_nenhum_verso_contem_barra(self, canto):
        for estrofe in canto.estrofes:
            for verso in estrofe:
                assert "/" not in verso

    def test_nenhum_verso_contem_numero_estrofe(self, canto):
        for estrofe in canto.estrofes:
            for verso in estrofe:
                assert not re.match(r"^\d+\.\s", verso)

    def test_creditos_nao_estao_no_canto(self, canto):
        textos = canto.refrao + [v for e in canto.estrofes for v in e]
        for t in textos:
            assert "Entrada:" not in t
            assert "José Alves" not in t


# ===== SAUDAÇÃO (diálogo crítico para teste de falantes) =====

class TestSaudacao:
    @pytest.fixture
    def saudacao(self, missa):
        return next(b for b in missa.blocos if b.titulo == "Saudação")

    def test_tipo(self, saudacao):
        assert saudacao.tipo == "dialogo"

    def test_quatro_turnos(self, saudacao):
        assert len(saudacao.turnos) == 4

    def test_sequencia_falantes(self, saudacao):
        assert [t.falante for t in saudacao.turnos] == ["P", "T", "P", "T"]

    def test_primeiro_turno(self, saudacao):
        # CRÍTICO: no PDF aparece como "P.Em nome..." (sem espaço)
        # O parser deve capturar mesmo assim e remover o "P."
        assert saudacao.turnos[0].texto == "Em nome do Pai e do Filho e do Espírito Santo."

    def test_segundo_turno(self, saudacao):
        assert saudacao.turnos[1].texto == "Amém."

    def test_terceiro_turno_completo(self, saudacao):
        # CRÍTICO: a fala do padre não pode ser cortada no meio
        assert saudacao.turnos[2].texto == \
            "A graça e a paz daquele que é, que era e que vem, estejam convosco."

    def test_quarto_turno(self, saudacao):
        assert saudacao.turnos[3].texto == \
            "Bendito seja Deus, que nos reuniu no amor de Cristo."

    def test_nenhum_turno_orfao(self, saudacao):
        for turno in saudacao.turnos:
            assert turno.texto.strip() != ""

    def test_nenhum_turno_tem_sigla_no_texto(self, saudacao):
        for turno in saudacao.turnos:
            assert not re.match(r"^[PTLVR]\.", turno.texto)


# ===== ANTÍFONA DA ENTRADA (bloco separado da Saudação) =====

class TestAntifonaEntrada:
    @pytest.fixture
    def antifona(self, missa):
        return next(b for b in missa.blocos if b.titulo == "Antífona da Entrada")

    def test_tipo(self, antifona):
        assert antifona.tipo == "antifona"

    def test_referencia(self, antifona):
        assert antifona.referencia == "At 1,11"

    def test_texto_completo(self, antifona):
        assert antifona.texto == (
            "Homens da Galileia, por que ficais aqui, parados, olhando para o céu? "
            "Esse Jesus virá do mesmo modo como o vistes partir para o céu, aleluia."
        )

    def test_e_bloco_independente(self, missa):
        """Antífona NÃO pode estar concatenada com a Saudação ou outro bloco."""
        for bloco in missa.blocos:
            if bloco.titulo == "Saudação":
                conteudo = str(bloco.model_dump())
                assert "Homens da Galileia" not in conteudo


# ===== ATO PENITENCIAL =====

class TestAtoPenitencial:
    @pytest.fixture
    def ato(self, missa):
        return next(b for b in missa.blocos if b.titulo == "Ato Penitencial")

    def test_tem_rubrica_de_silencio(self, ato):
        rubricas = [t for t in ato.turnos if t.falante == "rubrica"]
        assert len(rubricas) >= 1
        assert "silêncio" in rubricas[0].texto.lower()

    def test_alterna_padre_assembleia(self, ato):
        # Após a rubrica, deve haver pares P/T
        pos_rubrica = [t for t in ato.turnos if t.falante in ("P", "T")]
        # Pelo menos 3 pares P/T (Senhor / Cristo / Senhor + final)
        falantes = [t.falante for t in pos_rubrica]
        assert falantes.count("P") >= 4
        assert falantes.count("T") >= 4


# ===== PRIMEIRA LEITURA =====

class TestPrimeiraLeitura:
    @pytest.fixture
    def leitura(self, missa):
        return next(b for b in missa.blocos
                    if hasattr(b, "categoria") and b.categoria == "primeira_leitura")

    def test_referencia(self, leitura):
        assert leitura.referencia == "At 1,1-11"

    def test_postura(self, leitura):
        assert leitura.postura == "sentado"

    def test_introducao(self, leitura):
        assert leitura.introducao == "Leitura dos Atos dos Apóstolos."

    def test_conclusao(self, leitura):
        assert leitura.conclusao == "Palavra do Senhor."

    def test_resposta(self, leitura):
        assert leitura.resposta == "Graças a Deus."

    def test_tem_versiculos_numerados(self, leitura):
        assert len(leitura.versiculos) >= 11  # vai do versículo 1 ao 11
        numeros = [v.numero for v in leitura.versiculos]
        assert 1 in numeros
        assert 11 in numeros

    def test_versiculos_em_ordem(self, leitura):
        numeros = [v.numero for v in leitura.versiculos]
        assert numeros == sorted(numeros)

    def test_numero_nao_aparece_no_texto(self, leitura):
        for v in leitura.versiculos:
            # texto não pode começar com o próprio número
            assert not re.match(rf"^{v.numero}\D", v.texto)


# ===== PALAVRA DO DIA =====

class TestPalavraDoDia:
    def test_vem_do_evangelho_da_ascensao(self, missa):
        # Mt 28 = Evangelho da Ascensão Ano A
        assert missa.palavra_do_dia.referencia.startswith("Mt 28")

    def test_nao_e_frase_generica_aleatoria(self, missa):
        # "Eu sou o pão vivo" é Jo 6, NÃO deve aparecer em domingo de Ascensão
        assert "pão vivo" not in missa.palavra_do_dia.texto

    def test_tema_central(self, missa):
        assert "convosco" in missa.palavra_do_dia.texto.lower() \
            or "dias" in missa.palavra_do_dia.texto.lower()


# ===== INVARIANTES GLOBAIS =====

class TestInvariantesGlobais:
    """Testes que percorrem TODOS os textos da missa e garantem zero contaminação."""

    def _walk_strings(self, obj, caminho="missa"):
        if isinstance(obj, str):
            yield caminho, obj
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                yield from self._walk_strings(item, f"{caminho}[{i}]")
        elif hasattr(obj, "model_dump"):
            for k, v in obj.model_dump().items():
                yield from self._walk_strings(v, f"{caminho}.{k}")
        elif isinstance(obj, dict):
            for k, v in obj.items():
                yield from self._walk_strings(v, f"{caminho}.{k}")

    def test_zero_barras_separadoras(self, missa):
        for caminho, texto in self._walk_strings(missa):
            assert " / " not in texto, f"{caminho}: {texto!r}"

    def test_zero_markdown(self, missa):
        for caminho, texto in self._walk_strings(missa):
            assert "##" not in texto, f"{caminho}: {texto!r}"
            assert "**" not in texto, f"{caminho}: {texto!r}"

    def test_zero_hifens_orfaos(self, missa):
        for caminho, texto in self._walk_strings(missa):
            assert not re.search(r"\w+-\s*\n", texto), f"{caminho}: {texto!r}"

    def test_zero_palavras_mutiladas(self, missa):
        """'ífona' não pode aparecer (Antífona mutilada)."""
        for caminho, texto in self._walk_strings(missa):
            assert "ífona" not in texto or "Antífona" in texto, (
                f"{caminho}: palavra mutilada: {texto!r}"
            )

    def test_zero_palavras_coladas(self, missa):
        for caminho, texto in self._walk_strings(missa):
            assert "AleQue" not in texto, f"{caminho}: {texto!r}"
            assert "CantodeEntrada" not in texto, f"{caminho}: {texto!r}"
            assert "JoséAlves" not in texto, f"{caminho}: {texto!r}"

    def test_zero_postura_como_texto(self, missa):
        for caminho, texto in self._walk_strings(missa):
            assert not re.search(r"\(De pé\)", texto), f"{caminho}: {texto!r}"
            assert not re.search(r"\(Sentados?\)", texto), f"{caminho}: {texto!r}"

    def test_zero_siglas_falante_em_texto_de_dialogo(self, missa):
        for bloco in missa.blocos:
            if bloco.tipo == "dialogo":
                for turno in bloco.turnos:
                    assert not re.match(r"^[PTLVR]\.", turno.texto), \
                        f"{bloco.titulo}: {turno.texto!r}"

    def test_ordem_sequencial(self, missa):
        ordens = [b.ordem for b in missa.blocos]
        assert ordens == sorted(ordens)

    def test_todos_blocos_tem_titulo(self, missa):
        for bloco in missa.blocos:
            assert bloco.titulo.strip() != ""


# ===== IDEMPOTÊNCIA =====

class TestIdempotencia:
    def test_processar_duas_vezes_produz_mesmo_resultado(self):
        m1 = processar_pdf(PDF_FIXTURE)
        m2 = processar_pdf(PDF_FIXTURE)
        assert m1.model_dump_json() == m2.model_dump_json()
```

---

## 6. Pipeline em 5 etapas

### Etapa 1 — Download e cache (`src/pipeline/download.py`)

Baixa PDF da URL, cacheia por hash SHA-256 do conteúdo, TTL 24h. Se for path local (Path), apenas retorna o path.

### Etapa 2 — Extração (`src/pipeline/extract.py`)

```python
import fitz  # PyMuPDF

def extrair_texto_estruturado(pdf_path) -> str:
    """
    Extrai texto preservando estrutura. Resolve espaços perdidos por gap horizontal.
    """
    doc = fitz.open(pdf_path)
    linhas_finais = []
    
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                texto_linha = ""
                ultimo_span = None
                for span in line["spans"]:
                    if ultimo_span:
                        gap = span["bbox"][0] - ultimo_span["bbox"][2]
                        # Insere espaço se gap > 0.25 * fontsize OU se há mudança de case
                        if gap > 0.25 * ultimo_span["size"]:
                            if not texto_linha.endswith(" "):
                                texto_linha += " "
                    texto_linha += span["text"]
                    ultimo_span = span
                linhas_finais.append(texto_linha)
    
    return "\n".join(linhas_finais)
```

### Etapa 3 — Limpeza determinística (`src/pipeline/clean.py`)

```python
import re
import unicodedata

def limpar(texto: str) -> str:
    # 1. Normaliza unicode
    texto = unicodedata.normalize("NFC", texto)
    
    # 2. Desfaz hifenização de fim de linha
    texto = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", texto)
    
    # 3. Junta linhas quebradas por largura de coluna
    #    (linha terminando em letra minúscula/vírgula + próxima começa em minúscula)
    texto = re.sub(
        r"([a-záéíóúâêôãõçà,;:])\s*\n\s*([a-záéíóúâêôãõçà])",
        r"\1 \2",
        texto,
    )
    
    # 4. Insere espaço após sigla de falante grudada: "P.Em" → "P. Em"
    texto = re.sub(r"^([PTLVR])\.([A-ZÁÉÍÓÚÂÊÔÃÕÇ])", r"\1. \2", texto, flags=re.MULTILINE)
    
    # 5. Normaliza espaços
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    texto = "\n".join(linha.strip() for linha in texto.split("\n"))
    
    return texto.strip()
```

### Etapa 4 — Estruturação (`src/pipeline/structure.py`)

Chama LLM com o `SYSTEM_PROMPT` abaixo, texto limpo, valida com Pydantic, faz até 3 retries alimentando erro de volta:

```python
# src/llm/prompts.py
SYSTEM_PROMPT = """Você é um parser de folhetos de missa católica em português.
Recebe texto bruto extraído de PDF e devolve JSON estruturado.

REGRAS OBRIGATÓRIAS (violar qualquer uma invalida sua resposta):

1. NUNCA inclua "/", "##", "**", "*" no conteúdo de qualquer campo.
   - "/" no folheto separa versos. Cada verso = item separado do array.
   
2. NUNCA retorne palavras com hífen de quebra de linha.
   "Ale-luia" → "Aleluia". "vence-dor" → "vencedor".

3. NUNCA retorne palavras coladas. "AleQue" → "Aleluia! Que" (use contexto).

4. NUNCA inclua "(De pé)", "(Sentados)", "(Ajoelhados)" no texto.
   Vire o campo "postura" com valor "de_pe" / "sentado" / "ajoelhado".

5. NUNCA inclua "P.", "T.", "L." no início do texto de um turno.
   Use o campo "falante" com valor "P", "T", "L", "V", "R".
   Rubricas (instruções como "Momento de silêncio") usam falante "rubrica".

6. ESTROFES: cada estrofe é uma LISTA de versos. Numere a posição no array,
   NUNCA mantenha "1.", "2." dentro do texto.

7. ANTÍFONAS são BLOCOS SEPARADOS. A "Antífona da Entrada" não faz parte
   da "Saudação". A "Antífona da Comunhão" não faz parte do "Canto de Comunhão".

8. VERSÍCULOS bíblicos numerados (¹⁷O Deus...) vão em array de objetos
   {"numero": 17, "texto": "O Deus..."}. O número NUNCA fica dentro do texto.

9. CRÉDITOS ("Entrada: Fulano; Ofertas: Beltrano") vão em "creditos_cantos"
   no nível da Missa, NUNCA dentro de cantos individuais.

10. Se um campo não estiver claro no folheto, retorne null. NUNCA invente.

11. PALAVRA DO DIA: escolha entre (a) última frase do Evangelho, (b) refrão
    do Salmo, (c) versículo da Aclamação. Critério: o que melhor sintetiza
    o tema da celebração para um card devocional.

Retorne APENAS JSON válido, sem markdown, sem ```json, sem texto explicativo.
"""
```

### Etapa 5 — Pipeline orquestrador (`src/pipeline/__init__.py`)

```python
from pathlib import Path
from .download import baixar_se_url
from .extract import extrair_texto_estruturado
from .clean import limpar
from .structure import estruturar_com_retry
from ..schema.missa import Missa


def processar_pdf(fonte) -> Missa:
    pdf_path = baixar_se_url(fonte) if isinstance(fonte, str) else fonte
    texto_bruto = extrair_texto_estruturado(pdf_path)
    texto_limpo = limpar(texto_bruto)
    return estruturar_com_retry(texto_limpo)
```

---

## 7. Componentes de UI

**SÓ DEPOIS DO GATE 6 VERDE.** Cada bloco tem componente próprio:

- `<Canto>`: chip de postura no topo, refrão destacado, estrofes numeradas como cards
- `<Leitura>`: badge de referência, introdução em itálico, versículos com número sobrescrito, conclusão e resposta destacadas
- `<Salmo>`: refrão fixo destacado + estrofes alternadas com indicação visual de "responder com refrão"
- `<Antifona>`: card próprio, separado de Saudação ou Canto adjacente
- `<Dialogo>`: turnos com badge circular do falante (P=azul, T=dourado, L=neutro, rubrica=cinza itálico), divisores sutis
- `<Oracao>`: texto + resposta destacada

A UI **nunca** faz `.replace()` no texto que recebe. Se algum artefato aparecer na tela, o bug é no pipeline — não na UI.

---

## 8. Os 7 Gates — ordem obrigatória

Você **não pode** começar um gate sem o anterior estar verde e mostrado a mim.

### Gate 0 — Reset do projeto
- Executar seção 1 (reset + criar estrutura + baixar PDF).
- Mostrar `ls -la` da nova estrutura.

### Gate 1 — Schema + validators
- Criar `src/schema/missa.py` completo.
- Criar `tests/test_schema.py` com 5+ testes que tentam criar objetos com artefatos e verificam que `ValidationError` é levantado.
- Rodar `pytest tests/test_schema.py -v`. Mostrar output verde.

### Gate 2 — Limpeza determinística
- Criar `src/pipeline/clean.py`.
- Criar `tests/test_clean.py` com casos: `"Ale-\nluia"` → `"Aleluia"`, `"P.Em"` → `"P. Em"`, etc.
- Rodar `pytest tests/test_clean.py -v`. Mostrar output verde.

### Gate 3 — Extração com PyMuPDF
- Criar `src/pipeline/extract.py`.
- Criar `tests/test_extract.py` que processa o PDF e verifica: `"CantodeEntrada"` **não** aparece, `"AleQue"` **não** aparece, total de caracteres > 5000.
- Rodar `pytest tests/test_extract.py -v`. Mostrar output verde.

### Gate 4 — Suíte completa cria, **toda vermelha**
- Criar `tests/test_ascensao_2026.py` exatamente conforme seção 5.
- Criar `tests/fixtures/amissa_ascensao_2026.expected.json` conforme seção 3.
- Rodar `pytest tests/test_ascensao_2026.py -v`.
- **Esperado: toda vermelha.** Pipeline de estruturação ainda não existe.
- Mostrar output. Este é seu mapa: você vai pintar de verde, um teste por vez.

### Gate 5 — Estruturação LLM até primeiro grupo verde
- Criar `src/llm/prompts.py` + `src/llm/base.py` + `src/llm/deepseek.py`.
- Criar `src/pipeline/structure.py` com retry.
- Criar `src/pipeline/__init__.py` orquestrador.
- Iterar até `TestMetadados` e `TestCreditos` ficarem verdes.
- Mostrar output.

### Gate 6 — Suíte completa verde
- Iterar até **todas** as classes de teste passarem.
- Cada iteração: rodar pytest, identificar o primeiro vermelho, consertar **no pipeline**, repetir.
- Quando estiver tudo verde, mostrar output completo.

### Gate 7 — UI consome JSON validado
- **Agora** você pode tocar nos componentes.
- Cada componente recebe um objeto Pydantic, não string bruta.
- Crie um Storybook ou tela de teste mostrando cada tipo de bloco renderizado.

---

## 9. Regras inegociáveis (releia antes de cada commit)

1. **Pytest verde antes de avançar.** Sempre. Sem exceção.
2. **Nada de `.replace()` na UI.** Se for tentado, pare e suba a stack.
3. **Falha é melhor que saída contaminada.** Se a LLM não consegue estruturar após 3 retries, lance exceção. É melhor o usuário ver "erro ao carregar folheto desta semana" do que `## REFRÃO / AleQue` durante a missa.
4. **Idempotência.** Mesmo PDF → mesmo JSON, byte a byte.
5. **Nunca invente campos do schema.** Se faltar algo, me pergunte.
6. **Conserto vai pro pipeline, nunca pra UI.** Se "alguns P. não ficam em negrito", o problema é no parser, não no CSS.

---

## 10. Sua primeira resposta

Sua próxima mensagem deve conter **apenas o Gate 0**:

1. Output dos comandos shell de reset.
2. `ls -la` da nova estrutura.
3. Tamanho e checksum do PDF baixado.

Não crie nenhum código de schema, parser, ou UI ainda. Apenas reset + estrutura + fixture. Quando eu ver isso, eu autorizo Gate 1.
