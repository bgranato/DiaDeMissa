from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from uuid import uuid4
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, String, func

from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    criar_access_token,
    gerar_hash_senha,
    obter_usuario_atual,
    obter_usuario_opcional,
    obter_usuario_admin,
    verificar_senha,
)
from app.models.usuario import Usuario, PreferenciaUsuario, HistoricoUsuario, Lembrete, FeedbackUsuario
from app.models.missa import Missa, BlocoLiturgico
from app.models.igreja import Igreja, UsuarioIgreja
from app.models.uso_geocoding import UsoGeocodingMensal
from app.schemas.usuario import (
    UsuarioCreate, UsuarioResponse, UsuarioUpdate,
    LoginRequest, LoginGoogleRequest, LoginGoogleTokenRequest, LoginResponse,
    RecuperarSenhaRequest, RedefinirSenhaRequest, AlterarSenhaRequest,
    PreferenciasResponse, PreferenciasUpdate,
    HistoricoResponse, HistoricoCreate,
    LembreteCreate, LembreteResponse, LembreteUpdate, LembreteBroadcast,
    MetaMensalUpdate, AdminUsuarioUpdate, FeedbackCreate, FeedbackResponse,
)
from app.models.custo_llm import CustoLLM
from app.models.apoio import Apoio
from app.schemas.missa import (
    BlocoResponse, MissaResponse, MissaCompletaResponse,
)
from app.schemas.igreja import IgrejaCreate, IgrejaUpdate, IgrejaResponse, LocalizacaoEnderecoRequest
from app.pipeline import processar_pdf
from app.services.catalogo_catolico import eh_local_catolico_oficial
from app.services.google_places import GeocodingIndisponivelError, geocodificar_query_google, geocoding_configurado
from app.services.cota_geocoding import ControleGeocodingIndisponivelError, reservar_consulta
from app.schemas.apoio import (
    ApoioCheckoutRequest,
    ApoioCheckoutResponse,
    ApoioStatusResponse,
    ApoiosConfiguracaoResponse,
)
from app.services.mercado_pago import (
    MercadoPagoErro,
    VALORES_PERMITIDOS,
    configurado as mercado_pago_configurado,
    consultar_pagamento,
    criar_checkout,
    validar_assinatura_webhook,
)

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "version": settings.APP_VERSION, "app": settings.APP_NAME}


