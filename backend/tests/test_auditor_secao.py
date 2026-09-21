"""Regressão: seções são divisores sem os campos de um bloco de conteúdo."""
from app.schema.missa import Creditos, Missa, Oracao, Secao
from app.services.auditor_missa import _texto_montagem


def test_cobertura_aceita_secao_sem_conteudo():
    missa = Missa(
        data="2026-09-20",
        ano_liturgico="C",
        titulo_celebracao="25º Domingo do Tempo Comum",
        categoria="domingo",
        creditos_cantos=Creditos(),
        blocos=[
            Secao(ordem=1, titulo="Ritos Iniciais", descricao="A assembleia se reúne."),
            Oracao(ordem=2, titulo="Oração do dia", texto="Oremos ao Senhor."),
        ],
    )

    texto = _texto_montagem(missa)

    assert "ritos iniciais" in texto
    assert "assembleia se reúne" in texto
    assert "oremos ao senhor" in texto
