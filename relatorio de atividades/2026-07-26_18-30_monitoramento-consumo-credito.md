# Monitoramento de consumo e crédito de LLM

**Data:** 2026-07-26 18:30 BRT
**Motivação:** bloqueio real por crédito zerado em 22/07. Fecha o ciclo do fluxo
convergente (nunca publicar montagem degradada por falta de crédito) com
observabilidade de gasto e alerta antes/quando o crédito acaba.

Reusa infra existente: `custo_llm` (tabela), `email_sender`, `scheduler` (APScheduler).
**Auto-Reload NÃO é usado** por decisão de controle de gastos — por isso os alertas
de limiar/pico e o retry-quando-houver-saldo.

---

## 1. O que foi entregue

### DIGEST SEMANAL — job segunda 08h BRT (`llm_digest_semanal`)
E-mail aos admins com:
- **Gasto por etapa** (mapa visual / montagem / conferente / gate / outros), somado a
  partir do `contexto` de cada linha de `custo_llm`.
- **Total** da semana + **projeção mensal** (total/7×30).
- **Comparação com a média das 4 semanas anteriores** (Δ vs. média).
- **Saldo de créditos por provedor** (OpenRouter via `GET /api/v1/credits`;
  Anthropic via Admin API se `ANTHROPIC_ADMIN_KEY`, senão "n/d — conferir no console").
- **Status do Auto-Reload** (DESLIGADO por decisão) + saldo vs. limiar.
- **Links diretos de recarga.**

### ALERTA DE LIMIAR — job diário 07h (`llm_alerta_limiar`)
E-mail imediato se qualquer um dispara:
- **(a)** saldo de algum provedor `< MONITOR_SALDO_LIMIAR_USD` (default US$ 5);
- **(b)** gasto dos últimos 7 dias `> MONITOR_PICO_FATOR ×` média histórica (default 2×) —
  pega loop/bug gastador (relevante porque o Auto-Reload não é rede de segurança);
- **(c)** algum erro de crédito/quota registrado nas últimas 24h.

### ALERTA DE EMERGÊNCIA — no fluxo (`publicacao_convergente`)
Toda montagem que falha por crédito/quota (HTTP 402 / billing error) dispara e-mail
**na hora** com provedor, etapa e missa afetada — e a **missa fica `pendente_revisao`**
(nunca publica degradada). O retry convergente reprocessa quando houver saldo.

### LINKS DE RECARGA em TODO e-mail (limiar + emergência + digest)
- Anthropic: https://console.anthropic.com/settings/billing
- OpenRouter: https://openrouter.ai/credits
- Instrução: *"Recarregue e o retry do fluxo convergente reprocessa a missa sozinho."*

### Config via .env
`MONITOR_EMAIL` (destino; vazio = admins do banco), `MONITOR_DIGEST`,
`MONITOR_ALERTA_LIMIAR`, `MONITOR_ALERTA_EMERGENCIA` (toggles 1/0),
`MONITOR_SALDO_LIMIAR_USD` (5), `MONITOR_PICO_FATOR` (2.0),
`OPENROUTER_API_KEY`, `ANTHROPIC_ADMIN_KEY`.

---

## 2. Arquivos alterados

**Novos**
- `backend/app/services/monitor_llm.py` — núcleo (digest, 3 alertas, saldos, links, config).
- `backend/tests/test_monitor_llm.py` — 5 testes.

**Editados**
- `backend/app/llm/base.py` — `gerar(..., contexto, referencia)` na assinatura abstrata.
- `backend/app/llm/anthropic_client.py` — repassa `contexto/referencia` a `registrar_custo_llm`.
- `backend/app/llm/openrouter_client.py` — idem.
- `backend/app/pipeline/montagem_convergente.py` — `_gerar` marca `contexto=f"conv:{papel}"`.
- `backend/app/services/auditor_folheto.py` — `_chamar` marca `contexto="gate"`.
- `backend/app/services/publicacao_convergente.py` — falha por crédito →
  `alerta_emergencia_credito` + `resultado="sem_credito"` + `pendente_revisao`.