@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def enviar_feedback(
    dados: FeedbackCreate,
    db: Session = Depends(get_db),
    usuario: Usuario | None = Depends(obter_usuario_opcional),
):
    """Recebe relato de problema ou sugestão, inclusive de visitantes."""
    mensagem = dados.mensagem.strip()
    if len(mensagem) < 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Escreva pelo menos 10 caracteres para conseguirmos entender.",
        )
    feedback = FeedbackUsuario(
        usuario_id=usuario.id if usuario else None,
        tipo=dados.tipo,
        mensagem=mensagem,
        email_contato=str(dados.email_contato) if dados.email_contato else None,
        tela=dados.tela.strip() if dados.tela else None,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


@router.get("/apoios/configuracao", response_model=ApoiosConfiguracaoResponse)
def configuracao_apoios():
    """Expõe somente se o fluxo está seguro e habilitado; não vaza credenciais."""
    return {
        "ativo": mercado_pago_configurado(),
        "valores_centavos": [500, 1000, 1500],
        "reexibir_em_dias": 1,
    }


@router.post("/apoios/checkout", response_model=ApoioCheckoutResponse, status_code=status.HTTP_201_CREATED)
def iniciar_checkout_apoio(
    dados: ApoioCheckoutRequest,
    db: Session = Depends(get_db),
    usuario: Usuario | None = Depends(obter_usuario_opcional),
):
    """Inicia apoio avulso, com valor fechado e checkout externo do provedor."""
    if not mercado_pago_configurado():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Apoios ainda não estão disponíveis.")
    if dados.valor_centavos not in VALORES_PERMITIDOS:
        # Defesa adicional caso o schema seja alterado sem atualizar o contrato.
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Valor de apoio inválido.")

    apoio = Apoio(
        public_id=str(uuid4()),
        usuario_id=usuario.id if usuario else None,
        missa_id=dados.missa_id,
        valor_centavos=dados.valor_centavos,
        status="iniciado",
    )
    db.add(apoio)
    db.flush()
    try:
        checkout_url, preference_id = criar_checkout(apoio_id=apoio.public_id, valor_centavos=apoio.valor_centavos)
    except MercadoPagoErro as exc:
        apoio.status = "erro_checkout"
        db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Não foi possível abrir o pagamento agora.") from exc

    apoio.preference_id = preference_id
    apoio.status = "aguardando_pagamento"
    db.commit()
    return {"apoio_id": apoio.public_id, "checkout_url": checkout_url}


@router.get("/apoios/{apoio_id}/status", response_model=ApoioStatusResponse)
def status_apoio(apoio_id: str, db: Session = Depends(get_db)):
    """Estado enxuto para a tela de retorno; valores e dados pessoais não saem daqui."""
    apoio = db.query(Apoio).filter(Apoio.public_id == apoio_id).first()
    if apoio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Apoio não encontrado.")
    return {"status": apoio.status}


def _payment_id_do_webhook(request: Request, corpo: object) -> str | None:
    candidato = request.query_params.get("data.id")
    if not candidato and isinstance(corpo, dict):
        data = corpo.get("data")
        if isinstance(data, dict):
            candidato = data.get("id")
    if candidato is None:
        return None
    return str(candidato)


def _valor_em_centavos(valor: object) -> int | None:
    try:
        centavos = Decimal(str(valor)) * 100
        if centavos != centavos.to_integral_value():
            return None
        return int(centavos)
    except (InvalidOperation, ValueError, TypeError):
        return None


@router.post("/apoios/mercadopago/webhook", status_code=status.HTTP_200_OK)
async def webhook_mercado_pago(request: Request, db: Session = Depends(get_db)):
    """Confirma o pagamento somente após validar assinatura e consultar a API oficial."""
    try:
        corpo: object = await request.json()
    except ValueError:
        corpo = {}
    payment_id = _payment_id_do_webhook(request, corpo)
    if not payment_id or not validar_assinatura_webhook(
        x_signature=request.headers.get("x-signature"),
        x_request_id=request.headers.get("x-request-id"),
        payment_id=payment_id,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura de webhook inválida.")

    try:
        pagamento = consultar_pagamento(payment_id)
    except MercadoPagoErro as exc:
        # O Mercado Pago reenviará notificações que não recebam 2xx.
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Confirmação temporariamente indisponível.") from exc

    referencia = pagamento.get("external_reference")
    if not isinstance(referencia, str):
        return {"ok": True}
    apoio = db.query(Apoio).filter(Apoio.public_id == referencia).first()
    if apoio is None:
        return {"ok": True}

    valor = _valor_em_centavos(pagamento.get("transaction_amount"))
    moeda = pagamento.get("currency_id")
    if valor != apoio.valor_centavos or moeda != "BRL":
        apoio.status = "divergencia_pagamento"
        db.commit()
        return {"ok": True}

    status_provedor = str(pagamento.get("status") or "desconhecido")
    apoio.status = status_provedor
    apoio.payment_id = payment_id
    apoio.metodo_pagamento = str(pagamento.get("payment_type_id") or "") or None
    if status_provedor == "approved":
        apoio.confirmado_em = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


from pathlib import Path
from app.services.persist_missa import conferencia_publicavel, reconstruir_missa
PDF_FIXTURE = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures" / "amissa_ascensao_2026.pdf"

_fixture_cache = None


def missa_publicavel(missa: Missa | None, *, exigir_blocos: bool = True) -> bool:
    """Defesa em profundidade da exposição pública de uma missa.

    Mesmo se um dado inconsistente chegar ao banco, `concluido` sozinho jamais
    basta para entregá-lo ao fiel: a conferência Gauntlet completa é obrigatória.
    """
    return bool(
        missa
        and missa.status_processamento == "concluido"
        and conferencia_publicavel(missa.revisao_json)
        and (not exigir_blocos or bool(missa.blocos))
    )


MENSAGEM_CONTEUDO_RESTRITO = (
    "Conteúdo restrito à usuários cadastrados. Cadastre-se gratuitamente ou faça login para acessar."
)


def _exigir_conta_para_acervo(usuario: Usuario | None) -> Usuario:
    """Impede que URLs de agenda, busca ou PDF contornem a tela de acesso."""
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MENSAGEM_CONTEUDO_RESTRITO)
    return usuario


def _missa_publica_para_visitante(missa: Missa | None, db: Session) -> bool:
    """A exceção pública é a missa vigente e somente a primeira próxima montada.

    Missas passadas nunca entram nessa exceção; um lote futuro também não pode
    expor antecipadamente todo o acervo.
    """
    if not missa_publicavel(missa):
        return False

    hoje = _agora_brasilia().date()
    data_liturgica = data_liturgica_do_dia()
    if missa.data in {hoje, data_liturgica}:
        return True

    futuras = (
        db.query(Missa)
        .filter(Missa.data > hoje, Missa.status_processamento == "concluido")
        .order_by(Missa.data.asc())
        .all()
    )
    primeira_publicavel = next((item for item in futuras if missa_publicavel(item)), None)
    return bool(primeira_publicavel and primeira_publicavel.id == missa.id)


def _exigir_missa_publica_ou_conta(missa: Missa | None, db: Session, usuario: Usuario | None) -> None:
    if usuario is None and not _missa_publica_para_visitante(missa, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MENSAGEM_CONTEUDO_RESTRITO)

def _carregar_fixture():
    global _fixture_cache
    try:
        _fixture_cache = processar_pdf(PDF_FIXTURE).model_dump()
    except Exception as e:
        print(f"Erro ao carregar fixture: {e}")

# Fallback fixture para quando o BD ainda não tem a missa do dia
#_carregar_fixture()  # REMOVIDO: rodava montagem (multimodal LLM) no IMPORT -> boot lento/502; _fixture_cache nunca e lido


@router.get("/missas/buscar")
def buscar_missas(
    q: Optional[str] = None,
    dias: int = 365,
    apenas_arqrio: bool = False,
    db: Session = Depends(get_db),
    usuario: Usuario | None = Depends(obter_usuario_opcional),
):
    """Busca missas passadas. Útil para a Jornada do usuário acessar conteúdo
    de missas antigas (ex: Solenidades passadas).

    Args:
        q: texto livre — casa em celebracao (case-insensitive) OU em uma data ISO (YYYY-MM-DD)
        dias: quantos dias retroativos considerar (default 365)
        apenas_arqrio: filtra só missas vindas do folheto Arquidiocese (mais ricas)
    """
    _exigir_conta_para_acervo(usuario)
    from datetime import date as date_cls, timedelta
    hoje = date_cls.today()
    inicio = hoje - timedelta(days=dias)
    query = db.query(Missa).filter(Missa.data <= hoje, Missa.data >= inicio)
    if apenas_arqrio:
        query = query.filter(Missa.fonte_pdf_url.like("%arqrio%"))
    if q:
        q = q.strip()
        # Aceita formatos de data (PT-BR é prioritário):
        #   24/05/2026, 24-05-2026, 24.05.2026        (DD/MM/AAAA)
        #   24/05/26                                   (DD/MM/AA → 2024+26 = 2026)
        #   24/05                                      (DD/MM — qualquer ano)
        #   05/2026                                    (MM/AAAA — mês inteiro)
        #   2026-05-24, 2026/05/24, 20260524           (ISO)
        #   2026-05, 2026                              (prefixos)
        # Caso nenhum padrão de data funcione, busca texto em título e observações.
        import re as _re
        q_norm = _re.sub(r"[/.\-]", "-", q)
        partes = q_norm.split("-")
        usou_data = False
        try:
            # YYYYMMDD (8 dígitos sem separadores)
            if len(q_norm) == 8 and q_norm.isdigit():
                data_q = date_cls.fromisoformat(f"{q_norm[:4]}-{q_norm[4:6]}-{q_norm[6:]}")
                query = query.filter(Missa.data == data_q)
                usou_data = True
            # 3 partes: DD-MM-YYYY (BR) ou YYYY-MM-DD (ISO) ou DD-MM-YY
            elif len(partes) == 3:
                if len(partes[0]) == 4:  # ISO: YYYY-MM-DD
                    data_q = date_cls.fromisoformat(
                        f"{partes[0]}-{partes[1].zfill(2)}-{partes[2].zfill(2)}"
                    )
                elif len(partes[2]) == 4:  # BR: DD-MM-YYYY
                    data_q = date_cls.fromisoformat(
                        f"{partes[2]}-{partes[1].zfill(2)}-{partes[0].zfill(2)}"
                    )
                elif len(partes[2]) == 2:  # BR curto: DD-MM-YY → assume 2000+YY
                    yy = int(partes[2])
                    ano = 2000 + yy if yy < 50 else 1900 + yy
                    data_q = date_cls.fromisoformat(
                        f"{ano}-{partes[1].zfill(2)}-{partes[0].zfill(2)}"
                    )
                else:
                    raise ValueError("formato 3-partes não reconhecido")
                query = query.filter(Missa.data == data_q)
                usou_data = True
            # 2 partes: pode ser DD-MM (sem ano) OU YYYY-MM (mês) OU MM-YYYY
            elif len(partes) == 2:
                if len(partes[0]) == 4:  # YYYY-MM
                    prefixo = f"{partes[0]}-{partes[1].zfill(2)}"
                    query = query.filter(Missa.data.cast(String).like(f"{prefixo}%"))
                    usou_data = True
                elif len(partes[1]) == 4:  # MM-YYYY (brasileiro: mês/ano)
                    prefixo = f"{partes[1]}-{partes[0].zfill(2)}"
                    query = query.filter(Missa.data.cast(String).like(f"{prefixo}%"))
                    usou_data = True
                else:  # DD-MM (sem ano) — busca em todos os anos com esse mês-dia
                    sufixo = f"-{partes[1].zfill(2)}-{partes[0].zfill(2)}"
                    query = query.filter(Missa.data.cast(String).like(f"%{sufixo}"))
                    usou_data = True
            # 1 parte só: ano (YYYY)
            elif q_norm.isdigit() and len(q_norm) == 4:
                query = query.filter(Missa.data.cast(String).like(f"{q_norm}%"))
                usou_data = True
        except ValueError:
            pass
        if not usou_data:
            # Busca texto em celebracao OU observacoes
            from sqlalchemy import or_
            query = query.filter(or_(
                Missa.celebracao.ilike(f"%{q}%"),
                Missa.observacoes.ilike(f"%{q}%"),
            ))
    missas = [m for m in query.order_by(Missa.data.desc()).all() if missa_publicavel(m)][:50]
    return [
        {
            "id": m.id,
            "data": m.data.isoformat(),
            "celebracao": m.celebracao,
            "categoria": m.categoria,
            "observacoes": m.observacoes,
            "total_blocos": len(m.blocos) if m.blocos else 0,
            "fonte_arqrio": "arqrio" in (m.fonte_pdf_url or "").lower(),
            "status": m.status_processamento,
        }
        for m in missas
    ]


@router.get("/missas/{data_iso}/pdf-arqrio")
def baixar_pdf_arqrio(
    data_iso: str,
    usuario: Usuario | None = Depends(obter_usuario_opcional),
):
    """Serve o PDF original do folheto Arquidiocese arquivado pra essa data.

    Útil pra o usuário/admin conferir se a missa foi montada corretamente
    comparando com o folheto fonte. Path: /var/lib/diademissa/pdfs/archive/YYYY-MM-DD.pdf
    """
    _exigir_conta_para_acervo(usuario)
    from fastapi.responses import FileResponse
    from app.pipeline.download import CACHE_DIR
    pdf_path = CACHE_DIR / "archive" / f"{data_iso}.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF de {data_iso} não arquivado")
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"folheto-arqrio-{data_iso}.pdf",
    )


