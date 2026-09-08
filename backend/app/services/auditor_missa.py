"""Auditoria automática de qualidade das missas processadas.

Roda após o pipeline diário, varre as missas dos próximos N dias e detecta
padrões suspeitos que indicam falha de extração/estruturação:

- Blocos completamente vazios (sem turnos/conteúdo)
- Oração dos Fiéis sem alternância L/T (preces não separadas)
- Numeração de prece dentro de um único turno ("1. ... 2. ...")
- Sigla de falante (P./T./L.) vazando como texto
- Postura ("De pé", "Sentados") como conteúdo
- Tamanho anômalo de blocos críticos (Evangelho < 100 chars, etc.)
- Cantos sem refrão nem estrofes

Gera um relatório que é gravado num arquivo .md em reports/auditoria/ e
loga warnings. Quando o status total tem flag CRÍTICA, marca a missa com
status_processamento='pendente_revisao' pra revisão manual.
"""
from __future__ import annotations

import logging
import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from app.core.database import SessionLocal
from app.models.missa import Missa, BlocoLiturgico

logger = logging.getLogger(__name__)

# Em produção, use AUDITORIA_REPORTS_DIR=/var/lib/diademissa/reports/auditoria:
# o serviço tem ProtectSystem=strict e só esse volume é gravável. O fallback
# preserva o caminho de relatórios usado por desenvolvimento e testes locais.
REPORTS_DIR = Path(os.getenv(
    "AUDITORIA_REPORTS_DIR",
    str(Path(__file__).resolve().parent.parent.parent / "reports" / "auditoria"),
))

# Severidades
SEV_CRITICA = "CRÍTICA"
SEV_ALTA = "ALTA"
SEV_MEDIA = "MÉDIA"
SEV_BAIXA = "BAIXA"


@dataclass
class Achado:
    severidade: str
    bloco_ordem: int
    bloco_titulo: str
    bloco_tipo: str
    regra: str
    detalhe: str


@dataclass
class RelatorioMissa:
    data: date
    celebracao: str | None
    total_blocos: int
    achados: list[Achado] = field(default_factory=list)

    @property
    def tem_critica(self) -> bool:
        return any(a.severidade == SEV_CRITICA for a in self.achados)

    @property
    def severidade_max(self) -> str:
        ordem = [SEV_CRITICA, SEV_ALTA, SEV_MEDIA, SEV_BAIXA]
        for sev in ordem:
            if any(a.severidade == sev for a in self.achados):
                return sev
        return "OK"


# ---------------------------------------------------------------------------
# Regras de auditoria
# ---------------------------------------------------------------------------

def _conteudo_vazio(b: BlocoLiturgico) -> bool:
    """Bloco sem conteúdo nem turnos nem estrutura útil.

    Seções (tipo='secao') são cabeçalhos de container e legitimamente vazios.
    """
    if (b.tipo or "").lower() == "secao":
        return False
    if (b.conteudo or "").strip():
        return False
    ce = b.conteudo_estruturado or {}
    if any(ce.get(k) for k in ("turnos", "refrao", "estrofes", "texto", "versiculos")):
        return False
    return True


def _turnos_lista(b: BlocoLiturgico) -> list[dict]:
    return (b.conteudo_estruturado or {}).get("turnos") or []


def _eh_oracao_dos_fieis(b: BlocoLiturgico) -> bool:
    titulo = (b.titulo or "").lower()
    tipo = (b.tipo or "").lower()
    return (
        "fiéis" in titulo or "fieis" in titulo
        or "preces" in titulo or "universal" in titulo
        or tipo == "preces_comunidade"
    )