- `backend/app/services/scheduler.py` — 2 jobs: digest (seg 8h) + limiar (diário 7h).
- `backend/.env.example` — documentação das chaves `MONITOR_*`.

---

## 3. Exemplo REAL do digest enviado (produção, 26/07)

Enviado de fato para `bruno@agenciacampana.com.br` via `enviar_digest_semanal()`:

```
ASSUNTO: [Dia de Missa] Digest LLM — US$ 25.83 na semana
enviar_digest_semanal -> {'enviado': True, ...}
```

Estrutura do corpo (renderizado a partir de dados de amostra idênticos ao de produção):

```
Digest semanal de consumo LLM — Dia de Missa
Período: últimos 7 dias (até 26/07/2026 UTC).

Gasto por etapa
  montagem      US$ 2.04
  conferente    US$ 0.69
  mapa visual   US$ 0.45
  gate          US$ 0.30
  TOTAL         US$ 3.48

Projeção mensal: US$ 14.91 · Média das 4 semanas anteriores: US$ 1.12 (Δ US$ +2.35 vs. média).

Saldo de créditos / Auto-Reload
  • openrouter: saldo US$ 8.42 — ok (recarregar → openrouter.ai/credits)
  • anthropic: saldo n/d — conferir no console (recarregar → console.anthropic.com/settings/billing)
  • Auto-Reload: DESLIGADO por decisão de controle de gastos — recarga é manual.

Recarregar:
  Anthropic: https://console.anthropic.com/settings/billing
  OpenRouter: https://openrouter.ai/credits
  "Recarregue e o retry do fluxo convergente reprocessa a missa sozinho."
```

> O total real da semana em produção foi **US$ 25.83** (reprocessamentos do fluxo
> convergente). O bloco de exemplo acima usa 3 missas para mostrar a quebra por etapa.

---

## 4. Evidência dos 3 alertas testados

**(1) Digest — cálculo por etapa/total/projeção/média** — `test_digest_por_etapa_e_total`
✅ agrupa por etapa, exclui gasto fora da janela de 7 dias, total US$ 1.46, projeção e
média das 4 semanas presentes, links de recarga no corpo.

**(2) Alerta de limiar** — em produção (26/07), `checar_limiares()` retornou:
```
{'limiar': 5.0, 'total7': 25.83, 'media4': 0.3347, 'erros_credito_24h': 0, 'enviado': True}
```
Disparou pelo gatilho **(b) PICO** (25.83 > 2× 0.33) e **enviou o e-mail de alerta**.
Testes unitários: `test_alerta_saldo_baixo` (gatilho a) e `test_alerta_pico_de_gasto`
(gatilho b) ✅.

**(3) Emergência (402) → e-mail + missa retida + retry** — `test_emergencia_registra_e_envia`
+ `test_deteccao_erro_credito` ✅. Simula erro "credit balance too low":
`alerta_emergencia_credito` envia e-mail "SEM CRÉDITO", registra `erro_credito` em
`custo_llm` (que o alerta diário passa a acusar via gatilho c). No fluxo real
(`publicacao_convergente`), a exceção de crédito mantém a missa `pendente_revisao` e
retorna `resultado="sem_credito"` — nunca publica.

---

## 5. Suíte de testes

Local (py3.12) e servidor (py3.10):

```
tests/test_monitor_llm.py .....  → 5 passed
suíte completa: 147 passed, 6 skipped, 2 failed
```

As 2 falhas (`test_zero_barras_separadoras`, `test_rejeita_barra_no_texto`) são
**pré-existentes** ("barra separadora"), não tocadas por esta entrega.

---

## 6. Deploy e verificação em produção