@router.get("/missa/por-data/{data_iso}")
def missa_por_data_estruturada(
    data_iso: str,
    db: Session = Depends(get_db),
    usuario: Usuario | None = Depends(obter_usuario_opcional),
):
    """Retorna missa estruturada (com blocos) para uma data específica.
    Usado quando o usuário acessa uma missa de outro dia pela Agenda."""
    from datetime import date as date_cls
    try:
        data_obj = date_cls.fromisoformat(data_iso)
    except ValueError:
        raise HTTPException(status_code=400, detail="Data inválida (use YYYY-MM-DD)")
    missa_db = db.query(Missa).filter(Missa.data == data_obj).first()
    if missa_publicavel(missa_db):
        _exigir_missa_publica_ou_conta(missa_db, db, usuario)
        return reconstruir_missa(missa_db)
    # Regra "só folheto": sem folheto processado pra essa data → não há missa.
    # Não fabricamos mais via CNBB/Missal Padrão.
    raise HTTPException(status_code=404, detail=f"Missa de {data_iso} indisponível")


# A partir desta hora no SÁBADO, a "missa do dia" passa a ser a do DOMINGO — a missa
# vespertina de sábado (vigília) já é, liturgicamente, a missa do domingo.
VIGILIA_SABADO_HORA = 16  # 16h (horário de Brasília). Ajuste aqui se quiser mais cedo/tarde.


