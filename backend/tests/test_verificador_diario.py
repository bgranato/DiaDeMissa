"""Testes do verificador barato das fontes oficiais (executar_pipeline_diario).

Contrato verificado:
1. datas_disponiveis só devolve edições COMPLETAS (Celular + Celebrante);
2. missa já concluída + Gauntlet completo → 'ja_publicada' SEM download/LLM;
3. datas passadas e edições incompletas → 'sem_novidade', zero download;
4. edição nova é montada UMA vez; na segunda rodada só pula;
5. falha numa data não interrompe as demais;
6. página indisponível → 'erro_download';
7. baixar_fontes_oficiais reaproveita o HTML (sem refetch da página);
8. modo explícito (data_referencia) preserva o contrato antigo (baixa e decide por hash).
"""
from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.pipeline.clean as clean_mod
import app.pipeline.download as download_mod
import app.pipeline.extract as extract_mod
import app.services.daily_pipeline as dp
import app.services.publicacao_convergente as pc
from app.core.database import Base
from app.core.pipeline_version import pipeline_version
from app.models.missa import BlocoLiturgico, Missa as MissaModel
from app.pipeline.download import FonteFolheto, datas_disponiveis, hash_pdf

PDF_FAKE = b"%PDF-1.5 conteudo oficial fake"
HOJE = date.today()
D_PASSADA = HOJE - timedelta(days=7)
D_FUTURA = HOJE + timedelta(days=5)
D_FUTURA_2 = HOJE + timedelta(days=12)


def _html(completas=(), incompletas=()) -> str:
    linhas: list[str] = []
    for d in completas:
        dia = d.strftime("%d-%m-%Y")
        ext = d.strftime("%d/%m/%Y")
        linhas += [
            f'<a href="/assembleia-{dia}.pdf" data-folheto-id="{dia}-assembleia" '
            f'data-folheto-titulo="{ext} (Assembléia)">Assembleia</a>',
            f'<a href="/celular-{dia}.pdf" data-folheto-id="{dia}-celular" '
            f'data-folheto-titulo="{ext} (Celular)">Celular</a>',
            f'<a href="/celebrante-{dia}.pdf" data-folheto-id="{dia}-celebrante" '
            f'data-folheto-titulo="{ext} (Celebrante)">Celebrante</a>',
        ]
    for d in incompletas:
        dia = d.strftime("%d-%m-%Y")
        ext = d.strftime("%d/%m/%Y")
        linhas.append(
            f'<a href="/assembleia-{dia}.pdf" data-folheto-id="{dia}-assembleia" '
            f'data-folheto-titulo="{ext} (Assembléia)">Assembleia</a>',
        )
    return "\n".join(linhas)


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


@pytest.fixture()
def env(monkeypatch, tmp_path):
    """Verificador isolado: BD em memória, página/downloads/montagem controlados."""
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=eng, tables=[MissaModel.__table__, BlocoLiturgico.__table__])
    Session = sessionmaker(bind=eng)
    monkeypatch.setattr(dp, "SessionLocal", Session)
    monkeypatch.setattr(dp, "CACHE_DIR", tmp_path)
    monkeypatch.setenv("AUTO_ATUALIZAR_MISSAS", "0")

    estado = SimpleNamespace(
        html="",
        baixar=[],           # datas em que o download foi chamado
        montar=[],           # datas em que a montagem foi chamada
        falhar_pagina=False,
        baixar_falha_em=set(),  # datas com download propositalmente quebrado
    )

    def _pagina():
        if estado.falhar_pagina:
            raise RuntimeError("página de folhetos indisponível (teste)")
        return estado.html

    def _baixar(data_edicao, *, html=None):
        assert html, "baixar_fontes_oficiais deve reaproveitar o HTML já lido"
        if data_edicao in estado.baixar_falha_em:
            raise download_mod.FonteFolhetoIndisponivel(f"indisponível para {data_edicao} (teste)")
        estado.baixar.append(data_edicao)
        cel = FonteFolheto(data=data_edicao, tipo="celular", url="https://x/celular.pdf", titulo="Celular")
        cele = FonteFolheto(data=data_edicao, tipo="celebrante", url="https://x/celebrante.pdf", titulo="Celebrante")
        return cel, PDF_FAKE, cele, PDF_FAKE

    def _montar(db, data_iso, pdf_bytes, texto, **kwargs):
        estado.montar.append(data_iso)
        m = MissaModel(
            data=date.fromisoformat(data_iso),
            celebracao="Teste",
            fonte_pdf_url="https://x/celular.pdf",
            pdf_hash=hash_pdf(pdf_bytes),
            pipeline_version=pipeline_version(),
            status_processamento="concluido",
            revisao_json=_conferencia_aprovada(),
        )
        db.add(m)
        db.commit()
        return {
            "data": data_iso, "resultado": "publicada", "conferida": True,
            "iteracoes": 0, "custo_usd": 0.0, "divergencias": [],
        }

    monkeypatch.setattr(dp, "obter_pagina_folhetos", _pagina)
    monkeypatch.setattr(dp, "baixar_fontes_oficiais", _baixar)
    monkeypatch.setattr(pc, "montar_e_publicar", _montar)
    monkeypatch.setattr(extract_mod, "extrair_texto_estruturado", lambda path: "texto bruto")
    monkeypatch.setattr(clean_mod, "limpar", lambda texto: texto)

    def _seed(d, *, conferida=True, pdf_hash=None, status="concluido"):
        m = MissaModel(
            data=d, celebracao="Seed", fonte_pdf_url="https://x/celular.pdf",
            pdf_hash=pdf_hash, pipeline_version=pipeline_version(),
            status_processamento=status,
            revisao_json=_conferencia_aprovada() if conferida else {"conferencia": {"conferida": True}},
        )
        s = Session()
        try:
            s.add(m)
            s.commit()
            s.refresh(m)
            return m.id
        finally:
            s.close()

    return SimpleNamespace(Session=Session, estado=estado, seed=_seed, tmp_path=tmp_path)


