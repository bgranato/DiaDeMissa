import pytest
from app.pipeline.clean import limpar


class TestClean:
    def test_dehifenizacao(self):
        assert limpar("Ale-\nluia") == "Aleluia"

    def test_dehifenizacao_espacada(self):
        assert limpar("vence-\n   dor") == "vencedor"

    def test_juncao_linha_quebrada(self):
        assert limpar("celebra a solenida-\nde da Ascensão") == "celebra a solenidade da Ascensão"

    def test_juncao_apos_virgula(self):
        assert limpar("disse,\ne foi") == "disse, e foi"

    def test_nao_junta_apos_ponto(self):
        assert limpar("Senhor.\nEle") == "Senhor.\nEle"

    def test_separa_sigla_grudada(self):
        assert limpar("P.Em nome") == "P. Em nome"

    def test_separa_T_grudado(self):
        assert limpar("T.Amém") == "T. Amém"

    def test_normaliza_espacos_multiplos(self):
        assert limpar("muitos   espacos") == "muitos espacos"

    def test_normaliza_quebras_multiplas(self):
        assert limpar("linha1\n\n\n\nlinha2") == "linha1\n\nlinha2"

    def test_pipeline_completa(self):
        texto = "Ale-\nluia! P.Em nome\n\n\nFim."
        esperado = "Aleluia! P. Em nome\n\nFim."
        assert limpar(texto) == esperado
