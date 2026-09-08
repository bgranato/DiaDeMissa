"""Testes da Parte A — versionamento da montagem e auto-atualização.

(a) montagem nova grava pipeline_version;
(b) missa futura com versão antiga é selecionada para reprocesso;
(c) reprocesso que cai em pendente_revisao NÃO substitui a montagem boa (backup).
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.pipeline_version import pipeline_version
from app.models.missa import Missa as MissaModel, BlocoLiturgico
from app.services.daily_pipeline import selecionar_para_reprocesso
from app.services import reprocesso_seguro
from app.services.reprocesso_seguro import reprocessar_com_seguranca


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Cria só as tabelas do teste (o metadata global tem FKs a tabelas de outros
    # models não importados aqui, ex. igrejas).
    Base.metadata.create_all(bind=engine, tables=[MissaModel.__table__, BlocoLiturgico.__table__])
    Session = sessionmaker(bind=engine)
    s = Session()
    try:
        yield s
    finally:
        s.close()


def _missa(db, d: date, versao, status="concluido", blocos=1):
    m = MissaModel(
        data=d, celebracao="Teste", fonte_pdf_url="http://x/a.pdf",
        pipeline_version=versao, status_processamento=status,
    )
    db.add(m); db.flush()
    for i in range(blocos):
        db.add(BlocoLiturgico(
            missa_id=m.id, ordem=i, tipo="secao", titulo=f"Bloco {i}",
            conteudo_estruturado={"ordem": i, "tipo": "secao", "titulo": f"Bloco {i}"},
            visivel=True,
        ))
    db.commit(); db.refresh(m)
    return m


def _conferencia_aprovada():
    return {
        "conferencia": {
            "conferida": True,
            "iteracoes": 0,
            "divergencias_restantes": [],
            "contrato": {
                "referencia": "PDF oficial da mesma edição",
                "metrica": "zero divergências litúrgicas pendentes",
                "limite_iteracoes": 3,
                "papeis": {"construtor": "montagem", "critico": "conferente", "referencia": "PDF"},
                "fora_do_escopo": ["paginação"],
            },
        }
    }


# --- (a) montagem nova grava pipeline_version ---

def test_pipeline_version_estavel_e_nao_vazia():
    v = pipeline_version()
    assert v and "+" in v            # formato <hash>+<modelo>
    assert v == pipeline_version()   # determinística no processo


def test_persistir_fallback_nao_substitui_boa(db):
    """GUARDA item 0b: persistir_missa com montagem em '[pipeline] fallback='
    NÃO substitui uma montagem boa (concluida, sem fallback) já existente."""
    import app.services.persist_missa as pm
    from app.schema.missa import Missa as MissaSchema, Creditos, Secao
    # missa boa existente (concluida, sem fallback), com 1 bloco marcador
    boa = _missa(db, date(2026, 8, 2), versao=pipeline_version(), status="concluido", blocos=1)
    boa.revisao_json = _conferencia_aprovada()
    db.add(boa); db.commit(); db.refresh(boa)
    id_boa = boa.id
    titulos_antes = [b.titulo for b in
                     db.query(BlocoLiturgico).filter(BlocoLiturgico.missa_id == id_boa).all()]
    # nova montagem para a MESMA data, porém em fallback
    schema = MissaSchema(
        data="2026-08-02", ano_liturgico="C", titulo_celebracao="DEGRADADA",
        categoria="comum", creditos_cantos=Creditos(),
        observacoes="[pipeline] fallback=texto",
        blocos=[Secao(ordem=0, titulo="LIXO")],
    )
    ret = pm.persistir_missa(db, schema)
    assert ret.id == id_boa                                  # devolveu a existente
    titulos_depois = [b.titulo for b in
                      db.query(BlocoLiturgico).filter(BlocoLiturgico.missa_id == id_boa).all()]
    assert titulos_depois == titulos_antes                  # blocos bons preservados
    assert "LIXO" not in titulos_depois


def test_persistir_grava_pipeline_version(db, monkeypatch):
    """persistir_missa deve gravar a pipeline_version atual na missa."""
    from app.schema.missa import Missa as MissaSchema, Creditos, Secao
    import app.services.persist_missa as pm
    # neutraliza pós-processos externos (auditor/gate/notif) — não são o foco
    monkeypatch.setattr(pm, "settings", pm.settings)
    schema = MissaSchema(
        data="2026-08-01", ano_liturgico="C", titulo_celebracao="Teste",
        categoria="comum", creditos_cantos=Creditos(),
        blocos=[Secao(ordem=0, titulo="Ritos Iniciais")],
    )
    m = pm.persistir_missa(db, schema)
    assert m.pipeline_version == pipeline_version()
    assert m.status_processamento == "pendente_revisao"


def test_persistir_so_publica_com_conferencia_completa(db):
    from app.schema.missa import Missa as MissaSchema, Creditos, Secao
    from app.services.persist_missa import persistir_missa

    schema = MissaSchema(
        data="2026-08-03", ano_liturgico="C", titulo_celebracao="Teste",
        categoria="comum", creditos_cantos=Creditos(),
        blocos=[Secao(ordem=0, titulo="Ritos Iniciais")],
    )
    retida = persistir_missa(db, schema, revisao_json={"conferencia": {"conferida": True}})
    assert retida.status_processamento == "pendente_revisao"

    publicada = persistir_missa(db, schema, revisao_json=_conferencia_aprovada())
    assert publicada.status_processamento == "concluido"


def test_conferencia_publicavel_exige_contrato_e_lista_vazia():
    from app.services.persist_missa import conferencia_publicavel

    assert conferencia_publicavel(_conferencia_aprovada()) is True
    assert conferencia_publicavel({"conferencia": {"conferida": True, "contrato": {}}}) is False
    assert conferencia_publicavel({"conferencia": {
        "conferida": True, "contrato": {"referencia": "PDF"}, "divergencias_restantes": [{"tipo": "texto"}],
    }}) is False


def test_retem_legado_sem_gauntlet_e_preserva_aprovada(db):
    from app.services.daily_pipeline import reter_montagens_sem_gauntlet

    legado = _missa(db, date(2026, 8, 4), versao=pipeline_version())
    aprovada = _missa(db, date(2026, 8, 5), versao=pipeline_version())
    aprovada.revisao_json = _conferencia_aprovada()
    db.add(aprovada); db.commit()

    assert reter_montagens_sem_gauntlet(db) == ["2026-08-04"]
    assert legado.status_processamento == "pendente_revisao"
    assert aprovada.status_processamento == "concluido"


def test_leitura_publica_exige_prova_gauntlet_completa():
    from types import SimpleNamespace
    from app.api.routes import missa_publicavel

    legado = SimpleNamespace(status_processamento="concluido", revisao_json={"ok": True}, blocos=[object()])
    aprovada = SimpleNamespace(status_processamento="concluido", revisao_json=_conferencia_aprovada(), blocos=[object()])

    assert missa_publicavel(legado) is False
    assert missa_publicavel(aprovada) is True


# --- (b) seleção de missa futura com versão antiga ---

def test_seleciona_futura_versao_antiga_ou_sem_evidencia_gauntlet(db):
    hoje = date(2026, 7, 26)
    antiga = _missa(db, hoje + timedelta(days=1), versao=None)          # null → antiga
    atual = _missa(db, hoje + timedelta(days=2), versao=pipeline_version())
    atual.revisao_json = _conferencia_aprovada(); db.add(atual); db.commit()
    sem_prova = _missa(db, hoje + timedelta(days=4), versao=pipeline_version())
    passada = _missa(db, hoje - timedelta(days=1), versao=None)          # passada → ignora
    pendente = _missa(db, hoje + timedelta(days=3), versao=None, status="pendente_revisao")

    sel = selecionar_para_reprocesso(db, hoje)
    datas = {m.data for m in sel}
    assert antiga.data in datas
    assert atual.data not in datas        # já na versão atual
    assert sem_prova.data in datas        # versão atual sem Gauntlet ainda precisa migrar
    assert passada.data not in datas      # data < hoje
    assert pendente.data not in datas     # não mexe em pendente_revisao


# --- (c) não-regressão: gate reprovado mantém a montagem boa ---

def test_reprocesso_legado_e_bloqueado(db):
    m = _missa(db, date(2026, 7, 27), versao="antiga+haiku")
    with pytest.raises(RuntimeError, match="Gauntlet"):
        reprocessar_com_seguranca(db, m, b"%PDF-fake")
