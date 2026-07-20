#!/usr/bin/env python3
"""Teste offline da etapa de estruturação por LLM (A).

Roda o folheto de hoje pelo pipeline NOVO (texto bruto → LLM → validação Pydantic)
e imprime o JSON estruturado + um resumo de qualidade.

Modos:
  # Ao vivo (precisa de ANTHROPIC_API_KEY no ambiente):
  ANTHROPIC_API_KEY=sk-... python scripts/teste_estrutura_llm.py

  # A partir de um PDF (extrai e limpa antes):
  python scripts/teste_estrutura_llm.py --pdf caminho/para/folheto.pdf

  # Validar um JSON já gerado (ex.: a amostra corrigida) contra o schema:
  python scripts/teste_estrutura_llm.py --validar tests/fixtures/esperado_28-06-2026.llm.json

Sem API key e sem --validar, ele roda o FALLBACK regex pra provar que o pipeline
está ligado de ponta a ponta (a saída terá os erros conhecidos do regex).

Rode a partir de backend/:  python scripts/teste_estrutura_llm.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.schema.missa import Missa  # noqa: E402

FIXTURE_TXT = BACKEND / "tests" / "fixtures" / "folheto_28-06-2026.txt"


def _carregar_texto(pdf: str | None) -> str:
    if pdf:
        from app.pipeline.extract import extrair_texto_estruturado
        from app.pipeline.clean import limpar
        return limpar(extrair_texto_estruturado(pdf))
    # Default: usa o texto bruto de hoje já capturado
    return FIXTURE_TXT.read_text(encoding="utf-8")


def _checar_qualidade(missa: Missa) -> list[str]:
    """Checagens rápidas que pegam os defeitos reais vistos no app hoje."""
    problemas: list[str] = []
    if (missa.categoria or "").lower() in ("", "missa"):
        problemas.append("categoria genérica/ausente (esperado: Solenidade)")
    if not missa.descricao:
        problemas.append("descricao ausente (parágrafo de abertura perdido)")
    obs = (missa.observacoes or "")
    if "REFRÃO" in obs or "Festejamos" in obs:
        problemas.append("observacoes contaminado com letra de canto")
    # Procura artefatos por bloco
    for b in missa.blocos:
        dump = json.dumps(b.model_dump(), ensure_ascii=False)
        if "Ano A – no" in dump or "Editora" in dump or "Entrada: Cristiane" in dump:
            problemas.append(f"bloco '{getattr(b,'titulo','?')}' tem cabeçalho/créditos vazando")
        if getattr(b, "tipo", "") == "leitura":
            for v in getattr(b, "versiculos", []) or []:
                if len((v.texto or "").strip()) <= 2:
                    problemas.append(f"leitura '{b.titulo}' tem versículo-lixo ({v.numero!r}:{v.texto!r})")
                    break
    return problemas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", help="Caminho de um PDF de folheto (extrai e limpa)")
    ap.add_argument("--validar", help="Valida um JSON existente contra o schema Missa")
    args = ap.parse_args()

    if args.validar:
        dados = json.loads(Path(args.validar).read_text(encoding="utf-8"))
        from app.pipeline.structure_llm import _montar_missa
        missa = _montar_missa(dados)
        print(f"✅ JSON válido contra o schema. {len(missa.blocos)} blocos.")
        probs = _checar_qualidade(missa)
        print("Qualidade:", "OK ✅" if not probs else "")
        for p in probs:
            print("  ⚠️", p)
        return 0

    texto = _carregar_texto(args.pdf)
    print(f"Texto bruto: {len(texto)} chars\n")

    # Guarda: sem chave válida o pipeline cai no REGEX silenciosamente (resultado
    # defeituoso) — isso enganaria o teste. Então exigimos uma chave real aqui.
    chave = os.getenv("ANTHROPIC_API_KEY", "").strip()
    # Uma chave real da Anthropic começa com "sk-ant-" e é longa (~100 chars).
    # Isso barra os placeholders de exemplo (SUACHAVE, aSuaChaveDeVerdadeAqui, etc.).
    parece_real = chave.startswith("sk-ant-") and len(chave) >= 50 and "SUACHAVE" not in chave
    if not parece_real:
        print("⚠️  ANTHROPIC_API_KEY ausente ou é um EXEMPLO, não uma chave real.")
        print("    Uma chave de verdade começa com 'sk-ant-' e tem ~100 caracteres,")
        print("    copiada de console.anthropic.com → API Keys → Create Key.")
        print("    Sem chave REAL o teste não chama o LLM (e não valida nada).")
        return 1
    print(f"Usando LLM com chave real (…{chave[-4:]}).\n")

    from app.pipeline.structure_llm import estruturar_via_llm
    missa = estruturar_via_llm(texto, data_hint="2026-06-28")

    out = BACKEND / "scripts" / "saida_estrutura_llm.json"
    out.write_text(json.dumps(missa.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JSON salvo em {out}")
    print(f"Blocos: {len(missa.blocos)} · categoria={missa.categoria!r} · descricao={'sim' if missa.descricao else 'NÃO'}")

    probs = _checar_qualidade(missa)
    if not probs:
        print("\nQualidade: OK ✅ (nenhum defeito conhecido detectado)")
    else:
        print("\nDefeitos detectados (esperado no fallback regex):")
        for p in probs:
            print("  ⚠️", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