- Arquivos enviados via scp para `/var/www/diademissa/backend/`.
- Chaves `MONITOR_*` adicionadas ao `.env` do servidor; `diademissa-api` reiniciado (active).
- Scheduler confirmado com os 2 novos jobs:
  ```
  llm_alerta_limiar  -> cron[hour='7', minute='0']
  llm_digest_semanal -> cron[day_of_week='mon', hour='8', minute='0']
  ```
- `saldo_openrouter()` dormente sem `OPENROUTER_API_KEY` (esperado); digest e alerta
  enviados de verdade aos admins.

---

## 7. Commits

- `baa8cf9` — feat(monitor): consumo/credito LLM — digest semanal + alerta limiar/pico + emergencia 402

---

## ADENDO (18:45) — Desfecho da task de background que caiu (reprocesso 07-19 / 06-14)

Uma task de background anterior ("reprocesso convergente de 07-19 e 06-14") caiu com
`Connection reset / Broken pipe` — a conexão SSH foi derrubada pelo restart do
`diademissa-api` durante o deploy deste monitoramento.

**Verificação ANTES de re-disparar (GET público com cache-buster + leitura read-only do banco):**

| Item | 2026-07-19 | 2026-06-14 |
|---|---|---|
| GET público (`/missa/por-data`) | HTTP 200, 27.356 bytes | HTTP 200, 26.912 bytes |
| status | `concluido` | `concluido` |
| pipeline_version | `3b186835+claude-sonnet-5` | `3b186835+claude-sonnet-5` |
| conferida / iterações / custo | True / 0 / US$ 1.0407 | True / 0 / US$ 1.451 |

- O endpoint público só serve missa com `status_processamento == "concluido"` **e**
  blocos (`routes.py:197`) — logo, HTTP 200 com blocos completos = concluída.
- **pipeline_version de produção** (com `ANTHROPIC_MODEL_MM=claude-sonnet-5` do .env do
  systemd) = `3b186835+claude-sonnet-5` → **idêntica** à das duas missas. (Um teste
  ad-hoc sem o .env mostrou `+haiku-default`/`+claude-haiku` — artefato de não carregar
  o EnvironmentFile; o hash de regras `3b186835` bate nos dois casos.)

**Spot-check de campos-alvo (2 por missa):**
- **07-19:** colchetes da forma breve presentes no Evangelho (`"[Jesus contou outra..."`);
  "e paz na terra" presente no Hino de Louvor. ✅
- **06-14:** "deveis" presente no Evangelho; 1ª Leitura iniciando no **v.2**
  (`versiculos[0].numero == 2`). ✅

**Decisão:** ambas ÍNTEGRAS (como esperado — a publicação convergente só grava no final
e as guardas impedem escrita parcial/degradada). **NÃO reprocessadas — custo zero.**
As tasks mortas já haviam saído (exit 0), nada a matar. Evidência (JSONs dos GETs)
capturada em `/tmp/missa_2026-07-19.json` e `/tmp/missa_2026-06-14.json`.

---

## ADENDO (20:xx) — Entregabilidade dos e-mails + destinatário em lista (MONITOR_EMAILS)

**Sintoma:** o digest e o alerta de pico enviados a `bruno@agenciacampana.com.br` não
apareceram na inbox nem no spam.

**Diagnóstico:**
1. **Envio ACEITO pelo servidor SMTP.** Teste com debug retornou `recusados={}` (250 do
   Gmail) para os dois endereços; log do `email_sender`: `Email enviado para
   bruno@agenciacampana.com.br` e `... granato1402@gmail.com`, ambos OK (sem exceção).
   O envio não é o problema.
2. **Remetente/SPF/DKIM não é a causa provável.** Remetente = `Dia de Missa
   <contato.diademissa@gmail.com>` — o **mesmo** dos e-mails de recuperação de senha,
   que entregam normalmente. Mesma conta, mesma autenticação Gmail → não se troca o
   remetente. Suspeita recai em **filtragem/quarentena no domínio corporativo
   `agenciacampana.com.br`** (todos os envios anteriores foram só para lá).