def _checar_preces_nao_separadas(b: BlocoLiturgico, achados: list[Achado]) -> None:
    if not _eh_oracao_dos_fieis(b):
        return
    turnos = _turnos_lista(b)
    if not turnos:
        achados.append(Achado(
            SEV_ALTA, b.ordem, b.titulo or "", b.tipo,
            "preces_sem_turnos", "Oração dos Fiéis sem turnos estruturados",
        ))
        return
    # Cada turno não pode ter "N. ... N+1. ..." (preces amassadas)
    for i, t in enumerate(turnos):
        texto = (t.get("texto") or "")
        if len(re.findall(r"\s\d+\.\s", texto)) >= 2:
            achados.append(Achado(
                SEV_CRITICA, b.ordem, b.titulo or "", b.tipo,
                "preces_amassadas_em_um_turno",
                f"Turno #{i+1} tem múltiplas preces numeradas amassadas: {texto[:120]!r}",
            ))
    # A Oração dos Fiéis é válida com um LÍDER (L ou P) enunciando as intenções e
    # o povo (T) respondendo. O folheto da Arqrio usa P + intenções numeradas + T
    # (sem "L") — padrão legítimo, não deve gerar achado. Só sinaliza se faltar
    # líder OU resposta do povo.
    falantes = [t.get("falante", "") for t in turnos]
    tem_lider = ("L" in falantes) or ("P" in falantes)
    tem_resposta = "T" in falantes
    if not (tem_lider and tem_resposta) and len(turnos) >= 4:
        achados.append(Achado(
            SEV_ALTA, b.ordem, b.titulo or "", b.tipo,
            "preces_sem_resposta",
            f"Oração dos Fiéis sem líder+resposta do povo (falantes: {set(falantes)})",
        ))


def _checar_artefatos_texto(b: BlocoLiturgico, achados: list[Achado]) -> None:
    """Procura artefatos clássicos vazando em qualquer campo de texto."""
    tipo = (b.tipo or "").lower()
    # 'recitacao' = texto recitado CONTÍNUO (Pai-Nosso, Oração Eucarística no template
    # da liturgia diária). As siglas P./T. fazem parte do texto por design — não são
    # sigla vazando de um diálogo. Isenta esse tipo da regra sigla_falante_no_texto.
    ignora_sigla = tipo == "recitacao"
    artefatos = [
        (r"^[PTLVR]\.\s*", "sigla_falante_no_texto", SEV_ALTA),
        (r"\(De pé\)|\(Sentados?\)|\(Ajoelhados?\)", "postura_no_texto", SEV_MEDIA),
        (r"\w+-\s*\n", "hifenizacao_quebra_linha", SEV_BAIXA),
        (r"##|^\*\*|\*\*$", "markdown_vazado", SEV_BAIXA),
        (r"Entrada:\s*\w+;\s*Ofertas:", "creditos_no_texto", SEV_ALTA),
    ]
    textos = []
    if b.conteudo:
        textos.append(("conteudo", b.conteudo))
    for t in _turnos_lista(b):
        textos.append(("turno", t.get("texto") or ""))
    ce = b.conteudo_estruturado or {}
    if ce.get("texto"):
        textos.append(("texto", ce["texto"]))
    for est in (ce.get("estrofes") or []):
        if isinstance(est, list):
            for linha in est:
                textos.append(("estrofe", linha or ""))
    for campo, texto in textos:
        if not isinstance(texto, str) or not texto:
            continue
        for padrao, regra, sev in artefatos:
            if regra == "sigla_falante_no_texto" and ignora_sigla:
                continue
            if re.search(padrao, texto):
                achados.append(Achado(
                    sev, b.ordem, b.titulo or "", b.tipo,
                    regra, f"Em '{campo}': {texto[:120]!r}",
                ))
                break  # uma falha por campo é suficiente


def _checar_tamanho_minimo(b: BlocoLiturgico, achados: list[Achado]) -> None:
    """Blocos essenciais (leitura/evangelho) não podem ser curtíssimos.

    Só checa tipos do schema, não título — pra não falso-positivar
    'Aclamação ao Evangelho' (que tem 'evangelho' no nome mas é um diálogo).
    """
    minimos_por_tipo = {
        "evangelho": 200,
        "leitura": 150,         # primeira/segunda leitura genérica
        "primeira_leitura": 150,
        "segunda_leitura": 150,
    }
    tipo_lower = (b.tipo or "").lower()
    minimo = minimos_por_tipo.get(tipo_lower)
    if not minimo:
        return
    tamanho = len(b.conteudo or "") + sum(
        len(t.get("texto", "") or "") for t in _turnos_lista(b)
    )
    ce = b.conteudo_estruturado or {}
    if ce.get("texto"):
        tamanho += len(ce["texto"])
    for v in (ce.get("versiculos") or []):
        if isinstance(v, dict):
            tamanho += len(v.get("texto", "") or "")
    if tamanho < minimo:
        achados.append(Achado(
            SEV_ALTA, b.ordem, b.titulo or "", b.tipo,
            "bloco_essencial_curto",
            f"tipo={tipo_lower} tem só {tamanho} chars (mínimo {minimo})",
        ))


