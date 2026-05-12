import pytest
from app.pipeline.clean import limpar
from app.pipeline.structure import extrair_postura, remover_marcacao_postura


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


class TestExtrairPostura:
    def test_mesma_linha(self):
        linhas = ["1. Canto de Entrada (De pé)"]
        assert extrair_postura(linhas) == "de_pe"

    def test_linha_seguinte(self):
        linhas = ["1. Canto de Entrada", "(De pé)", "REFRÃO: ..."]
        assert extrair_postura(linhas) == "de_pe"

    def test_apos_referencia(self):
        linhas = ["6. Primeira Leitura (At 1,1-11) (Sentados)"]
        assert extrair_postura(linhas) == "sentado"

    def test_sentados_isolado(self):
        linhas = ["11. Homilia", "(Sentados)", "Momento de silêncio..."]
        assert extrair_postura(linhas) == "sentado"

    def test_sem_postura(self):
        linhas = ["2. Saudação", "P. Em nome do Pai..."]
        assert extrair_postura(linhas) is None

    def test_nao_confunde_referencia_biblica(self):
        linhas = ["Antífona da Entrada (At 1,11)", "Homens da Galileia..."]
        assert extrair_postura(linhas) is None


class TestLimparTitulo:
    def _clean(self, t):
        import re
        from app.pipeline.structure import remover_marcacao_postura
        t = re.sub(r"^\d+\.\s*", "", t).strip()
        return remover_marcacao_postura(t)

    def test_remove_de_pe(self):
        assert self._clean("Canto de Entrada (De pé)") == "Canto de Entrada"

    def test_remove_sentados(self):
        assert self._clean("Primeira Leitura (At 1,1-11) (Sentados)") == \
               "Primeira Leitura (At 1,1-11)"

    def test_remove_numero(self):
        assert self._clean("2. Saudação") == "Saudação"
