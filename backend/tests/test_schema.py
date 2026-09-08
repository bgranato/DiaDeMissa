import pytest
from app.schema.missa import Canto, Turno, Dialogo, Missa, Creditos, PalavraDoDia


class TestSchema:
    def test_cria_canto_valido(self):
        c = Canto(ordem=1, titulo="Canto de Entrada", postura="de_pe",
                  refrao=["O Senhor foi preparar"], estrofes=[["Aleluia!"]])
        assert c.tipo == "canto"

    def test_permite_barra_interna_como_separador_de_verso(self):
        canto = Canto(ordem=1, titulo="Canto / de Entrada")
        assert canto.titulo == "Canto / de Entrada"

    def test_rejeita_barra_como_artefato_no_inicio_ou_fim(self):
        with pytest.raises(ValueError, match="barra no início/fim"):
            Canto(ordem=1, titulo="/ Canto de Entrada")

    def test_rejeita_postura_como_texto(self):
        with pytest.raises(ValueError, match="postura como texto"):
            Canto(ordem=1, titulo="Canto de Entrada (De pé)")

    def test_rejeita_markdown(self):
        with pytest.raises(ValueError, match="markdown"):
            Canto(ordem=1, titulo="## Canto")

    def test_rejeita_sigla_falante_no_texto(self):
        with pytest.raises(ValueError, match="sigla de falante"):
            Canto(ordem=1, titulo="P. Em nome do Pai")

    def test_turno_valido(self):
        t = Turno(falante="P", texto="Em nome do Pai")
        assert t.falante == "P"

    def test_turno_com_rubrica(self):
        t = Turno(falante="rubrica", texto="Momento de silêncio.")
        assert t.falante == "rubrica"

    def test_rejeita_turno_com_sigla(self):
        with pytest.raises(ValueError, match="sigla de falante"):
            Turno(falante="P", texto="P. Em nome do Pai")

    def test_dialogo_valido(self):
        d = Dialogo(ordem=2, titulo="Saudação", turnos=[
            Turno(falante="P", texto="O Senhor esteja convosco"),
            Turno(falante="T", texto="Ele está no meio de nós"),
        ])
        assert len(d.turnos) == 2

    def test_missa_valida(self):
        m = Missa(
            data="2026-05-17", ano_liturgico="A",
            titulo_celebracao="Ascensão do Senhor", categoria="Solenidade",
            creditos_cantos=Creditos(entrada="José Alves"),
            palavra_do_dia=PalavraDoDia(texto="Eis que estou convosco", referencia="Mt 28,20"),
            blocos=[Canto(ordem=1, titulo="Canto de Entrada")],
        )
        assert len(m.blocos) == 1

    def test_ano_liturgico_valido(self):
        with pytest.raises(ValueError):
            Missa(
                data="2026-05-17", ano_liturgico="D",
                titulo_celebracao="Missa", categoria="Domingo",
                creditos_cantos=Creditos(),
                palavra_do_dia=PalavraDoDia(texto="x", referencia="Mt"),
                blocos=[],
            )
