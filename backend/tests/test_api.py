from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)


class TestApiMissa:
    def test_endpoint_missa_atual_retorna_json_valido(self):
        response = client.get("/missa/atual")
        assert response.status_code == 200
        data = response.json()
        assert data["titulo_celebracao"] == "Ascensão do Senhor"
        assert data["blocos"][0]["tipo"] == "canto"
        assert data["blocos"][0]["postura"] == "de_pe"

    def test_endpoint_retorna_canto_entrada_limpo(self):
        response = client.get("/missa/atual")
        canto = response.json()["blocos"][0]
        refrao = canto["refrao"]
        for verso in refrao:
            assert "/" not in verso
            assert "REFRÃO" not in verso
            assert "Ale-luia" not in verso
        assert len(canto["estrofes"]) == 4

    def test_canto_sem_artefatos(self):
        response = client.get("/missa/atual")
        canto = response.json()["blocos"][0]
        for estrofe in canto["estrofes"]:
            for verso in estrofe:
                assert "/" not in verso, f"Barra encontrada: {verso}"
                assert "Entrada:" not in verso, f"Crédito encontrado: {verso}"
