from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.pipeline import processar_pdf

app = FastAPI(title="Missa Hoje - API do Pipeline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PDF_PADRAO = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures" / "amissa_ascensao_2026.pdf"


@app.get("/missa/atual")
def missa_atual():
    try:
        missa = processar_pdf(PDF_PADRAO)
        return missa.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar PDF: {e}")
