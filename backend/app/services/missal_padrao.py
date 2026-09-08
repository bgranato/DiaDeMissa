"""Missal Romano Padrão — partes fixas da missa católica.

A Canção Nova só publica as leituras (1ª, salmo, 2ª, aclamação, evangelho).
O Ordinário da Missa (saudação, ato penitencial, glória, credo, oração eucarística,
pai-nosso, comunhão, bênção) é IDÊNTICO todo dia — vem do Missal Romano.

Esta função monta a missa completa estruturada combinando:
- Blocos fixos do Missal Padrão (presente módulo)
- Leituras variáveis do dia (parâmetro `leituras`)

Resultado: lista de blocos no formato esperado pelo BlocoRenderer.
"""
from __future__ import annotations

from datetime import date as date_type
from typing import Optional


def _dialogo(turnos: list[dict]) -> dict:
    """Helper: bloco de diálogo P/T."""
    return {"turnos": turnos}


def _canto(refrao: list[str], estrofes: Optional[list[list[str]]] = None) -> dict:
    return {"refrao": refrao, "estrofes": estrofes or []}


def _antifona(texto: str) -> dict:
    return {"texto": texto}


def _eh_quaresma_ou_advento(tempo: Optional[str]) -> bool:
    if not tempo:
        return False
    return tempo.lower() in ("quaresma", "advento")


def _classificar_celebracao(titulo: Optional[str]) -> str:
    """Identifica o rank litúrgico da celebração a partir do título da Canção Nova.

    Formatos típicos:
        'Ascensão do Senhor | Solenidade | Domingo' → solenidade
        'São Matias, Apóstolo | Festa | Quinta-feira' → festa
        'Santo Atanásio, Bispo e Doutor da Igreja | Memória | Sábado' → memoria
        '6ª Semana da Páscoa | Sexta-feira' → feria
    """
    if not titulo:
        return "feria"
    t = titulo.lower()
    if "solenidade" in t:
        return "solenidade"
    if "festa" in t:
        return "festa"
    if "memória" in t or "memoria" in t:
        return "memoria"
    return "feria"


