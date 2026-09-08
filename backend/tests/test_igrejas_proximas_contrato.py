"""Critérios mínimos de aceite do endpoint de proximidade de igrejas."""
from __future__ import annotations

import sys
import types
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# A extração de PDFs não participa deste contrato. A instalação local de testes
# não carrega PyMuPDF, portanto isolamos o import para exercitar a rota pura.
sys.modules.setdefault("fitz", types.SimpleNamespace())

from app.api import routes
from app.core.database import Base, get_db
from app.models.igreja import Igreja
from app.models.uso_geocoding import UsoGeocodingMensal


class _Query:
    def __init__(self, items):
        self.items = items

    def all(self):
        return self.items


class _Db:
    def __init__(self, igrejas):
        self.igrejas = igrejas

    def query(self, _model):
        return _Query(self.igrejas)


def _igreja(identificador: int, latitude: float) -> SimpleNamespace:
    return SimpleNamespace(
        id=identificador,
        nome=f"Paróquia {identificador}",
        endereco="Rua de Teste, 1 - Bairro",
        cidade="Rio de Janeiro",
        estado="RJ",
        cep=None,
        telefone=None,
        site=None,
        lat=latitude,
        lng=0.0,
        observacoes=None,
        horarios_missa=None,
        data_criacao=datetime.now(timezone.utc),
        arqrio_local_id=identificador,
    )


def _listar(igrejas, **kwargs):
    return routes.listar_igrejas(
        limite=50,
        usuario=None,
        db=_Db(igrejas),
        **kwargs,
    )


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[Igreja.__table__, UsoGeocodingMensal.__table__])
    Session = sessionmaker(bind=engine)

    app = FastAPI()
    app.include_router(routes.router)

    def _db_teste():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db_teste
    app.dependency_overrides[routes.obter_usuario_opcional] = lambda: None
    with TestClient(app) as teste:
        yield teste, Session


def _popular(session, igrejas):
    for item in igrejas:
        session.add(Igreja(
            id=item.id,
            nome=item.nome,
            endereco=item.endereco,
            cidade=item.cidade,
            estado=item.estado,
            lat=item.lat,
            lng=item.lng,
            arqrio_local_id=item.arqrio_local_id,
        ))
    session.commit()


def test_raio_usa_distancia_bruta_antes_do_arredondamento(monkeypatch):
    dentro = _igreja(1, 1.0)
    limite = _igreja(2, 2.0)
    fora_mas_arredonda = _igreja(3, 3.0)
    distancias = {1.0: 0.999, 2.0: 1.0, 3.0: 1.004}
    monkeypatch.setattr(routes, "_calc_distancia_km", lambda _a, _b, destino, _d: distancias[destino])

    resultado = _listar([fora_mas_arredonda, limite, dentro], lat=0.0, lng=0.0, raio_km=1)

    assert [item["id"] for item in resultado] == [1, 2]
    assert resultado[1]["distancia_km"] == 1.0


def test_ordem_tem_desempate_estavel_por_id(monkeypatch):
    segunda = _igreja(2, 2.0)
    primeira = _igreja(1, 1.0)
    monkeypatch.setattr(routes, "_calc_distancia_km", lambda *_args: 0.5)

    resultado = _listar([segunda, primeira], lat=0.0, lng=0.0, raio_km=1)

    assert [item["id"] for item in resultado] == [1, 2]


@pytest.mark.parametrize("raio", [1, 3, 5, 10])
def test_http_inclui_borda_do_raio_e_exclui_o_que_ultrapassa(client, monkeypatch, raio):
    dentro = _igreja(1, 1.0)
    limite = _igreja(2, 2.0)
    fora = _igreja(3, 3.0)
    distancias = {1.0: raio - 0.001, 2.0: float(raio), 3.0: raio + 0.001}
    monkeypatch.setattr(routes, "_calc_distancia_km", lambda _a, _b, destino, _d: distancias[destino])
    teste, Session = client
    db = Session()
    _popular(db, [fora, limite, dentro])
    db.close()

    resposta = teste.get("/igrejas", params={"lat": 0, "lng": 0, "raio_km": raio})

    assert resposta.status_code == 200
    assert [item["id"] for item in resposta.json()] == [1, 2]


@pytest.mark.parametrize(
    "params",
    [
        {"lat": 0},
        {"lng": 0},
        {"raio_km": 5},
        {"lat": 0, "lng": 0, "raio_km": 2},
        {"lat": 0, "lng": 0, "raio_km": 7},
        {"lat": 0, "lng": 0, "raio_km": 11},
        {"lat": 0, "lng": 0, "raio_km": 0},
        {"lat": 0, "lng": 0, "raio_km": -1},
        {"lat": 91, "lng": 0},
        {"lat": 0, "lng": 181},
        {"lat": "NaN", "lng": 0},
        {"lat": "inf", "lng": 0},
    ],
)
def test_http_rejeita_entrada_de_proximidade_invalida(client, params):
    teste, _ = client

    resposta = teste.get("/igrejas", params=params)

    assert resposta.status_code == 422


