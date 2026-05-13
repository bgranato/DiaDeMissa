from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
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
    obter_usuario_admin,
    verificar_senha,
)
from app.models.usuario import Usuario, PreferenciaUsuario, HistoricoUsuario, Lembrete
from app.models.missa import Missa, BlocoLiturgico
from app.schemas.usuario import (
    UsuarioCreate, UsuarioResponse, UsuarioUpdate,
    LoginRequest, LoginGoogleRequest, LoginResponse,
    RecuperarSenhaRequest, RedefinirSenhaRequest, AlterarSenhaRequest,
    PreferenciasResponse, PreferenciasUpdate,
    HistoricoResponse, HistoricoCreate,
    LembreteCreate, LembreteResponse, LembreteUpdate, LembreteBroadcast,
)
from app.schemas.missa import (
    BlocoResponse, MissaResponse, MissaCompletaResponse,
)
from app.services.mass_processor import processar_missa
from app.pipeline import processar_pdf

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "version": settings.APP_VERSION, "app": settings.APP_NAME}


from pathlib import Path
from app.services.persist_missa import reconstruir_missa
PDF_FIXTURE = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures" / "amissa_ascensao_2026.pdf"

_fixture_cache = None

def _carregar_fixture():
    global _fixture_cache
    try:
        _fixture_cache = processar_pdf(PDF_FIXTURE).model_dump()
    except Exception as e:
        print(f"Erro ao carregar fixture: {e}")

# Fallback fixture para quando o BD ainda não tem a missa do dia
_carregar_fixture()


@router.get("/missa/atual")
def missa_atual(db: Session = Depends(get_db)):
    hoje = date.today()
    missa_db = db.query(Missa).filter(Missa.data == hoje).first()
    if missa_db and missa_db.status_processamento == "concluido" and missa_db.blocos:
        return reconstruir_missa(missa_db)
    # Fallback: enquanto o pipeline diário não tiver populado a missa do dia,
    # devolve a fixture (Ascensão 2026) para o frontend não quebrar
    if _fixture_cache is None:
        raise HTTPException(status_code=503, detail="Missa do dia indisponível")
    return _fixture_cache


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


@router.post("/admin/pipeline/executar")
def executar_pipeline_manual(
    forcar: bool = False,
    admin: Usuario = Depends(obter_usuario_admin),
):
    """Dispara manualmente o pipeline diário (download + parse + persist).

    Use `?forcar=true` para reprocessar mesmo que o hash do PDF não tenha mudado.
    Esse endpoint existe pra desenvolvimento e operações; o cron de 5h da manhã
    chama a mesma função automaticamente.
    """
    from app.services.daily_pipeline import executar_pipeline_diario
    return executar_pipeline_diario(forcar=forcar)


@router.post("/admin/lembretes/disparar-nao-acompanhada")
def disparar_notif_nao_acompanhada(admin: Usuario = Depends(obter_usuario_admin)):
    """Dispara manualmente a geração de lembretes 'você não acompanhou a missa de ontem'.

    O cron noturno (22h America/Sao_Paulo) chama isso automaticamente. Este endpoint
    é pra desenvolvimento e operações.
    """
    from app.services.notif_nao_acompanhou import gerar_notificacoes_nao_acompanhada
    return gerar_notificacoes_nao_acompanhada()


@router.post("/usuarios", response_model=UsuarioResponse, status_code=201)
def criar_usuario(dados: UsuarioCreate, db: Session = Depends(get_db)):
    existente = db.query(Usuario).filter(Usuario.email == dados.email).first()
    if existente:
        raise HTTPException(status_code=409, detail="Email já cadastrado")
    usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        celular=dados.celular,
        igreja=dados.igreja,
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
    token = criar_access_token({"sub": str(usuario.id)})
    return LoginResponse(
        access_token=token,
        usuario=UsuarioResponse.model_validate(usuario),
    )


@router.post("/auth/recuperar-senha", status_code=200)
def recuperar_senha(dados: RecuperarSenhaRequest, db: Session = Depends(get_db)):
    """Gera um token de recuperação e envia link por e-mail.

    Sempre retorna sucesso (mesmo quando o email não existe) pra não vazar
    informação sobre quais e-mails estão cadastrados.
    """
    import secrets
    from app.services.email_sender import enviar_email_recuperacao

    usuario = db.query(Usuario).filter(Usuario.email == dados.email).first()
    if usuario:
        token = secrets.token_urlsafe(32)
        usuario.reset_token = token
        usuario.reset_token_expira = datetime.now(timezone.utc) + timedelta(hours=1)
        db.commit()
        link = f"{settings.APP_BASE_URL}/redefinir-senha?token={token}"
        enviar_email_recuperacao(usuario.email, usuario.nome, link)
    return {"message": "Se o e-mail estiver cadastrado, enviaremos as instruções"}


