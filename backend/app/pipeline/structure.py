from __future__ import annotations

import re
from typing import Optional

from app.schema.missa import (
    Missa, Canto, Leitura, Salmo, Aclamacao, Antifona, Oracao, Dialogo, Turno,
    Secao, Creditos, PalavraDoDia, Versiculo,
)


POSTURAS = {
    "de pé": "de_pe", "de pe": "de_pe",
    "sentado": "sentado", "sentados": "sentado",
    "ajoelhado": "ajoelhado", "ajoelhados": "ajoelhado",
}

# Posturas litúrgicas corretas por título do bloco (fallback quando o PDF não explicita)
POSTURAS_POR_TITULO: dict[str, str] = {
    "canto de entrada": "de_pe",
    "antífona da entrada": "de_pe",
    "antifona da entrada": "de_pe",
    "ato penitencial": "de_pe",
    "hino de louvor": "de_pe",
    "glória": "de_pe",
    "gloria": "de_pe",
    "coleta": "de_pe",
    "primeira leitura": "sentado",
    "salmo responsorial": "sentado",
    "segunda leitura": "sentado",
    "aclamação ao evangelho": "de_pe",
    "aclamacao ao evangelho": "de_pe",
    "evangelho": "de_pe",
    "homilia": "sentado",
    "profissão de fé": "de_pe",
    "profissao de fe": "de_pe",
    "oração dos fiéis": "de_pe",
    "oracao dos fieis": "de_pe",
    "canto das ofertas": "sentado",
    "preparação das ofertas": "sentado",
    "preparacao das ofertas": "sentado",
    "convite à oração": "de_pe",
    "convite a oracao": "de_pe",
    "sobre as oferendas": "de_pe",
    "oração eucarística": "de_pe",
    "oracao eucaristica": "de_pe",
    "rito da comunhão": "de_pe",
    "rito da comunhao": "de_pe",
    "pai nosso": "de_pe",
    "cordeiro de deus": "de_pe",
    "canto de comunhão": "de_pe",
    "canto de comunhao": "de_pe",
    "depois da comunhão": "de_pe",
    "depois da comunhao": "de_pe",
    "vivência": "de_pe",
    "vivencia": "de_pe",
    "bênção final": "de_pe",
    "bencao final": "de_pe",
}

def postura_por_titulo(titulo: str) -> Optional[str]:
    chave = titulo.lower().strip()
    if chave in POSTURAS_POR_TITULO:
        return POSTURAS_POR_TITULO[chave]
    return None


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


MESES = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
}

# Categorias litúrgicas reconhecidas (devem aparecer logo após o título)
CATEGORIAS_VALIDAS = {
    "solenidade", "festa", "memória", "memoria", "memória obrigatória",
    "memória facultativa", "domingo", "tempo comum", "advento", "natal",
    "quaresma", "páscoa", "pascoa", "tríduo pascal", "triduo pascal",
}


