"""Agregações da Jornada do usuário: contagens, taxas, ranking, streak.

Tudo computado em SQL/SQLAlchemy — frontend só renderiza. Ordem de execução
escolhida pra usar uma só leitura do histórico do usuário sempre que possível.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.usuario import HistoricoUsuario, Usuario
from app.models.missa import Missa


# Critério "considerado missa concluída/atendida" pra relatório
_LIMIAR_CONCLUIDO = 50.0  # >= 50% lido conta como "foi à missa"


@dataclass
class Periodo:
    inicio: date
    fim: date  # inclusivo
    label: str


def _periodos_referencia(hoje: date) -> dict[str, Periodo]:
    """Define semana atual (segunda → domingo), mês atual e ano atual."""
    # Semana: segunda-feira da semana atual até hoje
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    inicio_mes = hoje.replace(day=1)
    inicio_ano = hoje.replace(month=1, day=1)
    return {
        "semana": Periodo(inicio_semana, hoje, "Esta semana"),
        "mes": Periodo(inicio_mes, hoje, "Este mês"),
        "ano": Periodo(inicio_ano, hoje, "Este ano"),
    }


def _domingos_e_solenidades(db: Session, inicio: date, fim: date) -> int:
    """Quantas missas obrigatórias (domingo + solenidade) no intervalo.

    Conta domingos (ISO weekday 7) + qualquer missa do BD cuja categoria
    seja 'Solenidade' (mesmo que não-domingo). Domingo que coincide com
    Solenidade só conta uma vez.
    """
    # Domingos no intervalo
    dias_obrigatorios: set[date] = set()
    d = inicio
    while d <= fim:
        if d.weekday() == 6:  # 6 = domingo
            dias_obrigatorios.add(d)
        d += timedelta(days=1)
    # Solenidades no BD dentro do intervalo
    solenidades = db.query(Missa.data).filter(
        Missa.data >= inicio,
        Missa.data <= fim,
        Missa.categoria.ilike("solenidade"),
    ).all()
    for (data_sol,) in solenidades:
        dias_obrigatorios.add(data_sol)
    return len(dias_obrigatorios)


def _contar_missas_periodo(historicos: list, missa_por_id: dict, inicio: date, fim: date) -> int:
    return sum(
        1 for h in historicos
        if h.missa_id in missa_por_id
        and inicio <= missa_por_id[h.missa_id].data <= fim
        and (h.percentual_lido or 0) >= _LIMIAR_CONCLUIDO
    )


def _streak_atual(historicos: list, missa_por_id: dict, hoje: date) -> int:
    """Domingos consecutivos com missa concluída a partir do último domingo.

    Calculado retrocedendo de domingo em domingo até achar um sem missa.
    """
    # Mapa: data -> tem missa concluída?
    datas_concluidas = {
        missa_por_id[h.missa_id].data
        for h in historicos
        if h.missa_id in missa_por_id and (h.percentual_lido or 0) >= _LIMIAR_CONCLUIDO
    }
    # Último domingo (hoje ou anterior)
    delta_pra_domingo = (hoje.weekday() - 6) % 7
    ultimo_domingo = hoje - timedelta(days=delta_pra_domingo)
    # Se hoje ainda não é domingo OU é domingo mas ainda não foi à missa,
    # começa do domingo anterior pra não punir o usuário.
    if ultimo_domingo not in datas_concluidas:
        ultimo_domingo -= timedelta(days=7)
    streak = 0
    d = ultimo_domingo
    while d in datas_concluidas:
        streak += 1
        d -= timedelta(days=7)
    return streak


def _serie_12_meses(historicos: list, missa_por_id: dict, hoje: date) -> list[dict]:
    """Contagem mensal nos últimos 12 meses (do mais antigo pro mais recente)."""
    contador: Counter = Counter()
    for h in historicos:
        m = missa_por_id.get(h.missa_id)
        if not m or (h.percentual_lido or 0) < _LIMIAR_CONCLUIDO:
            continue
        chave = (m.data.year, m.data.month)
        contador[chave] += 1
    serie = []
    # Gera 12 meses pra trás incluindo o mês corrente
    ano = hoje.year
    mes = hoje.month
    pontos = []
    for _ in range(12):
        pontos.append((ano, mes))
        mes -= 1
        if mes == 0:
            mes = 12
            ano -= 1
    for (ano, mes) in reversed(pontos):
        serie.append({
            "ano": ano,
            "mes": mes,
            "label": f"{mes:02d}/{ano % 100:02d}",
            "missas": contador.get((ano, mes), 0),
        })
    return serie


def _ranking_igrejas(db: Session, historicos: list) -> list[dict]:
    """Top igrejas frequentadas (histórico completo, missa >= limiar)."""
    from app.models.igreja import Igreja
    contador: Counter = Counter()
    for h in historicos:
        if (h.percentual_lido or 0) < _LIMIAR_CONCLUIDO:
            continue
        if h.igreja_id:
            contador[h.igreja_id] += 1
    if not contador:
        return []
    ids = list(contador.keys())
    igrejas = {ig.id: ig for ig in db.query(Igreja).filter(Igreja.id.in_(ids)).all()}
    total = sum(contador.values())
    ranking = []
    for igreja_id, n in contador.most_common():
        ig = igrejas.get(igreja_id)
        if not ig:
            continue
        ranking.append({
            "igreja_id": igreja_id,
            "nome": ig.nome,
            "cidade": ig.cidade,
            "missas": n,
            "pct": round(n / total * 100, 1) if total else 0,
        })
    return ranking


def montar_relatorio(db: Session, usuario: Usuario) -> dict:
    """Gera o relatório completo da Jornada do usuário."""
    hoje = date.today()
    periodos = _periodos_referencia(hoje)

    # Lê histórico uma vez
    historicos = db.query(HistoricoUsuario).filter(
        HistoricoUsuario.usuario_id == usuario.id,
    ).all()
    missa_ids = [h.missa_id for h in historicos]
    missa_por_id = {
        m.id: m for m in db.query(Missa).filter(Missa.id.in_(missa_ids)).all()
    } if missa_ids else {}

    # Contagens por período
    contagens = {}
    for chave, p in periodos.items():
        n = _contar_missas_periodo(historicos, missa_por_id, p.inicio, p.fim)
        dias_periodo = (p.fim - p.inicio).days + 1
        recomendado = _domingos_e_solenidades(db, p.inicio, p.fim)
        contagens[chave] = {
            "label": p.label,
            "missas": n,
            "dias_periodo": dias_periodo,
            "recomendado_minimo": recomendado,
            "taxa_vs_dias": round(n / dias_periodo * 100, 1) if dias_periodo else 0,
            "taxa_vs_recomendado": (
                round(n / recomendado * 100, 1) if recomendado else None
            ),
        }

    # Meta do usuário (se setada) — taxa mensal
    meta_mensal = getattr(usuario, "meta_missas_mensal", None)
    if meta_mensal:
        contagens["mes"]["meta_usuario"] = meta_mensal
        contagens["mes"]["taxa_vs_meta"] = round(
            contagens["mes"]["missas"] / meta_mensal * 100, 1
        )

    return {
        "totais": {
            "missas_total": sum(
                1 for h in historicos
                if (h.percentual_lido or 0) >= _LIMIAR_CONCLUIDO
            ),
            "primeira_missa": min(
                (missa_por_id[h.missa_id].data for h in historicos
                 if h.missa_id in missa_por_id),
                default=None,
            ),
        },
        "periodos": contagens,
        "streak_domingos": _streak_atual(historicos, missa_por_id, hoje),
        "serie_12_meses": _serie_12_meses(historicos, missa_por_id, hoje),
        "ranking_igrejas": _ranking_igrejas(db, historicos),
        "meta_missas_mensal": meta_mensal,
    }
