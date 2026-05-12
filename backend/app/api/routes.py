from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    criar_access_token,
    gerar_hash_senha,
    obter_usuario_atual,
    verificar_senha,
)
from app.models.usuario import Usuario, PreferenciaUsuario, HistoricoUsuario, Lembrete
from app.models.missa import Missa, BlocoLiturgico
from app.schemas.usuario import (
    UsuarioCreate, UsuarioResponse, UsuarioUpdate,
    LoginRequest, LoginGoogleRequest, LoginResponse,
    PreferenciasResponse, PreferenciasUpdate,
    HistoricoResponse, HistoricoCreate,
    LembreteCreate, LembreteResponse, LembreteUpdate, LembreteBroadcast,
)
from app.schemas.missa import (
    BlocoResponse, MissaResponse, MissaCompletaResponse,
)
from app.services.mass_processor import processar_missa
from pathlib import Path
from app.pipeline import processar_pdf

router = APIRouter()
PDF_PADRAO = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures" / "amissa_ascensao_2026.pdf"


@router.get("/health")
def health_check():
    return {"status": "ok", "version": settings.APP_VERSION, "app": settings.APP_NAME}


@router.get("/missa/atual")
def missa_atual():
    try:
        from app.pipeline import processar_pdf as pp
        missa = pp(PDF_PADRAO)
        return missa.model_dump()
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"ERRO: {type(e).__name__}: {e}\n{traceback.format_exc()}")


@router.get("/missas/hoje", response_model=MissaResponse)
def get_missa_hoje(db: Session = Depends(get_db)):
    hoje = date.today()
    missa = db.query(Missa).filter(Missa.data == hoje).first()
    if not missa:
        raise HTTPException(status_code=404, detail="Missa para hoje ainda não disponível")
    return MissaResponse(
        id=missa.id,
        data=missa.data,
        celebracao=missa.celebracao,
        subtitulo=missa.subtitulo,
        descricao=missa.descricao,
        tempo_liturgico=missa.tempo_liturgico,
        status_processamento=missa.status_processamento,
        total_blocos=len(missa.blocos) if missa.blocos else 0,
    )


@router.get("/missas/{data}", response_model=MissaResponse)
def get_missa_por_data(data: date, db: Session = Depends(get_db)):
    missa = db.query(Missa).filter(Missa.data == data).first()
    if not missa:
        raise HTTPException(status_code=404, detail="Missa não encontrada para esta data")
    return MissaResponse(
        id=missa.id,
        data=missa.data,
        celebracao=missa.celebracao,
        subtitulo=missa.subtitulo,
        descricao=missa.descricao,
        tempo_liturgico=missa.tempo_liturgico,
        status_processamento=missa.status_processamento,
        total_blocos=len(missa.blocos) if missa.blocos else 0,
    )


@router.get("/missas/{id}/blocos", response_model=list[BlocoResponse])
def get_blocos_missa(id: int, db: Session = Depends(get_db)):
    missa = db.query(Missa).filter(Missa.id == id).first()
    if not missa:
        raise HTTPException(status_code=404, detail="Missa não encontrada")
    blocos = (
        db.query(BlocoLiturgico)
        .filter(BlocoLiturgico.missa_id == id, BlocoLiturgico.visivel == True)
        .order_by(BlocoLiturgico.ordem)
        .all()
    )
    return [BlocoResponse.model_validate(b) for b in blocos]


@router.get("/missas/{id}/completa", response_model=MissaCompletaResponse)
def get_missa_completa(id: int, db: Session = Depends(get_db)):
    missa = db.query(Missa).filter(Missa.id == id).first()
    if not missa:
        raise HTTPException(status_code=404, detail="Missa não encontrada")
    return MissaCompletaResponse.model_validate(missa)


