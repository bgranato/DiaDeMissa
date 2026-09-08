from app.core.security import obter_usuario_opcional


def test_usuario_opcional_sem_credenciais_e_visitante_anomino():
    """Uma rota pública não deve exigir cabeçalho Authorization."""
    assert obter_usuario_opcional(credentials=None, db=None) is None