def _agora_brasilia() -> datetime:
    """Datetime atual no fuso de Brasília (com fallback fixo UTC-3, sem horário de verão)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Sao_Paulo"))
    except Exception:
        return datetime.now(timezone.utc) - timedelta(hours=3)


def data_liturgica_do_dia() -> date:
    """Data da missa 'do dia', tratando a vigília: sábado à tarde/noite → domingo."""
    agora = _agora_brasilia()
    d = agora.date()
    if d.weekday() == 5 and agora.hour >= VIGILIA_SABADO_HORA:  # 5 = sábado
        return d + timedelta(days=1)
    return d


@router.get("/missa/atual")
def missa_atual(db: Session = Depends(get_db)):
    hoje_real = _agora_brasilia().date()
    alvo = data_liturgica_do_dia()
    # Na vigília, tenta primeiro o domingo; se ainda não estiver pronto, cai no dia real.
    candidatas = [alvo] if alvo == hoje_real else [alvo, hoje_real]
    for data in candidatas:
        missa_db = db.query(Missa).filter(Missa.data == data).first()
        if missa_publicavel(missa_db):
            return reconstruir_missa(missa_db)

    # Regra "só folheto": sem folheto processado pra hoje → não há missa.
    # O app usa /missa/proxima pra mostrar a próxima missa disponível.
    raise HTTPException(
        status_code=404,
        detail="Sem missa para hoje (só há missa em dias com folheto)",
    )


@router.get("/missa/proxima")
def missa_proxima(db: Session = Depends(get_db)):
    """Próxima missa disponível (com folheto concluído), a partir de hoje.

    Usado pelo app quando não há missa no dia: mostra 'próxima missa: <data>'.
    Retorna {data, celebracao, categoria} ou {data: null} se nada disponível ainda.
    """
    hoje = _agora_brasilia().date()
    candidatas = (
        db.query(Missa)
        .filter(Missa.data >= hoje, Missa.status_processamento == "concluido")
        .order_by(Missa.data.asc())
        .all()
    )
    for m in candidatas:
        if missa_publicavel(m):
            return {
                "data": m.data.isoformat(),
                "celebracao": m.celebracao,
                "categoria": getattr(m, "categoria", None),
                "montada": True,
            }
    return {"data": None, "celebracao": None, "categoria": None, "montada": False}


@router.get("/missa/agenda")
def missa_agenda(
    db: Session = Depends(get_db),
    usuario: Usuario | None = Depends(obter_usuario_opcional),
):
    """Agenda enxuta: as 3 últimas missas anteriores (com conteúdo) + a próxima.

    A próxima vem com `montada`: True se o folheto já foi montado (tem card completo),
    False se ainda não — nesse caso retorna só a data prevista (próximo domingo), para
    o app mostrar um card "em breve" que se atualiza sozinho quando a missa for montada.
    """
    _exigir_conta_para_acervo(usuario)
    from datetime import timedelta
    hoje = _agora_brasilia().date()

    def _dump(m):
        return {"id": m.id, "data": m.data.isoformat(), "celebracao": m.celebracao,
                "categoria": getattr(m, "categoria", None)}

    anteriores = []
    for m in (db.query(Missa)
              .filter(Missa.data < hoje, Missa.status_processamento == "concluido")
              .order_by(Missa.data.desc()).all()):
        if missa_publicavel(m):
            anteriores.append(_dump(m))
        if len(anteriores) >= 3:
            break

    proxima = None
    for m in (db.query(Missa)
              .filter(Missa.data >= hoje, Missa.status_processamento == "concluido")
              .order_by(Missa.data.asc()).all()):
        if missa_publicavel(m):
            proxima = {**_dump(m), "montada": True}
            break
    if proxima is None:
        # ainda não montada: próximo domingo (folheto sai sáb/dom/solenidades)
        dias = (6 - hoje.weekday()) % 7  # weekday: seg=0 … dom=6
        prox_dom = hoje if dias == 0 else hoje + timedelta(days=dias)
        proxima = {"data": prox_dom.isoformat(), "celebracao": None, "categoria": None, "montada": False}

    return {"anteriores": anteriores, "proxima": proxima}


@router.get("/missas/hoje", response_model=MissaResponse)
def get_missa_hoje(db: Session = Depends(get_db)):
    hoje_real = _agora_brasilia().date()
    alvo = data_liturgica_do_dia()  # vigília: sábado à tarde/noite → domingo
    missa = db.query(Missa).filter(Missa.data == alvo).first()
    if not missa and alvo != hoje_real:
        missa = db.query(Missa).filter(Missa.data == hoje_real).first()
    if not missa_publicavel(missa, exigir_blocos=False):
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
def get_missa_por_data(
    data: date,
    db: Session = Depends(get_db),
    usuario: Usuario | None = Depends(obter_usuario_opcional),
):
    missa = db.query(Missa).filter(Missa.data == data).first()
    if not missa_publicavel(missa, exigir_blocos=False):
        raise HTTPException(status_code=404, detail="Missa não encontrada para esta data")
    _exigir_missa_publica_ou_conta(missa, db, usuario)
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
def get_blocos_missa(
    id: int,
    db: Session = Depends(get_db),
    usuario: Usuario | None = Depends(obter_usuario_opcional),
):
    missa = db.query(Missa).filter(Missa.id == id).first()
    if not missa_publicavel(missa):
        raise HTTPException(status_code=404, detail="Missa não encontrada")
    _exigir_missa_publica_ou_conta(missa, db, usuario)
    blocos = (
        db.query(BlocoLiturgico)
        .filter(BlocoLiturgico.missa_id == id, BlocoLiturgico.visivel == True)
        .order_by(BlocoLiturgico.ordem)
        .all()
    )
    return [BlocoResponse.model_validate(b) for b in blocos]


@router.get("/missas/{id}/completa", response_model=MissaCompletaResponse)
def get_missa_completa(
    id: int,
    db: Session = Depends(get_db),
    usuario: Usuario | None = Depends(obter_usuario_opcional),
):
    missa = db.query(Missa).filter(Missa.id == id).first()
    if not missa_publicavel(missa):
        raise HTTPException(status_code=404, detail="Missa não encontrada")
    _exigir_missa_publica_ou_conta(missa, db, usuario)
    return MissaCompletaResponse.model_validate(missa)


@router.post("/missas/processar-pdf")
def processar_pdf_legado(admin: Usuario = Depends(obter_usuario_admin)):
    """Compatibilidade para a rota antiga, agora protegida pelo mesmo gate.

    A rota antes acionava o processador legado sem revisão independente. Mantemos
    a URL para clientes administrativos, mas delegamos ao pipeline produtivo.
    """
    from app.services.daily_pipeline import executar_pipeline_diario
    return executar_pipeline_diario()


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


@router.post("/admin/igrejas/atualizar-catalogo")
def atualizar_catalogo_igrejas_endpoint(admin: Usuario = Depends(obter_usuario_admin)):
    """Dispara manualmente a atualização do catálogo de igrejas (re-scrape Arquidiocese).

    O cron semanal (segundas 4h) faz isso automaticamente. Endpoint útil pra ops.
    Demora ~10min e roda síncrono — chame com timeout adequado.
    """
    from app.services.atualizacao_igrejas_job import atualizar_catalogo_igrejas
    return atualizar_catalogo_igrejas()


@router.post("/admin/liturgia/atualizar")
def atualizar_liturgia_manual(
    dias: int = 7,
    admin: Usuario = Depends(obter_usuario_admin),
):
    """Dispara manualmente o scraping da liturgia diária (Canção Nova/CNBB).

    Gera missa completa via Missal Padrão pra hoje + próximos `dias` (default 7).
    Esse endpoint existe pra ops/desenvolvimento; o cron diário às 5h05 chama
    a mesma função automaticamente.
    """
    raise HTTPException(
        status_code=409,
        detail="Fluxo CNBB/Missal bloqueado: publique somente pelo PDF oficial e Gauntlet Loop.",
    )


@router.post("/admin/lembretes/disparar-nao-acompanhada")
def disparar_notif_nao_acompanhada(admin: Usuario = Depends(obter_usuario_admin)):
    """Dispara manualmente a geração de lembretes 'você não acompanhou a missa de ontem'.

    O cron noturno (22h America/Sao_Paulo) chama isso automaticamente. Este endpoint
    é pra desenvolvimento e operações.
    """
    from app.services.notif_nao_acompanhou import gerar_notificacoes_nao_acompanhada
    return gerar_notificacoes_nao_acompanhada()


# ======================= REVISÃO DE MISSAS (gate PDF) =======================

@router.get("/admin/missas/revisao")
def admin_listar_revisao(
    incluir_ok: bool = False,
    admin: Usuario = Depends(obter_usuario_admin),
    db: Session = Depends(get_db),
):
    """Lista missas para revisão (pendente_revisao) com as divergências do gate.

    Cada item traz: data, título, status, o link do PDF-fonte, e as divergências
    (críticas primeiro) apontadas pelo gate PDF×montagem. `incluir_ok=true` traz
    também as concluídas que têm resultado de gate (para conferência).
    """
    q = db.query(Missa)
    if incluir_ok:
        q = q.filter(Missa.status_processamento.in_(["pendente_revisao", "concluido"]))
    else:
        q = q.filter(Missa.status_processamento == "pendente_revisao")
    missas = q.order_by(desc(Missa.data)).limit(60).all()

    def dump(m: Missa) -> dict:
        rev = m.revisao_json or {}
        conferencia = rev.get("conferencia") or {}
        divergencias = conferencia.get("divergencias_restantes", rev.get("todas", []))
        criticas = [d for d in divergencias
                     if str(d.get("severidade", "")).lower() == "critica"]
        return {
            "data": m.data.isoformat() if m.data else None,
            "titulo_celebracao": m.celebracao,
            "status": m.status_processamento,
            "pdf_url": f"/api/v1/missas/{m.data.isoformat()}/pdf-arqrio" if m.data else None,
            "gate_ok": conferencia.get("conferida", rev.get("ok")),
            "criticas": criticas or rev.get("criticas", []),
            "divergencias": divergencias,
            "iteracoes": conferencia.get("iteracoes"),
        }

    return {"total": len(missas), "missas": [dump(m) for m in missas]}


@router.post("/admin/missas/{data_iso}/aprovar")
def admin_aprovar_missa(
    data_iso: str,
    admin: Usuario = Depends(obter_usuario_admin),
    db: Session = Depends(get_db),
):
    """Publica somente uma revisão que já tenha passado pelo Gauntlet Loop."""
    from datetime import date as _date
    m = db.query(Missa).filter(Missa.data == _date.fromisoformat(data_iso)).first()
    if not m:
        raise HTTPException(status_code=404, detail=f"Missa {data_iso} não encontrada")
    from app.services.persist_missa import conferencia_publicavel

    conferencia = (m.revisao_json or {}).get("conferencia") or {}
    divergencias = conferencia.get("divergencias_restantes", (m.revisao_json or {}).get("todas", []))
    tem_critica = any(str(d.get("severidade", "")).lower() == "critica" for d in divergencias)
    if not conferencia_publicavel(m.revisao_json) or tem_critica:
        raise HTTPException(
            status_code=409,
            detail="Publicação bloqueada: corrija e reexecute a conferência independente contra o PDF.",
        )
    m.status_processamento = "concluido"
    db.add(m)
    db.commit()
    return {"data": data_iso, "status": m.status_processamento, "aprovado_por": admin.email}


# ======================= PAINEL MASTER (admin) — Fase 1 =======================

@router.get("/admin/feedback")
def admin_listar_feedback(
    status_feedback: str | None = Query(default=None, alias="status"),
    limite: int = 100,
    admin: Usuario = Depends(obter_usuario_admin),
    db: Session = Depends(get_db),
):
    """Fila de problemas e sugestões enviada pelo aplicativo."""
    query = db.query(FeedbackUsuario)
    if status_feedback:
        query = query.filter(FeedbackUsuario.status == status_feedback)
    itens = query.order_by(desc(FeedbackUsuario.data_criacao)).limit(max(1, min(limite, 500))).all()
    return {
        "total": len(itens),
        "feedback": [{
            "id": item.id,
            "usuario_id": item.usuario_id,
            "tipo": item.tipo,
            "mensagem": item.mensagem,
            "email_contato": item.email_contato,
            "tela": item.tela,
            "status": item.status,
            "data_criacao": item.data_criacao.isoformat() if item.data_criacao else None,
        } for item in itens],
    }

@router.get("/admin/usuarios")
def admin_listar_usuarios(
    q: str = "",
    limite: int = 200,
    admin: Usuario = Depends(obter_usuario_admin),
    db: Session = Depends(get_db),
):
    """Lista usuários (busca por nome/e-mail) com engajamento agregado."""
    query = db.query(Usuario)
    if q:
        like = f"%{q}%"
        query = query.filter((Usuario.nome.ilike(like)) | (Usuario.email.ilike(like)))
    usuarios = query.order_by(desc(Usuario.data_criacao)).limit(max(1, min(limite, 1000))).all()

    ids = [u.id for u in usuarios]
    eng: dict = {}
    if ids:
        rows = (
            db.query(
                HistoricoUsuario.usuario_id,
                func.count(HistoricoUsuario.id),
                func.max(HistoricoUsuario.data_ultimo_acesso),
            )
            .filter(HistoricoUsuario.usuario_id.in_(ids))
            .group_by(HistoricoUsuario.usuario_id)
            .all()
        )
        eng = {r[0]: (r[1], r[2]) for r in rows}

    def dump(u: Usuario) -> dict:
        n, ult = eng.get(u.id, (0, None))
        return {
            "id": u.id, "nome": u.nome, "email": u.email, "celular": u.celular,
            "provider": u.provider, "igreja": u.igreja,
            "is_admin": bool(u.is_admin), "status": getattr(u, "status", "ativo"),
            "data_criacao": u.data_criacao.isoformat() if u.data_criacao else None,
            "missas_acompanhadas": n,
            "ultimo_acesso": ult.isoformat() if ult else None,
        }

    return {"total": len(usuarios), "usuarios": [dump(u) for u in usuarios]}


@router.patch("/admin/usuarios/{usuario_id}")
def admin_atualizar_usuario(
    usuario_id: int,
    dados: AdminUsuarioUpdate,
    admin: Usuario = Depends(obter_usuario_admin),
    db: Session = Depends(get_db),
):
    """Promove/remove admin e muda status (ativo/bloqueado/cancelado)."""
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    # Trava anti-lockout: o admin não pode remover o próprio acesso nem se bloquear.
    if u.id == admin.id and (dados.is_admin is False or dados.status in ("bloqueado", "cancelado")):
        raise HTTPException(status_code=400, detail="Você não pode remover o próprio acesso de admin nem bloquear a si mesmo")
    if dados.is_admin is not None:
        u.is_admin = dados.is_admin
    if dados.status is not None:
        if dados.status not in ("ativo", "bloqueado", "cancelado"):
            raise HTTPException(status_code=400, detail="status inválido (use ativo|bloqueado|cancelado)")
        u.status = dados.status
    db.commit(); db.refresh(u)
    return {"id": u.id, "is_admin": bool(u.is_admin), "status": getattr(u, "status", "ativo")}


@router.get("/admin/metrics/overview")
def admin_metrics_overview(
    admin: Usuario = Depends(obter_usuario_admin),
    db: Session = Depends(get_db),
):
    """Números-resumo do painel."""
    agora = datetime.now(timezone.utc)
    d7 = agora - timedelta(days=7)
    d30 = agora - timedelta(days=30)
    ini_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def c(q):
        return q.scalar() or 0

    total = c(db.query(func.count(Usuario.id)))
    novos_7 = c(db.query(func.count(Usuario.id)).filter(Usuario.data_criacao >= d7))
    novos_30 = c(db.query(func.count(Usuario.id)).filter(Usuario.data_criacao >= d30))
    bloqueados = c(db.query(func.count(Usuario.id)).filter(Usuario.status == "bloqueado"))
    cancelados = c(db.query(func.count(Usuario.id)).filter(Usuario.status == "cancelado"))
    ativos_7 = c(db.query(func.count(func.distinct(HistoricoUsuario.usuario_id))).filter(HistoricoUsuario.data_ultimo_acesso >= d7))
    ativos_30 = c(db.query(func.count(func.distinct(HistoricoUsuario.usuario_id))).filter(HistoricoUsuario.data_ultimo_acesso >= d30))
    missas_acomp = c(db.query(func.count(HistoricoUsuario.id)))
    pct_medio = db.query(func.avg(HistoricoUsuario.percentual_lido)).scalar() or 0.0
    custo_mes = db.query(func.sum(CustoLLM.custo_usd)).filter(CustoLLM.data_criacao >= ini_mes).scalar() or 0.0
    custo_total = db.query(func.sum(CustoLLM.custo_usd)).scalar() or 0.0

    return {
        "total_usuarios": total,
        "novos_7d": novos_7, "novos_30d": novos_30,
        "ativos_7d": ativos_7, "ativos_30d": ativos_30,
        "bloqueados": bloqueados, "cancelados": cancelados,
        "missas_acompanhadas": missas_acomp,
        "pct_lido_medio": round(float(pct_medio), 1),
        "custo_llm_mes": round(float(custo_mes), 4),
        "custo_llm_total": round(float(custo_total), 4),
    }


@router.get("/admin/metrics/series")
def admin_metrics_series(
    dias: int = 30,
    admin: Usuario = Depends(obter_usuario_admin),
    db: Session = Depends(get_db),
):
    """Série diária: novos usuários, acessos e custo LLM (agregação em Python p/ portabilidade)."""
    dias = max(1, min(dias, 180))
    inicio = (datetime.now(timezone.utc) - timedelta(days=dias - 1)).date()

    novos: dict = {}
    for (dt,) in db.query(Usuario.data_criacao).filter(Usuario.data_criacao.isnot(None)).all():
        d = dt.date()
        if d >= inicio:
            novos[d.isoformat()] = novos.get(d.isoformat(), 0) + 1

    acessos: dict = {}
    for (dt,) in db.query(HistoricoUsuario.data_ultimo_acesso).filter(HistoricoUsuario.data_ultimo_acesso.isnot(None)).all():
        d = dt.date()
        if d >= inicio:
            acessos[d.isoformat()] = acessos.get(d.isoformat(), 0) + 1

    custos: dict = {}
    for dt, valor in db.query(CustoLLM.data_criacao, CustoLLM.custo_usd).filter(CustoLLM.data_criacao.isnot(None)).all():
        d = dt.date()
        if d >= inicio:
            custos[d.isoformat()] = round(custos.get(d.isoformat(), 0.0) + float(valor or 0.0), 4)

    serie = []
    for i in range(dias):
        d = (inicio + timedelta(days=i)).isoformat()
        serie.append({
            "data": d,
            "novos_usuarios": novos.get(d, 0),
            "acessos": acessos.get(d, 0),
            "custo_llm": custos.get(d, 0.0),
        })
    return {"dias": dias, "serie": serie}


@router.get("/admin/metrics/dias-semana")
def admin_metrics_dias_semana(
    admin: Usuario = Depends(obter_usuario_admin),
    db: Session = Depends(get_db),
):
    """Distribuição de acessos por dia da semana (Segunda..Domingo)."""
    nomes = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    cont = [0] * 7
    for (dt,) in db.query(HistoricoUsuario.data_ultimo_acesso).filter(HistoricoUsuario.data_ultimo_acesso.isnot(None)).all():
        cont[dt.weekday()] += 1
    return {"dias": [{"dia": nomes[i], "acessos": cont[i]} for i in range(7)]}


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


@router.post("/auth/google-token", response_model=LoginResponse)
def login_google_token(dados: LoginGoogleTokenRequest, db: Session = Depends(get_db)):
    """Login com Google usando um token de ACESSO (fluxo do botão próprio).

    Segurança: validamos o token no endpoint tokeninfo do Google e conferimos
    que o campo `aud` corresponde ao NOSSO client_id — assim um token emitido
    para outro app não consegue autenticar aqui.
    """
    import httpx
    try:
        ti = httpx.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"access_token": dados.access_token},
            timeout=10.0,
        )
        if ti.status_code != 200:
            raise HTTPException(status_code=401, detail="Token Google inválido")
        info = ti.json()
        # `aud`/`azp` devem ser o NOSSO client_id (token emitido para este app).
        if settings.GOOGLE_CLIENT_ID not in (info.get("aud"), info.get("azp")):
            raise HTTPException(status_code=401, detail="Token Google de origem inválida")
        email = info.get("email")
        if not email:
            raise HTTPException(status_code=401, detail="Permissão de e-mail não concedida")
        google_id = info.get("sub")
        nome = email
        try:
            ui = httpx.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {dados.access_token}"},
                timeout=10.0,
            )
            if ui.status_code == 200:
                nome = ui.json().get("name") or email
        except Exception:
            pass
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
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Falha no login com Google")


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
    """Retorna TODAS as missas tocadas pelo usuário, com status por percentual:
       100% → concluida
       >0 e <100% → em_progresso
       0% → nao_acompanhada
    """
    registros = (
        db.query(Missa, HistoricoUsuario)
        .join(
            HistoricoUsuario,
            (HistoricoUsuario.missa_id == Missa.id) & (HistoricoUsuario.usuario_id == usuario.id),
        )
        .order_by(desc(Missa.data))
        .all()
    )

    # Resolve nomes das igrejas em lote
    igreja_ids = {h.igreja_id for _, h in registros if h and h.igreja_id}
    nomes_igrejas = {
        i.id: i.nome for i in db.query(Igreja).filter(Igreja.id.in_(igreja_ids)).all()
    } if igreja_ids else {}

    def _status(pct: float) -> str:
        if pct >= 100:
            return "concluida"
        if pct > 0:
            return "em_progresso"
        return "nao_acompanhada"

    return [
        HistoricoResponse(
            missa_id=m.id,
            data=m.data.isoformat(),
            celebracao=m.celebracao,
            ultimo_bloco_id=h.ultimo_bloco_id,
            percentual_lido=h.percentual_lido,
            data_ultimo_acesso=h.data_ultimo_acesso,
            status=_status(h.percentual_lido or 0),
            igreja_id=h.igreja_id,
            igreja_nome=nomes_igrejas.get(h.igreja_id) if h.igreja_id else None,
        )
        for m, h in registros
    ]


@router.post("/usuarios/me/historico", status_code=201)
def salvar_progresso(dados: HistoricoCreate, usuario: Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    # Valida que a missa existe antes de criar/atualizar histórico (evita órfãos).
    if not db.query(Missa).filter(Missa.id == dados.missa_id).first():
        raise HTTPException(status_code=404, detail=f"Missa {dados.missa_id} não encontrada")
    registro = db.query(HistoricoUsuario).filter(
        HistoricoUsuario.usuario_id == usuario.id, HistoricoUsuario.missa_id == dados.missa_id,
    ).first()
    if registro:
        registro.ultimo_bloco_id = dados.ultimo_bloco_id
        registro.percentual_lido = dados.percentual_lido
        registro.data_ultimo_acesso = datetime.now(timezone.utc)
        if dados.igreja_id is not None:
            registro.igreja_id = dados.igreja_id
    else:
        registro = HistoricoUsuario(
            usuario_id=usuario.id, missa_id=dados.missa_id,
            ultimo_bloco_id=dados.ultimo_bloco_id, percentual_lido=dados.percentual_lido,
            igreja_id=dados.igreja_id,
        )
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


@router.post("/usuarios/me/historico/{missa_id}/desconcluir", status_code=200)
def desconcluir_missa(missa_id: int, usuario: Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    """Remove a marcação de concluída. Idempotente: se não havia registro, retorna OK
    silenciosamente (cliente pode ter marcado só em localStorage)."""
    registro = db.query(HistoricoUsuario).filter(
        HistoricoUsuario.usuario_id == usuario.id, HistoricoUsuario.missa_id == missa_id,
    ).first()
    if registro:
        registro.percentual_lido = 0.0
        registro.ultimo_bloco_id = None
        registro.data_ultimo_acesso = datetime.now(timezone.utc)
        db.commit()
    return {"message": "Conclusão desfeita", "status": "nao_acompanhada"}


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
    for attr in ["tamanho_fonte", "modo_escuro", "alto_contraste", "leitura_simplificada", "notificacoes_ativas", "alerta_missa_email"]:
        val = getattr(dados, attr, None)
        if val is not None:
            setattr(pref, attr, val)
    db.commit()
    db.refresh(pref)
    return pref


# ===== JORNADA (relatório + meta) =====

@router.get("/usuarios/me/jornada/relatorio")
def get_relatorio_jornada(usuario: Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    """Dashboard agregado da Jornada: contagens, taxas, ranking, streak, série mensal."""
    from app.services.jornada import montar_relatorio
    return montar_relatorio(db, usuario)


@router.put("/usuarios/me/meta")
def atualizar_meta_mensal(dados: MetaMensalUpdate, usuario: Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    """Define ou remove (None) a meta de missas/mês do usuário."""
    valor = dados.meta_missas_mensal
    if valor is not None and (valor < 0 or valor > 200):
        raise HTTPException(status_code=400, detail="Meta inválida (0-200 missas/mês)")
    usuario.meta_missas_mensal = valor
    db.commit()
    db.refresh(usuario)
    return {"meta_missas_mensal": usuario.meta_missas_mensal}


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


@router.post("/usuarios/me/lembretes/{id}/lido", response_model=LembreteResponse)
def marcar_lembrete_lido(id: int, usuario: Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    lembrete = db.query(Lembrete).filter(Lembrete.id == id, Lembrete.usuario_id == usuario.id).first()
    if not lembrete:
        raise HTTPException(status_code=404, detail="Lembrete não encontrado")
    lembrete.lido = True
    db.commit()
    db.refresh(lembrete)
    return lembrete


@router.post("/usuarios/me/lembretes/marcar-todos-lidos", status_code=200)
def marcar_todos_lidos(usuario: Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    qty = db.query(Lembrete).filter(
        Lembrete.usuario_id == usuario.id,
        Lembrete.lido == False,
    ).update({"lido": True})
    db.commit()
    return {"marcados": qty}


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


# ============================================================
# IGREJAS — Catálogo + Favoritos do usuário
# ============================================================

def _calc_distancia_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine simplificada — distância em km entre dois pontos."""
    from math import asin, cos, radians, sin, sqrt
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * R * asin(sqrt(a))