def _checar_canto_vazio(b: BlocoLiturgico, achados: list[Achado]) -> None:
    if (b.tipo or "").lower() not in ("canto", "canto_entrada", "canto_comunhao",
                                       "canto_ofertorio", "canto_final"):
        return
    ce = b.conteudo_estruturado or {}
    tem_refrao = bool(ce.get("refrao"))
    tem_estrofe = bool(ce.get("estrofes"))
    tem_conteudo = bool((b.conteudo or "").strip())
    if not (tem_refrao or tem_estrofe or tem_conteudo):
        achados.append(Achado(
            SEV_MEDIA, b.ordem, b.titulo or "", b.tipo,
            "canto_vazio", "Canto sem refrão, estrofes nem conteúdo",
        ))


def _checar_template_generico(missa: Missa, achados: list[Achado]) -> None:
    """Detecta missas servidas via CNBB/missal padrão genérico quando deveriam
    ter folheto Arquidiocese rico. Heurística: missa de Domingo/Solenidade SEM
    folheto arqrio E com cantos majoritariamente vazios = falhou o pipeline.

    Esse é exatamente o caso do dia 07/06/2026 onde o cron das 5h caiu por
    filesystem read-only e a missa ficou como template genérico.
    """
    # Só checa domingos (weekday=6) ou solenidades
    eh_domingo = missa.data.weekday() == 6
    eh_solenidade = (missa.categoria or "").lower() == "solenidade"
    if not (eh_domingo or eh_solenidade):
        return
    # Se a fonte é arqrio, o folheto chegou — ok
    if "arqrio" in (missa.fonte_pdf_url or "").lower():
        return
    # Conta quantos cantos do tipo 'canto' têm refrão/estrofes preenchidos
    cantos_total = 0
    cantos_vazios = 0
    for b in missa.blocos:
        if (b.tipo or "").lower() != "canto":
            continue
        cantos_total += 1
        ce = b.conteudo_estruturado or {}
        if not (ce.get("refrao") or ce.get("estrofes")):
            cantos_vazios += 1
    if cantos_total >= 3 and cantos_vazios >= cantos_total - 1:
        achados.append(Achado(
            SEV_CRITICA, 0, "Missa (geral)", "missa",
            "template_generico_em_domingo_ou_solenidade",
            f"{cantos_vazios}/{cantos_total} cantos vazios em domingo/solenidade sem folheto Arquidiocese. "
            "Pipeline falhou - reprocessar.",
        ))


# ---------------------------------------------------------------------------
# Reforço: checks estruturais novos + cross-check contra o texto-fonte (PDF)
# ---------------------------------------------------------------------------

# Tipos que o BlocoRenderer do front sabe renderizar (fora disso → placeholder).
TIPOS_RENDERIZAVEIS = {
    "secao", "canto", "canto_entrada", "canto_de_entrada", "canto_das_ofertas",
    "canto_de_comunhao", "canto_de_comunhão", "canto_comunhao", "canto_ofertorio",
    "canto_final", "gloria", "hino_de_louvor", "salmo", "salmo_responsorial",
    "aclamacao", "aclamacao_evangelho", "aclamação_evangelho",
    "dialogo", "saudacao_inicial", "ato_penitencial", "preces_comunidade",
    "bencao_final", "antifona", "antifona_entrada", "leitura", "primeira_leitura",
    "segunda_leitura", "evangelho", "oracao", "recitacao",
}

# Âncoras: se o texto-fonte contém, a montagem TAMBÉM tem de conter.
# (regex sobre texto normalizado: minúsculas, sem pontuação, espaços colapsados)
_ANCORAS = [
    (r"tomai +todos +e +comei", "Consagração (pão)", SEV_CRITICA),
    (r"tomai +todos +e +bebei", "Consagração (cálice)", SEV_CRITICA),
    (r"pai nosso", "Pai nosso", SEV_ALTA),
    (r"santo +santo +santo", "Santo", SEV_ALTA),
    (r"gl[oó]ria a deus nas alturas", "Glória (Hino de Louvor)", SEV_ALTA),
    (r"proclama[çc][aã]o do evangelho", "Proclamação do Evangelho (preâmbulo)", SEV_ALTA),
]


