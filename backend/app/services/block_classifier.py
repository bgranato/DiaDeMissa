from __future__ import annotations
import re
from typing import Optional

from app.services.liturgical_parser import BlocoExtraido


TITLE_TO_TYPE: dict[str, str] = {
    "CANTO DE ENTRADA": "canto_entrada",
    "ANTÍFONA DE ENTRADA": "antifona_entrada",
    "ANTÍFONA DA ENTRADA": "antifona_entrada",
    "SAUDAÇÃO": "saudacao_inicial",
    "SAUDAÇÃO INICIAL": "saudacao_inicial",
    "ATO PENITENCIAL": "ato_penitencial",
    "GLÓRIA": "gloria",
    "GLORIA A DEUS": "gloria",
    "HINO DE LOUVOR": "gloria",
    "COLETA": "oracao_dia",
    "ORAÇÃO DO DIA": "oracao_dia",
    "PRIMEIRA LEITURA": "primeira_leitura",
    "SEGUNDA LEITURA": "segunda_leitura",
    "SALMO RESPONSORIAL": "salmo_responsorial",
    "SEQUÊNCIA": "sequencia",
    "ACLAMAÇÃO AO EVANGELHO": "aclamação_evangelho",
    "ACLAMAÇÃO DO EVANGELHO": "aclamação_evangelho",
    "EVANGELHO": "evangelho",
    "HOMILIA": "homilia",
    "PROFISSÃO DE FÉ": "profissao_fe",
    "PROFISSÃO DA FÉ": "profissao_fe",
    "CREIO": "profissao_fe",
    "ORAÇÃO DOS FIÉIS": "preces_comunidade",
    "PRECES DA COMUNIDADE": "preces_comunidade",
    "CANTO DAS OFERTAS": "ofertorio",
    "OFERTÓRIO": "ofertorio",
    "PREPARAÇÃO DAS OFERENDAS": "ofertorio",
    "SOBRE AS OFERENDAS": "ofertorio",
    "CONVITE À ORAÇÃO": "oracao_eucaristica",
    "ORAI": "oracao_eucaristica",
    "ORAÇÃO EUCARÍSTICA": "oracao_eucaristica",
    "SANTO": "santo",
    "RITO DA COMUNHÃO": "comunhao",
    "PAI NOSSO": "pai_nosso",
    "CORDEIRO DE DEUS": "cordeiro_deus",
    "CANTO DE COMUNHÃO": "comunhao",
    "COMUNHÃO": "comunhao",
    "ANTÍFONA DA COMUNHÃO": "comunhao",
    "DEPOIS DA COMUNHÃO": "oracao_pos_comunhao",
    "ORAÇÃO PÓS-COMUNHÃO": "oracao_pos_comunhao",
    "ORAÇÃO DEPOIS DA COMUNHÃO": "oracao_pos_comunhao",
    "VIVÊNCIA": "avisos",
    "AVISOS": "avisos",
    "BÊNÇÃO FINAL": "bencao_final",
    "BÊNÇÃO E DESPEDIDA": "bencao_final",
    "BÊNÇÃO FINAL E DESPEDIDA": "bencao_final",
    "CANTO FINAL": "canto_final",
    "ANTÍFONA MARIANA": "canto_final",
}

CANONICAL_ORDER: list[str] = [
    "canto_entrada",
    "antifona_entrada",
    "saudacao_inicial",
    "ato_penitencial",
    "gloria",
    "oracao_dia",
    "primeira_leitura",
    "salmo_responsorial",
    "segunda_leitura",
    "sequencia",
    "aclamação_evangelho",
    "evangelho",
    "homilia",
    "profissao_fe",
    "preces_comunidade",
    "ofertorio",
    "santo",
    "oracao_eucaristica",
    "pai_nosso",
    "cordeiro_deus",
    "comunhao",
    "oracao_pos_comunhao",
    "avisos",
    "bencao_final",
    "canto_final",
    "desconhecido",
]


def _normalizar_titulo(texto: str) -> str:
    texto = texto.strip()
    texto = re.sub(r"^\d+\.\s*", "", texto)
    texto = texto.strip()
    return texto.upper()


def _contem_palavra(texto: str, palavra: str) -> bool:
    return palavra in texto.lower()


def classificar_bloco(bloco: BlocoExtraido) -> str:
    titulo = bloco.titulo or ""
    titulo_norm = _normalizar_titulo(titulo)
    conteudo = bloco.conteudo[:200] if bloco.conteudo else ""

    if titulo_norm in TITLE_TO_TYPE:
        return TITLE_TO_TYPE[titulo_norm]

    # Partial match on normalized title
    for key, tipo in TITLE_TO_TYPE.items():
        if key in titulo_norm or titulo_norm in key:
            return tipo

    # Keyword match on full title and content
    titulo_lower = titulo.lower()
    conteudo_lower = conteudo.lower()

    keyword_map = [
        ("primeira leitura", "primeira_leitura"),
        ("segunda leitura", "segunda_leitura"),
        ("salmo responsorial", "salmo_responsorial"),
        ("salmo", "salmo_responsorial"),
        ("evangelho", "evangelho"),
        ("aclamação", "aclamação_evangelho"),
        ("homilia", "homilia"),
        ("profissão de fé", "profissao_fe"),
        ("profissão da fé", "profissao_fe"),
        ("creio", "profissao_fe"),
        ("oração dos fiéis", "preces_comunidade"),
        ("preces", "preces_comunidade"),
        ("ofertório", "ofertorio"),
        ("ofertas", "ofertorio"),
        ("santo", "santo"),
        ("eucarística", "oracao_eucaristica"),
        ("pai nosso", "pai_nosso"),
        ("cordeiro", "cordeiro_deus"),
        ("comunhão", "comunhao"),
        ("pós-comunhão", "oracao_pos_comunhao"),
        ("bênção final", "bencao_final"),
        ("abenção", "bencao_final"),
        ("canto de entrada", "canto_entrada"),
        ("canto final", "canto_final"),
        ("antífona de entrada", "antifona_entrada"),
        ("antífona da entrada", "antifona_entrada"),
        ("antífona mariana", "canto_final"),
        ("saudação", "saudacao_inicial"),
        ("ato penitencial", "ato_penitencial"),
        ("glória", "gloria"),
        ("hino de louvor", "gloria"),
        ("coleta", "oracao_dia"),
        ("oração do dia", "oracao_dia"),
        ("sequência", "sequencia"),
        ("vivência", "avisos"),
        ("ritos finais", "bencao_final"),
    ]

    for palavra, tipo in keyword_map:
        if palavra in titulo_lower or palavra in conteudo_lower:
            return tipo

    # Check if it's a section header
    secoes = ["ritos iniciais", "liturgia da palavra", "liturgia eucarística", "ritos finais"]
    if titulo_lower in secoes:
        return "desconhecido"

    return "desconhecido"


def obter_ordem_canonica(tipo: str) -> int:
    try:
        return CANONICAL_ORDER.index(tipo)
    except ValueError:
        return len(CANONICAL_ORDER) - 1


def reordenar_blocos(blocos: list[tuple[BlocoExtraido, str]]) -> list[tuple[BlocoExtraido, str, int]]:
    classificados = [(b, t, obter_ordem_canonica(t)) for b, t in blocos]
    # Keep original order but assign canonical ordering score
    for i, (b, t, _) in enumerate(classificados):
        classificados[i] = (b, t, i + 1)
    return classificados
