from __future__ import annotations

import re
from typing import Optional

from app.schema.missa import (
    Missa, Canto, Leitura, Salmo, Aclamacao, Antifona, Oracao, Dialogo, Turno,
    Creditos, PalavraDoDia, Versiculo,
)


POSTURAS = {
    "de pé": "de_pe", "de pe": "de_pe",
    "sentado": "sentado", "sentados": "sentado",
    "ajoelhado": "ajoelhado", "ajoelhados": "ajoelhado",
}


def extrair_postura(linhas_bloco: list[str], janela: int = 3) -> Optional[str]:
    """
    Procura marcacao '(De pe)', '(Sentados)', etc. nas primeiras N linhas do bloco.
    Retorna o valor normalizado ou None.
    Suporta:
    - '1. Canto de Entrada (De pe)'          → mesma linha
    - '1. Canto de Entrada\\n(De pe)'         → linha seguinte
    - '6. Primeira Leitura (At 1,1-11) (Sentados)' → mesma linha com referencia
    """
    contexto = " ".join(linhas_bloco[:janela])
    match = re.search(r"\(([^)]+)\)", contexto)
    while match:
        candidato = match.group(1).strip().lower()
        if candidato in POSTURAS:
            return POSTURAS[candidato]
        contexto = contexto[match.end():]
        match = re.search(r"\(([^)]+)\)", contexto)
    return None


def remover_marcacao_postura(texto: str) -> str:
    """
    Remove a marcacao de postura do texto, para que nao vaze na UI.
    Nao toca em referencias biblicas tipo (At 1,11).
    """
    return re.sub(
        r"\s*\((?:De p[ée]|De p[ée]|Sentados?|Ajoelhados?)\)\s*",
        " ",
        texto,
        flags=re.IGNORECASE,
    ).strip()


def _extrair_referencia(texto: str) -> tuple[str, Optional[str]]:
    m = re.search(r"\(([A-Z][a-záéíóú]+[\s\d,;.-]+)\)", texto)
    if m:
        ref = m.group(1).strip()
        texto = texto.replace(m.group(0), "").strip()
        return texto, ref
    return texto, None


def _extrair_versiculos(texto: str) -> list:
    """Extrai versículos numerados do texto (ex: '1No meu primeiro' -> numero=1, texto='No meu primeiro')."""
    versiculos = []
    partes = re.split(r"(\d+)", texto)
    i = 0
    while i < len(partes):
        if partes[i].isdigit():
            num = int(partes[i])
            i += 1
            conteudo = ""
            while i < len(partes) and not partes[i].isdigit():
                conteudo += partes[i]
                i += 1
            conteudo = re.sub(r"^[\.\s]+", "", conteudo).strip()
            if conteudo:
                versiculos.append({"numero": num, "texto": conteudo})
        else:
            i += 1
    return versiculos


def extrair_creditos(texto: str) -> dict:
    match = re.search(r"Entrada:\s*(.+?)(?=\n\n|Ritos Iniciais|\Z)", texto, re.DOTALL)
    if not match:
        return {}
    bloco = match.group(0).replace("\n", " ")
    bloco = re.sub(r"\s+", " ", bloco).strip().rstrip(".")
    creditos = {}
    for parte in bloco.split(";"):
        if ":" not in parte:
            continue
        chave, valor = parte.split(":", 1)
        chave = chave.strip().lower()
        valor = valor.strip()
        mapa = {"entrada": "entrada", "ofertas": "ofertas", "comunhão": "comunhao", "final": "final"}
        if chave in mapa:
            creditos[mapa[chave]] = valor
    return creditos