def _norm(s: str) -> str:
    s = re.sub(r"[^0-9a-zà-úãõâêôçáéíóú ]", " ", (s or "").lower())
    return re.sub(r"\s+", " ", s).strip()


def _ascii_fold(s: str) -> str:
    """Remove acentos/cedilha (coração->coracao, aclamações->aclamacoes).

    Usado SÓ na cobertura por palavra: a extração do PDF às vezes trunca a
    palavra na quebra de linha ('aclamaçõ'), e dobrar sem acento + tolerar
    truncagem evita falso-positivo sem afrouxar o limiar.
    """
    nkfd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nkfd if not unicodedata.combining(c))


def _texto_montagem(missa: Missa) -> str:
    """Concatena, normalizado, TODO o texto da montagem (metadados + blocos).

    Inclui os campos de nível da missa (descrição/celebração/categoria/créditos)
    e TODOS os campos de texto dos blocos — inclusive introducao/conclusao/
    resposta/versiculo — pra a checagem de cobertura não acusar falso-positivo.
    """
    partes: list[str] = []
    # Nível da missa (casa com masthead/créditos/parágrafo de abertura do folheto).
    for campo in ("celebracao", "descricao", "observacoes", "categoria"):
        v = getattr(missa, campo, None)
        if isinstance(v, str):
            partes.append(v)
    cred = getattr(missa, "creditos_cantos", None)
    if isinstance(cred, dict):
        partes.extend([str(x) for x in cred.values() if x])
    for b in missa.blocos:
        if b.conteudo:
            partes.append(b.conteudo)
        if b.titulo:
            partes.append(b.titulo)
        ce = b.conteudo_estruturado or {}
        for campo in ("introducao", "texto", "conclusao", "resposta",
                      "versiculo", "descricao", "subtitulo"):
            if isinstance(ce.get(campo), str):
                partes.append(ce[campo])
        for t in ce.get("turnos") or []:
            partes.append(t.get("texto") or "")
        for r in ce.get("refrao") or []:
            if isinstance(r, str):
                partes.append(r)
        for est in ce.get("estrofes") or []:
            if isinstance(est, list):
                partes.extend([x for x in est if isinstance(x, str)])
        for v in ce.get("versiculos") or []:
            if isinstance(v, dict):
                partes.append(v.get("texto") or "")
    return _norm(" ".join(partes))


def _eh_arqrio(missa: Missa) -> bool:
    if "arqrio" in (getattr(missa, "fonte_pdf_url", "") or "").lower():
        return True
    try:
        from app.pipeline.download import CACHE_DIR
        return (CACHE_DIR / "archive" / f"{missa.data.isoformat()}.pdf").exists()
    except Exception:
        return False


def _carregar_texto_fonte(missa: Missa) -> str | None:
    """Re-extrai/limpa o texto do folheto-fonte arquivado (SEM LLM). None se não houver."""
    try:
        from app.pipeline.download import CACHE_DIR
        from app.pipeline.extract import extrair_texto_estruturado
        from app.pipeline.clean import limpar
        for cand in (CACHE_DIR / "archive" / f"{missa.data.isoformat()}.pdf",
                     CACHE_DIR / f"{missa.data.isoformat()}.pdf"):
            if cand.exists():
                return limpar(extrair_texto_estruturado(cand))
    except Exception:
        logger.exception("auditor: falha ao carregar texto-fonte de %s", missa.data)
    return None


def _checar_tipo_renderizavel(b: BlocoLiturgico, achados: list[Achado]) -> None:
    tipo = (b.tipo or "").lower()
    if tipo and tipo not in TIPOS_RENDERIZAVEIS:
        achados.append(Achado(
            SEV_MEDIA, b.ordem, b.titulo or "", b.tipo,
            "tipo_nao_renderizavel",
            f"tipo '{b.tipo}' fora do conjunto que o front renderiza (risco de placeholder)",
        ))


