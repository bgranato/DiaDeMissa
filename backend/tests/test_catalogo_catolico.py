from types import SimpleNamespace

from app.services.catalogo_catolico import eh_local_catolico_oficial


def test_catalogo_publico_exige_vinculo_com_a_arquidiocese():
    assert eh_local_catolico_oficial(SimpleNamespace(arqrio_local_id=123))
    assert not eh_local_catolico_oficial(SimpleNamespace(arqrio_local_id=None))
