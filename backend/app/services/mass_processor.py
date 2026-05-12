import re
from datetime import date, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.missa import Missa, BlocoLiturgico
from app.services.pdf_downloader import baixar_pdf, calcular_hash, pdf_foi_alterado, salvar_pdf
from app.services.pdf_parser import extrair_texto
from app.services.liturgical_parser import segmentar_blocos, extrair_referencia
from app.services.block_classifier import classificar_bloco, reordenar_blocos
from app.core.config import settings


def processar_missa(db: Session, data: Optional[date] = None) -> Missa:
    if data is None:
        data = date.today()

    missa_existente = db.query(Missa).filter(Missa.data == data).first()

    conteudo_pdf = baixar_pdf()
    hash_pdf = calcular_hash(conteudo_pdf)

    if missa_existente and not pdf_foi_alterado(hash_pdf, missa_existente.pdf_hash):
        return missa_existente

    salvar_pdf(conteudo_pdf, data.isoformat())

    linhas = extrair_texto(conteudo_pdf)
    blocos_extraidos = segmentar_blocos(linhas)

    # Enriquecer blocos com conteúdo formatado (bold/italic)
    # Mapeia texto plano → texto formatado para cada linha extraída
    fmt_map: dict[str, str] = {}
    for l in linhas:
        plain = l.texto.strip()
        fmt = l.texto_formatado.strip()
        if plain != fmt:
            fmt_map[plain] = fmt

    for bloco in blocos_extraidos:
        linhas_fmt: list[str] = []
        for linha_plain in bloco.linhas_raw:
            stripped = linha_plain.strip()
            if stripped in fmt_map:
                linhas_fmt.append(fmt_map[stripped])
            else:
                linhas_fmt.append(stripped)
        bloco.linhas_formatadas = linhas_fmt

    blocos_classificados = []
    for bloco in blocos_extraidos:
        tipo = classificar_bloco(bloco)
        blocos_classificados.append((bloco, tipo))

    blocos_ordenados = reordenar_blocos(blocos_classificados)

    celebracao = _extrair_celebracao(linhas)
    tempo_liturgico = _extrair_tempo_liturgico(linhas)

    subtitulo = _extrair_subtitulo(linhas)
    descricao = _extrair_descricao(linhas)

    if missa_existente:
        missa = missa_existente
        missa.pdf_hash = hash_pdf
        missa.status_processamento = "concluido"
        missa.celebracao = celebracao
        missa.subtitulo = subtitulo
        missa.descricao = descricao
        missa.tempo_liturgico = tempo_liturgico
        db.query(BlocoLiturgico).filter(BlocoLiturgico.missa_id == missa.id).delete()
    else:
        missa = Missa(
            data=data,
            celebracao=celebracao,
            subtitulo=subtitulo,
            descricao=descricao,
            tempo_liturgico=tempo_liturgico,
            fonte_pdf_url=settings.PDF_URL,
            pdf_hash=hash_pdf,
            status_processamento="concluido",
        )
        db.add(missa)
        db.flush()

    for bloco_obj, tipo, ordem in blocos_ordenados:
        if not bloco_obj.titulo:
            titulo = tipo.replace("_", " ").title()
        else:
            titulo = bloco_obj.titulo

        bloco_db = BlocoLiturgico(
            missa_id=missa.id,
            ordem=ordem,
            tipo=tipo,
            titulo=titulo,
            referencia=extrair_referencia(bloco_obj.titulo or ""),
            conteudo=bloco_obj.conteudo if bloco_obj.conteudo else None,
            conteudo_formatado=bloco_obj.conteudo_formatado if bloco_obj.conteudo_formatado else None,
            visivel=True,
        )
        if tipo == "desconhecido":
            bloco_db.observacoes = "Bloco não classificado automaticamente"
        db.add(bloco_db)

    db.commit()
    db.refresh(missa)
    return missa