def _normalizar(s: Optional[str]) -> str:
    """Lowercase + sem acentos. Pra busca tolerante a acentuação."""
    if not s:
        return ""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))


def _extrair_bairro(endereco: Optional[str]) -> str:
    """Extrai o bairro do endereço (heurística: último segmento sem número/prefixo de rua).

    'Rua Marquês de São Vicente, 19 - Gávea'  → 'Gávea'
    'Estrada da Gávea, 1 - Jardim Botânico'   → 'Jardim Botânico'
    'Av. Atlântica, 1500'                      → ''
    """
    if not endereco:
        return ""
    import re
    # Quebra por hífen ou vírgula
    partes = re.split(r"[-,]", endereco)
    PREFIXOS_RUA = re.compile(
        r"^(rua|r\.|av|av\.|avenida|pra[çc]a|p[çc]\.|estrada|estr\.|travessa|tv\.|largo|alameda|al\.|rodovia|rod\.|beco|ladeira|caminho|via|servid[ãa]o)\b",
        re.IGNORECASE,
    )
    for p in reversed(partes):
        p = p.strip()
        if not p:
            continue
        # Pula partes com números (CEP, número da rua)
        if re.search(r"\d", p):
            continue
        # Pula partes que começam com prefixo de logradouro
        if PREFIXOS_RUA.match(p):
            continue
        return p
    return ""