@router.post("/missas/processar-pdf")
def processar_pdf(db: Session = Depends(get_db)):
    try:
        missa = processar_missa(db)
        return {"message": "Processamento concluído", "missa_id": missa.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no processamento: {str(e)}")


@router.post("/usuarios", response_model=UsuarioResponse, status_code=201)
def criar_usuario(dados: UsuarioCreate, db: Session = Depends(get_db)):
    existente = db.query(Usuario).filter(Usuario.email == dados.email).first()
    if existente:
        raise HTTPException(status_code=409, detail="Email já cadastrado")
    usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=gerar_hash_senha(dados.senha),
        provider="email",
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.post("/auth/login", response_model=LoginResponse)
def login(dados: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == dados.email).first()
    if not usuario or not usuario.senha_hash:
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")
    if not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")
    token = criar_access_token({"sub": usuario.id})
    return LoginResponse(
        access_token=token,
        usuario=UsuarioResponse.model_validate(usuario),
    )


@router.post("/auth/google", response_model=LoginResponse)
def login_google(dados: LoginGoogleRequest, db: Session = Depends(get_db)):
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token
    try:
        info = id_token.verify_oauth2_token(
            dados.token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
        email = info.get("email")
        nome = info.get("name", email)
        google_id = info.get("sub")
        usuario = db.query(Usuario).filter(
            (Usuario.email == email) | (
                (Usuario.provider == "google") & (Usuario.provider_id == google_id)
            )
        ).first()
        if not usuario:
            usuario = Usuario(nome=nome, email=email, provider="google", provider_id=google_id)
            db.add(usuario)
            db.commit()
            db.refresh(usuario)
        token = criar_access_token({"sub": usuario.id})
        return LoginResponse(access_token=token, usuario=UsuarioResponse.model_validate(usuario))
    except ValueError:
        raise HTTPException(status_code=401, detail="Token Google inválido")


@router.get("/usuarios/me", response_model=UsuarioResponse)
def get_usuario_atual(usuario: Usuario = Depends(obter_usuario_atual)):
    return usuario


@router.put("/usuarios/me", response_model=UsuarioResponse)
def atualizar_usuario(dados: UsuarioUpdate, usuario: Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    if dados.nome is not None:
        usuario.nome = dados.nome
    if dados.email is not None:
        existente = db.query(Usuario).filter(Usuario.email == dados.email, Usuario.id != usuario.id).first()
        if existente:
            raise HTTPException(status_code=409, detail="Email já cadastrado")
        usuario.email = dados.email
    db.commit()
    db.refresh(usuario)
    return usuario


@router.get("/usuarios/me/historico", response_model=list[HistoricoResponse])
def get_historico(usuario: Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    registros = (
        db.query(HistoricoUsuario, Missa)
        .join(Missa, HistoricoUsuario.missa_id == Missa.id)
        .filter(HistoricoUsuario.usuario_id == usuario.id)
        .order_by(desc(HistoricoUsuario.data_ultimo_acesso))
        .all()
    )
    return [
        HistoricoResponse(
            missa_id=h.missa_id, data=m.data.isoformat(), celebracao=m.celebracao,
            ultimo_bloco_id=h.ultimo_bloco_id, percentual_lido=h.percentual_lido, data_ultimo_acesso=h.data_ultimo_acesso,
        ) for h, m in registros
    ]


@router.post("/usuarios/me/historico", status_code=201)
def salvar_progresso(dados: HistoricoCreate, usuario: Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    registro = db.query(HistoricoUsuario).filter(
        HistoricoUsuario.usuario_id == usuario.id, HistoricoUsuario.missa_id == dados.missa_id,
    ).first()
    if registro:
        registro.ultimo_bloco_id = dados.ultimo_bloco_id
        registro.percentual_lido = dados.percentual_lido
        registro.data_ultimo_acesso = datetime.now(timezone.utc)
    else:
        registro = HistoricoUsuario(usuario_id=usuario.id, missa_id=dados.missa_id, ultimo_bloco_id=dados.ultimo_bloco_id, percentual_lido=dados.percentual_lido)
        db.add(registro)
    db.commit()
    return {"message": "Progresso salvo"}


@router.get("/usuarios/me/preferencias", response_model=PreferenciasResponse)
def get_preferencias(usuario: Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    pref = db.query(PreferenciaUsuario).filter(PreferenciaUsuario.usuario_id == usuario.id).first()
    if not pref:
        pref = PreferenciaUsuario(usuario_id=usuario.id)
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref


@router.put("/usuarios/me/preferencias", response_model=PreferenciasResponse)
def atualizar_preferencias(dados: PreferenciasUpdate, usuario: Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    pref = db.query(PreferenciaUsuario).filter(PreferenciaUsuario.usuario_id == usuario.id).first()
    if not pref:
        pref = PreferenciaUsuario(usuario_id=usuario.id)
        db.add(pref)
    for attr in ["tamanho_fonte", "modo_escuro", "alto_contraste", "leitura_simplificada", "notificacoes_ativas"]:
        val = getattr(dados, attr, None)
        if val is not None:
            setattr(pref, attr, val)
    db.commit()
    db.refresh(pref)
    return pref


# ===== LEMBRETES =====

@router.get("/usuarios/me/lembretes", response_model=list[LembreteResponse])
def get_lembretes(usuario: Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    lembretes = (
        db.query(Lembrete)
        .filter(Lembrete.usuario_id == usuario.id)
        .order_by(Lembrete.data_hora_alerta)
        .all()
    )
    return lembretes


@router.post("/usuarios/me/lembretes", response_model=LembreteResponse, status_code=201)
def criar_lembrete(dados: LembreteCreate, usuario: Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    lembrete = Lembrete(
        usuario_id=usuario.id,
        missa_id=dados.missa_id,
        titulo=dados.titulo,
        nota=dados.nota,
        data_hora_alerta=dados.data_hora_alerta,
        minutos_antecedencia=dados.minutos_antecedencia,
        tipo=dados.tipo,
        remetente="Missa do Dia" if dados.tipo == "master" else "usuario",
    )
    db.add(lembrete)
    db.commit()
    db.refresh(lembrete)
    return lembrete


@router.put("/usuarios/me/lembretes/{id}", response_model=LembreteResponse)
def atualizar_lembrete(id: int, dados: LembreteUpdate, usuario: Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    lembrete = db.query(Lembrete).filter(Lembrete.id == id, Lembrete.usuario_id == usuario.id).first()
    if not lembrete:
        raise HTTPException(status_code=404, detail="Lembrete não encontrado")
    for attr in ["titulo", "nota", "data_hora_alerta", "minutos_antecedencia", "ativo"]:
        val = getattr(dados, attr, None)
        if val is not None:
            setattr(lembrete, attr, val)
    db.commit()
    db.refresh(lembrete)
    return lembrete


@router.delete("/usuarios/me/lembretes/{id}", status_code=204)
def deletar_lembrete(id: int, usuario: Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    lembrete = db.query(Lembrete).filter(Lembrete.id == id, Lembrete.usuario_id == usuario.id).first()
    if not lembrete:
        raise HTTPException(status_code=404, detail="Lembrete não encontrado")
    db.delete(lembrete)
    db.commit()


# ===== LEMBRETES MASTER/BROADCAST =====

@router.post("/admin/lembretes/broadcast", status_code=201)
def broadcast_lembrete(dados: LembreteBroadcast, db: Session = Depends(get_db)):
    if dados.usuario_id:
        usuarios = db.query(Usuario).filter(Usuario.id == dados.usuario_id).all()
    else:
        usuarios = db.query(Usuario).all()
    for u in usuarios:
        lembrete = Lembrete(
            usuario_id=u.id,
            titulo=dados.titulo,
            nota=dados.nota,
            data_hora_alerta=dados.data_hora_alerta,
            minutos_antecedencia=dados.minutos_antecedencia,
            tipo="master",
            remetente="Missa do Dia",
        )
        db.add(lembrete)
    db.commit()
    return {"message": f"Lembrete enviado para {len(usuarios)} usuário(s)"}


# ===== LEMBRETES PRÉ-DEFINIDOS (APP) =====

@router.post("/usuarios/me/lembretes/app/domingo", response_model=LembreteResponse, status_code=201)
def criar_lembrete_domingo(usuario: Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    """Cria lembrete para a missa de domingo às 11h."""
    from datetime import timedelta
    hoje = date.today()
    dias_ate_domingo = (6 - hoje.weekday()) % 7
    if dias_ate_domingo == 0:
        dias_ate_domingo = 7
    prox_domingo = hoje + timedelta(days=dias_ate_domingo)
    alerta = datetime(prox_domingo.year, prox_domingo.month, prox_domingo.day, 11, 0, tzinfo=timezone.utc)
    lembrete = Lembrete(
        usuario_id=usuario.id,
        titulo="Missa de Domingo",
        nota="Não se esqueça da Missa deste domingo! 🙏",
        data_hora_alerta=alerta,
        minutos_antecedencia=30,
        tipo="app",
        remetente="Missa do Dia",
    )
    db.add(lembrete)
    db.commit()
    db.refresh(lembrete)
    return lembrete


# ===== MONITORAMENTO DE LOGS =====
from pydantic import BaseModel as PydanticBaseModel

class LogEntry(PydanticBaseModel):
    tipo: str
    mensagem: str
    dados: Optional[dict] = None

logs_memoria: list[dict] = []

@router.post("/logs")
def registrar_log(entry: LogEntry):
    logs_memoria.append({
        "tipo": entry.tipo, "mensagem": entry.mensagem, "dados": entry.dados,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    if len(logs_memoria) > 200:
        logs_memoria.pop(0)
    return {"ok": True}

@router.get("/logs")
def listar_logs():
    return list(reversed(logs_memoria))
