# Google Setup — Passo a Passo

Guia para configurar **3 integrações Google** no projeto Dia de Missa:
1. **Google Places API** (busca semântica de igrejas)
2. **Google OAuth** (login com Google)
3. **Gmail SMTP** (recuperação de senha por email)

> Tudo é feito **uma vez só** e fica permanente. Custos: tudo dentro do free tier pra um app pessoal/pequeno.

---

## Pré-requisito: Google Cloud Project

1. Acessa https://console.cloud.google.com/
2. Faz login com sua conta Google (granato1402@gmail.com)
3. No topo: **"Select a project" → "NEW PROJECT"**
4. Nome do projeto: `Dia de Missa` → **CREATE**
5. Aguarda ~30s e troca pro projeto recém-criado

> Você vai usar este projeto pras 3 integrações abaixo.

---

## 1. Google Places API (Busca semântica)

**Pra que serve:** entender queries tipo "Igreja da PUC", "Catedral perto do Maracanã" e geocodificar pra coordenadas reais. Substitui o Nominatim (que é fraco em queries semânticas).

**Custo:** $200/mês de crédito grátis = ~40k buscas/mês. Pra app pessoal, sobra muito.

### Passos

1. Console Google Cloud → **menu hambúrguer (☰)** → **APIs & Services → Library**
2. Busca **"Geocoding API"** → clica → **ENABLE**
3. (Opcional, recomendado) Habilita também:
   - **Places API (New)** — pra busca de lugares por texto
   - **Maps JavaScript API** — se quiser mapa Leaflet→Google Maps depois
4. Vai em **APIs & Services → Credentials**
5. **CREATE CREDENTIALS → API key**
6. Copia a key gerada (algo tipo `AIzaSyC...`)
7. **EDIT API KEY** → seta restrições:
   - **Application restrictions:** "HTTP referrers"
     - Adiciona `https://diademissa.com.br/*` e `http://localhost:*` (dev)
   - **API restrictions:** "Restrict key" → marca só Geocoding API (e Places se habilitou)
   - **SAVE**
8. Me passa a key (ou seta direto via SSH):

```bash
# Via SSH (você ou eu)
ssh -p 22022 root@129.121.53.8
echo 'GOOGLE_MAPS_API_KEY=AIzaSyC...' >> /var/www/diademissa/backend/.env
systemctl restart diademissa-api
```

9. **Pronto.** Já existe código no backend que usa essa key automaticamente quando ela está setada. Testa buscar "santo agostinho leblon" — deve achar Santa Mônica direto via geocode Google.

---

## 2. Login com Google (OAuth)

**Pra que serve:** botão "Entrar com Google" — usuários não precisam criar senha, login em 1 clique.

**Custo:** **grátis** (sem limite).

### Passos

1. Console Google Cloud → **APIs & Services → OAuth consent screen**
2. **User Type:** External → **CREATE**
3. Preenche:
   - **App name:** `Dia de Missa`
   - **User support email:** seu email
   - **App logo:** opcional (PNG quadrado, 120kb max)
   - **Application home page:** `https://diademissa.com.br`
   - **Application privacy policy link:** `https://diademissa.com.br/privacy` (criamos depois — pode deixar vazio em dev)
   - **Application terms of service link:** vazio
   - **Authorized domains:** `diademissa.com.br`
   - **Developer contact:** seu email
   - **SAVE AND CONTINUE**
4. **Scopes** → ADD OR REMOVE SCOPES → marca:
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`
   - `openid`
   → **UPDATE → SAVE AND CONTINUE**
5. **Test users** → adiciona seu email (granato1402@gmail.com) e qualquer outro que vai testar antes de publicar → **SAVE AND CONTINUE**
6. **Summary** → **BACK TO DASHBOARD**

### Criar credencial OAuth

7. **APIs & Services → Credentials**
8. **CREATE CREDENTIALS → OAuth client ID**
9. **Application type:** Web application
10. **Name:** `Dia de Missa Web`
11. **Authorized JavaScript origins:**
    - `https://diademissa.com.br`
    - `http://localhost:3000` (dev)
12. **Authorized redirect URIs:**
    - `https://diademissa.com.br/auth/google/callback`
    - `http://localhost:3000/auth/google/callback`
13. **CREATE**
14. Copia **Client ID** e **Client secret** que aparecem.
15. Me passa (ou seta via SSH):

```bash
ssh -p 22022 root@129.121.53.8
cat >> /var/www/diademissa/backend/.env <<EOF
GOOGLE_CLIENT_ID=...apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-...
EOF
systemctl restart diademissa-api
```

16. Eu implemento o botão "Entrar com Google" no frontend (já tem stub em AuthScreens — falta wiring final).

### Publicação (após testar)

17. Quando tiver tudo funcionando: OAuth consent screen → **PUBLISH APP** (sai do modo "Testing" — qualquer um pode usar). Não exige verificação Google enquanto pedir só email/profile/openid.

---

## 3. Gmail SMTP — Recuperação de senha por email

**Pra que serve:** mandar email "Esqueci a senha → reset link". Usa sua conta Gmail.

**Custo:** **grátis** (limite generoso: 500 emails/dia via SMTP).

### Passos — gerar App Password

1. Acessa https://myaccount.google.com/security
2. Em **"Como você faz login no Google"** → **Verificação em duas etapas** → ativa se ainda não tiver. **Obrigatório** pra conseguir App Password.
3. Volta em https://myaccount.google.com/apppasswords
   (se não aparecer, busca "app passwords" no Google search da conta)
4. **Selecione um app:** "Other (custom name)" → digita `Dia de Missa`
5. **GENERATE**
6. Copia a senha de 16 caracteres mostrada (algo tipo `abcd efgh ijkl mnop`) — **só aparece uma vez**.

### Configurar no backend

7. Adiciona ao `.env`:

```bash
ssh -p 22022 root@129.121.53.8
cat >> /var/www/diademissa/backend/.env <<EOF
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu-email@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
SMTP_FROM=Dia de Missa <seu-email@gmail.com>
EOF
systemctl restart diademissa-api
```

8. Pronto. Eu implemento o fluxo "esqueci a senha → email" usando essas credenciais. (Já existe stub no backend, falta a função de envio real).

### Testar

Após implementação:
- Tela de login → "Esqueci a senha"
- Digita email
- Recebe email com link `https://diademissa.com.br/redefinir?token=...`
- Clica → redefine senha → loga

---

## Resumo de variáveis de ambiente (`.env` da VPS)

```bash
# Já configurado
APP_NAME=Dia de Missa API
DEBUG=False
DATABASE_URL=sqlite:////var/lib/diademissa/missa_hoje.db
SECRET_KEY=...
APP_BASE_URL=https://diademissa.com.br
CORS_ORIGINS=["https://diademissa.com.br"]

# Adicionar (a partir dos passos acima)
GOOGLE_MAPS_API_KEY=AIza...
GOOGLE_CLIENT_ID=...apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-...
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu@gmail.com
SMTP_PASSWORD=app-password-16-chars
SMTP_FROM=Dia de Missa <seu@gmail.com>
```

---

## Ordem recomendada

1. **Gmail SMTP** primeiro (5 min, sem precisar de Cloud Console complicado, libera reset de senha)
2. **Google Places** (10 min, libera busca semântica de igrejas)
3. **OAuth** (15 min, libera login social — mais complexo)

---

## Suporte

Quando tiver as credenciais nas mãos, me manda em uma mensagem (vou tratar com cuidado, configuro no `.env` da VPS, restarto o serviço, valido e te aviso). Pra cada uma das 3 fica uma mensagem separada se preferir.
