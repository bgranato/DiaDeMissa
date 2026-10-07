"""E-mails de falha da montagem: assunto e corpo HONESTOS.

Regressão 11/10: o `_alerta` de publicação_convergente reutilizava o template do
verificador léxico — o e-mail de uma falha de montagem saía como
"[Dia de Missa] Verificação léxica — ... (suspeita de typo)" com a mensagem de
erro no lugar de "palavra", confundindo quem recebia.
"""
from __future__ import annotations

import pytest

from app.services import publicacao_convergente, verificador_lexical


class _FakeAdmin:
    def __init__(self, email: str) -> None:
        self.email = email


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, rows):
        self._rows = rows

    def query(self, *_args, **_kwargs):
        return _FakeQuery(self._rows)

    def close(self) -> None:
        pass


def _capturar_envio(monkeypatch, emails=("admin@x.com",)):
    """Intercepta SessionLocal e enviar_email; devolve lista de (dest, assunto, html)."""
    from app.core import database
    from app.services import email_sender

    enviados: list[tuple] = []
    monkeypatch.setattr(database, "SessionLocal",
                        lambda: _FakeDB([_FakeAdmin(e) for e in emails]))
    monkeypatch.setattr(
        email_sender, "enviar_email",
        lambda dest, assunto, corpo_html, corpo_texto=None:
            (enviados.append((dest, assunto, corpo_html)) or True),
    )
    return enviados


def test_alerta_conferencia_assunto_e_corpo_honestos(monkeypatch):
    enviados = _capturar_envio(monkeypatch)
    verificador_lexical.enviar_alerta_conferencia(
        "2026-10-11", "Montagem multimodal falhou: Extra data. Retry agendado.")

    assert len(enviados) == 1
    _dest, assunto, corpo = enviados[0]
    assert "2026-10-11" in assunto
    assert "montagem" in assunto.lower()
    # O defeito regressado: o e-mail de falha NÃO pode virar "verificação léxica".
    assert "léxico" not in assunto.lower() and "lexico" not in assunto.lower()
    assert "suspeita de typo" not in corpo.lower()
    assert "Montagem multimodal falhou: Extra data." in corpo


def test_alerta_conferencia_escapa_html_no_motivo(monkeypatch):
    enviados = _capturar_envio(monkeypatch)
    verificador_lexical.enviar_alerta_conferencia(
        "2026-10-11", 'divergência em <script>alert(1)</script>')

    _dest, _assunto, corpo = enviados[0]
    assert "<script>" not in corpo
    assert "&lt;script&gt;" in corpo


def test_alerta_conferencia_sem_admins_nao_envia(monkeypatch):
    enviados = _capturar_envio(monkeypatch, emails=())
    verificador_lexical.enviar_alerta_conferencia("2026-10-11", "x")
    assert enviados == []


def test__alerta_encaminha_para_alerta_conferencia_e_nao_o_lexico(monkeypatch):
    """O `_alerta` (3 call sites: erro_montagem, reprovada_mantida,
    pendente_revisao) deve usar o template de falha — nunca o do léxico."""
    chamadas: list[tuple] = []
    monkeypatch.setattr(
        verificador_lexical, "enviar_alerta_conferencia",
        lambda data, msg: chamadas.append((data, msg)),
    )
    monkeypatch.setattr(
        verificador_lexical, "enviar_alerta_lexical",
        lambda *_a, **_k: pytest.fail("não pode usar o template do verificador léxico"),
    )

    publicacao_convergente._alerta("2026-10-11", "Montagem multimodal falhou: X.")

    assert chamadas == [("2026-10-11", "Montagem multimodal falhou: X.")]


def test__alerta_nao_propaga_excecao_do_envio(monkeypatch):
    """Best-effort: falha de e-mail não pode derrubar o fluxo de publicação."""
    def _explode(*_a, **_k):
        raise RuntimeError("SMTP fora do ar")

    monkeypatch.setattr(verificador_lexical, "enviar_alerta_conferencia", _explode)
    publicacao_convergente._alerta("2026-10-11", "mensagem")  # não deve levantar