# --- 1) listagem de edições completas ---

def test_datas_disponiveis_so_edicoes_completas():
    html = _html(completas=[D_PASSADA, D_FUTURA], incompletas=[D_FUTURA_2])
    so_celular = (
        '<a href="/c.pdf" data-folheto-id="20-10-2026-celular" '
        'data-folheto-titulo="20/10/2026 (Celular)">Celular</a>'
    )

    assert datas_disponiveis(html + so_celular) == sorted([D_PASSADA, D_FUTURA])


# --- 2) pula publicada sem download (o ciclo saudável custa só o GET) ---

def test_verificador_pula_publicada_sem_download(env):
    id_missa = env.seed(D_FUTURA)
    env.estado.html = _html(completas=[D_FUTURA])

    ret = dp.executar_pipeline_diario()

    assert ret["status"] == "ja_publicada"
    assert ret["resultados"][0]["status"] == "ja_publicada"
    assert ret["missa_id"] == id_missa            # contrato antigo espelhado no topo
    assert env.estado.baixar == []                 # zero download
    assert env.estado.montar == []                 # zero LLM
    assert not (env.tmp_path / "archive").exists()  # nem tocou no cache


# --- 3) datas passadas e edições incompletas fora do modo automático ---

def test_verificador_ignora_passadas_e_incompletas(env):
    env.estado.html = _html(completas=[D_PASSADA], incompletas=[D_FUTURA])

    ret = dp.executar_pipeline_diario()

    assert ret["status"] == "sem_novidade"
    assert ret["resultados"] == []
    assert env.estado.baixar == []
    assert env.estado.montar == []


# --- 4) monta UMA vez; depois só espera a próxima edição ---

def test_verificador_monta_data_nova_so_uma_vez(env):
    env.estado.html = _html(completas=[D_FUTURA])

    primeira = dp.executar_pipeline_diario()

    assert primeira["status"] == "ok"
    assert env.estado.baixar == [D_FUTURA]
    assert env.estado.montar == [D_FUTURA.isoformat()]
    assert (env.tmp_path / "archive" / f"{D_FUTURA.isoformat()}.pdf").exists()
    assert (env.tmp_path / "archive" / f"{D_FUTURA.isoformat()}-celebrante.pdf").exists()

    segunda = dp.executar_pipeline_diario()

    assert segunda["status"] == "ja_publicada"
    assert env.estado.baixar == [D_FUTURA]                 # 2ª rodada: sem download
    assert env.estado.montar == [D_FUTURA.isoformat()]     # 2ª rodada: sem remontagem


# --- 5) falha numa data não interrompe as demais ---

def test_erro_de_uma_data_nao_interrompe_as_demais(env):
    env.estado.html = _html(completas=[D_FUTURA, D_FUTURA_2])
    env.estado.baixar_falha_em = {D_FUTURA}

    ret = dp.executar_pipeline_diario()

    assert ret["status"] == "erro_download"
    assert [r["status"] for r in ret["resultados"]] == ["erro_download", "ok"]
    assert env.estado.montar == [D_FUTURA_2.isoformat()]   # a boa foi montada


# --- 6) página indisponível: erro explícito, sem exceção propagada ---

def test_pagina_indisponivel_retorna_erro_download(env):
    env.estado.falhar_pagina = True

    ret = dp.executar_pipeline_diario()

    assert ret["status"] == "erro_download"
    assert ret["resultados"] == []
    assert env.estado.baixar == []


# --- 7) HTML reaproveitado: nenhum refetch da página ---

def test_baixar_fontes_reaproveita_html_sem_refetch(monkeypatch):
    class _Resp:
        content = PDF_FAKE

        def raise_for_status(self):
            pass

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url):
            return _Resp()

    def _explode(*args, **kwargs):
        raise AssertionError("refetch da página — o HTML já estava em mãos")

    monkeypatch.setattr(download_mod, "obter_pagina_folhetos", _explode)
    monkeypatch.setattr(download_mod.httpx, "Client", _Client)

    celular, conteudo, celebrante, conteudo_celebrante = download_mod.baixar_fontes_oficiais(
        D_FUTURA, html=_html(completas=[D_FUTURA]),
    )

    assert celular.tipo == "celular"
    assert celebrante.tipo == "celebrante"
    assert conteudo == PDF_FAKE
    assert conteudo_celebrante == PDF_FAKE


# --- 8) modo explícito (data_referencia) preserva o contrato antigo ---

def test_data_referencia_explicita_preserva_contrato_antigo(env):
    id_missa = env.seed(D_PASSADA, pdf_hash=hash_pdf(PDF_FAKE))
    env.estado.html = _html(completas=[D_PASSADA])

    ret = dp.executar_pipeline_diario(data_referencia=D_PASSADA)

    assert env.estado.baixar == [D_PASSADA]   # sem o 'skip' barato: baixa mesmo publicada
    assert env.estado.montar == []            # hash inalterado → não remonta
    assert ret["status"] == "ignorado"
    assert ret["missa_id"] == id_missa
