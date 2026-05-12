# API.md

## Visão Geral

Base URL: `http://localhost:8000/api/v1`

Autenticação: `Authorization: Bearer <token>`

## Rotas

### Health Check

```
GET /health
```

**Resposta:**
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

---

### Missas

#### Buscar Missa de Hoje

```
GET /missas/hoje
```

**Headers:** `Authorization: Bearer <token>` (opcional)

**Resposta 200:**
```json
{
  "id": 1,
  "data": "2026-05-11",
  "celebracao": "5º Domingo da Páscoa",
  "tempo_liturgico": "Páscoa",
  "status_processamento": "concluido",
  "total_blocos": 18
}
```

**Resposta 404:**
```json
{
  "detail": "Missa para hoje ainda não disponível"
}
```

#### Buscar Missa por Data

```
GET /missas/{data}
```

**Parâmetros:** `data` no formato `YYYY-MM-DD`

**Resposta 200:** Mesmo formato de `/missas/hoje`

---

#### Buscar Missa por ID

```
GET /missas/{id}
```

**Resposta 200:**
```json
{
  "id": 1,
  "data": "2026-05-11",
  "celebracao": "5º Domingo da Páscoa",
  "tempo_liturgico": "Páscoa",
  "fonte_pdf_url": "https://...",
  "pdf_hash": "abc123...",
  "status_processamento": "concluido",
  "data_criacao": "2026-05-11T06:00:00"
}
```

#### Buscar Blocos de uma Missa

```
GET /missas/{id}/blocos
```

**Resposta 200:**
```json
{
  "missa_id": 1,
  "blocos": [
    {
      "id": 1,
      "ordem": 1,
      "tipo": "canto_entrada",
      "titulo": "Canto de Entrada",
      "referencia": null,
      "conteudo": "Letra do canto de entrada...",
      "visivel": true
    },
    {
      "id": 2,
      "ordem": 2,
      "tipo": "primeira_leitura",
      "titulo": "Primeira Leitura",
      "referencia": "At 13,14.43-52",
      "conteudo": "Leitura dos Atos dos Apóstolos...",
      "visivel": true
    }
  ]
}
```

#### Processar PDF Manualmente

```
POST /missas/processar-pdf
```

**Headers:** `Authorization: Bearer <token>` (admin)

**Resposta 202:**
```json
{
  "message": "Processamento iniciado",
  "missa_id": null
}
```

---

### Usuários

#### Criar Usuário

```
POST /usuarios
```

**Body:**
```json
{
  "nome": "Maria de Souza",
  "email": "maria@email.com",
  "senha": "senha123"
}
```

**Resposta 201:**
```json
{
  "id": 1,
  "nome": "Maria de Souza",
  "email": "maria@email.com",
  "data_criacao": "2026-05-11T10:00:00"
}
```

#### Login

```
POST /auth/login
```

**Body:**
```json
{
  "email": "maria@email.com",
  "senha": "senha123"
}
```

**Resposta 200:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "usuario": {
    "id": 1,
    "nome": "Maria de Souza",
    "email": "maria@email.com"
  }
}
```

#### Login com Google

```
POST /auth/google
```

**Body:**
```json
{
  "token": "google-oauth-id-token"
}
```

**Resposta 200:** Mesmo formato de login

---

#### Buscar Usuário Logado

```
GET /usuarios/me
```

**Headers:** `Authorization: Bearer <token>`

**Resposta 200:**
```json
{
  "id": 1,
  "nome": "Maria de Souza",
  "email": "maria@email.com",
  "provider": "email",
  "data_criacao": "2026-05-11T10:00:00"
}
```

#### Atualizar Usuário

```
PUT /usuarios/me
```

**Body:**
```json
{
  "nome": "Maria Aparecida de Souza"
}
```

---

### Histórico

#### Listar Histórico

```
GET /usuarios/me/historico
```

**Resposta 200:**
```json
[
  {
    "missa_id": 1,
    "data": "2026-05-11",
    "celebracao": "5º Domingo da Páscoa",
    "ultimo_bloco_id": 10,
    "percentual_lido": 55.5,
    "data_ultimo_acesso": "2026-05-11T11:30:00"
  }
]
```

#### Salvar Progresso

```
POST /usuarios/me/historico
```

**Body:**
```json
{
  "missa_id": 1,
  "ultimo_bloco_id": 10,
  "percentual_lido": 55.5
}
```

---

### Preferências

#### Listar Preferências

```
GET /usuarios/me/preferencias
```

**Resposta 200:**
```json
{
  "tamanho_fonte": 20,
  "modo_escuro": false,
  "alto_contraste": false,
  "leitura_simplificada": false,
  "notificacoes_ativas": true
}
```

#### Atualizar Preferências

```
PUT /usuarios/me/preferencias
```

**Body:**
```json
{
  "tamanho_fonte": 22,
  "modo_escuro": true,
  "alto_contraste": false,
  "leitura_simplificada": true,
  "notificacoes_ativas": true
}
```

---

### Lembretes

#### Listar Lembretes

```
GET /usuarios/me/lembretes
```

**Resposta 200:**
```json
[
  {
    "id": 1,
    "missa_id": null,
    "titulo": "Missa Dominical",
    "data_hora_alerta": "2026-05-17T09:00:00",
    "ativo": true
  }
]
```

#### Criar Lembrete

```
POST /usuarios/me/lembretes
```

**Body:**
```json
{
  "missa_id": null,
  "titulo": "Missa Dominical",
  "data_hora_alerta": "2026-05-17T09:00:00"
}
```

#### Atualizar Lembrete

```
PUT /usuarios/me/lembretes/{id}
```

#### Deletar Lembrete

```
DELETE /usuarios/me/lembretes/{id}
```

---

## Códigos de Erro

| Código | Significado |
|--------|-------------|
| 400 | Bad Request |
| 401 | Não autenticado |
| 403 | Sem permissão |
| 404 | Recurso não encontrado |
| 409 | Conflito (ex: email já cadastrado) |
| 422 | Erro de validação |
| 500 | Erro interno |