_PREFIXOS_IGREJA = ("paroquia ", "paróquia ", "igreja ", "capela ", "santuario ", "santuário ", "comunidade ", "comunida ", "catedral ", "matriz ")


def _raiz_nome(nome: Optional[str]) -> str:
    """Normaliza nome removendo prefixos comuns ('Paróquia', 'Igreja', etc.) e acentos.

    Usado para detectar a mesma igreja escrita de jeitos diferentes:
      'Paróquia Nossa Senhora da Paz' e 'Igreja Nossa Senhora da Paz' → mesma raiz.
    """
    n = _normalizar(nome or "")
    for _ in range(2):  # remove até 2 prefixos (ex.: "paroquia igreja ...")
        for p in _PREFIXOS_IGREJA:
            if n.startswith(p):
                n = n[len(p):]
                break
        else:
            break
    # Colapsa espaços múltiplos
    return " ".join(n.split())


def _eh_mesma_igreja(a: Igreja, b_nome: str, b_lat: Optional[float], b_lng: Optional[float]) -> bool:
    """True se `a` e (b_nome, b_lat, b_lng) provavelmente referem à mesma igreja.

    Critério: mesma raiz de nome E (sem coords ou distância ≤ 200m).
    Não considera duplicata por proximidade física só — Centro do Rio tem várias
    igrejas históricas legítimas a menos de 50m.
    """
    if _raiz_nome(a.nome) != _raiz_nome(b_nome):
        return False
    if a.lat is None or a.lng is None or b_lat is None or b_lng is None:
        return True
    return _calc_distancia_km(a.lat, a.lng, b_lat, b_lng) <= 0.2


