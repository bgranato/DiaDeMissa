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


# --- (b) seleção de missa futura com versão antiga ---

def test_seleciona_futura_versao_antiga(db):
    hoje = date(2026, 7, 26)
    antiga = _missa(db, hoje + timedelta(days=1), versao=None)          # null → antiga
    atual = _missa(db, hoje + timedelta(days=2), versao=pipeline_version())
    passada = _missa(db, hoje - timedelta(days=1), versao=None)          # passada → ignora
    pendente = _missa(db, hoje + timedelta(days=3), versao=None, status="pendente_revisao")

    sel = selecionar_para_reprocesso(db, hoje)
    datas = {m.data for m in sel}
    assert antiga.data in datas
    assert atual.data not in datas        # já na versão atual
    assert passada.data not in datas      # data < hoje
    assert pendente.data not in datas     # não mexe em pendente_revisao


# --- (c) não-regressão: gate reprovado mantém a montagem boa ---

def test_reprocesso_reprovado_nao_substitui(db, monkeypatch):
    hoje = date(2026, 7, 26)
    m = _missa(db, hoje + timedelta(days=1), versao="antiga+haiku", blocos=3)
    ids_titulos_antes = [(b.ordem, b.titulo) for b in
                         db.query(BlocoLiturgico).filter(BlocoLiturgico.missa_id == m.id).order_by(BlocoLiturgico.ordem)]

    # processar_pdf não precisa retornar nada útil (persistir é mockado)
    monkeypatch.setattr("app.pipeline.processar_pdf", lambda p: object(), raising=False)

    def persist_ruim(db_, missa_pyd, **kw):
        # simula reprocesso que DEGRADA: apaga blocos, põe 1 só, pendente_revisao
        mm = db_.query(MissaModel).filter(MissaModel.data == m.data).first()
        db_.query(BlocoLiturgico).filter(BlocoLiturgico.missa_id == mm.id).delete()
        db_.add(BlocoLiturgico(missa_id=mm.id, ordem=0, tipo="secao", titulo="DEGRADADO",
                               conteudo_estruturado={"ordem": 0}, visivel=True))
        mm.status_processamento = "pendente_revisao"
        mm.observacoes = "[pipeline] fallback=texto"
        mm.pipeline_version = pipeline_version()
        db_.add(mm); db_.commit(); db_.refresh(mm)
        return mm
    monkeypatch.setattr("app.services.persist_missa.persistir_missa", persist_ruim, raising=False)

    res = reprocessar_com_seguranca(db, m, b"%PDF-fake")

    assert res["resultado"] == "revertido"
    m2 = db.query(MissaModel).filter(MissaModel.data == m.data).first()
    assert m2.status_processamento == "concluido"        # montagem boa preservada
    assert m2.pipeline_version == "antiga+haiku"          # versão restaurada
    ids_titulos_depois = [(b.ordem, b.titulo) for b in
                          db.query(BlocoLiturgico).filter(BlocoLiturgico.missa_id == m2.id).order_by(BlocoLiturgico.ordem)]
    assert ids_titulos_depois == ids_titulos_antes        # 3 blocos originais de volta
    assert "DEGRADADO" not in [t for _, t in ids_titulos_depois]


def test_reprocesso_fallback_nao_substitui(db, monkeypatch):
    """Mesmo 'concluido', se a montagem caiu em '[pipeline] fallback=' (multimodal
    indisponível), NÃO substitui a montagem existente — reverte ao backup."""
    hoje = date(2026, 7, 26)
    m = _missa(db, hoje + timedelta(days=1), versao="antiga+haiku", blocos=3)
    titulos_antes = [b.titulo for b in
                     db.query(BlocoLiturgico).filter(BlocoLiturgico.missa_id == m.id).order_by(BlocoLiturgico.ordem)]

    monkeypatch.setattr("app.pipeline.processar_pdf", lambda p: object(), raising=False)

    def persist_fallback(db_, missa_pyd, **kw):
        mm = db_.query(MissaModel).filter(MissaModel.data == m.data).first()
        db_.query(BlocoLiturgico).filter(BlocoLiturgico.missa_id == mm.id).delete()
        db_.add(BlocoLiturgico(missa_id=mm.id, ordem=0, tipo="secao", titulo="FALLBACK",
                               conteudo_estruturado={"ordem": 0}, visivel=True))
        mm.status_processamento = "concluido"                 # gate passou...
        mm.observacoes = "[pipeline] fallback=texto"          # ...mas foi fallback!
        mm.pipeline_version = pipeline_version()
        db_.add(mm); db_.commit(); db_.refresh(mm)
        return mm
    monkeypatch.setattr("app.services.persist_missa.persistir_missa", persist_fallback, raising=False)

    res = reprocessar_com_seguranca(db, m, b"%PDF-fake")

    assert res["resultado"] == "revertido"
    m2 = db.query(MissaModel).filter(MissaModel.data == m.data).first()
    assert m2.pipeline_version == "antiga+haiku"              # versão boa restaurada
    titulos_depois = [b.titulo for b in
                      db.query(BlocoLiturgico).filter(BlocoLiturgico.missa_id == m2.id).order_by(BlocoLiturgico.ordem)]
    assert titulos_depois == titulos_antes                    # backup restaurado
    assert "FALLBACK" not in titulos_depois