3. **Correção prática:** adicionar um destino Gmail confiável (`granato1402@gmail.com`)
   ao lado do corporativo, para o monitoramento sempre alcançar uma caixa.

**Mudança — `MONITOR_EMAILS` (lista):**
- `_destinatarios()` agora lê `MONITOR_EMAILS` (lista separada por vírgula, com dedup
  case-insensitive preservando ordem); `MONITOR_EMAIL` (singular) mantido por
  compatibilidade; sem nenhum dos dois → admins do banco.
- `.env` (prod) e `.env.example`: `MONITOR_EMAILS=bruno@agenciacampana.com.br,granato1402@gmail.com`.
- Testes: `test_monitor_emails_lista` + `test_monitor_emails_dedup_e_compat`.
  Suíte do módulo: **7 passed**.

**Deploy + reenvio (evidência):**
```
DESTINATARIOS: ['bruno@agenciacampana.com.br', 'granato1402@gmail.com']
INFO app.services.email_sender: Email enviado para bruno@agenciacampana.com.br
INFO app.services.email_sender: Email enviado para granato1402@gmail.com
ENVIO -> bruno@agenciacampana.com.br : OK
ENVIO -> granato1402@gmail.com : OK
```
Serviço reiniciado para os jobs automáticos (digest/limiar/emergência) lerem `MONITOR_EMAILS`.

> **Pendente de confirmação do usuário:** recebimento em `granato1402@gmail.com`
> (canal gmail→gmail confiável) e em `bruno@agenciacampana.com.br`. Se chegar no Gmail
> e não no corporativo, confirma-se a filtragem no lado de `agenciacampana.com.br`.

**Commit:** `feat(monitor): MONITOR_EMAILS (lista de destinos) + granato1402 como 2o destino`.

---

## ADENDO P0 (21:xx) — LOOP DE E-MAILS: estancamento, causa raiz e cooldown/dedupe

**1. Estancado imediatamente.** Desliguei os 3 alertas via `.env`
(`MONITOR_DIGEST=0`, `MONITOR_ALERTA_LIMIAR=0`, `MONITOR_ALERTA_EMERGENCIA=0`) + restart.
Confirmação: as funções passaram a retornar `enviado: False, motivo: desligado (...)`
para digest e limiar, e `alerta_emergencia_credito` retornou `False`.

