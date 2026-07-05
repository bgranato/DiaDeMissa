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
    """Extrai versículos numerados do texto.

    Padrões aceitos:
        '1No meu primeiro' → numero=1, texto='No meu primeiro'
        '3bNinguém pode'   → numero=3, texto='Ninguém pode'  (sub-letra 'a/b/c')

    A sub-letra (3a, 3b...) é DESCARTADA — agrupamos no número base.
    """
    versiculos = []
    # Captura "N" ou "Na" / "Nb" / etc (digit + optional sub-letter)
    partes = re.split(r"(\d+[a-z]?)", texto)
    versiculo_re = re.compile(r"^(\d+)([a-z]?)$")
    i = 0
    while i < len(partes):
        m = versiculo_re.match(partes[i])
        if m:
            num = int(m.group(1))
            i += 1
            conteudo = ""
            while i < len(partes) and not versiculo_re.match(partes[i]):
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

    # Acha a linha de cabeçalho "Ano X – no Y – DIA de MÊS de ANO".
    # O folheto repete esse cabeçalho 2x: 1ª vez no topo da página (com quebras de
    # linha agressivas do PDF), 2ª vez como cabeçalho do corpo (geralmente íntegro).
    # Preferimos a 2ª ocorrência porque o título vem completo (sem line-break partido).
    cabecalho_re = re.compile(
        r"Ano\s+([A-C])\s*[–\-]\s*n?o?\.?\s*\d+\s*[–\-]\s*"
        r"(\d{1,2})\s+de\s+([a-zçãé]+)\s+de\s+(\d{4})",
        re.IGNORECASE,
    )
    indices_cab: list[int] = []
    grupos_cab: dict | None = None
    for idx, linha in enumerate(linhas):
        m = cabecalho_re.search(linha)
        if m:
            indices_cab.append(idx)
            grupos_cab = m.groups()
    idx_cab = None
    if indices_cab and grupos_cab is not None:
        ano_lit, dia, mes_nome, ano = grupos_cab
        mes = MESES.get(mes_nome.lower())
        if mes:
            meta["ano_liturgico"] = ano_lit.upper()
            meta["data"] = f"{ano}-{mes:02d}-{int(dia):02d}"
        # Pega a 2ª ocorrência se existir (mais íntegra), senão a 1ª
        idx_cab = indices_cab[1] if len(indices_cab) >= 2 else indices_cab[0]

    # Em cada ocorrência do cabeçalho, coleta o título candidato. Depois escolhe
    # o melhor — heurística defensiva contra layouts ruins.
    # Fragmento do cabeçalho a IGNORAR (não título): "34 – 17 de maio de 2026",
    # "17 de maio de 2026", "no 34 – ...". Detecta por estar começando com dígito
    # solto (sem ordinal "º"/"ª") seguido de " – " ou " de ".
    fragmento_re = re.compile(
        r"^\d+\s*[–\-]\s*\d+|^\d+\s+de\s+[a-zçãé]+"
    )
    candidatos_titulo: list[tuple[int, str, list[str]]] = []
    for idx_cab in indices_cab:
        titulo_candidato = None
        obs_linhas: list[str] = []
        for prox in linhas[idx_cab + 1:idx_cab + 8]:
            if cabecalho_re.search(prox):
                continue
            if titulo_candidato is None:
                if not prox or fragmento_re.match(prox):
                    continue  # pula fragmento de cabeçalho quebrado
                if len(prox) < 6:
                    continue  # muito curto pra ser título ("Comum" sozinho)
                titulo_candidato = prox
                continue
            if prox.lower().strip() in CATEGORIAS_VALIDAS:
                if not meta.get("categoria") or meta["categoria"] == "Missa":
                    meta["categoria"] = prox
                continue
            if prox.lower().startswith(("neste ", "entrada:", "ritos ", "liturgia ")):
                break
            obs_linhas.append(prox)
        if titulo_candidato:
            candidatos_titulo.append((idx_cab, titulo_candidato, obs_linhas))

    if candidatos_titulo:
        # Escolhe o título mais longo (geralmente é o mais íntegro)
        idx_cab, melhor_titulo, melhor_obs = max(
            candidatos_titulo, key=lambda c: len(c[1])
        )
        meta["titulo_celebracao"] = melhor_titulo
        if melhor_obs:
            meta["observacoes"] = " ".join(melhor_obs)

    return meta