def extrair_metadados(texto_limpo: str) -> dict:
    """Extrai data, ano_liturgico, titulo_celebracao, categoria e observacoes do cabeçalho do PDF.

    Padrão esperado (folheto Arquidiocese RJ):
        Ano A – no 34 – 17 de maio de 2026
        Ascensão do Senhor
        Solenidade
        [observações opcionais]
    """
    linhas = [l.strip() for l in texto_limpo.split("\n") if l.strip()]
    meta: dict = {
        "data": None, "ano_liturgico": "A", "titulo_celebracao": "Missa do Dia",
        "categoria": "Missa", "observacoes": None,
    }

    # Acha a linha de cabeçalho "Ano X – no Y – DIA de MÊS de ANO"
    cabecalho_re = re.compile(
        r"Ano\s+([A-C])\s*[–\-]\s*n?o?\.?\s*\d+\s*[–\-]\s*"
        r"(\d{1,2})\s+de\s+([a-zçãé]+)\s+de\s+(\d{4})",
        re.IGNORECASE,
    )
    idx_cab = None
    for idx, linha in enumerate(linhas):
        m = cabecalho_re.search(linha)
        if m:
            ano_lit, dia, mes_nome, ano = m.groups()
            mes = MESES.get(mes_nome.lower())
            if mes:
                meta["ano_liturgico"] = ano_lit.upper()
                meta["data"] = f"{ano}-{mes:02d}-{int(dia):02d}"
                idx_cab = idx
                break

    if idx_cab is not None:
        # Título: primeira linha após o cabeçalho que não seja outro cabeçalho duplicado
        observacoes_linhas: list[str] = []
        titulo_encontrado = False
        for prox in linhas[idx_cab + 1:idx_cab + 8]:
            if cabecalho_re.search(prox):
                continue
            if not titulo_encontrado:
                meta["titulo_celebracao"] = prox
                titulo_encontrado = True
                continue
            # Próxima linha após o título é a categoria (se for válida)
            if prox.lower().strip() in CATEGORIAS_VALIDAS:
                meta["categoria"] = prox
                continue
            # Demais linhas até "Neste " / "Entrada:" / "Ritos" viram observação
            if prox.lower().startswith(("neste ", "entrada:", "ritos ", "liturgia ")):
                break
            observacoes_linhas.append(prox)
        if observacoes_linhas:
            meta["observacoes"] = " ".join(observacoes_linhas)

    return meta


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
    descricao = ""
    _blocos_vistos: set = set()
    i = 0
    while i < len(linhas):
        linha = linhas[i]
        linha_lower = linha.lower()

        # Captura descricao ANTES de qualquer skip
        if not descricao and re.match(r"^Neste\s+(Domingo|Sábado|sábado|dia)", linha, re.IGNORECASE):
            descricao = linha
            i += 1
            _stop_re = re.compile(
                r"^(Ritos\s+Iniciais|Liturgia\s+da|Liturgia\s+Eucar|Entrada:|"
                r"Ano\s+[A-C]\s*[–\-]|\d+\.\s*[A-Z])"
            )
            while i < len(linhas) and not _stop_re.match(linhas[i]):
                descricao += " " + linhas[i]
                i += 1
            descricao = re.sub(r"\s+", " ", descricao).strip()
            continue

        # Detecta seções (Ritos Iniciais / Liturgia da Palavra / Liturgia Eucarística / Ritos Finais)
        secao_re = re.match(
            r"^(Ritos\s+Iniciais|Liturgia\s+da\s+Palavra|Liturgia\s+Eucar[ií]stica|Ritos\s+Finais)\s*$",
            linha, re.IGNORECASE,
        )
        if secao_re:
            ordem += 1
            secao_titulo = secao_re.group(1).strip()
            # Captura uma linha L. opcional logo após o título da seção
            descricao_secao = None
            if i + 1 < len(linhas):
                prox = linhas[i + 1]
                m_l = re.match(r"^L\.\s*(.+)", prox)
                if m_l:
                    descricao_secao = m_l.group(1).strip()
                    i += 1  # Consome a linha L.
            blocos.append(Secao(ordem=ordem, titulo=secao_titulo, descricao=descricao_secao))
            i += 1
            continue

        skip = any(p in linha for p in ["Versão Celular", "Folheto Oficial", "Produção:", "Vicariato",
                      "Editora", "Rua Benjamin", "Portal da", "Do Rio de Janeiro", "COM APROVAÇÃO",
                      "LEITURAS DA SEMANA", "Cantos selecionados", "Publicação", "www.arqrio",
                      "AA nnoo", "Ano A", "-", "60 o Dia Mundial", "60o Dia Mundial"])
        if skip or linha in ("Ascensão do Senhor", "Solenidade", "Comunicações Sociais", "Ano Jubilar"):
            i += 1
            continue
        if any(p in linha for p in ["Entrada:", "Ofertas:", "Comunhão:", "Final:"]):
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
            ultimo_terminou_barra = False
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
                        refrao = [" ".join(v.strip() for v in re.split(r"\s*/\s*", texto_ref) if v.strip())]
                    i += 1
                    continue
                if re.match(r"^\d+\.\s", prox):
                    ultimo_terminou_barra = prox.rstrip().endswith("/")
                    sem_num = re.sub(r"^\d+\.\s*", "", prox).strip()
                    if sem_num:
                        estrofes.append(_parse_estrofe(sem_num))
                else:
                    if estrofes:
                        novos = [v.strip() for v in re.split(r"\s*/\s*", prox) if v.strip()]
                        if novos and ultimo_terminou_barra:
                            estrofes[-1] += novos
                        elif novos and not prox.strip().startswith("/") and len(estrofes[-1]) >= 1:
                            estrofes[-1][-1] = estrofes[-1][-1] + " " + novos[0]
                            estrofes[-1] += novos[1:]
                        else:
                            estrofes[-1] += novos
                        ultimo_terminou_barra = prox.rstrip().endswith("/")
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
                                    referencia=referencia, texto=texto_ant, postura="de_pe"))
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
            blocos.append(Dialogo(ordem=ordem, titulo="Ato Penitencial", postura="de_pe",
                                   turnos=[Turno(**t) for t in turnos]))
            continue

        # Saudação
        if "saudação" in linha_lower or "saudacao" in linha_lower:
            ordem += 1
            turnos = []
            blocos_linhas = [linha]
            i += 1
            while i < len(linhas):
                prox = linhas[i]
                blocos_linhas.append(prox)
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
            postura_saudacao = extrair_postura(blocos_linhas) or "de_pe"
            blocos.append(Dialogo(ordem=ordem, titulo="Saudação", postura=postura_saudacao,
                                   turnos=[Turno(**t) for t in turnos]))
            continue

        # Antífona da Comunhão (aparece entre blocos numerados)
        if "antífona da comunh" in linha_lower or "antifona da comunh" in linha_lower:
            ordem += 1
            referencia_ant = None
            texto_ant = ""
            i += 1
            if i < len(linhas) and re.match(r"^\([A-Z]", linhas[i]):
                ref_m = re.search(r"\(([^)]+)\)", linhas[i])
                if ref_m:
                    referencia_ant = ref_m.group(1).strip()
                i += 1
            while i < len(linhas):
                prox = linhas[i]
                if re.match(r"^\d+\.\s", prox) or "ritos finais" in prox.lower():
                    break
                texto_ant += " " + prox
                i += 1
            texto_ant = re.sub(r"\s+", " ", texto_ant).strip()
            blocos.append(Antifona(ordem=ordem, titulo="Antífona da Comunhão",
                                    referencia=referencia_ant, texto=texto_ant, postura=None))
            continue

        # Antífona Mariana (vem após Bênção Final, conteúdo em latim)
        if linha_lower.strip() == "antífona mariana" or linha_lower.strip() == "antifona mariana":
            ordem += 1
            texto_mar = ""
            i += 1
            while i < len(linhas):
                prox = linhas[i]
                pl = prox.lower()
                # Para no rodapé editorial / leituras da semana
                if any(p in pl for p in ["leituras da semana", "editora", "portal da", "publicação",
                        "publicacao", "rua benjamin"]):
                    break
                texto_mar += " " + prox
                i += 1
            texto_mar = re.sub(r"\s+", " ", texto_mar).strip()
            # Preserva as barras `/` como separadores de verso, normalizando espaços ao redor
            texto_mar = re.sub(r"\s*/\s*", " / ", texto_mar).strip()
            if texto_mar:
                blocos.append(Antifona(ordem=ordem, titulo="Antífona Mariana",
                                        referencia=None, texto=texto_mar, postura=None))
            continue

        # Generic numbered block fallback — catch remaining blocks
        m_num = re.match(r"^(\d+)\.\s+(.+)", linha)
        if m_num:
            bloco_num = int(m_num.group(1))
            if 4 <= bloco_num <= 22 and bloco_num not in _blocos_vistos:
                _blocos_vistos.add(bloco_num)
                ordem += 1
                titulo_gen = m_num.group(2).strip()
                # Extrai referência do título (ex: "Salmo Responsorial [Sl 46(47),2-3.6-7.8-9 (R. 6)]")
                ref_titulo = None
                m_ref = re.search(r"[\[\(]([^\]\)]*(?:Sl|Mt|Mc|Lc|Jo|At|Rm|Cor|Gl|Ef|Fl|Cl|Ts|Tm|Tt|Fm|Hb|Tg|Pd|Jd|Ap)[^\]\)]*)[\]\)]", titulo_gen)
                if m_ref:
                    ref_titulo = m_ref.group(1).strip()
                    titulo_gen = re.sub(r"\s*[\[\(][^\]\)]*[\]\)]\s*", "", titulo_gen).strip()
                titulo_gen_clean = re.sub(r"\s*\([^)]+\)\s*", " ", titulo_gen).strip()
                texto_lines_gen: list[str] = []
                blocos_linhas_gen = [linha]
                i += 1
                while i < len(linhas):
                    prox = linhas[i]
                    blocos_linhas_gen.append(prox)
                    pm = re.match(r"^(\d+)\.\s", prox)
                    if pm and int(pm.group(1)) >= 4 and int(pm.group(1)) not in _blocos_vistos:
                        break
                    # Interrompe ao encontrar um marcador de seção ou bloco especial
                    if re.match(
                        r"^(Ritos\s+Iniciais|Liturgia\s+da\s+Palavra|Liturgia\s+Eucar[ií]stica|Ritos\s+Finais)\s*$",
                        prox, re.IGNORECASE,
                    ):
                        break
                    if any(p in prox.lower() for p in ["antífona da comunh", "antifona da comunh",
                            "antífona mariana", "antifona mariana"]):
                        break
                    texto_lines_gen.append(prox)
                    i += 1
                postura_gen = extrair_postura(blocos_linhas_gen) or postura_por_titulo(titulo_gen_clean) or None

                # Tenta detectar diálogo P/T no conteúdo
                turnos = _extrair_turnos(texto_lines_gen)
                # Se a 1ª rubrica é uma referência bíblica solta, promove pro campo referencia
                ref_rubrica = None
                if turnos and turnos[0]["falante"] == "rubrica":
                    candidato = turnos[0]["texto"].strip()
                    if re.match(
                        r"^[\(\[]?\s*(Sl|Mt|Mc|Lc|Jo|At|Rm|Cor|Gl|Ef|Fl|Cl|Ts|Tm|Tt|Fm|Hb|Tg|Pd|Jd|Ap)\b[^A-Za-z]*$",
                        candidato,
                    ):
                        ref_rubrica = candidato.strip("()[] ")
                        turnos = turnos[1:]
                if turnos and any(t["falante"] in ("P", "T") for t in turnos):
                    # Captura subtítulos: linhas antes do primeiro turno P/T/L/V/R
                    subtitulo_lines: list[str] = []
                    for lin in texto_lines_gen:
                        s = lin.strip()
                        if re.match(r"^[PTLVR]\.\s", s) or s.startswith("("):
                            break
                        if s:
                            subtitulo_lines.append(s)
                    subtitulo = " — ".join(subtitulo_lines) if subtitulo_lines else None
                    if subtitulo:
                        # Limpa barras separadoras
                        subtitulo = re.sub(r"\s*/\s*", " ", subtitulo).strip()
                    blocos.append(Dialogo(
                        ordem=ordem, titulo=titulo_gen_clean, postura=postura_gen,
                        subtitulo=subtitulo,
                        referencia=ref_titulo or ref_rubrica,
                        turnos=[Turno(**t) for t in turnos],
                    ))
                    continue

                texto_gen = " ".join(texto_lines_gen)
                texto_gen = re.sub(r"\s+", " ", texto_gen).strip()
                texto_gen = re.sub(r"\s*/\s*$", "", texto_gen)
                texto_gen = re.sub(r"^\s*/\s*", "", texto_gen)
                texto_gen = texto_gen.replace(" / ", " ")
                texto_gen = re.sub(r"\s*\((?:De p[ée]|Sentados?|Ajoelhados?)\)\s*", " ", texto_gen, flags=re.IGNORECASE).strip()

                # Extrai referência bíblica do início do texto.
                # Ex.: "[Sl 46(47),2-3.6-7.8-9 (R. 6)] REFRÃO: ..." → referencia=Sl 46(47),2-3.6-7.8-9 (R. 6)
                # Tenta colchetes primeiro (suporta (47) interno), depois parênteses sem nesting.
                ref_corpo = None
                m_corpo = re.match(r"^\s*\[([^\]]+)\]\s*", texto_gen)
                if not m_corpo:
                    m_corpo = re.match(r"^\s*\(([^()]+)\)\s*", texto_gen)
                if m_corpo and re.search(
                    r"\b(Sl|Mt|Mc|Lc|Jo|At|Rm|Cor|Gl|Ef|Fl|Cl|Ts|Tm|Tt|Fm|Hb|Tg|Pd|Jd|Ap)\b",
                    m_corpo.group(1),
                ):
                    ref_corpo = m_corpo.group(1).strip()
                    texto_gen = texto_gen[m_corpo.end():].strip()

                # Se o conteúdo tem REFRÃO: + estrofes numeradas, vira Canto (mesmo render do Canto de Entrada).
                canto_parsed = _tentar_extrair_canto(texto_gen)
                if canto_parsed:
                    refrao_p, estrofes_p = canto_parsed
                    blocos.append(Canto(
                        ordem=ordem, titulo=titulo_gen_clean, postura=postura_gen,
                        refrao=refrao_p, estrofes=estrofes_p,
                        referencia=ref_titulo or ref_corpo,
                    ))
                    continue

                blocos.append(Oracao(ordem=ordem, titulo=titulo_gen_clean,
                                      texto=texto_gen, postura=postura_gen,
                                      referencia=ref_titulo or ref_corpo))
                continue

        i += 1

    if not blocos:
        blocos.append(Canto(ordem=1, titulo="Canto de Entrada", postura="de_pe",
                            refrao=[], estrofes=[]))

    meta = extrair_metadados(texto_limpo)
    from datetime import date as _date
    data_iso = meta["data"] or _date.today().isoformat()

    return Missa(
        data=data_iso,
        ano_liturgico=meta["ano_liturgico"],
        titulo_celebracao=meta["titulo_celebracao"],
        categoria=meta["categoria"],
        descricao=descricao or None,
        observacoes=meta["observacoes"],
        creditos_cantos=creditos,
        palavra_do_dia=palavra_do_dia,
        blocos=blocos,
    )


