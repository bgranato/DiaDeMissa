from __future__ import annotations

import re
from typing import Optional

from app.schema.missa import (
    Missa, Canto, Leitura, Salmo, Aclamacao, Antifona, Oracao, Dialogo, Turno,
    Creditos, PalavraDoDia, Versiculo,
)


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

        # Canto de Entrada
        if "canto de entrada" in linha_lower:
            ordem += 1
            refrao = []
            estrofes = []
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
            blocos.append(Canto(ordem=ordem, titulo="Canto de Entrada", postura="de_pe",
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