@router.post("/auth/redefinir-senha", status_code=200)
def redefinir_senha(dados: RedefinirSenhaRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.reset_token == dados.token).first()
    if not usuario:
        raise HTTPException(status_code=400, detail="Token inválido")
    if not usuario.reset_token_expira:
        raise HTTPException(status_code=400, detail="Token inválido")
    expira = usuario.reset_token_expira
    if expira.tzinfo is None:
        expira = expira.replace(tzinfo=timezone.utc)
    if expira < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token expirado")
    if len(dados.nova_senha) < 4:
        raise HTTPException(status_code=400, detail="Senha muito curta")
    usuario.senha_hash = gerar_hash_senha(dados.nova_senha)
    usuario.reset_token = None
    usuario.reset_token_expira = None
    db.commit()
    return {"message": "Senha redefinida com sucesso"}


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
    if dados.celular is not None:
        usuario.celular = dados.celular
    if dados.igreja is not None:
        usuario.igreja = dados.igreja
    db.commit()
    db.refresh(usuario)
    return usuario


@router.post("/usuarios/me/alterar-senha", status_code=200)
def alterar_senha(
    dados: AlterarSenhaRequest,
    usuario: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    if not usuario.senha_hash:
        raise HTTPException(status_code=400, detail="Conta sem senha local (login via Google)")
    if not verificar_senha(dados.senha_atual, usuario.senha_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    if len(dados.nova_senha) < 4:
        raise HTTPException(status_code=400, detail="Nova senha muito curta")
    usuario.senha_hash = gerar_hash_senha(dados.nova_senha)
    db.commit()
    return {"message": "Senha alterada com sucesso"}


@router.get("/usuarios/me/historico", response_model=list[HistoricoResponse])
def get_historico(usuario: Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    registros = (
        db.query(Missa, HistoricoUsuario)
        .outerjoin(
            HistoricoUsuario,
            (HistoricoUsuario.missa_id == Missa.id) & (HistoricoUsuario.usuario_id == usuario.id),
        )
        .order_by(desc(Missa.data))
        .all()
    )

    def _status(h: Optional[HistoricoUsuario]) -> str:
        if h is None:
            return "nao_acompanhada"
        if (h.percentual_lido or 0) >= 100:
            return "concluida"
        return "em_progresso"

    return [
        HistoricoResponse(
            missa_id=m.id,
            data=m.data.isoformat(),
            celebracao=m.celebracao,
            ultimo_bloco_id=h.ultimo_bloco_id if h else None,
            percentual_lido=h.percentual_lido if h else 0.0,
            data_ultimo_acesso=h.data_ultimo_acesso if h else None,
            status=_status(h),
        )
        for m, h in registros
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


@router.post("/usuarios/me/historico/{missa_id}/concluir", status_code=200)
def concluir_missa(missa_id: int, usuario: Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    missa = db.query(Missa).filter(Missa.id == missa_id).first()
    if not missa:
        raise HTTPException(status_code=404, detail="Missa não encontrada")
    registro = db.query(HistoricoUsuario).filter(
        HistoricoUsuario.usuario_id == usuario.id, HistoricoUsuario.missa_id == missa_id,
    ).first()
    if registro:
        registro.percentual_lido = 100.0
        registro.data_ultimo_acesso = datetime.now(timezone.utc)
    else:
        registro = HistoricoUsuario(usuario_id=usuario.id, missa_id=missa_id, percentual_lido=100.0)
        db.add(registro)
    db.commit()
    return {"message": "Missa marcada como concluída", "status": "concluida"}


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
def broadcast_lembrete(
    dados: LembreteBroadcast,
    admin: Usuario = Depends(obter_usuario_admin),
    db: Session = Depends(get_db),
):
    """Envia um lembrete em massa para usuários segmentados.

    Filtros (combinam com AND):
    - `usuario_id`: envia só para esse usuário
    - `igreja`: envia só para usuários daquela igreja
    Sem filtros → envia pra todos.
    """
    query = db.query(Usuario)
    if dados.usuario_id:
        query = query.filter(Usuario.id == dados.usuario_id)
    if dados.igreja:
        query = query.filter(Usuario.igreja == dados.igreja)
    usuarios = query.all()
    remetente = dados.remetente or "Missa do Dia"
    for u in usuarios:
        lembrete = Lembrete(
            usuario_id=u.id,
            titulo=dados.titulo,
            nota=dados.nota,
            data_hora_alerta=dados.data_hora_alerta,
            minutos_antecedencia=dados.minutos_antecedencia,
            tipo="master",
            remetente=remetente,
        )
        db.add(lembrete)
    db.commit()
    return {
        "message": f"Lembrete enviado para {len(usuarios)} usuário(s)",
        "destinatarios": len(usuarios),
    }


@router.get("/admin/igrejas", response_model=list[str])
def listar_igrejas(
    admin: Usuario = Depends(obter_usuario_admin),
    db: Session = Depends(get_db),
):
    """Lista as igrejas distintas registradas (para segmentação no painel admin)."""
    rows = db.query(Usuario.igreja).filter(Usuario.igreja.isnot(None)).distinct().all()
    return sorted([r[0] for r in rows if r[0]])


@router.get("/admin/usuarios/contagem")
def contar_usuarios_admin(
    igreja: Optional[str] = None,
    admin: Usuario = Depends(obter_usuario_admin),
    db: Session = Depends(get_db),
):
    """Retorna a contagem de usuários por filtro — útil pra prever o alcance de um broadcast."""
    query = db.query(Usuario)
    if igreja:
        query = query.filter(Usuario.igreja == igreja)
    return {"total": query.count(), "igreja": igreja}


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