def _extrair_celebracao(linhas: list) -> Optional[str]:
    # Procura por padrão de celebração nas primeiras 40 linhas
    for linha_obj in linhas[:40]:
        t = linha_obj.texto.strip()
        if not t or len(t) > 80:
            continue
        # Padrão: "Nº Domingo/Tempo/Solenidade/Festa de..."
        padrao = re.compile(
            r"^\d+[º°]\s*(?:DOMINGO|SÁBADO|SEGUNDA|TERÇA|QUARTA|QUINTA|SEXTA)\s+(?:FEIRA\s+)?(?:DA|DO|DE)\s+.+",
            re.IGNORECASE,
        )
        if padrao.match(t):
            return t
        # Dia de semana + celebração: "Domingo da Páscoa", "Domingo de Ramos" etc.
        t_up_stripped = t.upper().lstrip()
        for dia in ["DOMINGO", "SÁBADO", "SEGUNDA", "TERÇA", "QUARTA", "QUINTA", "SEXTA"]:
            if t_up_stripped.startswith(dia) and len(t) > 8 and len(t) < 80:
                # Verifica se NÃO é uma frase (não tem vírgula após o dia)
                pos = len(dia)
                resto = t_up_stripped[pos:].lstrip()
                if not resto.startswith(","):
                    return t
    # Fallback: pegar linhas que são nomes de celebração (ex: "Ascensão do Senhor")
    # Geralmente estão nas primeiras 10 linhas, são curtas e têm mais de 3 palavras
    for linha_obj in linhas[:15]:
        t = linha_obj.texto.strip()
        if not t:
            continue
        t_upper = t.upper()
        # Ignorar linhas que começam com números, versão, folheto, etc.
        if re.match(r'^[\d\s\-–—]+$', t_upper):
            continue
        if any(p in t_upper for p in ['VERSÃO', 'FOLHETO', 'ANO', 'ANNO', 'PRODUÇÃO', 'VICARIATO', 'EDITORA', 'PORTAL', 'RUA']):
            continue
        # Nome de celebração típico: 2-8 palavras, começa com maiúscula
        palavras = t.split()
        if 2 <= len(palavras) <= 8 and t[0].isupper() and not t_upper.startswith('NESTE'):
            return t
    return None


def _extrair_subtitulo(linhas: list) -> Optional[str]:
    """Extrai o subtítulo: linhas entre o título e a primeira seção."""
    partes = []
    for linha_obj in linhas[5:10]:
        t = linha_obj.texto.strip()
        t_upper = t.upper()
        if not t or t == '-':
            continue
        if any(p in t_upper for p in ['VERSÃO', 'FOLHETO', 'ANNO', 'PRODUÇÃO', 'VICARIATO', 'EDITORA', 'PRODU', 'VICAR', 'RUA', 'PUBLIC', 'PORTAL', 'ASCENSÃO', 'SOLENIDADE', 'COMUNICAÇÕES', 'VERSÃO']):
            if t_upper.startswith('ASCENSÃO'):
                continue
            if t_upper.startswith('SOLENIDADE') and not partes:
                continue
            if t_upper.startswith('PRODUÇÃO') or t_upper.startswith('VICARIATO') or t_upper.startswith('EDITORA'):
                continue
        if 'AA NNOO' in t_upper or re.match(r'^AA\s+NNOO', t_upper):
            continue
        partes.append(t)
    return ' | '.join(partes) if partes else None


def _extrair_descricao(linhas: list) -> Optional[str]:
    """Extrai o parágrafo de descrição entre o cabeçalho e a primeira seção."""
    desc_lines = []
    capturando = False
    pular = {'Solenidade', '-', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.',
             'Versão Celular', 'Folheto Oficial da Arquidiocese do Rio de Janeiro',
             'Ritos Iniciais', 'Liturgia da Palavra', 'Liturgia Eucarística', 'Ritos Finais'}
    for linha_obj in linhas[13:33]:
        t = linha_obj.texto.strip()
        if not t or t in pular:
            continue
        if t.startswith('Ascensão') or t.startswith('Solenidade'):
            continue
        if 'Ritos Iniciais' in t or 'Liturgia' in t:
            break
        if not capturando:
            if t == 'N' or (t.startswith('N') and 'Domingo' in t) or ('Domingo' in t and len(t) > 10):
                capturando = True
                desc_lines.append(t)
                continue
            if not desc_lines and t.startswith('N'):
                capturando = True
                desc_lines.append(t)
                continue
            continue
        desc_lines.append(t)
    if not desc_lines:
        return None
    # Para antes de "1." ou "Canto de Entrada"
    corte = len(desc_lines)
    for idx, line in enumerate(desc_lines):
        if line.strip().startswith(('1.', 'Canto', 'REFRÃO', '(De')):
            corte = idx
            break
    desc_lines = desc_lines[:corte]
    if not desc_lines:
        return None
    texto = ' '.join(desc_lines)
    texto = texto.replace('- ', '').replace(' -', '')
    texto = texto.replace('-', '').replace('  ', ' ').strip()
    if texto.startswith('N ') and not texto.startswith('Ne'):
        texto = 'N' + texto[1:]
    texto = texto.replace('N este', 'Neste')
    return texto


def _extrair_tempo_liturgico(linhas: list) -> Optional[str]:
    tempos = ["ADVENTO", "NATAL", "QUARESMA", "PÁSCOA", "PASCOA", "COMUM", "TEMPO COMUM"]
    for linha_obj in linhas[:50]:
        for tempo in tempos:
            if tempo in linha_obj.texto.upper():
                return tempo.capitalize()
    return None
