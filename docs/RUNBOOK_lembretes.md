# Runbook — conserto dos lembretes duplicados (local → produção)

## O que mudou (3 arquivos)
1. `backend/app/models/usuario.py` — índice único PARCIAL `uq_lembrete_nao_acompanhada`
   em `(usuario_id, missa_id)` só para `tipo='nao_acompanhada'`.
2. `backend/app/services/notif_nao_acompanhou.py` — idempotência por
   `(usuario, missa, tipo)` (não mais por título) + savepoint que ignora corrida.
3. `backend/scripts/fix_lembretes_duplicados.py` — apaga duplicatas existentes e
   cria o índice. Idempotente; tem `--dry-run`.

Testado offline: dedupe remove só as duplicatas de `nao_acompanhada`, preserva
lembretes do usuário/broadcast, e o índice bloqueia novas duplicatas.

---

## Parte A — LOCAL (validar antes de produção)
Rode a partir de `backend/`, com o ambiente do projeto ativo:

```bash
cd backend
python3 scripts/fix_lembretes_duplicados.py --dry-run   # mostra quantas apagaria
python3 scripts/fix_lembretes_duplicados.py             # aplica no banco LOCAL
pytest                                                   # confirma que nada quebrou
```

(Se quiser, suba o servidor `uvicorn app.main:app --reload` e veja a tela de
Lembretes sem duplicatas.)

Depois, salve no git:
```bash
git add backend/app/models/usuario.py backend/app/services/notif_nao_acompanhou.py backend/scripts/fix_lembretes_duplicados.py
git commit -m "fix(lembretes): impede e remove notificacoes 'nao acompanhou' duplicadas"
```

---

## Parte B — PRODUÇÃO (servidor via SSH)
> ⚠️ Mexe no banco real. **Backup primeiro.**

1. **Backup do banco** (Postgres):
   ```bash
   pg_dump "$DATABASE_URL" > ~/backup_diademissa_$(date +%F_%H%M).sql
   ```
2. **Levar o código novo** ao servidor (do jeito que você já faz hoje — `git pull`
   no servidor, ou rsync/scp da pasta `backend/`).
3. **Rodar a migração** no servidor, a partir de `backend/`:
   ```bash
   python3 scripts/fix_lembretes_duplicados.py --dry-run   # confere o número
   python3 scripts/fix_lembretes_duplicados.py             # aplica
   ```
4. **Reiniciar o serviço** do backend (systemd/pm2/docker — o que você usa).
   Ex.: `sudo systemctl restart diademissa` (ajuste ao nome real).
5. **Conferir** no app: a tela de Lembretes não deve ter mais itens repetidos, e
   o índice impede que voltem.

Se algo der errado, restaure o backup:
```bash
psql "$DATABASE_URL" < ~/backup_diademissa_AAAA-MM-DD_HHMM.sql
```

---

## Texto pronto para o Claude Code (cole no Claude Code, na pasta do projeto)

> Apliquei manualmente 3 mudanças (modelo `Lembrete` com índice único parcial
> `uq_lembrete_nao_acompanhada`, job `notif_nao_acompanhou` idempotente por
> (usuario,missa,tipo), e o script `backend/scripts/fix_lembretes_duplicados.py`).
> Por favor:
> 1. Rode `cd backend && python3 scripts/fix_lembretes_duplicados.py --dry-run` e me mostre o resultado.
> 2. Se fizer sentido, rode sem `--dry-run` no banco local.
> 3. Rode `pytest` e conserte qualquer teste que quebrar por causa do índice novo.
> 4. Faça o commit das 3 mudanças.
> 5. Me diga exatamente como fazer o deploy por SSH (descubra host/serviço pelos
>    arquivos do projeto, ex.: reports/github-push.md, e me dê os comandos), mas
>    NÃO rode nada em produção sem eu confirmar e sem backup do banco antes.