def _tentar_extrair_canto(texto: str) -> Optional[tuple[list[str], list[list[str]]]]:
    """Detecta conteúdo de canto/salmo: REFRÃO opcional + estrofes numeradas opcionais.

    Funciona com separadores `/` (cânticos da Arquidiocese) ou `*` (salmos).
    Retorna (refrao, estrofes) se ao menos um dos dois for detectado.
    """
    tem_refrao = re.search(r"REFR[ÃA]O\s*:", texto, re.IGNORECASE)
    tem_estrofes_num = re.search(r"\b1\s*\.\s+\w", texto)
    if not tem_refrao and not tem_estrofes_num:
        return None

    refrao: list[str] = []
    resto = texto

    if tem_refrao:
        # Refrão vai até o primeiro "1." (estrofe) ou fim do texto.
        m_refrao = re.search(
            r"REFR[ÃA]O\s*:\s*(.+?)(?=\s*\b1\s*\.\s+\w|\Z)",
            texto, re.IGNORECASE | re.DOTALL,
        )
        if m_refrao:
            refrao_txt = m_refrao.group(1).strip()
            refrao_txt = re.sub(r"\s*\*\s*", " / ", refrao_txt)
            refrao = [" ".join(v.strip() for v in re.split(r"\s*/\s*", refrao_txt) if v.strip())]
            resto = texto[m_refrao.end():]

    # Estrofes numeradas
    estrofes: list[list[str]] = []
    for m in re.finditer(r"(\d+)\.\s+(.+?)(?=\s+\d+\.\s|\Z)", resto, re.DOTALL):
        bloco = m.group(2).strip()
        bloco = re.sub(r"\s*\*\s*", " / ", bloco)
        bloco = re.sub(r"\s+", " ", bloco)
        versos = [v.strip() for v in re.split(r"\s*/\s*", bloco) if v.strip()]
        if versos:
            estrofes.append(versos)

    # Se sobrou um "L. ..." (leitor, padrão da Aclamação) sem estrofes, capta como única estrofe.
    if not estrofes and refrao:
        m_l = re.search(r"L\.\s*(.+?)\Z", resto.strip(), re.DOTALL)
        if m_l:
            verso_l = re.sub(r"\s+", " ", m_l.group(1)).strip()
            verso_l = re.sub(r"\s*\*\s*", " / ", verso_l)
            versos = [v.strip() for v in re.split(r"\s*/\s*", verso_l) if v.strip()]
            if versos:
                estrofes.append(versos)

    if not refrao and not estrofes:
        return None
    return refrao, estrofes


