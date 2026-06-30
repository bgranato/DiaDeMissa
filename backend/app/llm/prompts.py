from __future__ import annotations

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
   Rubricas usam falante "rubrica".

6. ESTROFES: cada estrofe é uma LISTA de versos. Numere a posição no array.

7. ANTÍFONAS são BLOCOS SEPARADOS.

8. VERSÍCULOS bíblicos numerados (¹⁷) vão em array de objetos.

9. CRÉDITOS vão em "creditos_cantos" no nível da Missa.

10. Se um campo não estiver claro, retorne null. NUNCA invente.

11. PALAVRA DO DIA: escolha entre (a) última frase do Evangelho, (b) refrão
    do Salmo, (c) versículo da Aclamação.

Retorne APENAS JSON válido, sem markdown, sem ```json, sem texto explicativo.
"""


# ---------------------------------------------------------------------------
# Regras específicas dos erros reais observados no folheto Arquidiocese RJ.
# Cada item abaixo corresponde a um defeito real do parser de regex.
# ---------------------------------------------------------------------------
REGRAS_FOLHETO = """REGRAS ESPECÍFICAS DO FOLHETO DA ARQUIDIOCESE DO RIO (críticas):

A. CABEÇALHO REPETIDO (masthead): o folheto reimprime a tarja
   "Ano X – no Y – DIA de MÊS de ANO / TÍTULO / Solenidade – ... / Dia do Papa"
   no MEIO da página (layout em 2 colunas). Essas linhas NÃO são conteúdo de
   nenhum canto/bloco. Use-as só para metadados (data, ano_liturgico,
   titulo_celebracao, categoria) e DESCARTE as repetições. Nunca deixe vazar
   dentro de uma estrofe.

B. CATEGORIA: a linha de categoria litúrgica ("Solenidade", "Festa", "Memória",
   "Domingo ...", às vezes "Solenidade – Dia do Papa") vai no campo `categoria`.
   NÃO é observação nem subtítulo de canto.

C. DESCRIÇÃO: o parágrafo de abertura entre o cabeçalho e "Ritos Iniciais"
   (ex.: "Hoje celebramos a solenidade...") é a `descricao` da missa.
   Capture-o mesmo que NÃO comece com "Neste Domingo/dia".

D. CRÉDITOS DOS CANTOS: a linha "Entrada: Fulano; Ofertas e Comunhão: Beltrano"
   vai em `creditos_cantos`. Se vier "Ofertas e Comunhão: X", preencha tanto
   `ofertas` quanto `comunhao` com X. NUNCA deixe créditos dentro de um canto.

E. REFERÊNCIA BÍBLICA NO TÍTULO: "Segunda Leitura (2Tm 4,6-8.17-18)" → a
   referência é "2Tm 4,6-8.17-18" (campo `referencia`). NUNCA quebre a
   referência em "versículos". Versículos são só o corpo numerado da leitura.

F. APÊNDICES pós-missa ("Oração pelas Vocações Sacerdotais", "Óbolo de São
   Pedro", "Leituras da Semana", "Antífona Mariana") são BLOCOS SEPARADOS com
   `secao: "apendice"`. NUNCA cole esse conteúdo no turno da Bênção Final.

G. SÍMBOLOS: a cruz litúrgica "✠" às vezes vem como "=". Remova-a do texto.
   Junte números de versículo colados à palavra ("13Jesus" → versículo 13,
   texto "Jesus...").

H. SEÇÕES: os divisores (tipo "secao") devem usar EXATAMENTE estes nomes:
   "Ritos Iniciais", "Liturgia da Palavra", "Liturgia Eucarística", "Ritos Finais".
   NÃO crie divisores como "Introdução à...". A frase introdutória do Leitor
   (linha "L. ...") logo após o nome da seção vai no campo `descricao` do divisor.

I. HOMILIA é um BLOCO próprio (tipo "oracao", com numero_folheto), nunca uma seção.
   O texto "Momento de silêncio para meditação pessoal" vai no campo `texto`.

J. APÊNDICES (Oração pelas Vocações Sacerdotais, Óbolo de São Pedro, Leituras da
   Semana, Antífona Mariana) são BLOCOS tipo "oracao" com `secao: "apendice"` e o
   conteúdo no campo `texto` — NUNCA divisores de seção.

K. REFRÃO: se no folheto o refrão aparece DEPOIS da estrofe N, defina
   `posicao_refrao_apos: N`. Use 0/null só quando o refrão vem antes de todas as
   estrofes (padrão do Salmo Responsorial).

L. ASPAS: PRESERVE as aspas (" " ' ') do texto original nas falas e leituras.
   Não as remova. Rubricas curtas no fim de um canto ("Momento de silêncio para
   oração pessoal") ficam como rubrica/anexo do bloco, não viram seção nova.

M. DESCRIÇÃO vs OBSERVAÇÕES (não confunda):
   - O parágrafo de reflexão de abertura (ex.: "Hoje celebramos...", "Reunidos em
     oração com Maria...", "Neste Domingo...") vai SEMPRE em `descricao`.
   - `observacoes` é só para uma nota curta extra (ex.: "Dia do Papa") ou null.
     NUNCA coloque o parágrafo de abertura em `observacoes`.

N. MASTHEAD a DESCARTAR (não vai para descricao nem observacoes): "Ano Jubilar
   Arquidiocesano", "Ano Jubilar", "A Comunicação Social", "Comunicação Social",
   "Versão Celular" e linhas de cabeçalho repetido.

O. CATEGORIA das solenidades: Pentecostes, Santíssima Trindade, Corpus Christi
   (Santíssimo Corpo e Sangue de Cristo), Ascensão, São Pedro e São Paulo,
   Sagrado Coração, Imaculada, Assunção, Cristo Rei, etc. são "Solenidade".
   NUNCA use "Missa" como categoria; se não houver rótulo explícito, deduza pelo
   título da celebração (Domingo comum → "Domingo"; festa → "Festa").
"""

# Catálogo de tipos de bloco que o JSON pode conter (espelha app/schema/missa.py).
SCHEMA_SPEC = """FORMATO DO JSON (campos por tipo de bloco):

Missa (raiz): {
  "data": "AAAA-MM-DD", "ano_liturgico": "A"|"B"|"C",
  "titulo_celebracao": str, "categoria": str,
  "descricao": str|null, "observacoes": str|null,
  "creditos_cantos": {"entrada":str|null,"ofertas":str|null,"comunhao":str|null,"final":str|null},
  "palavra_do_dia": {"texto":str,"referencia":str}|null,
  "blocos": [ ...blocos... ]
}

Cada bloco tem: ordem(int), numero_folheto(int|null), secao(str|null),
titulo(str), postura("de_pe"|"sentado"|"ajoelhado"|null), subtitulo(str|null), tipo.

tipos:
- {"tipo":"secao","ordem":..,"titulo":"Ritos Iniciais","descricao":str|null}
- {"tipo":"canto",...,"refrao":[str],"estrofes":[[str]],"referencia":str|null,"posicao_refrao_apos":int|null}
- {"tipo":"salmo",...,"referencia":str,"refrao":[str],"estrofes":[[str]]}
- {"tipo":"aclamacao",...,"referencia":str,"refrao":[str],"versiculo":str}
- {"tipo":"leitura",...,"categoria":"primeira_leitura"|"segunda_leitura"|"evangelho","referencia":str,"introducao":str,"versiculos":[{"numero":int,"texto":str}],"conclusao":str|null,"resposta":str|null}
- {"tipo":"antifona",...,"referencia":str|null,"texto":str}
- {"tipo":"oracao",...,"texto":str,"resposta":str|null,"referencia":str|null}
- {"tipo":"dialogo",...,"turnos":[{"falante":"P"|"T"|"L"|"V"|"R"|"rubrica","texto":str}],"referencia":str|null}

Regras de uso: Salmo Responsorial → tipo "salmo". Aclamação ao Evangelho →
tipo "aclamacao". Evangelho → tipo "leitura" com categoria "evangelho".
Partes faladas (Saudação, Ato Penitencial, Coleta, Hino de Louvor, Profissão,
Oração dos Fiéis, Oração Eucarística, Bênção) → tipo "dialogo".
"""


def build_user_prompt(texto_limpo: str, data_hint: str | None = None) -> str:
    """Monta o prompt do usuário com as regras + schema + texto bruto do folheto."""
    hint = f"\nDica de data (use se o cabeçalho não trouxer): {data_hint}\n" if data_hint else ""
    return (
        f"{REGRAS_FOLHETO}\n\n{SCHEMA_SPEC}\n{hint}\n"
        "Estruture o folheto abaixo em JSON seguindo TODAS as regras. "
        "Retorne só o JSON.\n\n"
        "=== TEXTO BRUTO DO FOLHETO ===\n"
        f"{texto_limpo}\n"
        "=== FIM ==="
    )


def build_correcao_prompt(json_invalido: str, erro: str) -> str:
    """Prompt de reprocessamento: devolve ao modelo o erro de validação pra corrigir."""
    return (
        "O JSON anterior falhou na validação com este erro:\n"
        f"{erro}\n\n"
        "Corrija APENAS o necessário e devolva o JSON inteiro válido de novo, "
        "sem markdown nem explicação.\n\n"
        "JSON anterior:\n"
        f"{json_invalido}"
    )