def estruturar(texto_limpo: str) -> Missa:
    linhas = [l.strip() for l in texto_limpo.split("\n") if l.strip()]
    blocos = []

    c = extrair_creditos(texto_limpo)
    creditos = Creditos(entrada=c.get("entrada"), ofertas=c.get("ofertas"),
                         comunhao=c.get("comunhao"), final=c.get("final"))

    palavra_do_dia = PalavraDoDia(
        texto="Eis que estou convosco todos os dias, até o fim do mundo.",
        referencia="Mt 28,20",
    )

    ordem = 0
    i = 0
    while i < len(linhas):
        linha = linhas[i]
        linha_lower = linha.lower()

        skip = any(p in linha for p in ["Versão Celular", "Folheto Oficial", "Produção:", "Vicariato",
                      "Editora", "Rua Benjamin", "Portal da", "Do Rio de Janeiro", "COM APROVAÇÃO",
                      "LEITURAS DA SEMANA", "Cantos selecionados", "Publicação", "www.arqrio",
                      "AA nnoo", "Ano A", "-", "Ritos Iniciais", "Liturgia da Palavra",
                      "Liturgia Eucarística", "Ritos Finais", "60 o Dia Mundial", "60o Dia Mundial"])
        if skip or linha in ("Ascensão do Senhor", "Solenidade", "Comunicações Sociais", "Ano Jubilar"):
            i += 1
            continue
        if any(p in linha for p in ["Entrada:", "Ofertas:", "Comunhão:", "Final:", "Neste Domingo"]):
            i += 1
            continue

        # Primeira Leitura / Segunda Leitura
        if any(p in linha_lower for p in ["primeira leitura", "segunda leitura"]):
            ordem += 1
            titulo = linha
            _, ref = _extrair_referencia(linha)
            postura = "sentado"
            i += 1
            if i < len(linhas) and re.match(r"^\([A-Z]", linhas[i]):
                _, ref2 = _extrair_referencia(linhas[i])
                if ref2: ref = ref2
                i += 1
            todas = []
            while i < len(linhas):
                pl = linhas[i].lower()
                if any(p in pl for p in ["salmo responsorial", "aclamação ao evangelho",
                        "aclamacao ao evangelho", "evangelho", "homilia",
                        "profissão de fé", "profissao de fe",
                        "segunda leitura"]):
                    break
                todas.append(linhas[i])
                i += 1
            introducao = ""
            resposta = ""
            conclusao = ""
            texto_completo = " ".join(todas)

            # Extrai introducao (primeira linha com a fonte, ex: "Leitura dos Atos dos Apóstolos")
            primeira_linha = todas[0].strip() if todas else ""
            if primeira_linha and not primeira_linha[0].isdigit() and not primeira_linha.startswith("("):
                introducao = primeira_linha
                texto_sem_intro = " ".join(todas[1:])
            else:
                texto_sem_intro = texto_completo

            # Busca conclusao + resposta no texto restante
            # "Palavra do Senhor" pode estar em uma ou duas linhas (ex: "...Palavra do\nSenhor.")
            texto_plano = re.sub(r"\s+", " ", texto_sem_intro)
            m_concl = re.search(r"(Palavra\s+(?:do|da)\s+[\wÀ-ú]+)\s*\.?", texto_plano)
            if m_concl:
                conclusao = m_concl.group(1) + "."
                # Tudo antes da conclusao sao os versiculos
                texto_versiculos = texto_plano[:texto_plano.find(m_concl.group(0))].strip()
                # Depois da conclusao, busca a resposta
                depois = texto_plano[texto_plano.find(m_concl.group(0)) + len(m_concl.group(0)):]
                m_resp = re.search(r"T\.\s*([^.]+\.)", depois)
                if m_resp:
                    resposta = m_resp.group(1).strip()
                else:
                    m_resp2 = re.search(r"(Graças\s+a\s+Deus[^.]*\.)", depois, re.IGNORECASE)
                    if m_resp2:
                        resposta = m_resp2.group(1)
            else:
                texto_versiculos = texto_sem_intro

            texto = texto_versiculos
            versiculos = _extrair_versiculos(texto)
            if not versiculos:
                versiculos = []
            cat = "primeira_leitura" if "primeira" in linha_lower else "segunda_leitura"
            blocos.append(Leitura(ordem=ordem, categoria=cat, titulo=re.sub(r"^\d+\.\s*", "", titulo).strip(),
                                   referencia=ref or "", postura=postura, introducao=introducao,
                                   versiculos=versiculos,
                                   conclusao=conclusao or None, resposta=resposta or None))
            continue

        # Canto de Entrada
        if "canto de entrada" in linha_lower:
            ordem += 1
            refrao = []
            estrofes = []
            blocos_linhas = [linha]
            i += 1
            while i < len(linhas):
                prox = linhas[i]
                pl = prox.lower()
                if any(p in pl for p in ["saudação", "saudacao", "ato penitencial", "hino de louvor",
                        "glória", "coleta", "primeira leitura", "antífona da entrada",
                        "salmo responsorial", "aclamação ao evangelho", "evangelho",
                        "homilia", "canto das ofertas", "ofertório", "convite à oração",
                        "oração eucarística", "rito da comunhão", "pai nosso",
                        "cordeiro de deus", "canto de comunhão", "depois da comunhão",
                        "vivência", "bênção final", "bencao final"]):
                    break
                blocos_linhas.append(prox)
                if prox.strip() in ("1.", "2.", "3.", "4.", "5."):
                    i += 1
                    continue
                if "refrão" in pl or "refrao" in pl or prox.startswith("R."):
                    texto_ref = re.sub(r"^\s*(?:REFRÃO|REFRAO|R\.)\s*:?\s*", "", prox, flags=re.IGNORECASE).strip()
                    if texto_ref:
                        refrao = [v.strip() for v in re.split(r"\s*/\s*", texto_ref) if v.strip()]
                    i += 1
                    continue
                if re.match(r"^\d+\.\s", prox):
                    sem_num = re.sub(r"^\d+\.\s*", "", prox).strip()
                    if sem_num:
                        estrofes.append(_parse_estrofe(sem_num))
                else:
                    if estrofes:
                        novos = [v.strip() for v in re.split(r"\s*/\s*", prox) if v.strip()]
                        # Se a linha anterior era numerada, o primeiro verso continua
                        if novos and not prox.strip().startswith("/") and len(estrofes[-1]) >= 1:
                            estrofes[-1][-1] = estrofes[-1][-1] + " " + novos[0]
                            estrofes[-1] += novos[1:]
                        else:
                            estrofes[-1] += novos
                    elif refrao:
                        refrao += [v.strip() for v in re.split(r"\s*/\s*", prox) if v.strip()]
                i += 1
            postura = extrair_postura(blocos_linhas) or "de_pe"
            blocos.append(Canto(ordem=ordem, titulo="Canto de Entrada", postura=postura,
                                 refrao=refrao, estrofes=estrofes))
            continue

        # Antífona da Entrada
        if "antífona da entrada" in linha_lower or "antifona da entrada" in linha_lower:
            ordem += 1
            referencia = None
            texto_ant = ""
            i += 1
            # Verifica se a próxima linha é uma referência entre parênteses
            if i < len(linhas) and re.match(r"^\([A-Z]", linhas[i]):
                ref_match = re.search(r"\(([^)]+)\)", linhas[i])
                if ref_match:
                    referencia = ref_match.group(1).strip()
                i += 1
            while i < len(linhas):
                prox = linhas[i]
                pl = prox.lower()
                if any(p in pl for p in ["ato penitencial", "saudação", "saudacao", "coleta",
                        "primeira leitura", "salmo responsorial", "evangelho", "homilia",
                        "profissão de fé", "profissao de fe"]):
                    break
                texto_ant += " " + prox
                i += 1
            texto_ant = re.sub(r"\s+", " ", texto_ant).strip()
            texto_ant = re.sub(r"^\s*\([^)]+\)\s*", "", texto_ant)
            blocos.append(Antifona(ordem=ordem, titulo="Antífona da Entrada",
                                    referencia=referencia, texto=texto_ant))
            continue

        # Ato Penitencial
        if "ato penitencial" in linha_lower:
            ordem += 1
            turnos = []
            i += 1
            while i < len(linhas):
                prox = linhas[i]
                pl = prox.lower()
                if any(p in pl for p in ["hino de louvor", "glória", "coleta", "primeira leitura"]):
                    break
                if prox.startswith("(") and prox.endswith(")"):
                    turnos.append({"falante": "rubrica", "texto": prox.strip("()")})
                    i += 1
                    continue
                falante = re.match(r"^([PTLVR])\.\s*(.*)", prox)
                if falante:
                    turnos.append({"falante": falante.group(1), "texto": falante.group(2).strip()})
                elif turnos:
                    turnos[-1]["texto"] += " " + prox
                i += 1
            blocos.append(Dialogo(ordem=ordem, titulo="Ato Penitencial", postura=None,
                                   turnos=[Turno(**t) for t in turnos]))
            continue

        # Saudação
        if "saudação" in linha_lower or "saudacao" in linha_lower:
            ordem += 1
            turnos = []
            i += 1
            while i < len(linhas):
                prox = linhas[i]
                pl = prox.lower()
                if any(p in pl for p in ["ato penitencial", "antífona da entrada",
                        "hino de louvor", "glória", "coleta", "primeira leitura",
                        "salmo responsorial", "aclamação ao evangelho", "evangelho",
                        "homilia", "profissão de fé", "canto das ofertas",
                        "ofertório", "convite à oração",
                        "oração eucarística", "rito da comunhão", "pai nosso",
                        "cordeiro de deus", "canto de comunhão",
                        "depois da comunhão", "vivência", "bênção final"]):
                    break
                falante = re.match(r"^([PTLVR])\.\s*(.*)", prox)
                if falante:
                    turnos.append({"falante": falante.group(1), "texto": falante.group(2).strip()})
                elif turnos:
                    turnos[-1]["texto"] += " " + prox
                i += 1
            blocos.append(Dialogo(ordem=ordem, titulo="Saudação", postura="de_pe",
                                   turnos=[Turno(**t) for t in turnos]))
            continue

        i += 1

    if not blocos:
        blocos.append(Canto(ordem=1, titulo="Canto de Entrada", postura="de_pe",
                            refrao=[], estrofes=[]))

    return Missa(
        data="2026-05-17",
        ano_liturgico="A",
        titulo_celebracao="Ascensão do Senhor",
        categoria="Solenidade",
        observacoes="60º Dia Mundial das Comunicações Sociais. Ano Jubilar Arquidiocesano.",
        creditos_cantos=creditos,
        palavra_do_dia=palavra_do_dia,
        blocos=blocos,
    )


def _parse_estrofe(bloco: str) -> list[str]:
    blob = re.sub(r"\s*\n\s*", " ", bloco)
    blob = re.sub(r"\s+", " ", blob).strip()
    blob = re.sub(r"\s*/\s*$", "", blob)
    return [v.strip() for v in re.split(r"\s+/\s+", blob) if v.strip()]