def _extrair_turnos(linhas: list[str]) -> list[dict]:
    """Detecta turnos de fala P/T/L/V/R no padrão 'P. texto' ou 'T. texto'.

    Linhas que começam com `(...)` viram rubricas. Linhas sem prefixo de falante
    são concatenadas ao último turno detectado. Limpa barras separadoras
    de versos (`/`) que vêm do layout em colunas do PDF.
    """
    turnos: list[dict] = []
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        # Rubricas em parênteses (Momento de silêncio, etc.)
        if linha.startswith("(") and linha.endswith(")"):
            turnos.append({"falante": "rubrica", "texto": linha.strip("()")})
            continue
        m = re.match(r"^([PTLVR])\.\s*(.*)", linha)
        if m:
            turnos.append({"falante": m.group(1), "texto": m.group(2).strip()})
        elif turnos:
            turnos[-1]["texto"] = (turnos[-1]["texto"] + " " + linha).strip()

    # Limpa barras de quebra de coluna que vieram do PDF
    for t in turnos:
        t["texto"] = re.sub(r"\s*/\s*", " ", t["texto"]).strip()
        t["texto"] = re.sub(r"\s+", " ", t["texto"])

    # Filtra rubricas que são só marcação de postura (já temos no header)
    POSTURAS_RX = re.compile(r"^\s*(De\s+p[ée]|Sentados?|Ajoelhados?)\s*\.?$", re.IGNORECASE)
    turnos = [
        t for t in turnos
        if t["texto"] and not (t["falante"] == "rubrica" and POSTURAS_RX.match(t["texto"]))
    ]
    return turnos


def _parse_estrofe(bloco: str) -> list[str]:
    blob = re.sub(r"\s*\n\s*", " ", bloco)
    blob = re.sub(r"\s+", " ", blob).strip()
    # Remove / do inicio e fim para evitar versos vazios
    blob = re.sub(r"^\s*/\s*", "", blob)
    blob = re.sub(r"\s*/\s*$", "", blob)
    # Separa por / com espacos, preservando versos
    return [v.strip() for v in re.split(r"\s*/\s*", blob) if v.strip()]