def _extrair_palavra_do_dia(texto_limpo: str) -> Optional[PalavraDoDia]:
    """Extrai a 'palavra do dia' do bloco do Evangelho.

    Estratégia:
    1. Acha o bloco do Evangelho (tipicamente "Evangelho" + referência tipo "(Mt 28,16-20)")
    2. Captura a referência
    3. Captura a primeira frase de fala de Jesus (entre aspas "" ou "”) — geralmente a citação central
    4. Se não houver fala em aspas, pega a primeira frase com mais de 60 caracteres
    5. Sem Evangelho → retorna None
    """
    m_evang = re.search(
        r"(?:^|\n)\s*\d+\.\s*Evangelho\s*\n?\s*[\(\[]([^\]\)]+)[\]\)]\s*(.+?)(?=\n\s*\d+\.\s|\nHomilia|\Z)",
        texto_limpo,
        re.IGNORECASE | re.DOTALL,
    )
    if not m_evang:
        return None
    referencia = m_evang.group(1).strip()
    corpo = m_evang.group(2)
    # Procura uma fala entre aspas (citação direta de Jesus)
    m_aspas = re.search(r"[“\"]([^”\"]{20,800})[”\"]", corpo)
    texto = None
    if m_aspas:
        bloco_aspas = m_aspas.group(1).strip()
        # Remove numeração de versículos (ex.: "18Então", "19Portanto") para limpar
        bloco_aspas = re.sub(r"\b\d+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])", "", bloco_aspas)
        # Tira frases curtas e fica com a ÚLTIMA frase substancial (o "highlight")
        frases = [f.strip() for f in re.split(r"(?<=[.!?])\s+", bloco_aspas) if len(f.strip()) >= 30]
        if frases:
            texto = frases[-1].rstrip(".") + "."
        else:
            # Caso não dê pra dividir, usa o bloco inteiro mas trunca
            texto = (bloco_aspas[:200].rstrip(".") + ".") if len(bloco_aspas) > 200 else bloco_aspas
    else:
        # Fallback: primeira frase com mais de 60 chars
        for frase in re.split(r"(?<=[.!?])\s+", corpo):
            f = frase.strip()
            if len(f) >= 60 and not f.startswith(("P.", "T.", "L.")):
                texto = f.rstrip(".") + "."
                break
    if not texto:
        return None
    # Limpa quebras de linha e barras
    texto = re.sub(r"\s+", " ", texto).strip()
    texto = re.sub(r"\s*/\s*", " ", texto)
    return PalavraDoDia(texto=texto, referencia=referencia)


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

    # Palavra do dia: tenta extrair do bloco do Evangelho (primeira frase em destaque).
    # Fallback: None — frontend omite o card "Evangelho do Dia"
    palavra_do_dia = _extrair_palavra_do_dia(texto_limpo)

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
            # Captura linha L. opcional após o título da seção.
            # Variações observadas no PDF (depende da versão do extrator):
            #   1) "L. O coração misericordioso..."  (sigla + texto na mesma linha)
            #   2) "L."  +  "O coração misericordioso..."  (sigla isolada, texto na próxima)
            descricao_secao = None
            if i + 1 < len(linhas):
                prox = linhas[i + 1]
                m_l = re.match(r"^L\.\s*(.+)", prox)
                if m_l:
                    descricao_secao = m_l.group(1).strip()
                    i += 1  # Consome a linha L.
                elif re.match(r"^L\.\s*$", prox) and i + 2 < len(linhas):
                    seguinte = linhas[i + 2].strip()
                    # Aceita se a linha seguinte não é título numerado nem outra sigla
                    if seguinte and not re.match(r"^\d+\.\s|^[PTLVR]\.\s|^\(", seguinte):
                        descricao_secao = seguinte
                        i += 2  # Consome "L." + linha de texto
            blocos.append(Secao(ordem=ordem, titulo=secao_titulo, descricao=descricao_secao))
            i += 1
            continue

        # Marcadores especiais que viram BLOCOS estruturados próprios — pula a skip list
        # e cai na lógica de extração específica abaixo.
        eh_bloco_especial = (
            linha_lower.strip() in ("leituras da semana", "semana eucarística",
                                     "semana eucaristica")
            or linha_lower.strip().startswith("semana eucar")
            or linha_lower.startswith("rito para apagar o")
            or linha_lower.startswith("oração para o 60")
            or linha_lower.startswith("oracao para o 60")
            or linha_lower.startswith("oração para o ")
            or linha_lower.startswith("oracao para o ")
        )
        if not eh_bloco_especial:
            # NOTA: a string solta "-" foi REMOVIDA do skip — pulava todas as
            # linhas com hífen (ex: "Antífona da Comunhão (At 2,4-11)" tem
            # hífen na referência bíblica e era descartada incorretamente).
            skip = any(p in linha for p in ["Versão Celular", "Folheto Oficial", "Produção:", "Vicariato",
                          "Editora", "Rua Benjamin", "Portal da", "Do Rio de Janeiro", "COM APROVAÇÃO",
                          "Cantos selecionados", "Publicação", "www.arqrio",
                          "AA nnoo", "Ano A"])
            # Linha solitária que é só um traço/hífen (descartar). Não usa o `p in linha`
            # genérico porque hífens aparecem dentro de palavras legítimas.
            if linha.strip() in ("-", "–", "—"):
                i += 1
                continue
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
                        "segunda leitura",
                        # Sequência (canto litúrgico em Solenidades como Pentecostes,
                        # Corpus Christi, Páscoa) vem entre Segunda Leitura e Aclamação
                        "sequência", "sequencia"]):
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
            # Limpa o título: remove "N." e qualquer parêntese (referência e/ou
            # postura), que já vão para os campos `referencia`/`postura`. Sem isso,
            # um "(Sentados)" no título quebra o validador (postura como texto).
            titulo_leitura = re.sub(r"\s*\([^)]*\)\s*", " ", re.sub(r"^\d+\.\s*", "", titulo)).strip()
            blocos.append(Leitura(ordem=ordem, categoria=cat, titulo=titulo_leitura,
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

        # Leituras da Semana (rodapé do folheto, lista de referências dia a dia)
        # === Conteúdos pós-missa adicionais (apêndices) ===
        # RITO PARA APAGAR O CÍRIO PASCAL (Pentecostes, fim do Tempo Pascal)
        if (linha_lower.startswith("rito para apagar o c")
            or linha_lower.startswith("rito para apagar o círio")):
            ordem += 1
            titulo_rito = linha.strip()
            i += 1
            # Pode ter título em 2 linhas: "RITO PARA APAGAR O CÍRIO / PASCAL"
            if i < len(linhas) and linhas[i].strip().upper() == "PASCAL":
                titulo_rito += " " + linhas[i].strip()
                i += 1
            titulo_rito = re.sub(r"\s+", " ", titulo_rito).title()
            texto_rito = ""
            while i < len(linhas):
                prox = linhas[i]
                pl = prox.lower()
                if any(p in pl for p in [
                    "leituras da semana", "semana eucarística", "semana eucaristica",
                    "oração para o", "oracao para o", "antífona mariana",
                    "antifona mariana", "editora nossa senhora", "portal da",
                    "publicação da", "publicacao da", "cantos selecionados",
                ]):
                    break
                texto_rito += " " + prox
                i += 1
            texto_rito = re.sub(r"\s+", " ", texto_rito).strip()
            if texto_rito:
                blocos.append(Oracao(ordem=ordem, titulo=titulo_rito,
                                     texto=texto_rito, postura=None, referencia=None))
            continue

        # SEMANA EUCARÍSTICA (anúncio pastoral da Arquidiocese)
        if (linha_lower.strip().startswith("semana eucar")
            or linha_lower.strip() == "semana eucarística"):
            ordem += 1
            i += 1
            texto_se = ""
            while i < len(linhas):
                prox = linhas[i]
                pl = prox.lower()
                if any(p in pl for p in [
                    "leituras da semana", "rito para apagar", "oração para o",
                    "oracao para o", "antífona mariana", "antifona mariana",
                    "editora nossa senhora", "portal da",
                    "publicação da", "publicacao da", "cantos selecionados",
                ]):
                    break
                texto_se += " " + prox
                i += 1
            texto_se = re.sub(r"\s+", " ", texto_se).strip()
            if texto_se:
                blocos.append(Oracao(ordem=ordem, titulo="Semana Eucarística",
                                     texto=texto_se, postura=None, referencia=None))
            continue

        if linha_lower.strip() == "leituras da semana":
            ordem += 1
            texto_lds = ""
            i += 1
            while i < len(linhas):
                prox = linhas[i]
                pl = prox.lower()
                # Para no rodapé editorial ou nos blocos seguintes (Semana Eucarística etc.)
                if any(p in pl for p in ["editora nossa senhora", "portal da", "publicação",
                        "publicacao", "rua benjamin", "com aprovação", "com aprovacao",
                        "oração para o", "oracao para o", "cantos selecionados",
                        "ceps:", "tel.:", "www.arqrio",
                        "semana eucarística", "semana eucaristica",
                        "rito para apagar"]):
                    break
                texto_lds += " " + prox
                i += 1
            texto_lds = re.sub(r"\s+", " ", texto_lds).strip()
            if texto_lds:
                blocos.append(Oracao(ordem=ordem, titulo="Leituras da Semana",
                                     texto=texto_lds, postura=None, referencia=None))
            continue

        # Oração para o 60º Dia Mundial das Comunicações Sociais (ou similar)
        if linha_lower.startswith("oração para o ") or linha_lower.startswith("oracao para o "):
            ordem += 1
            titulo_oc = linha.strip()
            # Pode ter título quebrado em 2 linhas ("ORAÇÃO PARA O 60º DIA MUNDIAL DAS / COMUNICAÇÕES SOCIAIS")
            i += 1
            if i < len(linhas):
                prox = linhas[i].strip()
                if prox and prox.isupper() and not prox.startswith("(") and len(prox) < 80:
                    titulo_oc += " " + prox
                    i += 1
            titulo_oc = re.sub(r"\s+", " ", titulo_oc).title()  # caixa-padrão
            texto_oc = ""
            subtitulo_oc = None
            while i < len(linhas):
                prox = linhas[i]
                pl = prox.lower()
                # Para no rodapé editorial
                if any(p in pl for p in ["editora nossa senhora", "portal da", "publicação",
                        "publicacao", "rua benjamin", "com aprovação", "com aprovacao",
                        "cantos selecionados", "ceps:", "tel.:", "www.arqrio"]):
                    break
                # Linha "(Inspirada em ...)" entre parênteses vira subtítulo
                if subtitulo_oc is None and re.match(r"^\(.+\)$", prox.strip()):
                    subtitulo_oc = prox.strip("() ")
                    i += 1
                    continue
                texto_oc += " " + prox
                i += 1
            texto_oc = re.sub(r"\s+", " ", texto_oc).strip()
            # Preserva barras `/` como separadores de verso
            texto_oc = re.sub(r"\s*/\s*", " / ", texto_oc).strip()
            if texto_oc:
                blocos.append(Oracao(ordem=ordem, titulo=titulo_oc,
                                     texto=texto_oc, postura=None, referencia=subtitulo_oc))
            continue

        # Generic numbered block fallback — catch remaining blocks
        m_num = re.match(r"^(\d+)\.\s+(.+)", linha)
        if m_num:
            bloco_num = int(m_num.group(1))
            # Aceita até #30 (alguns folhetos têm Canto Final = #23, Vivência = #21
            # +-2 etc.). O limite era 22 e cortava o Canto Final. Limite superior
            # generoso (30) cobre todos os layouts vistos.
            if 4 <= bloco_num <= 30 and bloco_num not in _blocos_vistos:
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
                # Rastreia a maior estrofe vista (1, 2, 3...) pra distinguir entre:
                #   - Estrofe sequencial do canto atual ("6. Sempre que a Igreja…"
                #     continua o canto se já viu "1. ... 5. ...")
                #   - Bloco litúrgico próximo ("20. Depois da Comunhão" — pulo grande)
                ultima_estrofe = 0
                while i < len(linhas):
                    prox = linhas[i]
                    blocos_linhas_gen.append(prox)
                    pm = re.match(r"^(\d+)\.\s+(.+)", prox)
                    if pm:
                        n = int(pm.group(1))
                        titulo_prox = pm.group(2).strip()
                        # Detecta se o próximo "N." é um título litúrgico conhecido
                        # (Aclamação, Evangelho, Coleta, etc.). Se for, é bloco;
                        # senão é continuação (estrofe) — mesmo que `n > bloco_num`.
                        # Isso resolve o caso Pentecostes: Sequência (#9) tem 10
                        # estrofes; a 10ª colide com #10 Aclamação ao Evangelho.
                        eh_titulo_bloco = _eh_titulo_litur(titulo_prox)
                        # Estrofe sequencial (1..K seguida de K+1): faz parte do canto
                        eh_estrofe_seq = (n == ultima_estrofe + 1) or (n == 1 and ultima_estrofe == 0 and bloco_num >= 1)
                        # Continua estrofe se: é sequencial E (n<bloco_num OU não é título litúrgico)
                        if eh_estrofe_seq and (n < bloco_num or not eh_titulo_bloco):
                            ultima_estrofe = n
                            texto_lines_gen.append(prox)
                            i += 1
                            continue
                        # Outro bloco litúrgico próximo: para
                        if n >= 4 and n not in _blocos_vistos and n != bloco_num:
                            break
                    # Interrompe ao encontrar um marcador de seção ou bloco especial
                    if re.match(
                        r"^(Ritos\s+Iniciais|Liturgia\s+da\s+Palavra|Liturgia\s+Eucar[ií]stica|Ritos\s+Finais)\s*$",
                        prox, re.IGNORECASE,
                    ):
                        break
                    pl = prox.lower()
                    if any(p in pl for p in ["antífona da comunh", "antifona da comunh",
                            "antífona mariana", "antifona mariana"]):
                        break
                    # Apêndices e rodapé editorial — TUDO depois disso é conteúdo
                    # complementar do folheto, não pertence ao bloco litúrgico atual
                    if any(p in pl for p in [
                        "leituras da semana",
                        "oração para o ", "oracao para o ",
                        "editora nossa senhora", "portal da arquidiocese",
                        "com aprovação eclesiástica", "com aprovacao eclesiastica",
                        "publicação da comissão", "publicacao da comissao",
                        "cantos selecionados", "próximo encontro", "proximo encontro",
                        "clube vocacional", "www.arqrio", "rua benjamin",
                    ]):
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
                    refrao_p, estrofes_p, posicao_p = canto_parsed
                    blocos.append(Canto(
                        ordem=ordem, titulo=titulo_gen_clean, postura=postura_gen,
                        refrao=refrao_p, estrofes=estrofes_p,
                        posicao_refrao_apos=posicao_p,
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

    # Pós-processamento: separa preces numeradas (Oração dos Fiéis) em turnos L/T.
    # O folheto da Arquidiocese frequentemente concatena várias preces numeradas
    # ("1. Pela Igreja... 2. Pelo Papa... 3. Pelos..."  dentro de um único turno
    # T ou P, perdendo a estrutura visual L→T→L→T. Esta função reverte isso.
    blocos = _separar_preces_numeradas(blocos)

    # Pós-processamento estrutural: hierarquia explícita + numeração do folheto.
    # 1) Atribui `secao` a cada bloco (Ritos Iniciais / Liturgia da Palavra / etc.)
    #    walking forward a partir do último marcador Secao.
    # 2) Atribui `numero_folheto` (1, 2, ... 22) sequencial pra cada bloco navegável
    #    (não-seção, não-antífona-anexada, não-apêndice).
    # 3) Anexa Antífona da Entrada/Comunhão como atributo do Canto correspondente
    #    (busca por nome, não posição). Remove o bloco antífona da lista.
    # 4) Marca Leituras da Semana / Antífona Mariana / Oração do dia como secao="apendice".
    blocos = _aplicar_hierarquia_e_numeracao(blocos)

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


def _tentar_extrair_canto(texto: str) -> Optional[tuple[list[str], list[list[str]], Optional[int]]]:
    """Detecta conteúdo de canto/salmo: REFRÃO opcional + estrofes numeradas opcionais.

    Suporta as 4 formas que aparecem no folheto Arquidiocese:
      (a) REFRÃO: ... seguido por 1. ... 2. ... 3. ... (refrão antes — posicao=None)
      (b) 1. ... REFRÃO: ... 2. ... 3. ... (refrão depois da estrofe 1 — posicao=1)
      (c) Só REFRÃO ou só estrofes
      (d) REFRÃO: ... L. versículo (Aclamação ao Evangelho — posicao=None)

    Funciona com separadores `/` (cânticos da Arquidiocese) ou `*` (salmos).
    Retorna (refrao, estrofes, posicao_refrao_apos) — posicao indica depois de
    qual estrofe (1-indexed) o refrão aparece no folheto. None = antes de tudo.
    """
    tem_refrao = re.search(r"REFR[ÃA]O\s*:", texto, re.IGNORECASE)
    tem_estrofes_num = re.search(r"\b\d+\s*\.\s+\w", texto)
    if not tem_refrao and not tem_estrofes_num:
        return None

    # PASSO 1: localiza onde está o REFRÃO no texto (se houver)
    refrao: list[str] = []
    pos_refrao_inicio = -1
    pos_refrao_fim = -1
    if tem_refrao:
        # Refrão para em:
        # - qualquer próxima estrofe numerada (1./2./3.…)
        # - "L." (versículo do Leitor — Aclamação ao Evangelho)
        # - fim do texto
        m_refrao = re.search(
            r"REFR[ÃA]O\s*:\s*(.+?)(?=\s+L\.\s|\s*\b\d+\s*\.\s+\w|\Z)",
            texto, re.IGNORECASE | re.DOTALL,
        )
        if m_refrao:
            refrao_txt = m_refrao.group(1).strip()
            refrao_txt = re.sub(r"\s*\*\s*", " / ", refrao_txt)
            refrao = [" ".join(v.strip() for v in re.split(r"\s*/\s*", refrao_txt) if v.strip())]
            pos_refrao_inicio = m_refrao.start()
            pos_refrao_fim = m_refrao.end()

    # PASSO 2: captura TODAS as estrofes (antes E depois do refrão).
    # Também detecta quantas estrofes vêm antes do refrão (posicao_refrao_apos).
    estrofes: list[list[str]] = []
    estrofes_antes_refrao = 0
    for m in re.finditer(
        r"(\d+)\.\s+(.+?)(?=\s+\d+\.\s|REFR[ÃA]O\s*:|\Z)",
        texto, re.DOTALL | re.IGNORECASE,
    ):
        bloco = m.group(2).strip()
        # Se o início do bloco-estrofe está dentro do trecho do refrão, ignora
        if pos_refrao_inicio != -1 and pos_refrao_inicio < m.start() < pos_refrao_fim:
            continue
        bloco = re.sub(r"\s*\*\s*", " / ", bloco)
        bloco = re.sub(r"\s+", " ", bloco)
        versos = [v.strip() for v in re.split(r"\s*/\s*", bloco) if v.strip()]
        if versos:
            estrofes.append(versos)
            if pos_refrao_inicio != -1 and m.start() < pos_refrao_inicio:
                estrofes_antes_refrao += 1

    # Caso especial (d): Aclamação ao Evangelho — REFRÃO + L. versículo sem estrofes
    if not estrofes and refrao:
        resto_pos_refrao = texto[pos_refrao_fim:] if pos_refrao_fim > 0 else texto
        m_l = re.search(r"L\.\s*(.+?)\Z", resto_pos_refrao.strip(), re.DOTALL)
        if m_l:
            verso_l = re.sub(r"\s+", " ", m_l.group(1)).strip()
            verso_l = re.sub(r"\s*\*\s*", " / ", verso_l)
            versos = [v.strip() for v in re.split(r"\s*/\s*", verso_l) if v.strip()]
            if versos:
                estrofes.append(versos)

    if not refrao and not estrofes:
        return None
    posicao_refrao_apos = estrofes_antes_refrao if estrofes_antes_refrao > 0 else None
    return refrao, estrofes, posicao_refrao_apos


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

    # Normaliza barras separadoras de verso (`/`) mantendo a estrutura visual:
    # o folheto usa `/` pra separar versos do Hino de Louvor, Glória, hinos longos.
    # Antes removíamos como artefato de coluna; mas isso destruía a estrutura.
    # Agora normalizamos espaçamento ao redor mas preservamos o separador.
    for t in turnos:
        t["texto"] = re.sub(r"\s*/\s*", " / ", t["texto"]).strip()
        t["texto"] = re.sub(r" +", " ", t["texto"])
        # Remove `/` espúrio no início/fim do texto
        t["texto"] = re.sub(r"^/\s*|\s*/$", "", t["texto"]).strip()

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


# ============================================================================
# Pós-processamento de blocos
# ============================================================================


def _eh_oracao_dos_fieis(bloco) -> bool:
    """Detecta o bloco de Oração Universal / dos Fiéis / Preces."""
    titulo = (getattr(bloco, "titulo", "") or "").lower()
    tipo = (getattr(bloco, "tipo", "") or "").lower()
    return (
        "fiéis" in titulo or "fieis" in titulo
        or "preces" in titulo or "universal" in titulo
        or tipo == "preces_comunidade"
    )


def _detectar_refrao_preces(turnos) -> str | None:
    """Descobre o REFRÃO real da Oração dos Fiéis a partir do PRÓPRIO folheto.

    Nunca inventa: retorna None se não encontrar. O chamador, nesse caso, NÃO
    injeta o refrão genérico do Missal — precedência é folheto > fallback, e
    falha explícita é melhor que texto padrão por cima do folheto.
    """
    from collections import Counter

    _IGNORAR = {"amém.", "amem.", "amém", "amem"}

    # Caso 1: refrão já isolado — turnos T curtos e repetidos (ex.: folheto já
    # separado prece a prece).
    curtos = [
        (t.texto or "").strip()
        for t in turnos
        if t.falante == "T"
        and (t.texto or "").strip()
        and (t.texto or "").strip().lower() not in _IGNORAR
        and len((t.texto or "").strip()) <= 140
    ]
    if curtos:
        return Counter(curtos).most_common(1)[0][0]

    # Caso 2: preces agrupadas num T longo → o refrão é o texto ANTES da 1ª
    # numeração ("refrão 1. ... 2. ...").
    for t in turnos:
        if t.falante == "T" and t.texto:
            partes = re.split(r"(?=\s\d+\.\s)", t.texto.strip())
            if len(partes) > 1:
                cabeca = partes[0].strip()
                if cabeca and cabeca.lower() not in _IGNORAR and len(cabeca) <= 140:
                    return cabeca

    return None


def _separar_preces_numeradas(blocos: list) -> list:
    """Pós-processa blocos de Oração dos Fiéis pra separar preces numeradas
    ("1. ... 2. ... 3.") em turnos L (Leitor) seguidos de T (refrão).

    O folheto da Arquidiocese frequentemente agrupa várias preces dentro do
    mesmo turno T (depois do refrão PRÓPRIO do dia). Esta função reverte isso
    pra apresentação correta no app, repetindo o refrão REAL do folheto (nunca
    o genérico do Missal) após cada prece.

    Idempotente: já-separado não muda.
    """
    novos_blocos = []
    for bloco in blocos:
        if not _eh_oracao_dos_fieis(bloco):
            novos_blocos.append(bloco)
            continue

        turnos_orig = getattr(bloco, "turnos", None)
        if not turnos_orig:
            novos_blocos.append(bloco)
            continue

        # Refrão REAL do folheto (nunca o genérico). Se None, não injeta nada.
        refrao_real = _detectar_refrao_preces(turnos_orig)

        novos_turnos: list[Turno] = []

        for t in turnos_orig:
            falante = t.falante
            texto = (t.texto or "").strip()

            if falante == "rubrica" or not texto:
                novos_turnos.append(t)
                continue

            # Procura padrão "N. ..." no meio do texto (numeração de prece)
            partes = re.split(r"(?=\s\d+\.\s)", texto)
            if len(partes) <= 1:
                novos_turnos.append(t)
                continue

            # Primeira parte: mantém falante original (P intro OU T refrão)
            primeira = partes[0].strip()
            if primeira:
                novos_turnos.append(Turno(falante=falante, texto=primeira))

            # Demais partes começam com "N. ..." — cada uma é uma prece do Leitor.
            # Strip do prefixo "N. " porque o validador proíbe numeração em texto
            # (cada prece já é seu próprio turno, a ordem é a numeração).
            for parte in partes[1:]:
                p = parte.strip()
                if not p:
                    continue
                p_sem_num = re.sub(r"^\s*\d+\.\s*", "", p).strip()
                if not p_sem_num:
                    continue
                novos_turnos.append(Turno(falante="L", texto=p_sem_num))
                # Injeta o refrão REAL do folheto após cada prece.
                # PRECEDÊNCIA folheto > fallback: se não detectamos refrão no
                # folheto, NÃO inventa o genérico — deixa sem (falha explícita).
                # (duplicatas consecutivas são limpas logo abaixo)
                if refrao_real and refrao_real.lower() not in p_sem_num.lower():
                    novos_turnos.append(Turno(falante="T", texto=refrao_real))

        # Limpa duplicação de refrão consecutivo no início (pode acontecer se T do PDF já tinha)
        turnos_limpos: list[Turno] = []
        for t in novos_turnos:
            if (turnos_limpos and turnos_limpos[-1].falante == "T" and t.falante == "T"
                and turnos_limpos[-1].texto == t.texto):
                continue  # skip duplicado
            turnos_limpos.append(t)

        bloco.turnos = turnos_limpos
        novos_blocos.append(bloco)

    return novos_blocos


# ============================================================================
# Pós-processamento estrutural: hierarquia + numeração do folheto
# ============================================================================

_TITULOS_LITURGICOS = (
    "canto de entrada", "saudação", "saudacao", "ato penitencial",
    "hino de louvor", "glória", "gloria", "coleta",
    "primeira leitura", "salmo responsorial", "segunda leitura",
    "sequência", "sequencia", "aclamação ao evangelho",
    "aclamacao ao evangelho", "evangelho", "homilia",
    "profissão de fé", "profissao de fe", "oração dos fiéis",
    "oracao dos fieis", "oração universal", "oracao universal",
    "canto das ofertas", "ofertório", "ofertorio", "convite à oração",
    "convite a oracao", "sobre as oferendas", "oração eucarística",
    "oracao eucaristica", "santo", "pai-nosso", "pai nosso",
    "cordeiro de deus", "rito da comunhão", "rito da comunhao",
    "canto de comunhão", "canto de comunhao", "depois da comunhão",
    "depois da comunhao", "vivência", "vivencia", "bênção final",
    "bencao final", "canto final",
)


def _eh_titulo_litur(titulo: str) -> bool:
    """Verifica se o texto após 'N.' é um título de bloco litúrgico conhecido.

    Usado pra desambiguar 'N. continuação de estrofe' vs 'N. Próximo Bloco'.
    Ex: '10. Dai em prêmio...' (estrofe da Sequência) vs '10. Aclamação ao Evangelho'.
    """
    t = (titulo or "").lower().strip()
    return any(t.startswith(p) for p in _TITULOS_LITURGICOS)


_TITULOS_APENDICE = {
    "leituras da semana", "antífona mariana", "antifona mariana",
    "semana eucarística", "semana eucaristica",
}
_TITULOS_ORACAO_DIA_PREFIXO = (
    "oração para o ", "oracao para o ",
    "rito para apagar o ",
)


def _eh_apendice(bloco) -> bool:
    """Conteúdo de rodapé do folheto que não pertence a nenhuma seção litúrgica."""
    titulo = (getattr(bloco, "titulo", "") or "").lower().strip()
    if titulo in _TITULOS_APENDICE:
        return True
    if any(titulo.startswith(p) for p in _TITULOS_ORACAO_DIA_PREFIXO):
        return True
    return False


def _eh_antifona_par(bloco) -> Optional[str]:
    """Retorna 'entrada' / 'comunhao' se a antífona deve anexar a um canto homônimo."""
    if getattr(bloco, "tipo", None) != "antifona":
        return None
    t = (getattr(bloco, "titulo", "") or "").lower()
    if "entrada" in t:
        return "entrada"
    if "comunhão" in t or "comunhao" in t:
        return "comunhao"
    return None


def _aplicar_hierarquia_e_numeracao(blocos: list) -> list:
    """Atribui seção, número do folheto e anexa antífonas. Vide chamada em estruturar()."""
    # Pass 1: marca seção corrente (walking forward) e identifica apêndices.
    secao_corrente: Optional[str] = None
    for b in blocos:
        if getattr(b, "tipo", None) == "secao":
            secao_corrente = b.titulo
            continue
        if _eh_apendice(b):
            try:
                b.secao = "apendice"
            except Exception:
                pass
            continue
        if secao_corrente:
            try:
                b.secao = secao_corrente
            except Exception:
                pass

    # Pass 2: NÃO anexa mais antífonas — ficam como blocos próprios na posição
    # original do PDF (Antífona da Entrada entre Saudação e Ato Penitencial,
    # Antífona da Comunhão entre Canto de Comunhão e Depois da Comunhão).
    blocos_finais: list = blocos

    # Pass 3: atribui numero_folheto sequencial (1..N) apenas aos blocos navegáveis,
    # ignorando seções, apêndices e Antífonas Entrada/Comunhão (mantém posição
    # mas não recebe número — o folheto também não dá número a elas).
    n = 0
    for b in blocos_finais:
        if getattr(b, "tipo", None) == "secao":
            continue
        if getattr(b, "secao", None) == "apendice":
            continue
        if _eh_antifona_par(b):
            # Antífona da Entrada/Comunhão fica sem numero_folheto (corresponde
            # à apresentação no folheto que não as numera).
            continue
        n += 1
        try:
            b.numero_folheto = n
        except Exception:
            pass

    return blocos_finais