def _checar_posicao_refrao(b: BlocoLiturgico, achados: list[Achado]) -> None:
    if (b.tipo or "").lower() != "canto":
        return
    ce = b.conteudo_estruturado or {}
    pos = ce.get("posicao_refrao_apos")
    if pos is None or not (ce.get("refrao")):
        return
    n_est = len(ce.get("estrofes") or [])
    if not isinstance(pos, int) or pos < 0 or pos > n_est:
        achados.append(Achado(
            SEV_MEDIA, b.ordem, b.titulo or "", b.tipo,
            "posicao_refrao_invalida",
            f"posicao_refrao_apos={pos} fora de [0, {n_est}]",
        ))


def _checar_referencia_leitura(b: BlocoLiturgico, achados: list[Achado]) -> None:
    tipo = (b.tipo or "").lower()
    if tipo not in ("leitura", "primeira_leitura", "segunda_leitura",
                    "evangelho", "salmo", "salmo_responsorial"):
        return
    ce = b.conteudo_estruturado or {}
    if not (ce.get("referencia") or b.referencia):
        achados.append(Achado(
            SEV_ALTA, b.ordem, b.titulo or "", b.tipo,
            "leitura_sem_referencia", "Leitura/Salmo/Evangelho sem referência bíblica",
        ))


def _checar_numeracao(missa: Missa, achados: list[Achado]) -> None:
    nums = [ce.get("numero_folheto") for b in missa.blocos
            for ce in [b.conteudo_estruturado or {}]
            if isinstance(ce.get("numero_folheto"), int)]
    if len(nums) < 5:  # missa sem numeração (ex.: liturgia diária CNBB) — não checa
        return
    dup = sorted({x for x in nums if nums.count(x) > 1})
    if dup:
        achados.append(Achado(
            SEV_ALTA, 0, "Missa (geral)", "missa",
            "numeracao_duplicada", f"números repetidos no folheto: {dup}",
        ))
    faltando = [x for x in range(1, max(nums) + 1) if x not in set(nums)]
    if faltando:
        achados.append(Achado(
            SEV_ALTA, 0, "Missa (geral)", "missa",
            "numeracao_com_buraco", f"números faltando na sequência: {faltando}",
        ))


def _checar_metadados(missa: Missa, achados: list[Achado]) -> None:
    if not _eh_arqrio(missa):
        return
    desc = (getattr(missa, "descricao", "") or "").strip()
    if not desc:
        achados.append(Achado(
            SEV_MEDIA, 0, "Missa (geral)", "missa",
            "descricao_ausente", "Folheto Arquidiocese sem parágrafo de abertura (descrição)",
        ))
    obs = (getattr(missa, "observacoes", "") or "").strip()
    if len(obs) > 200:
        achados.append(Achado(
            SEV_MEDIA, 0, "Missa (geral)", "missa",
            "observacoes_longas",
            f"observações com {len(obs)} chars — parece reflexão de abertura no campo errado",
        ))
    cat = (getattr(missa, "categoria", "") or "").strip()
    if not cat:
        achados.append(Achado(
            SEV_BAIXA, 0, "Missa (geral)", "missa",
            "categoria_vazia", "categoria vazia em folheto Arquidiocese",
        ))


def _checar_ancoras(src_norm: str, mont_norm: str, achados: list[Achado]) -> None:
    for rgx, label, sev in _ANCORAS:
        if re.search(rgx, src_norm) and not re.search(rgx, mont_norm):
            achados.append(Achado(
                sev, 0, "Missa (geral)", "missa",
                "conteudo_essencial_ausente",
                f"'{label}' está no folheto-fonte mas NÃO na montagem",
            ))


def _checar_cobertura(src_norm: str, mont_norm: str, achados: list[Achado]) -> None:
    palavras_src = {w for w in src_norm.split() if len(w) >= 4}
    if len(palavras_src) < 60:
        return  # fonte pequena/ruidosa — não confiável
    presentes = {w for w in mont_norm.split() if len(w) >= 4}
    cob = sum(1 for w in palavras_src if w in presentes) / len(palavras_src)
    # Fonte tem rodapé/leituras-da-semana/masthead que não vão p/ montagem → tolerância.
    if cob < 0.55:
        achados.append(Achado(
            SEV_ALTA, 0, "Missa (geral)", "missa", "cobertura_muito_baixa",
            f"só {cob:.0%} das palavras do folheto-fonte aparecem na montagem — provável conteúdo perdido",
        ))
    elif cob < 0.70:
        achados.append(Achado(
            SEV_MEDIA, 0, "Missa (geral)", "missa", "cobertura_baixa",
            f"{cob:.0%} de cobertura do folheto-fonte (verificar possível corte de conteúdo)",
        ))


