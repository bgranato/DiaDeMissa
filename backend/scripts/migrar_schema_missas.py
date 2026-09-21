"""Migração de schema: varre TODOS os modelos vs TODAS as tabelas e adiciona
colunas/cria tabelas faltantes — sem precisar conhecer cada coluna individualmente.

O backend usa ``Base.metadata.create_all`` no boot, que só CRIA tabelas novas; nunca
adiciona colunas em tabela existente. Sempre que o modelo ganha uma coluna (ou
uma classe inteira é adicionada sem o ``main.py`` importá-la antes do
``create_all``), o banco legado fica desalinhado e qualquer SELECT/INSERT nessa
coluna explode com ``no such column`` / ``no such table``. O pipeline de missas
é o primeiro a sentir (passa por ``reter_montagens_sem_gauntlet``,
``freios_gasto.pode_montar``, etc.).

Este script é IDEMPOTENTE em todos os bancos (SQLite dev / Postgres prod):
- Para cada tabela do ``Base.metadata``, compara colunas do modelo vs colunas do banco.
- Coluna faltante: ``ALTER TABLE ADD COLUMN`` com tipo e default do modelo.
- Backfill: se o modelo tem default e a coluna está NULL em linhas existentes, UPDATE.
- Tabela faltante: ``Base.metadata.create_all`` (com ``checkfirst=True``) cria.

Funciona em SQLite (dev) e Postgres (produção). Postgres exige mais cuidado em
tipos e defaults — ver `_tipo_para_dialect()` e `_default_para_dialect()`.

Uso::

    backend/.venv/bin/python -m backend.scripts.migrar_schema_missas        # detecta engine e aplica
    backend/.venv/bin/python -m backend.scripts.migrar_schema_missas --check # só diagnostica
    backend/.venv/bin/python -m backend.scripts.migrar_schema_missas --backup # dump de segurança antes
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

# Garante import do pacote ``app`` mesmo rodando fora do cwd do backend.
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# Carrega .env do backend (sem dependência extra) — produção define via env real,
# dev usa sqlite:///./data/missa_hoje.db.
try:
    from dotenv import load_dotenv  # type: ignore
    _env_path = _BACKEND / ".env"
    if _env_path.exists():
        load_dotenv(_env_path, override=False)
except Exception:
    pass

from app.core.config import settings  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402

# SQLite com caminho relativo (``./data/missa_hoje.db``) resolve contra o cwd.
# Isso cria confusão quando o script é invocado de outro diretório e pode até
# CRIAR um banco vazio novo. Reescrevemos para um caminho absoluto ancorado em
# ``backend/``, que é onde o `.env` espera encontrar o arquivo.
_db_url = settings.DATABASE_URL
if _db_url.startswith("sqlite:///") and not _db_url.startswith("sqlite:////"):
    rel = _db_url[len("sqlite:///"):]
    abs_path = (_BACKEND / rel).resolve()
    _db_url = f"sqlite:///{abs_path}"
engine = create_engine(_db_url)

# Importa TODOS os modelos para que ``Base.metadata`` registre todas as classes.
import app.models  # noqa: E402,F401  (efeito colateral desejado: popula metadata)
from app.core.database import Base  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("migrar_schema_missas")


def _dialect(engine: Engine) -> str:
    return engine.dialect.name


def _tipo_para_dialect(col, dialect: str) -> str:
    """Mapeia o tipo SQLAlchemy da coluna para um DDL compatível com o dialect."""
    sa_type_name = type(col.type).__name__
    py_type = getattr(col.type, "python_type", None)

    if dialect == "sqlite":
        # SQLite ignora tipos no ALTER TABLE — só precisa de algo válido.
        if sa_type_name == "Boolean" or py_type is bool:
            return "INTEGER"
        if sa_type_name in ("Integer",):
            return "INTEGER"
        if sa_type_name in ("Float", "Numeric"):
            return "REAL"
        # str, date, datetime, JSON, Text → TEXT
        return "TEXT"

    # Postgres
    if sa_type_name == "Integer":
        return "INTEGER"
    if sa_type_name == "Float":
        return "REAL"
    if sa_type_name == "Numeric":
        return "NUMERIC"
    if sa_type_name == "Boolean":
        return "BOOLEAN"
    if sa_type_name == "DateTime":
        return "TIMESTAMP"
    if sa_type_name == "Date":
        return "DATE"
    if sa_type_name == "JSON":
        return "JSON"
    if sa_type_name == "String":
        length = getattr(col.type, "length", None) or 255
        return f"VARCHAR({length})"
    if sa_type_name == "Text":
        return "TEXT"
    return "TEXT"


def _default_para_dialect(col, dialect: str) -> str | None:
    """Devolve o DDL do default para o dialect, ou None se não houver.

    SQLite NÃO aceita DEFAULT em ADD COLUMN para a maioria dos tipos — retornamos
    None lá e fazemos backfill manual depois.
    """
    default = getattr(col, "default", None)
    if default is None:
        return None
    arg = getattr(default, "arg", None)
    if arg is None:
        return None
    if not callable(arg) and not hasattr(arg, "__call__"):
        pass  # valor literal
    if dialect == "sqlite":
        return None
    # Postgres
    py_type = getattr(col.type, "python_type", None)
    if py_type is bool:
        return "TRUE" if bool(arg) else "FALSE"
    if py_type is int:
        return str(int(arg))
    if py_type is float:
        return str(float(arg))
    if py_type is str:
        s = str(arg).replace("'", "''")
        return f"'{s}'"
    return None


def _aplicar(engine: Engine, somente_check: bool) -> dict:
    """Para cada tabela do modelo: ADD COLUMN nas faltantes + backfill defaults."""
    dialect = _dialect(engine)
    if dialect not in ("sqlite", "postgresql"):
        raise RuntimeError(f"Dialect não suportado por este script: {dialect!r}")

    insp = inspect(engine)
    relatorio = {"dialect": dialect, "por_tabela": {}, "total_aplicadas": 0, "total_backfill": 0}

    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            tabela = table.name
            if not insp.has_table(tabela):
                continue

            cols_banco = {c["name"] for c in insp.get_columns(tabela)}
            cols_modelo = [c for c in table.columns if c.name not in cols_banco]

            entrada = {"aplicadas": [], "backfill": [], "ja_existentes": sorted(cols_banco)}
            for col in cols_modelo:
                tipo = _tipo_para_dialect(col, dialect)
                default = _default_para_dialect(col, dialect)
                stmt = (
                    f'ALTER TABLE "{tabela}" ADD COLUMN "{col.name}" {tipo}'
                    if default is None
                    else f'ALTER TABLE "{tabela}" ADD COLUMN "{col.name}" {tipo} DEFAULT {default}'
                )
                log.info("  %s.%s — %s", tabela, col.name, stmt)
                if not somente_check:
                    conn.execute(text(stmt))
                entrada["aplicadas"].append({"coluna": col.name, "tipo": tipo, "default": default})

                if not somente_check and col.default is not None:
                    # Só faz backfill quando o modelo declara default. Sem default
                    # declarado, ``nullable=True`` significa "ausência é estado válido"
                    # (ex.: meta_missas_mensal=None = "sem meta") e forçar 0/string
                    # vazia seria mudar a semântica do dado.
                    py_type = getattr(col.type, "python_type", None)
                    arg = getattr(col.default, "arg", None)
                    if arg is None:
                        res = None
                    elif py_type is bool:
                        upd = text(f'UPDATE "{tabela}" SET "{col.name}" = :v WHERE "{col.name}" IS NULL')
                        res = conn.execute(upd, {"v": int(bool(arg))})
                    elif py_type is int:
                        upd = text(f'UPDATE "{tabela}" SET "{col.name}" = :v WHERE "{col.name}" IS NULL')
                        res = conn.execute(upd, {"v": int(arg)})
                    elif py_type is str:
                        upd = text(f'UPDATE "{tabela}" SET "{col.name}" = :v WHERE "{col.name}" IS NULL')
                        res = conn.execute(upd, {"v": str(arg)})
                    else:
                        res = None
                    if res is not None and res.rowcount:
                        entrada["backfill"].append({"coluna": col.name, "linhas": res.rowcount})

            relatorio["por_tabela"][tabela] = entrada
            relatorio["total_aplicadas"] += len(entrada["aplicadas"])
            relatorio["total_backfill"] += len(entrada["backfill"])

    return relatorio


def _criar_tabelas_faltantes(engine: Engine, somente_check: bool) -> dict:
    """Cria tabelas inteiras que existem no modelo mas não no banco."""
    insp = inspect(engine)
    existentes = set(insp.get_table_names())
    relatorio = {"ja_existentes": [], "criadas": []}

    log.info("Banco %s — tabelas existentes: %s", _dialect(engine), sorted(existentes))

    for table in Base.metadata.sorted_tables:
        tabela = table.name
        if tabela in existentes:
            relatorio["ja_existentes"].append(tabela)
            continue
        log.info("  tabela %s ausente — criar", tabela)
        relatorio["criadas"].append(tabela)
        if not somente_check:
            table.create(bind=engine, checkfirst=True)

    return relatorio


def _backup(engine: Engine) -> Path | None:
    """Dump de segurança antes da migração."""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    dialect = _dialect(engine)
    if dialect == "sqlite":
        db_path = Path(engine.url.database)
        if not db_path.is_absolute():
            db_path = (Path.cwd() / db_path).resolve()
        bak = db_path.with_suffix(db_path.suffix + f".bak-{ts}")
        shutil.copy2(db_path, bak)
        log.info("Backup SQLite gravado em %s (%d bytes)", bak, bak.stat().st_size)
        return bak
    if dialect == "postgresql":
        url = str(engine.url)
        if shutil.which("pg_dump") is None:
            log.warning("pg_dump não encontrado — faça o backup manualmente antes da migração")
            return None
        bak = Path(f"missas.dump-{ts}.sql")
        cmd = ["pg_dump", "--no-owner", url]
        try:
            with bak.open("w") as f:
                subprocess.run(cmd, check=True, stdout=f, stderr=subprocess.PIPE)
            log.info("Backup Postgres gravado em %s", bak)
            return bak
        except subprocess.CalledProcessError as e:
            log.error("pg_dump falhou: %s", e.stderr.decode(errors="replace"))
            raise
    return None


def main() -> int:
    p = argparse.ArgumentParser(description="Migração idempotente universal: varre modelos vs banco")
    p.add_argument("--check", action="store_true", help="só diagnostica, não aplica")
    p.add_argument("--backup", action="store_true", help="gera dump de segurança antes")
    args = p.parse_args()

    log.info("Engine alvo: %s", engine.url)
    if args.backup and not args.check:
        _backup(engine)

    rel_colunas = _aplicar(engine, somente_check=args.check)
    rel_tabelas = _criar_tabelas_faltantes(engine, somente_check=args.check)

    out = {"colunas": rel_colunas, "tabelas": rel_tabelas}
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))

    houve_mudanca = bool(rel_colunas["total_aplicadas"] or rel_tabelas["criadas"])
    if args.check:
        if houve_mudanca:
            print("\n→ Mudanças necessárias. Rode sem --check para aplicar.")
            return 1
        print("\n→ Schema já está alinhado com o modelo. Nada a fazer.")
        return 0
    if houve_mudanca:
        print(f"\n→ Migração aplicada: {rel_colunas['total_aplicadas']} colunas adicionadas, "
              f"{len(rel_tabelas['criadas'])} tabelas criadas, "
              f"{rel_colunas['total_backfill']} backfills executados.")
    else:
        print("\n→ Nada a aplicar (já estava alinhado).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
