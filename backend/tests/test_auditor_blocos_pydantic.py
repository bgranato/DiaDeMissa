"""Regressão: o gate de publicação recebe blocos Pydantic (montagem em memória).

Os blocos da união ``Dialogo``/``Oracao``/``Canto`` NÃO têm
``conteudo_estruturado`` — só o ``BlocoLiturgico`` persistido tem. Sem a ponte
``_ce()``, ``conferir_cobertura_liturgica`` levantava AttributeError e a
publicação era BLOQUEADA (caso real de 2026-10-04:
``'Dialogo' object has no attribute 'conteudo_estruturado'``).
"""
from app.schema.missa import Creditos, Dialogo, Missa, Oracao, Secao
from app.services import auditor_missa as A


FONTE = (
    "13. Oração dos Fiéis\n"
    "Apresentemos ao Pai as súplicas, dizendo:\n"
    "Senhor, fortalecei a vossa Igreja na fé.\n"
    "1. Pela Santa Igreja de Deus, rezemos.\n"
)


def _missa_pydantic() -> Missa:
    return Missa(
        data="2026-10-04",
        ano_liturgico="C",
        titulo_celebracao="27º Domingo do Tempo Comum",
        categoria="domingo",
        creditos_cantos=Creditos(),
        blocos=[
            Secao(ordem=1, titulo="Ritos Iniciais"),
            Oracao(ordem=2, titulo="Coleta", texto="Oremos ao Senhor."),
            Dialogo(
                ordem=3,
                titulo="Oração dos Fiéis",
                turnos=[
                    {"falante": "P", "texto": "Apresentemos ao Pai as súplicas, dizendo:"},
                    {"falante": "T", "texto": "Senhor, fortalecei a vossa Igreja na fé."},
                    {"falante": "L", "texto": "Pela Santa Igreja de Deus, rezemos."},
                    {"falante": "T", "texto": "Senhor, fortalecei a vossa Igreja na fé."},
                ],
            ),
        ],
    )


def test_turnos_lista_le_pydantic_sem_conteudo_estruturado():
    bloco = _missa_pydantic().blocos[2]
    assert not hasattr(bloco, "conteudo_estruturado")
    turnos = A._turnos_lista(bloco)
    assert [t["falante"] for t in turnos] == ["P", "T", "L", "T"]


def test_gate_nao_quebra_com_blocos_pydantic():
    missa = _missa_pydantic()
    achados = A.conferir_cobertura_liturgica(FONTE, missa)
    assert isinstance(achados, list)
    preces = [a for a in achados if a.regra == "resposta_preces_fora_do_folheto"]
    assert preces == [], f"refrão real do folheto não pode ser reprovado: {preces}"


def test_refrao_generico_continua_reprovado_em_bloco_pydantic():
    # A correção não pode enfraquecer a regra: refrão genérico do Missal,
    # ausente do folheto-fonte, continua CRÍTICA em bloco Pydantic.
    missa = _missa_pydantic()
    dialogo = missa.blocos[2]
    for t in dialogo.turnos:
        if t.falante == "T":
            t.texto = "Senhor, escutai a nossa prece."
    achados = [
        a for a in A.conferir_cobertura_liturgica(FONTE, missa)
        if a.regra == "resposta_preces_fora_do_folheto"
    ]
    assert len(achados) == 1, f"esperava 1 achado, veio: {achados}"
    assert achados[0].severidade == A.SEV_CRITICA


def test_checar_fonte_fino_nao_quebra_com_blocos_pydantic():
    # Depois de _checar_resposta_preces_no_fonte, o gate chama
    # _checar_fonte_fino (falas/refrão/referência/título) — mesmo perigo.
    missa = _missa_pydantic()
    achados: list = []
    A._checar_fonte_fino(missa, A._norm(FONTE), achados)
    assert isinstance(achados, list)