def test_http_localiza_endereco_sem_persistir_texto(client, monkeypatch):
    monkeypatch.setattr(routes, "geocoding_configurado", lambda: True)
    monkeypatch.setattr(routes, "geocodificar_query_google", lambda _endereco: (-22.9848, -43.2245))
    teste, Session = client
    db = Session()
    _popular(db, [_igreja(99, -22.98)])
    antes = db.query(Igreja).count()
    db.close()

    resposta = teste.post("/igrejas/localizar-endereco", json={"endereco": "Avenida Ataulfo de Paiva, 527, Leblon"})

    assert resposta.status_code == 200
    assert resposta.json() == {"lat": -22.9848, "lng": -43.2245}
    db = Session()
    assert db.query(Igreja).count() == antes
    assert db.query(Igreja).filter(Igreja.endereco.contains("Ataulfo")).count() == 0
    db.close()


def test_http_bloqueia_geocoding_apos_teto_mensal_sem_salvar_endereco(client, monkeypatch):
    monkeypatch.setenv("GEOCODING_MENSAL_MAXIMO", "1")
    monkeypatch.setattr(routes, "geocoding_configurado", lambda: True)
    chamadas_google = []
    monkeypatch.setattr(routes, "geocodificar_query_google", lambda endereco: chamadas_google.append(endereco) or (-22.9848, -43.2245))
    teste, Session = client

    primeira = teste.post("/igrejas/localizar-endereco", json={"endereco": "Leblon, Rio de Janeiro"})
    segunda = teste.post("/igrejas/localizar-endereco", json={"endereco": "Gávea, Rio de Janeiro"})

    assert primeira.status_code == 200
    assert segunda.status_code == 429
    assert chamadas_google == ["Leblon, Rio de Janeiro"]
    db = Session()
    uso = db.query(UsoGeocodingMensal).one()
    assert uso.consultas == 1
    assert not hasattr(uso, "endereco")
    db.close()


def test_http_rejeita_endereco_nao_localizado(client, monkeypatch):
    monkeypatch.setattr(routes, "geocoding_configurado", lambda: True)
    monkeypatch.setattr(routes, "geocodificar_query_google", lambda _endereco: None)
    teste, _ = client

    resposta = teste.post("/igrejas/localizar-endereco", json={"endereco": "Lugar inexistente"})

    assert resposta.status_code == 422


def test_http_informa_indisponibilidade_do_geocodificador(client, monkeypatch):
    monkeypatch.setattr(routes, "geocoding_configurado", lambda: True)
    def indisponivel(_endereco):
        raise routes.GeocodingIndisponivelError("teste")

    monkeypatch.setattr(routes, "geocodificar_query_google", indisponivel)
    teste, _ = client

    resposta = teste.post("/igrejas/localizar-endereco", json={"endereco": "Leblon, Rio de Janeiro"})

    assert resposta.status_code == 503


@pytest.mark.parametrize(
    "corpo",
    [
        None,
        {},
        {"endereco": 123},
        {"endereco": "abcd"},
        {"endereco": "     "},
        {"endereco": "a" * 301},
    ],
)
def test_http_rejeita_corpo_de_endereco_invalido(client, corpo):
    teste, _ = client

    resposta = teste.post("/igrejas/localizar-endereco", json=corpo)

    assert resposta.status_code == 422


@pytest.mark.parametrize("ponto", [(float("nan"), 0.0), (0.0, float("inf")), (91.0, 0.0), (0.0, 181.0)])
def test_http_rejeita_coordenada_invalida_do_provedor(client, monkeypatch, ponto):
    monkeypatch.setattr(routes, "geocoding_configurado", lambda: True)
    monkeypatch.setattr(routes, "geocodificar_query_google", lambda _endereco: ponto)
    teste, _ = client

    resposta = teste.post("/igrejas/localizar-endereco", json={"endereco": "Leblon, Rio de Janeiro"})

    assert resposta.status_code == 502


@pytest.mark.parametrize(
    ("lat", "lng", "raio"),
    [
        (0.0, None, None),
        (None, 0.0, None),
        (91.0, 0.0, None),
        (0.0, 181.0, None),
        (float("nan"), 0.0, None),
        (0.0, 0.0, 2),
        (None, None, 5),
    ],
)
def test_entrada_de_proximidade_invalida_e_rejeitada(lat, lng, raio):
    with pytest.raises(HTTPException) as erro:
        _listar([], lat=lat, lng=lng, raio_km=raio)
    assert erro.value.status_code == 422
