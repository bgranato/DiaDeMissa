from pathlib import Path
import pytest
from app.pipeline.extract import extrair_texto_estruturado

PDF_FIXTURE = Path(__file__).parent / "fixtures" / "amissa_ascensao_2026.pdf"


class TestExtract:
    def test_extrai_texto(self):
        texto = extrair_texto_estruturado(PDF_FIXTURE)
        assert len(texto) > 5000, f"Apenas {len(texto)} caracteres extraídos"

    def test_sem_cantodeentrada(self):
        texto = extrair_texto_estruturado(PDF_FIXTURE)
        assert "CantodeEntrada" not in texto, "'CantodeEntrada' encontrado"

    def test_sem_aleque(self):
        texto = extrair_texto_estruturado(PDF_FIXTURE)
        assert "AleQue" not in texto, "'AleQue' encontrado"

    def test_contem_ascensao(self):
        texto = extrair_texto_estruturado(PDF_FIXTURE)
        assert "Ascensão do Senhor" in texto

    def test_contem_canto_entrada(self):
        texto = extrair_texto_estruturado(PDF_FIXTURE)
        assert "Canto de Entrada" in texto