# Marcadores onde começa o RODAPÉ de publicação (não é conteúdo litúrgico).
# Tudo a partir daqui é cortado antes da checagem palavra-a-palavra.
_RODAPE_MARCADORES = (
    "editora nossa senhora",
    "portal da arquidiocese",
    "com aprovacao eclesiastica",
    "publicacao da comissao",
)

# Palavras de masthead/rodapé de publicação + rótulos estruturais/rubricas que
# legitimamente NÃO vão para a montagem. Evitam falso-positivo na cobertura.
_NOISE_FONTE = {
    # publicação / masthead / rodapé
    "folheto", "oficial", "arquidiocese", "arquidiocesano", "arquidiocesana",
    "sebastiao", "sebastião", "versao", "versão", "celular", "jubilar",
    "comunicacao", "comunicação", "social", "arqrio", "www", "org", "http",
    "https", "publicacao", "publicação", "comissao", "comissão", "eclesiastica",
    "eclesiástica", "aprovacao", "aprovação", "editora", "portal", "livraria",
    "nspaz", "ipanema", "angelica", "angélica", "benjamin", "constant",
    "selecionados", "sacra", "producao", "produção", "senhora", "presidente",
    # meses (data de publicação do folheto)
    "janeiro", "fevereiro", "março", "marco", "abril", "junho", "julho",
    "agosto", "setembro", "outubro", "novembro", "dezembro",
    # rótulos estruturais / rubricas editoriais (não é texto rezado)
    "refrao", "refrão", "estrofe", "antifona", "antífona", "rubrica",
    "continua", "inclinam", "inclina", "sentados", "intenções", "intencoes",
}


def _texto_fonte_liturgico(src_norm: str) -> str:
    """Corta o rodapé de publicação do texto-fonte normalizado.

    Usa a ÚLTIMA ocorrência dos marcadores: "Editora Nossa Senhora da Paz"
    aparece tanto no masthead do topo quanto no rodapé; queremos o rodapé.
    """
    corte = len(src_norm)
    for marca in _RODAPE_MARCADORES:
        i = src_norm.rfind(marca)
        if i > 300:  # só corta se já passou o corpo litúrgico
            corte = min(corte, i)
    return src_norm[:corte]


_NOISE_FONTE_FOLD = {_ascii_fold(w) for w in _NOISE_FONTE}


def _tokens_liturgicos(txt: str) -> set[str]:
    """Palavras distintivas (>=5 letras), SEM acento e sem ruído.

    Descola o número do versículo ("10Depois" -> "depois"), dobra sem acento
    (coração -> coracao) e descarta masthead/rodapé/rótulo (_NOISE_FONTE).
    """
    out: set[str] = set()
    for w in txt.split():
        w = _ascii_fold(w.lstrip("0123456789"))  # nº colado + sem acento
        if len(w) >= 5 and w not in _NOISE_FONTE_FOLD:
            out.add(w)
    return out


