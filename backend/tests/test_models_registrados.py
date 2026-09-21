"""Garante que o boot conhece todas as tabelas antes de criar o schema."""
from app.core.database import Base
import app.models  # noqa: F401  — registro intencional no metadata


def test_todas_as_tabelas_operacionais_estao_no_metadata():
    esperadas = {"missas", "custos_llm", "feedback_usuario", "uso_geocoding_mensal", "apoios"}

    assert esperadas <= set(Base.metadata.tables)