def _serializar_igreja(igreja: Igreja, favorita_ids: set[int], lat: Optional[float] = None, lng: Optional[float] = None) -> dict:
    payload = {
        "id": igreja.id,
        "nome": igreja.nome,
        "endereco": igreja.endereco,
        "cidade": igreja.cidade,
        "estado": igreja.estado,
        "cep": igreja.cep,
        "telefone": igreja.telefone,
        "site": igreja.site,
        "lat": igreja.lat,
        "lng": igreja.lng,
        "observacoes": igreja.observacoes,
        "horarios_missa": igreja.horarios_missa,
        "data_criacao": igreja.data_criacao,
        "favorita": igreja.id in favorita_ids,
        "distancia_km": None,
    }
    if lat is not None and lng is not None and igreja.lat is not None and igreja.lng is not None:
        payload["distancia_km"] = round(_calc_distancia_km(lat, lng, igreja.lat, igreja.lng), 2)
    return payload


@router.get("/igrejas")
def listar_igrejas(
    q: Optional[str] = None,
    lat: Optional[float] = Query(default=None, ge=-90, le=90),
    lng: Optional[float] = Query(default=None, ge=-180, le=180),
    raio_km: Optional[float] = Query(default=None, gt=0, le=10),
    limite: int = Query(default=50, ge=1, le=50),
    usuario: Optional[Usuario] = Depends(obter_usuario_opcional),
    db: Session = Depends(get_db),
):
    """Lista igrejas com filtros opcionais.

    - `q`: substring case-insensitive em nome, endereço ou cidade
    - `lat`+`lng`: ordena por proximidade; `raio_km` opcional para filtrar
    - o catálogo é público; `favorita` só é calculado quando há usuário autenticado
    """
    from math import isfinite

    # Proximidade só é uma afirmação válida com um par completo de coordenadas.
    # Nunca ignoramos silenciosamente metade do par ou um raio sem ponto de origem.
    if (lat is None) != (lng is None):
        raise HTTPException(status_code=422, detail="Informe latitude e longitude juntas.")
    if lat is not None and (
        not isfinite(lat) or not isfinite(lng)
        or not -90 <= lat <= 90 or not -180 <= lng <= 180
    ):
        raise HTTPException(status_code=422, detail="Latitude e longitude devem ser números finitos.")
    if raio_km is not None:
        if lat is None:
            raise HTTPException(status_code=422, detail="Informe latitude e longitude para usar um raio.")
        if raio_km not in (1, 3, 5, 10):
            raise HTTPException(status_code=422, detail="O raio deve ser 1, 3, 5 ou 10 km.")

    IGNORAR = {"de", "da", "do", "das", "dos", "e", "a", "o", "em", "na", "no"}
    tokens = []
    if q:
        for t in _normalizar(q).split():
            if len(t) >= 2 and t not in IGNORAR:
                tokens.append(t)

    # O catálogo é a fonte local atualizada pelo job da Arquidiocese. A busca de
    # visitantes não consulta Google/OSM, evitando custo e resultados instáveis.
    todas = [
        igreja for igreja in db.query(Igreja).all()
        if eh_local_catolico_oficial(igreja)
    ]

    # Score por relevância:
    # +4 token no bairro extraído — quer dizer que a igreja FICA naquele lugar
    # +3 token no nome da igreja (matriz/capela)
    # +2 token na cidade ou nos aliases cadastrados
    # +1 token em qualquer outro lugar do endereço (rua) — match fraco, evita confundir
    #    rua chamada "Estrada da Gávea" com bairro Gávea.
    def _score_nome(i: Igreja) -> int:
        if not tokens:
            return 0
        nome_n = _normalizar(i.nome or "")
        bairro_n = _normalizar(_extrair_bairro(i.endereco))
        cidade_n = _normalizar(i.cidade or "")
        endereco_n = _normalizar(i.endereco or "")
        # `observacoes` é usado também como container de apelidos/aliases
        # (ex.: "Igreja Santa Mônica" tem alias "Colégio Santo Agostinho").
        obs_n = _normalizar(i.observacoes or "")
        score = 0
        for t in tokens:
            if t in bairro_n:
                score += 4
            elif t in nome_n:
                score += 3
            elif t in cidade_n:
                score += 2
            elif t in obs_n:
                score += 2  # apelido é útil, mas não supera o bairro real
            elif t in endereco_n:
                score += 1
        return score

    matches_nome = [(i, _score_nome(i)) for i in todas if _score_nome(i) > 0] if tokens else []

    igrejas: list[Igreja] = []

    if matches_nome:
        # Ordena por relevância do catálogo local; proximidade é aplicada abaixo
        # quando o próprio navegador fornece latitude/longitude.
        # Como score em bairro/cidade (+2) é maior que em rua (+1), igrejas que FICAM no
        # bairro buscado ranqueiam acima de igrejas em rua com nome do bairro mas localizadas
        # em outro bairro (ex.: "Estrada da Gávea, Jardim Botânico").
        matches_nome.sort(key=lambda x: -x[1])

        # Mantém TODAS as igrejas com score alto (≥2 = match bairro/cidade ou nome).
        # Matches de score 1 (só rua) entram após e em quantidade limitada — evita ruído.
        fortes = [i for i, s in matches_nome if s >= 2]
        fracos = [i for i, s in matches_nome if s == 1]
        igrejas = fortes + fracos[:10]

    elif not tokens:
        igrejas = todas

    fav_ids = set()
    if usuario is not None:
        fav_ids = set(
            r[0] for r in db.query(UsuarioIgreja.igreja_id)
            .filter(UsuarioIgreja.usuario_id == usuario.id).all()
        )

    # Mantém a distância bruta para ordenar e limitar. O valor arredondado é
    # exclusivamente de apresentação: 1,004 km não pode entrar no raio de 1 km.
    items_com_distancia: list[tuple[dict, Optional[float]]] = []
    for igreja in igrejas:
        distancia_bruta = None
        if lat is not None and lng is not None and igreja.lat is not None and igreja.lng is not None:
            distancia_bruta = _calc_distancia_km(lat, lng, igreja.lat, igreja.lng)
        items_com_distancia.append((
            _serializar_igreja(igreja, fav_ids, lat, lng),
            distancia_bruta,
        ))

    if lat is not None and lng is not None:
        items_com_distancia.sort(
            key=lambda item: (
                item[1] is None,
                item[1] if item[1] is not None else float("inf"),
                item[0]["id"],
            )
        )
        if raio_km is not None:
            items_com_distancia = [
                item for item in items_com_distancia
                if item[1] is not None and item[1] <= raio_km
            ]

    return [item for item, _ in items_com_distancia[:limite]]


@router.post("/igrejas/localizar-endereco")
def localizar_endereco_igrejas(
    payload: LocalizacaoEnderecoRequest,
    db: Session = Depends(get_db),
):
    """Resolve um endereço informado em coordenadas, sem salvar o texto recebido.

    A chave de Geocoding fica exclusivamente no servidor. O frontend recebe somente
    latitude/longitude e usa o catálogo católico local para a consulta seguinte.
    """
    from math import isfinite

    endereco = payload.endereco.strip()
    if len(endereco) < 5:
        raise HTTPException(status_code=422, detail="Informe um endereço ou bairro mais completo.")

    if not geocoding_configurado():
        raise HTTPException(
            status_code=503,
            detail="O serviço de localização está indisponível no momento. Tente novamente mais tarde.",
        )

    try:
        dentro_da_cota = reservar_consulta(db)
    except ControleGeocodingIndisponivelError:
        raise HTTPException(
            status_code=503,
            detail="O controle de uso da localização está indisponível no momento. Tente novamente mais tarde.",
        )
    if not dentro_da_cota:
        raise HTTPException(
            status_code=429,
            detail="O limite mensal de buscas por endereço foi atingido. Use a sua localização atual ou tente no próximo mês.",
        )

    try:
        ponto = geocodificar_query_google(endereco)
    except GeocodingIndisponivelError:
        raise HTTPException(
            status_code=503,
            detail="O serviço de localização está indisponível no momento. Tente novamente mais tarde.",
        )
    if ponto is None:
        raise HTTPException(status_code=422, detail="Não foi possível localizar este endereço. Confira e tente novamente.")
    lat, lng = ponto
    if not isfinite(lat) or not isfinite(lng) or not -90 <= lat <= 90 or not -180 <= lng <= 180:
        raise HTTPException(status_code=502, detail="O serviço de localização retornou uma coordenada inválida.")
    return {"lat": lat, "lng": lng}