def _checar_cobertura_liturgica(src_norm: str, mont_norm: str, achados: list[Achado]) -> None:
    """GATE de conteúdo: cada palavra distintiva do CORPO litúrgico do folheto
    tem de aparecer na montagem. É o que garante que nada da missa seja omitido.

    Diferente de `_checar_cobertura` (frouxa, tolera 30-45% de perda por causa
    do ruído de masthead/rodapé), aqui o ruído é removido (rodapé truncado +
    masthead/rótulos filtrados + nº de versículo descolado + acento dobrado) e
    as palavras que faltam são LISTADAS. Uma palavra da fonte conta como
    presente se casa exatamente OU se algum token da montagem começa por ela
    com no máx. 2 letras a mais (cobre truncagem de extração 'aclamaçõ' ->
    'aclamacoes'). Calibrado em missas reais: missa íntegra fica <0,5% (só
    rubrica editorial), qualquer BLOCO omitido passa de 2% (Evangelho ~4%,
    leitura ~9%). Acima de 2% → CRÍTICA → a missa vai a revisão e não chega ao
    fiel incompleta; entre 0,8% e 2% → MÉDIA (revisar possível corte parcial).
    """
    src_lit = _texto_fonte_liturgico(src_norm)
    palavras_src = _tokens_liturgicos(src_lit)
    if len(palavras_src) < 80:
        return  # fonte pequena/ruidosa — não confiável para o gate rígido
    presentes = {
        _ascii_fold(w.lstrip("0123456789")) for w in mont_norm.split()
        if len(_ascii_fold(w.lstrip("0123456789"))) >= 5
    }
    presentes_lista = list(presentes)

    def _presente(w: str) -> bool:
        if w in presentes:
            return True
        # tolerância a truncagem da extração: montagem tem a palavra inteira,
        # a fonte veio cortada ('aclamaco' é prefixo de 'aclamacoes').
        return any(
            t.startswith(w) and 0 < len(t) - len(w) <= 2 for t in presentes_lista
        )

    faltando = sorted(w for w in palavras_src if not _presente(w))
    ratio = len(faltando) / len(palavras_src)
    amostra = ", ".join(faltando[:25])
    if ratio > 0.020:
        achados.append(Achado(
            SEV_CRITICA, 0, "Missa (geral)", "missa",
            "conteudo_liturgico_ausente",
            f"{len(faltando)} palavra(s) do folheto ({ratio:.1%}) NÃO aparecem na "
            f"montagem — conteúdo litúrgico perdido: {amostra}",
        ))
    elif ratio > 0.008:
        achados.append(Achado(
            SEV_MEDIA, 0, "Missa (geral)", "missa",
            "conteudo_liturgico_parcial",
            f"{len(faltando)} palavra(s) do folheto podem estar faltando "
            f"({ratio:.1%}): {amostra}",
        ))


def _checar_resposta_preces_no_fonte(missa: Missa, src_norm: str, achados: list[Achado]) -> None:
    """A resposta (refrão) da Oração dos Fiéis TEM de existir no folheto-fonte.

    Pega exatamente a bomba do refrão GENÉRICO do Missal ("Senhor, escutai a
    nossa prece.") sendo injetado por cima do refrão real do folheto: se a
    resposta renderizada não aparece no PDF-fonte, é texto padrão inventado.
    Dupla checagem (substring exata → cobertura de palavras distintivas) pra
    não falso-positivar por artefato de extração. → CRÍTICA (esconde até revisão).
    """
    from collections import Counter

    for b in missa.blocos:
        if not _eh_oracao_dos_fieis(b):
            continue
        turnos = _turnos_lista(b)
        respostas = [
            (t.get("texto") or "").strip() for t in turnos
            if t.get("falante") == "T" and len(_norm(t.get("texto") or "")) >= 8
        ]
        if not respostas:
            return
        refrao = Counter(respostas).most_common(1)[0][0]
        refrao_norm = _norm(refrao)
        if refrao_norm and refrao_norm in src_norm:
            return  # match exato com o folheto-fonte → ok
        distintivas = [w for w in refrao_norm.split() if len(w) >= 5]
        if not distintivas:
            return
        src_words = set(src_norm.split())
        cob = sum(1 for w in distintivas if w in src_words) / len(distintivas)
        if cob < 0.6:
            achados.append(Achado(
                SEV_CRITICA, b.ordem, b.titulo or "", b.tipo,
                "resposta_preces_fora_do_folheto",
                f"resposta das Preces {refrao[:80]!r} NÃO consta no folheto-fonte "
                f"(cobertura {cob:.0%}) — provável refrão genérico injetado por cima do folheto",
            ))
        return  # só o 1º bloco de Preces


# ---------------------------------------------------------------------------
# Auditoria de uma missa
# ---------------------------------------------------------------------------

