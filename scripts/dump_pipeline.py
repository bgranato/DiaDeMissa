"""
Dump dos estados intermediários do pipeline para inspeção manual.
Salva em reports/debug/ os outputs de cada etapa.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.pipeline.extract import extrair_texto_estruturado
from app.pipeline.clean import limpar

PDF = Path(__file__).resolve().parent.parent / "backend" / "tests" / "fixtures" / "amissa_ascensao_2026.pdf"
OUT_DIR = Path(__file__).resolve().parent.parent / "reports" / "debug"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    texto_extraido = extrair_texto_estruturado(PDF)
    (OUT_DIR / "01_extract.txt").write_text(texto_extraido, encoding="utf-8")
    print(f"✅ 01_extract.txt — {len(texto_extraido)} chars")

    texto_limpo = limpar(texto_extraido)
    (OUT_DIR / "02_clean.txt").write_text(texto_limpo, encoding="utf-8")
    print(f"✅ 02_clean.txt — {len(texto_limpo)} chars")

    print(f"\n📁 Dumps salvos em: {OUT_DIR}")

if __name__ == "__main__":
    main()