@router.get("/igrejas/minhas")
def listar_minhas_igrejas(
    usuario: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Igreja)
        .join(UsuarioIgreja, UsuarioIgreja.igreja_id == Igreja.id)
        .filter(
            UsuarioIgreja.usuario_id == usuario.id,
            Igreja.arqrio_local_id.isnot(None),
        )
        .order_by(UsuarioIgreja.data_salva.desc())
        .all()
    )
    fav_ids = {i.id for i in rows}
    return [_serializar_igreja(i, fav_ids) for i in rows]


@router.get("/igrejas/{igreja_id}")
def detalhar_igreja(
    igreja_id: int,
    usuario: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    igreja = db.query(Igreja).filter(
        Igreja.id == igreja_id,
        Igreja.arqrio_local_id.isnot(None),
    ).first()
    if not igreja:
        raise HTTPException(status_code=404, detail="Igreja não encontrada")
    fav = db.query(UsuarioIgreja).filter(
        UsuarioIgreja.usuario_id == usuario.id,
        UsuarioIgreja.igreja_id == igreja_id,
    ).first() is not None
    return _serializar_igreja(igreja, {igreja_id} if fav else set())


@router.post("/igrejas/{igreja_id}/favoritar", status_code=200)
def favoritar_igreja(
    igreja_id: int,
    usuario: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    igreja = db.query(Igreja).filter(
        Igreja.id == igreja_id,
        Igreja.arqrio_local_id.isnot(None),
    ).first()
    if not igreja:
        raise HTTPException(status_code=404, detail="Igreja não encontrada")
    existente = db.query(UsuarioIgreja).filter(
        UsuarioIgreja.usuario_id == usuario.id,
        UsuarioIgreja.igreja_id == igreja_id,
    ).first()
    if existente:
        return {"message": "Já favoritada", "favorita": True}
    db.add(UsuarioIgreja(usuario_id=usuario.id, igreja_id=igreja_id))
    db.commit()
    return {"message": "Igreja salva", "favorita": True}


@router.delete("/igrejas/{igreja_id}/favoritar", status_code=200)
def desfavoritar_igreja(
    igreja_id: int,
    usuario: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    db.query(UsuarioIgreja).filter(
        UsuarioIgreja.usuario_id == usuario.id,
        UsuarioIgreja.igreja_id == igreja_id,
    ).delete()
    db.commit()
    return {"message": "Igreja removida", "favorita": False}


# ----- Admin: gerenciar catálogo de igrejas -----

@router.post("/admin/igrejas", response_model=IgrejaResponse, status_code=201)
def criar_igreja(
    dados: IgrejaCreate,
    admin: Usuario = Depends(obter_usuario_admin),
    db: Session = Depends(get_db),
):
    igreja = Igreja(**dados.model_dump())
    db.add(igreja)
    db.commit()
    db.refresh(igreja)
    return _serializar_igreja(igreja, set())


@router.put("/admin/igrejas/{igreja_id}", response_model=IgrejaResponse)
def atualizar_igreja(
    igreja_id: int,
    dados: IgrejaUpdate,
    admin: Usuario = Depends(obter_usuario_admin),
    db: Session = Depends(get_db),
):
    igreja = db.query(Igreja).filter(Igreja.id == igreja_id).first()
    if not igreja:
        raise HTTPException(status_code=404, detail="Igreja não encontrada")
    for k, v in dados.model_dump(exclude_unset=True).items():
        setattr(igreja, k, v)
    db.commit()
    db.refresh(igreja)
    return _serializar_igreja(igreja, set())


@router.delete("/admin/igrejas/{igreja_id}", status_code=204)
def deletar_igreja(
    igreja_id: int,
    admin: Usuario = Depends(obter_usuario_admin),
    db: Session = Depends(get_db),
):
    igreja = db.query(Igreja).filter(Igreja.id == igreja_id).first()
    if not igreja:
        raise HTTPException(status_code=404, detail="Igreja não encontrada")
    db.delete(igreja)
    db.commit()


@router.post("/admin/igrejas/limpar")
def limpar_catalogo_igrejas(
    admin: Usuario = Depends(obter_usuario_admin),
    db: Session = Depends(get_db),
):
    """Dedupe + enrich do catálogo existente.

    - Agrupa por raiz de nome + proximidade (≤200m); mantém a mais completa (endereço preenchido > vazio,
      depois id mais baixo), reaponta favoritos e deleta as outras.
    - Para sobreviventes sem endereço, faz reverse geocode (Nominatim).
    """
    from app.services.geocoding import reverse_geocode

    todas = db.query(Igreja).all()
    # Agrupa por raiz + bucket grosso de coords (~1km) só pra reduzir comparações
    grupos: list[list[Igreja]] = []
    for i in todas:
        achou = False
        for g in grupos:
            if _eh_mesma_igreja(g[0], i.nome, i.lat, i.lng):
                g.append(i)
                achou = True
                break
        if not achou:
            grupos.append([i])

    duplicatas_removidas = 0
    enderecos_enriquecidos = 0
    favoritos_remapeados = 0

    for g in grupos:
        if len(g) > 1:
            # Escolhe a "melhor": com endereço preenchido > sem endereço; em empate, menor id.
            def _peso(x: Igreja) -> tuple[int, int]:
                tem_endereco = 1 if (x.endereco and x.endereco.strip()) else 0
                return (-tem_endereco, x.id)
            g_sorted = sorted(g, key=_peso)
            mestre = g_sorted[0]
            for outra in g_sorted[1:]:
                # Repointa favoritos: usuários que tinham a duplicata viram favoritos da mestre
                favs = db.query(UsuarioIgreja).filter(UsuarioIgreja.igreja_id == outra.id).all()
                for f in favs:
                    ja_tem = db.query(UsuarioIgreja).filter(
                        UsuarioIgreja.usuario_id == f.usuario_id,
                        UsuarioIgreja.igreja_id == mestre.id,
                    ).first()
                    if ja_tem:
                        db.delete(f)
                    else:
                        f.igreja_id = mestre.id
                    favoritos_remapeados += 1
                db.delete(outra)
                duplicatas_removidas += 1

    db.commit()

    # Enrich endereços vazios das sobreviventes
    sobreviventes = db.query(Igreja).filter(
        ((Igreja.endereco.is_(None)) | (Igreja.endereco == "")),
        Igreja.lat.isnot(None),
        Igreja.lng.isnot(None),
    ).all()
    for i in sobreviventes:
        rev = reverse_geocode(i.lat, i.lng)
        if rev and rev.get("endereco"):
            i.endereco = rev["endereco"]
            if not i.cidade and rev.get("cidade"):
                i.cidade = rev["cidade"]
            if not i.estado and rev.get("estado"):
                i.estado = rev["estado"]
            if not i.cep and rev.get("cep"):
                i.cep = rev["cep"]
            enderecos_enriquecidos += 1
    db.commit()

    return {
        "duplicatas_removidas": duplicatas_removidas,
        "favoritos_remapeados": favoritos_remapeados,
        "enderecos_enriquecidos": enderecos_enriquecidos,
        "total_apos_limpeza": db.query(Igreja).count(),
    }