def auditar_missa(missa: Missa, texto_fonte: str | None = None) -> RelatorioMissa:
    rel = RelatorioMissa(
        data=missa.data,
        celebracao=missa.celebracao,
        total_blocos=len(missa.blocos),
    )
    for b in missa.blocos:
        if _conteudo_vazio(b):
            rel.achados.append(Achado(
                SEV_MEDIA, b.ordem, b.titulo or "", b.tipo,
                "bloco_vazio", "Sem conteúdo/turnos/refrão/texto",
            ))
            continue
        _checar_preces_nao_separadas(b, rel.achados)
        _checar_artefatos_texto(b, rel.achados)
        _checar_tamanho_minimo(b, rel.achados)
        _checar_canto_vazio(b, rel.achados)
        _checar_tipo_renderizavel(b, rel.achados)
        _checar_posicao_refrao(b, rel.achados)
        _checar_referencia_leitura(b, rel.achados)
    # Checagens em nível de missa
    _checar_template_generico(missa, rel.achados)
    _checar_numeracao(missa, rel.achados)
    _checar_metadados(missa, rel.achados)
    # Cross-check contra o folheto-fonte (SEM LLM): âncoras + cobertura
    if texto_fonte is None:
        texto_fonte = _carregar_texto_fonte(missa)
    if texto_fonte:
        src_norm = _norm(texto_fonte)
        mont_norm = _texto_montagem(missa)
        _checar_ancoras(src_norm, mont_norm, rel.achados)
        _checar_cobertura(src_norm, mont_norm, rel.achados)
        _checar_cobertura_liturgica(src_norm, mont_norm, rel.achados)
        _checar_resposta_preces_no_fonte(missa, src_norm, rel.achados)
    return rel


def _formatar_relatorio(relatorios: list[RelatorioMissa]) -> str:
    linhas = [
        "# Auditoria de Qualidade — Missas",
        "",
        f"Total de missas auditadas: **{len(relatorios)}**",
        "",
    ]
    for rel in relatorios:
        emoji = {
            SEV_CRITICA: "🔴",
            SEV_ALTA: "🟠",
            SEV_MEDIA: "🟡",
            SEV_BAIXA: "🔵",
            "OK": "🟢",
        }.get(rel.severidade_max, "⚪")
        linhas.append(f"## {emoji} {rel.data} — {rel.celebracao or '(sem celebração)'}")
        linhas.append(f"Blocos: {rel.total_blocos} · Achados: {len(rel.achados)} · Severidade: **{rel.severidade_max}**")
        linhas.append("")
        if not rel.achados:
            linhas.append("_Sem problemas detectados._")
            linhas.append("")
            continue
        for a in rel.achados:
            linhas.append(
                f"- [{a.severidade}] bloco #{a.bloco_ordem} "
                f"_{a.bloco_titulo or a.bloco_tipo}_ — **{a.regra}**: {a.detalhe}"
            )
        linhas.append("")
    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# Entry point: roda como parte do scheduler
# ---------------------------------------------------------------------------

def executar_auditoria(lookahead_dias: int = 7) -> dict:
    """Audita missa de hoje + próximos N dias. Grava relatório e marca status."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Iniciando auditoria de missas — lookahead=%d dias", lookahead_dias)
    db = SessionLocal()
    relatorios: list[RelatorioMissa] = []
    criticas = 0
    try:
        hoje = date.today()
        for delta in range(lookahead_dias + 1):
            d = hoje + timedelta(days=delta)
            m = db.query(Missa).filter(Missa.data == d).first()
            if m is None:
                continue
            rel = auditar_missa(m)
            relatorios.append(rel)
            if rel.tem_critica:
                criticas += 1
                # Marca missa pra revisão
                if m.status_processamento != "pendente_revisao":
                    m.status_processamento = "pendente_revisao"
                    db.add(m)
                logger.warning(
                    "Missa %s tem %d achado(s) CRÍTICO(s) — marcada pendente_revisao",
                    d, sum(1 for a in rel.achados if a.severidade == SEV_CRITICA),
                )
            elif rel.achados:
                logger.info("Missa %s: %d achado(s) (%s)", d, len(rel.achados), rel.severidade_max)
        db.commit()
    finally:
        db.close()

    nome = f"auditoria_{date.today().isoformat()}.md"
    arquivo = REPORTS_DIR / nome
    arquivo.write_text(_formatar_relatorio(relatorios), encoding="utf-8")

    resultado = {
        "missas_auditadas": len(relatorios),
        "criticas": criticas,
        "total_achados": sum(len(r.achados) for r in relatorios),
        "relatorio": str(arquivo),
    }
    logger.info("Auditoria finalizada: %s", resultado)
    return resultado