def montar_missa_completa(
    leituras: dict,
    data: date_type,
    tempo_liturgico: Optional[str] = None,
) -> list[dict]:
    """Monta uma missa completa (~25 blocos) combinando Missal Padrão + leituras do dia.

    Args:
        leituras: dict no formato retornado por scraper_cancaonova.buscar_liturgia(),
            com chaves leitura_1, salmo, leitura_2, aclamacao, evangelho.
        data: data da missa (usado pra decidir se é domingo → 2ª leitura + credo).
        tempo_liturgico: 'Páscoa', 'Advento', 'Quaresma', 'Comum' — omite Glória em Quaresma/Advento.

    Returns:
        Lista ordenada de dicts no formato:
            { ordem, tipo, titulo, secao_master, postura, ...payload conforme tipo }
    """
    eh_domingo = data.weekday() == 6  # 0=segunda ... 6=domingo
    rank = _classificar_celebracao(leituras.get("titulo"))
    eh_solenidade = rank == "solenidade"
    eh_festa = rank == "festa"
    eh_memoria = rank == "memoria"
    tem_segunda_leitura = bool(leituras.get("leitura_2"))

    # Regras oficiais do Missal Romano:
    # GLÓRIA: domingos (exceto Quaresma/Advento) + solenidades + festas. Não em férias/memórias.
    em_quaresma_advento = _eh_quaresma_ou_advento(tempo_liturgico)
    tem_gloria = (eh_domingo and not em_quaresma_advento) or eh_solenidade or eh_festa
    # CREDO: só domingos e solenidades. Festas e memórias NÃO têm.
    tem_credo = eh_domingo or eh_solenidade

    blocos: list[dict] = []
    ordem = 0

    def add(tipo: str, titulo: str, secao: str, postura: Optional[str] = None, **payload):
        nonlocal ordem
        ordem += 1
        bloco = {
            "ordem": ordem,
            "tipo": tipo,
            "titulo": titulo,
            "secao_master": secao,
            "postura": postura,
            **payload,
        }
        blocos.append(bloco)

    # ==========================================================================
    # I. RITOS INICIAIS  (de pé)
    # ==========================================================================
    SEC1 = "Ritos Iniciais"

    add("secao", "Ritos Iniciais", SEC1, descricao=(
        "Reunidos como Povo de Deus, somos acolhidos pelo presidente da celebração. "
        "Pedimos perdão pelos nossos pecados e louvamos a Deus."
    ))

    # 1. Saudação Inicial
    add(
        "saudacao_inicial",
        "Saudação Inicial",
        SEC1, postura="de_pe",
        turnos=[
            {"falante": "rubrica", "texto": "Todos fazem o sinal da cruz, enquanto o presidente diz:"},
            {"falante": "P", "texto": "Em nome do Pai, e do Filho, e do Espírito Santo."},
            {"falante": "T", "texto": "Amém."},
            {"falante": "P", "texto": "A graça de Nosso Senhor Jesus Cristo, o amor do Pai e a comunhão do Espírito Santo estejam convosco."},
            {"falante": "T", "texto": "Bendito seja Deus que nos reuniu no amor de Cristo."},
        ],
    )

    # 2. Ato Penitencial
    add(
        "ato_penitencial",
        "Ato Penitencial",
        SEC1, postura="de_pe",
        turnos=[
            {"falante": "P", "texto": "Irmãos e irmãs, para celebrarmos dignamente os santos mistérios, reconheçamos que somos pecadores."},
            {"falante": "rubrica", "texto": "Momento de silêncio"},
            {"falante": "T", "texto": "Confesso a Deus todo-poderoso e a vós, irmãos e irmãs, que pequei muitas vezes, por pensamentos e palavras, atos e omissões, por minha culpa, minha tão grande culpa. E peço à Virgem Maria, aos Anjos e Santos, e a vós, irmãos e irmãs, que rogueis por mim a Deus, nosso Senhor."},
            {"falante": "P", "texto": "Deus todo-poderoso tenha compaixão de nós, perdoe os nossos pecados e nos conduza à vida eterna."},
            {"falante": "T", "texto": "Amém."},
            {"falante": "P", "texto": "Senhor, tende piedade de nós."},
            {"falante": "T", "texto": "Senhor, tende piedade de nós."},
            {"falante": "P", "texto": "Cristo, tende piedade de nós."},
            {"falante": "T", "texto": "Cristo, tende piedade de nós."},
            {"falante": "P", "texto": "Senhor, tende piedade de nós."},
            {"falante": "T", "texto": "Senhor, tende piedade de nós."},
        ],
    )

    # 3. Hino do Glória (domingos, solenidades e festas; nunca em férias/memórias)
    if tem_gloria:
        add(
            "gloria",
            "Hino de Louvor — Glória",
            SEC1, postura="de_pe",
            refrao=["Glória a Deus nas alturas, e paz na terra aos homens por Ele amados."],
            estrofes=[[
                "Senhor Deus, Rei dos céus, Deus Pai todo-poderoso:",
                "nós vos louvamos, nós vos bendizemos, nós vos adoramos,",
                "nós vos glorificamos, nós vos damos graças por vossa imensa glória.",
            ], [
                "Senhor Jesus Cristo, Filho Unigênito, Senhor Deus, Cordeiro de Deus, Filho de Deus Pai:",
                "Vós que tirais o pecado do mundo, tende piedade de nós.",
                "Vós que tirais o pecado do mundo, acolhei a nossa súplica.",
                "Vós que estais à direita do Pai, tende piedade de nós.",
            ], [
                "Só vós sois o Santo, só vós, o Senhor, só vós, o Altíssimo, Jesus Cristo,",
                "com o Espírito Santo, na glória de Deus Pai. Amém.",
            ]],
        )

    # 4. Oração da Coleta
    add(
        "dialogo",
        "Oração da Coleta",
        SEC1, postura="de_pe",
        turnos=[
            {"falante": "P", "texto": "Oremos."},
            {"falante": "rubrica", "texto": "Momento de silêncio — o presidente conclui com a oração própria do dia."},
            {"falante": "P", "texto": "Por nosso Senhor Jesus Cristo, vosso Filho, na unidade do Espírito Santo."},
            {"falante": "T", "texto": "Amém."},
        ],
    )

    # ==========================================================================
    # II. LITURGIA DA PALAVRA  (sentado, exceto evangelho)
    # ==========================================================================
    SEC2 = "Liturgia da Palavra"

    add("secao", "Liturgia da Palavra", SEC2, descricao=(
        "Deus fala ao seu povo, abrindo-lhe o mistério da redenção e da salvação. "
        "Cristo está presente em sua palavra."
    ))

    # 1ª Leitura
    l1 = leituras.get("leitura_1") or {}
    add(
        "primeira_leitura",
        "1ª Leitura",
        SEC2, postura="sentado",
        referencia=l1.get("referencia"),
        conteudo=l1.get("texto", ""),
        conclusao="— Palavra do Senhor.",
        resposta="T. Graças a Deus.",
    )

    # Salmo
    salmo = leituras.get("salmo") or {}
    add(
        "salmo_responsorial",
        "Salmo Responsorial",
        SEC2, postura="sentado",
        referencia=salmo.get("referencia"),
        conteudo=salmo.get("texto", ""),
    )

    # 2ª Leitura (domingos / solenidades / festas)
    if tem_segunda_leitura:
        l2 = leituras.get("leitura_2") or {}
        add(
            "segunda_leitura",
            "2ª Leitura",
            SEC2, postura="sentado",
            referencia=l2.get("referencia"),
            conteudo=l2.get("texto", ""),
            conclusao="— Palavra do Senhor.",
            resposta="T. Graças a Deus.",
        )

    # Aclamação ao Evangelho (de pé)
    acl = leituras.get("aclamacao") or {}
    if acl.get("texto"):
        add(
            "aclamacao",
            "Aclamação ao Evangelho",
            SEC2, postura="de_pe",
            referencia=acl.get("referencia"),
            conteudo=acl.get("texto", ""),
        )

    # Evangelho (de pé)
    ev = leituras.get("evangelho") or {}
    add(
        "evangelho",
        "Evangelho",
        SEC2, postura="de_pe",
        referencia=ev.get("referencia"),
        introducao="— O Senhor esteja convosco.\nT. Ele está no meio de nós.",
        conteudo=ev.get("texto", ""),
        conclusao="— Palavra da Salvação.",
        resposta="T. Glória a vós, Senhor.",
    )

    # Homilia (placeholder)
    add(
        "oracao",
        "Homilia",
        SEC2, postura="sentado",
        conteudo="(O presidente faz a homilia, explicando a Palavra de Deus proclamada.)",
    )

    # Profissão de Fé (Credo) — apenas domingos e solenidades
    if tem_credo:
        add(
            "recitacao",
            "Profissão de Fé — Símbolo dos Apóstolos",
            SEC2, postura="de_pe",
            conteudo=(
                "Creio em Deus Pai todo-poderoso, Criador do céu e da terra, "
                "e em Jesus Cristo, seu único Filho, Nosso Senhor, "
                "que foi concebido pelo poder do Espírito Santo, "
                "nasceu da Virgem Maria, padeceu sob Pôncio Pilatos, foi crucificado, morto e sepultado, "
                "desceu à mansão dos mortos, ressuscitou ao terceiro dia, "
                "subiu aos céus, está sentado à direita de Deus Pai todo-poderoso, "
                "donde há de vir a julgar os vivos e os mortos. "
                "Creio no Espírito Santo, na Santa Igreja Católica, "
                "na comunhão dos santos, na remissão dos pecados, "
                "na ressurreição da carne, na vida eterna. Amém."
            ),
        )

    # Oração Universal / Preces
    add(
        "preces_comunidade",
        "Oração Universal",
        SEC2, postura="de_pe",
        turnos=[
            {"falante": "P", "texto": "Apresentemos a Deus Pai as nossas preces, pedindo a sua misericórdia."},
            {"falante": "L", "texto": "Pela santa Igreja, para que seja sinal de unidade no meio do mundo, rezemos ao Senhor."},
            {"falante": "T", "texto": "Senhor, escutai a nossa prece."},
            {"falante": "L", "texto": "Por todas as autoridades civis e religiosas, e por todos os que buscam a paz e a justiça, rezemos."},
            {"falante": "T", "texto": "Senhor, escutai a nossa prece."},
            {"falante": "L", "texto": "Por todos os que sofrem, os doentes, os pobres e abandonados, rezemos."},
            {"falante": "T", "texto": "Senhor, escutai a nossa prece."},
            {"falante": "L", "texto": "Por nossa comunidade aqui reunida, para que seja imagem viva de Cristo, rezemos."},
            {"falante": "T", "texto": "Senhor, escutai a nossa prece."},
            {"falante": "P", "texto": "Ó Deus, escutai as preces que vos apresentamos, por Cristo, nosso Senhor."},
            {"falante": "T", "texto": "Amém."},
        ],
    )

    # ==========================================================================
    # III. LITURGIA EUCARÍSTICA  (sentado / ajoelhado / de pé)
    # ==========================================================================
    SEC3 = "Liturgia Eucarística"

    add("secao", "Liturgia Eucarística", SEC3, descricao=(
        "Apresentamos as oferendas e celebramos a Eucaristia: o memorial da Paixão, "
        "Morte e Ressurreição de Cristo, alimento para a vida eterna."
    ))

    # Apresentação dos Dons
    add(
        "dialogo",
        "Apresentação dos Dons",
        SEC3, postura="sentado",
        turnos=[
            {"falante": "P", "texto": "Bendito sejais, Senhor, Deus do universo, pelo pão que recebemos de vossa bondade, fruto da terra e do trabalho humano, que agora vos apresentamos e para nós se vai tornar pão da vida."},
            {"falante": "T", "texto": "Bendito seja Deus para sempre."},
            {"falante": "P", "texto": "Bendito sejais, Senhor, Deus do universo, pelo vinho que recebemos de vossa bondade, fruto da videira e do trabalho humano, que agora vos apresentamos e para nós se vai tornar vinho da salvação."},
            {"falante": "T", "texto": "Bendito seja Deus para sempre."},
            {"falante": "P", "texto": "Orai, irmãos e irmãs, para que o nosso sacrifício seja aceito por Deus Pai todo-poderoso."},
            {"falante": "T", "texto": "Receba o Senhor por tuas mãos este sacrifício, para glória do seu nome, para nosso bem e de toda a santa Igreja."},
        ],
    )

    # Oração Eucarística II (a mais comum em missa de semana)
    add(
        "dialogo",
        "Prefácio",
        SEC3, postura="de_pe",
        turnos=[
            {"falante": "P", "texto": "O Senhor esteja convosco."},
            {"falante": "T", "texto": "Ele está no meio de nós."},
            {"falante": "P", "texto": "Corações ao alto."},
            {"falante": "T", "texto": "O nosso coração está em Deus."},
            {"falante": "P", "texto": "Demos graças ao Senhor, nosso Deus."},
            {"falante": "T", "texto": "É nosso dever e nossa salvação."},
        ],
    )

    add(
        "canto",
        "Santo",
        SEC3, postura="de_pe",
        refrao=[
            "Santo, Santo, Santo, Senhor Deus do universo!",
            "O céu e a terra proclamam a vossa glória.",
            "Hosana nas alturas!",
            "Bendito o que vem em nome do Senhor!",
            "Hosana nas alturas!",
        ],
    )

    add(
        "recitacao",
        "Oração Eucarística II",
        SEC3, postura="ajoelhado",
        conteudo=(
            "Na verdade, ó Pai, vós sois Santo, e fonte de toda santidade. "
            "Santificai, pois, estas oferendas, derramando sobre elas o vosso Espírito, "
            "a fim de que se tornem para nós o Corpo e o Sangue de Jesus Cristo, vosso Filho e Senhor nosso. "
            "Estando para ser entregue e abraçando livremente a Paixão, ele tomou o pão, deu graças, "
            "e o partiu e deu a seus discípulos, dizendo:\n\n"
            "TOMAI, TODOS, E COMEI: ISTO É O MEU CORPO, QUE SERÁ ENTREGUE POR VÓS.\n\n"
            "Do mesmo modo, ao fim da ceia, ele tomou o cálice em suas mãos, "
            "deu graças novamente, e o deu a seus discípulos, dizendo:\n\n"
            "TOMAI, TODOS, E BEBEI: ESTE É O CÁLICE DO MEU SANGUE, O SANGUE DA NOVA E ETERNA ALIANÇA, "
            "QUE SERÁ DERRAMADO POR VÓS E POR TODOS, PARA REMISSÃO DOS PECADOS. FAZEI ISTO EM MEMÓRIA DE MIM.\n\n"
            "P. Eis o mistério da fé!\n"
            "T. Anunciamos, Senhor, a vossa morte e proclamamos a vossa ressurreição. Vinde, Senhor Jesus!"
        ),
    )

    # Pai-Nosso
    add(
        "recitacao",
        "Pai-Nosso",
        SEC3, postura="de_pe",
        conteudo=(
            "P. Rezemos com confiança, como o Senhor nos ensinou:\n\n"
            "Pai nosso que estais nos céus, santificado seja o vosso nome; "
            "venha a nós o vosso Reino; seja feita a vossa vontade, assim na terra como no céu. "
            "O pão nosso de cada dia nos dai hoje; perdoai-nos as nossas ofensas, "
            "assim como nós perdoamos a quem nos tem ofendido; "
            "e não nos deixeis cair em tentação, mas livrai-nos do mal.\n\n"
            "P. Livrai-nos de todos os males, ó Pai, e dai-nos hoje a vossa paz. "
            "Para que, ajudados pela vossa misericórdia, sejamos sempre livres do pecado "
            "e protegidos de todos os perigos, enquanto, vivendo a esperança, "
            "aguardamos a vinda do nosso Salvador, Jesus Cristo.\n"
            "T. Vosso é o Reino, o poder e a glória para sempre!"
        ),
    )

    # Sinal da Paz
    add(
        "dialogo",
        "Sinal da Paz",
        SEC3, postura="de_pe",
        turnos=[
            {"falante": "P", "texto": "Senhor Jesus Cristo, dissestes aos vossos Apóstolos: 'Eu vos deixo a paz, eu vos dou a minha paz'. Não olheis os nossos pecados, mas a fé que anima vossa Igreja."},
            {"falante": "P", "texto": "A paz do Senhor esteja sempre convosco."},
            {"falante": "T", "texto": "O amor de Cristo nos uniu."},
            {"falante": "rubrica", "texto": "Os fiéis saúdam-se mutuamente com um sinal de paz."},
        ],
    )

    # Cordeiro de Deus
    add(
        "canto",
        "Cordeiro de Deus",
        SEC3, postura="de_pe",
        refrao=[
            "Cordeiro de Deus, que tirais o pecado do mundo, tende piedade de nós!",
            "Cordeiro de Deus, que tirais o pecado do mundo, tende piedade de nós!",
            "Cordeiro de Deus, que tirais o pecado do mundo, dai-nos a paz!",
        ],
    )

    # Comunhão
    add(
        "dialogo",
        "Comunhão",
        SEC3, postura="de_pe",
        turnos=[
            {"falante": "P", "texto": "Eis o Cordeiro de Deus, que tira o pecado do mundo. Felizes os convidados para a Ceia do Senhor."},
            {"falante": "T", "texto": "Senhor, eu não sou digno(a) de que entreis em minha morada, mas dizei uma palavra e serei salvo(a)."},
            {"falante": "rubrica", "texto": "Procissão da Comunhão"},
        ],
    )

    # ==========================================================================
    # IV. RITOS DE CONCLUSÃO  (de pé)
    # ==========================================================================
    SEC4 = "Ritos de Conclusão"

    add("secao", "Ritos de Conclusão", SEC4, descricao=(
        "Recebemos a bênção final e somos enviados a anunciar o Evangelho com a vida."
    ))

    add(
        "bencao_final",
        "Bênção Final e Despedida",
        SEC4, postura="de_pe",
        turnos=[
            {"falante": "P", "texto": "O Senhor esteja convosco."},
            {"falante": "T", "texto": "Ele está no meio de nós."},
            {"falante": "P", "texto": "Abençoe-vos Deus todo-poderoso, Pai e Filho ✠ e Espírito Santo."},
            {"falante": "T", "texto": "Amém."},
            {"falante": "P", "texto": "Ide em paz e o Senhor vos acompanhe."},
            {"falante": "T", "texto": "Graças a Deus."},
        ],
    )

    return blocos
