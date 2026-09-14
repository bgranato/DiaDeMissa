from jose import jwt

from app.core.config import settings
from app.core.security import criar_access_token, obter_usuario_opcional


def test_usuario_opcional_sem_credenciais_e_visitante_anomino():
    """Uma rota pública não deve exigir cabeçalho Authorization."""
    assert obter_usuario_opcional(credentials=None, db=None) is None


def test_token_aceita_id_numerico_e_grava_sub_como_texto():
    """Evita sessão inválida após login Google, que usa id inteiro."""
    token = criar_access_token({"sub": 42})

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    assert payload["sub"] == "42"
