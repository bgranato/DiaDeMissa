from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.usuario import Usuario

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


def _truncar_senha(senha: str) -> bytes:
    """bcrypt aceita no máximo 72 BYTES (não chars). Acentos/emoji em UTF-8 ocupam 2+ bytes.
    Trunca defensivamente pra não estourar o limite e quebrar login."""
    return senha.encode("utf-8")[:72]


def verificar_senha(senha: str, hash: str) -> bool:
    return pwd_context.verify(_truncar_senha(senha), hash)


def gerar_hash_senha(senha: str) -> str:
    return pwd_context.hash(_truncar_senha(senha))


def criar_access_token(data: dict) -> str:
    to_encode = data.copy()
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": exp})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def obter_usuario_atual(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Usuario:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        usuario_id = int(sub)
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    # Bloqueio/cancelamento pelo painel admin derruba o acesso (mesmo com token válido).
    if getattr(usuario, "status", "ativo") in ("bloqueado", "cancelado"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cadastro bloqueado ou cancelado")
    return usuario


def obter_usuario_opcional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_optional),
    db: Session = Depends(get_db),
) -> Usuario | None:
    """Resolve o usuário quando há token válido, sem bloquear rotas públicas.

    Catálogos públicos podem usar esta dependência para personalizar campos como
    `favorita`. Token ausente, expirado ou inválido equivale a visitante anônimo;
    ações que alteram dados continuam usando `obter_usuario_atual`.
    """
    if credentials is None:
        return None
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        usuario_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        return None

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if usuario is None or getattr(usuario, "status", "ativo") in ("bloqueado", "cancelado"):
        return None
    return usuario


def obter_usuario_admin(usuario: Usuario = Depends(obter_usuario_atual)) -> Usuario:
    """Dependência que exige usuário admin. Use em endpoints de broadcast/admin."""
    if not getattr(usuario, "is_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a administradores")
    return usuario