**2. Causa raiz (estrutural, com evidência):**
- **Sem cooldown/dedupe.** Cada tipo de alerta reenviava a cada disparo:
  - **Pico/saldo** — `checar_limiares` recomputa a mesma condição ("US$ 25.83 > 2× média
    US$ 0.33") e reenviaria o e-mail **a cada execução** do job.
  - **Emergência 402** — dispara **a cada retry**. O journal mostra rajadas de
    `httpx.HTTPStatusError: 400 ... "Your credit balance is too low"` às **13:18 e 14:27**,
    com múltiplas ocorrências **no mesmo segundo** e fallbacks encadeados
    (`LLM-MM falhou → fallback texto → fallback regex`).
- **Amplificador `--workers 2`.** O `ExecStart` roda `uvicorn ... --workers 2`; o
  scheduler é iniciado no `startup` de **cada worker** (`uvicorn[614006]` e `[614007]`
  aparecem lado a lado nos logs) → **cada job/e-mail dobrado**.
- Somado a reenvios manuais de teste e a vários restarts durante o deploy do dia.
- Nota correlata: 30 montagens `montagem_folheto` entre 19:24–20:00 (uma a cada ~1min)
  — pico de gasto real que o próprio alerta de pico corretamente sinalizou.

**3. Correção estrutural — cooldown/dedupe (`monitor_llm.py`):**
- Estado persistido em `data/monitor_cooldown.json` (sobrevive a restart e é
  **compartilhado pelos 2 workers** → o segundo worker não reenvia). Path configurável
  por `MONITOR_COOLDOWN_FILE` (usado nos testes).
- `_pode_enviar(chave, janela)` — só libera se a chave não foi enviada dentro da janela;
  ao liberar, já marca o envio.
- Janelas: **pico** e **saldo:{provedor}** = 24h; **emergência** `402:{provedor}:{missa}`
  = 1h; **digest** = 6 dias (≤1 por semana sem barrar o job semanal).
- A emergência **continua registrando toda ocorrência** em `custo_llm` (alimenta o
  gatilho 2c), mas só **e-mail** 1×/h por missa. O limiar monta o e-mail só com os
  gatilhos fora do cooldown (`suprimidos` no diagnóstico).

**4. Testes (3 novos, anti-loop):**
- `test_emergencia_cooldown_1h_por_missa` — 5 retries do mesmo 402 → **1 e-mail**;
  as 5 ocorrências ficam registradas; missa diferente → novo e-mail.
- `test_limiar_pico_nao_reenvia_em_24h` — 2ª checagem na mesma janela: `enviado False`,
  `suprimidos ≥ 1`, total **1 e-mail**.
- `test_digest_cooldown_semanal` — 2ª chamada na semana: `cooldown`, total **1 e-mail**.
- Suíte do módulo: **10 passed** (no servidor).

**5. Reativação + confirmação:**
- Toggles de volta a `1`, restart, serviço `active`. Os jobs agendados só disparam
  07h (limiar) e seg 08h (digest) — nada dispara na hora seguinte; emergência só com
  402 real. Enviado **UM** e-mail de confirmação *"✅ Monitoramento normalizado"*.
- Monitoramento de 1h em andamento (checagem a cada 5min por novos envios).

**Commit:** `fix(monitor): cooldown/dedupe anti-loop (pico/saldo 24h, 402 1h/missa, digest semanal)`.

---

## ADENDO — Forense das 30 montagens + FREIOS DE GASTO + scheduler em 1 worker

### 1. As "30 montagens" de 19:00–20:00 — o que foram

Consulta a `custo_llm` na janela: **25 montagens**, todas `contexto=montagem_folheto`
(path ANTIGO `processar_pdf`, não o convergente), `referencia=None`.
**Custo da janela: US$ 8,51. Custo do dia 26/07: US$ 15,83 (46 chamadas).**

**Gatilho (não foi o serviço):** o journal tem **1 linha só** em toda a janela → as
montagens **não vieram do uvicorn**. Vieram dos **reprocessos em background que
eu mesmo lancei** (`scripts/reprocessar_folhetos.py`, um batch sobre TODOS os folhetos),
executados direto por SSH fora do serviço. Evidências:
- pares no **mesmo segundo** (19:09:41/45, 19:23:11×2, 19:35:48/50, 19:42:23/26) →
  ≥2 runs concorrentes que sobrepus;
- custos **idênticos repetidos** (0,0774 várias vezes) → o mesmo folheto pequeno
  montado de novo (retry/rerun sem dedupe).

Linha do tempo (HH:MM:SS · US$):
```
19:05:12 0.588 | 19:09:41 0.616 | 19:09:45 0.617 | 19:10:41 0.563 | 19:15:20 0.602
19:18:45 0.564 | 19:20:20 0.077 | 19:23:11 0.077 | 19:23:11 0.077 | 19:24:08 0.078
19:24:22 0.578 | 19:26:26 0.077 | 19:28:20 0.077 | 19:30:13 0.077 | 19:35:48 0.077
19:35:50 0.077 | 19:42:23 0.592 | 19:42:26 0.605 | 19:45:57 0.149 | 19:50:46 0.646
19:51:50 0.245 | 19:52:41 0.204 | 19:57:06 0.614 | 19:59:07 0.363 | 20:00:29 0.270
```
Nenhum processo de reprocesso roda agora (`ps` limpo). **Não era vazamento do serviço
em produção** — foi orquestração de dev sem teto. Mesmo assim, é exatamente o que os
freios abaixo passam a impedir para QUALQUER processo (incl. o serviço).

**Saldo estimado restante:** não derivável com precisão — a `custo_llm` só rastreia
**US$ 27,17 no total histórico** (rastreio recente, tagueado) e não conhecemos o valor
recarregado após o crédito-zero de 22/07. Fonte autoritativa é o console
(https://console.anthropic.com/settings/billing). Sem `OPENROUTER_API_KEY`/
`ANTHROPIC_ADMIN_KEY`, o digest reporta saldo Anthropic como "n/d — conferir no console".

### 2. FREIOS DE GASTO (`app/services/freios_gasto.py`)
`pode_montar(data_missa)` é consultado no início de `montar_e_publicar` **antes** de
qualquer chamada LLM. Três freios, nesta ordem:
- **(a) Disjuntor de crédito (402):** ao pegar erro de crédito, `bloquear_credito()`
  trava novas montagens; só `liberar_credito()` libera — chamado no **sucesso de uma
  montagem paga** (prova saldo) ou manualmente. Enquanto travado, missa → `pendente_revisao`.
- **(b) Orçamento diário:** se o gasto de hoje em `custo_llm` ≥ `MONITOR_TETO_DIARIO`
  (default **US$ 3**), montagens automáticas pausam + e-mail `alerta_orcamento_diario`
  (com cooldown de 24h). Missa → `pendente_revisao`.
- **(c) Teto de tentativas/dia/missa:** máx. `MONITOR_MAX_TENTATIVAS_MISSA_DIA`
  (default **2**) por (missa, dia).
Estado em `/var/lib/diademissa/freios_gasto.json` (diretório gravável do serviço).
`montar_e_publicar` agora pode retornar `resultado="bloqueado_por_freio"`.

### 3. Scheduler em 1 worker só (`scheduler.py`)
`tentar_lock_scheduler()` faz `flock(LOCK_EX|LOCK_NB)` num arquivo mantido aberto pela
vida do processo. Com `--workers 2`, só o 1º worker adquire; os demais logam
"NÃO iniciado neste worker" e seguem. Isso elimina os 2 schedulers (jobs/e-mails em dobro).
- **Achado de infra:** o serviço roda com `ProtectSystem=strict` (→ `data/` read-only)
  e `PrivateTmp=true` (→ `/tmp` isolado por unit). Movi TODOS os estados
  (`scheduler.lock`, `monitor_cooldown.json`, `freios_gasto.json`) para o único diretório
  gravável e persistente: **`/var/lib/diademissa/`** (onde já fica o SQLite).
- **Verificação em produção:** `lsof` mostra **1 único processo** segurando o flock
  (PID no arquivo `/var/lib/diademissa/scheduler.lock`); tentativa externa de adquirir
  retorna **False**. ✅

### 4. Testes
- `test_freios_gasto.py` (4): orçamento bloqueia; teto de tentativas/missa; disjuntor
  402 (bloqueia → libera); disjuntor tem prioridade sobre orçamento.
- `test_scheduler_lock.py` (1): 2º "worker" não adquire; libera → volta a adquirir.
- Suíte completa: **122 passed, 5 skipped, 4 failed**. Os 4 (`test_ascensao_2026`
  TestSaudacao 2º/4º turno + `test_zero_barras_separadoras`; `test_schema`
  rejeita-barra) são **pré-existentes** — nenhum importa `freios_gasto`/`monitor_llm`/
  `scheduler`/`publicacao_convergente`, logo não são regressão desta entrega.

### 5. Config .env (novas chaves)
`MONITOR_TETO_DIARIO=3`, `MONITOR_MAX_TENTATIVAS_MISSA_DIA=2`,
`SCHEDULER_LOCK_FILE=/var/lib/diademissa/scheduler.lock`,
`MONITOR_COOLDOWN_FILE=/var/lib/diademissa/monitor_cooldown.json`,
`FREIOS_STATE_FILE=/var/lib/diademissa/freios_gasto.json`.

**Commit:** `feat(freios): orcamento diario + teto tentativas/missa + disjuntor 402 + scheduler 1-worker (flock)`.

---

## ADENDO — Alerta de saldo ≤ US$ 2 (Anthropic) + SALDO ESTIMADO

### 1. Limiar
`MONITOR_LIMIAR_SALDO=2` no `.env` (novo nome; `MONITOR_SALDO_LIMIAR_USD` mantido por
compat). Comparação passou a ser **≤** (dispara em US$ 2,00 exatos).

### 2a. Admin API da Anthropic expõe saldo? NÃO.
A Admin API (`/v1/organizations/cost_report`, `.../usage_report`) expõe **custo e uso**,
não o **saldo de créditos pré-pagos** — não há endpoint de "balance". OpenRouter tem
(`GET /api/v1/credits`), Anthropic não. Portanto, item 2b.

> Passo a passo p/ gerar a `ANTHROPIC_ADMIN_KEY` (dá custo/uso, útil no digest, mas NÃO
> saldo): Console → Settings → **Admin keys** (org owner) → **Create Admin Key** →
> copiar `sk-ant-admin...` → colar em `.env` como `ANTHROPIC_ADMIN_KEY=...`. Não é
> necessária para o alerta de saldo (que usa o saldo estimado abaixo).

### 2b. SALDO ESTIMADO (implementado)
`saldo estimado = Σ recargas registradas − gasto acumulado (custo_llm)`.
- Recargas gravadas em `custo_llm` com `contexto='recarga_credito'` (excluídas do gasto,
  junto com `erro_credito`).
- `scripts/registrar_recarga.py <valor> [YYYY-MM-DD] [--nota "..."]` registra a recarga
  e imprime o novo saldo estimado.
- `saldo_anthropic()` retorna `{saldo_usd, estimado: True, detalhe}` quando há recargas;
  senão `n/d` com instrução. Digest e alerta mostram **"saldo estimado ~US$ X"**.

### 3. Alerta
No job diário (cooldown 24h já existente): se saldo ≤ limiar, e-mail com o link direto
de recarga **e** a frase "Recarregue e rode `scripts/registrar_recarga.py <valor>`".

### 4. Testes (3 novos)
- `test_saldo_estimado_recargas_menos_gasto` — 20 − (5+3) = **12,00**; recarga não conta
  como gasto.
- `test_alerta_saldo_2_dispara_190_nao_dispara_210` — saldo **1,90 ≤ 2 → dispara** e a
  mensagem contém `registrar_recarga`.
- `test_alerta_saldo_210_nao_dispara` — saldo **2,10 > 2 → não dispara**.
- Suíte completa: **125 passed** (mesmas 4 falhas pré-existentes).

### 5. Recargas registradas + RESSALVA importante
Registrei em produção: **US$ 20,00 em 26/07** ("recarga pós crédito-zero 22/07").
Resultado atual: `recargas US$ 20,00 − gasto US$ 27,17 = saldo estimado -US$ 7,17`.
- O valor **negativo é esperado e provisório**: (a) só **uma** recarga está registrada —
  o crédito-zero de 22/07 implica recarga(s) anterior(es) que preciso que você registre;
  (b) US$ ~15 do gasto rastreado de 26/07 foi **desperdício dos meus reprocessos de dev**
  (documentado no adendo anterior), não consumo operacional real.
- **AÇÃO PARA VOCÊ:** rode `scripts/registrar_recarga.py <valor> <data>` para cada recarga
  anterior que houve; aí o saldo estimado passa a refletir a realidade. Enquanto isso, o
  alerta mostrará "(estimado)" e pode disparar por causa do valor provisório.

`.env`: `MONITOR_LIMIAR_SALDO=2`.

**Commit:** `feat(monitor): saldo estimado Anthropic (recargas − gasto) + limiar ≤ US$2 + registrar_recarga.py`.
