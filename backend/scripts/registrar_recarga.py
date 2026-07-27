"""Registra uma recarga de crédito da Anthropic (para o SALDO ESTIMADO do monitor).

A Anthropic não expõe saldo de créditos pré-pagos por API — o monitor estima
  saldo ≈ (soma das recargas registradas) − (gasto acumulado em custo_llm).
Sempre que recarregar no console, rode este script com o valor recarregado.

Uso:  .venv/bin/python scripts/registrar_recarga.py <valor> [YYYY-MM-DD] [--nota "texto"]
Ex.:  .venv/bin/python scripts/registrar_recarga.py 20.00 2026-07-26
"""
from __future__ import annotations

import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)


def _carregar_env() -> None:
    caminho = os.path.join(BACKEND, ".env")
    if not os.path.exists(caminho):
        return
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            linha = linha.rstrip("\n")
            if not linha or linha.lstrip().startswith("#") or "=" not in linha:
                continue
            k, v = linha.split("=", 1)
            k, v = k.strip(), v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            os.environ.setdefault(k, v)


_carregar_env()

from app.services.custo_llm_service import registrar_custo_llm  # noqa: E402
from app.services import monitor_llm  # noqa: E402


def main(argv: list[str]) -> int:
    args = [a for a in argv if a != "--nota"]
    nota = ""
    if "--nota" in argv:
        i = argv.index("--nota")
        if i + 1 < len(argv):
            nota = argv[i + 1]
            args = [a for a in args if a != nota]
    if len(args) < 1:
        print("Uso: registrar_recarga.py <valor> [YYYY-MM-DD] [--nota \"texto\"]")
        return 2
    try:
        valor = float(args[0].replace(",", "."))
    except ValueError:
        print(f"Valor inválido: {args[0]!r}")
        return 2
    if valor <= 0:
        print("Valor da recarga deve ser > 0.")
        return 2
    data = args[1] if len(args) > 1 else None
    ref = data or nota or "recarga"

    # Recarga = linha em custo_llm com contexto 'recarga_credito' (excluída do gasto).
    registrar_custo_llm("anthropic", 0, 0, valor,
                        contexto=monitor_llm._CTX_RECARGA, referencia=ref)
    recargas = monitor_llm.total_recargas()
    gasto = monitor_llm.gasto_acumulado()
    print(f"Recarga registrada: US$ {valor:.2f}" + (f" ({data})" if data else "")
          + (f" — {nota}" if nota else ""))
    print(f"Total de recargas registradas: US$ {recargas:.2f}")
    print(f"Gasto acumulado (custo_llm): US$ {gasto:.2f}")
    print(f"SALDO ESTIMADO: US$ {recargas - gasto:.2f}")
    print("Obs.: o saldo estimado só é preciso se TODAS as recargas foram registradas "
          "e cobre o gasto já rastreado em custo_llm.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
