# SESSION_SUMMARY.md

## 1. Objetivo Geral do Projeto

Criar o webapp **"Missa Hoje"** — uma alternativa digital, acessível e estruturada ao folheto impresso distribuído nas missas católicas.  
O app baixa, interpreta e transforma o conteúdo do PDF oficial da Arquidiocese do Rio de Janeiro em blocos litúrgicos ordenados, exibidos em interface web responsiva com foco em **acessibilidade para idosos**.

## 2. Stack Definida

| Camada    | Tecnologia                              |
|-----------|-----------------------------------------|
| Frontend  | React + Vite + TypeScript + React Router |
| Backend   | Python + FastAPI                        |
| Banco     | PostgreSQL                              |
| Autenticação | Email/senha + Google OAuth          |
| PDF       | Extração textual com parser heurístico próprio |
| Infra     | Monorepo com web/ e backend/ (backend serve frontend estático) |

## 3. Estrutura Atual de Pastas

```
_dev/
  SESSION_SUMMARY.md

web/
  src/
    components/     (AccessibleButton, FontControl, ProgressBar)
    pages/          (13 páginas React Router)
    contexts/       (AuthContext, ThemeContext)
    services/       (api, auth, missa)
    theme/          (tokens, CSS custom properties)
    types/          (missa, usuario)
    styles/         (global.css com suporte a 4 temas)
  dist/             (build estático servido pelo backend)

backend/
  app/
    api/
    core/
    models/
    schemas/
    services/
    repositories/
    workers/
    utils/
  tests/

docs/
  ARCHITECTURE.md
  API.md
  ACCESSIBILITY.md
  PARSER.md
```

## 4. Funcionalidades já Implementadas

- [x] Estrutura de pastas do monorepo criada
- [x] Documentação base: ARCHITECTURE.md, API.md, ACCESSIBILITY.md, PARSER.md
- [x] SESSION_SUMMARY.md criado e versionado
- [x] .gitignore e .env.example
- [x] Backend: requirements.txt com dependências
- [x] Backend: app/core/config.py (config centralizada via Pydantic Settings)
- [x] Backend: app/core/database.py (SQLAlchemy engine + session)
- [x] Backend: app/core/security.py (bcrypt, JWT, auth dependency)
- [x] Backend: modelos SQLAlchemy (Usuario, PreferenciaUsuario, HistoricoUsuario, Lembrete, Missa, BlocoLiturgico)
- [x] Backend: schemas Pydantic (todos os schemas de request/response)
- [x] Backend: pdf_downloader.py (download, hash, detecção de alteração)
- [x] Backend: pdf_parser.py (extração de texto com pdfplumber + coordenadas)
- [x] Backend: liturgical_parser.py (limpeza, segmentação, detecção de títulos/referências)
- [x] Backend: block_classifier.py (classificação por título, keyword, fallback + ordenação canônica)
- [x] Backend: mass_processor.py (orquestração completa download → parse → classificação → persistência)
- [x] Backend: rotas da API (health, missas, usuários, auth, histórico, preferências, lembretes)
- [x] Backend: app/main.py (FastAPI app com CORS, router, auto-create tables)
- [x] Backend: testes do parser (9 testes unitários)
- [x] Web: Vite + React + TypeScript + React Router v6
- [x] Web: Tema acessível com CSS custom properties (light/dark/high-contrast/high-contrast-dark)
- [x] Web: CSS global com design system acessível (fonte 20px, botões 56px, alto contraste)
- [x] Web: API service (axios + interceptor de token + redirect 401)
- [x] Web: Auth service (login, cadastro, Google, logout com localStorage)
- [x] Web: Missa service (getMissaHoje, getBlocosMissa, etc.)
- [x] Web: AuthContext (estado global de autenticação)
- [x] Web: ThemeContext (fonte, modo escuro, alto contraste)
- [x] Web: Componente AccessibleButton (botão grande, acessível)
- [x] Web: Componente FontControl (A+/A-)
- [x] Web: Componente ProgressBar (progresso de leitura)
- [x] Web: 13 páginas React Router com rotas protegidas
- [x] Web: Splash, Login, Cadastro, RecuperarSenha
- [x] Web: Home (acesso rápido à missa do dia)
- [x] Web: LeituraMissa (bloco a bloco, navegação anterior/próximo)
- [x] Web: IndiceMissa (lista de blocos)
- [x] Web: Calendario (navegação mensal)
- [x] Web: Historico (lista com progresso)
- [x] Web: Configuracoes (menu central)
- [x] Web: Preferencias (fonte, modo escuro, alto contraste)
- [x] Web: AreaUsuario (editar nome/email)
- [x] Web: Lembretes (listar e remover)
- [x] Backend: StaticFiles e SPA catch-all para servir web build
- [x] App unificado: backend FastAPI serve frontend React em produção (porta única 8000)

## 5. Funcionalidades Pendentes

### MVP:
- [ ] Backend: worker agendado para download diário automático do PDF
- [ ] Backend: testes de integração (API)
- [ ] Web: modo offline com Service Worker (PWA)
- [ ] Web: salvamento de progresso de leitura (chamar API)
- [ ] Web: integração real com Google Sign-In
- [ ] Web: notificações para lembretes (Push API)
- [ ] Web: tela de "Favoritos"
- [ ] Web: teste de acessibilidade com leitores de tela (NVDA, VoiceOver)
- [ ] Web: deploy em produção (Docker + VPS)

### Melhorias futuras:
- [ ] Suporte a múltiplas arquidioceses/fontes de PDF
- [ ] Player de áudio para salmos e cânticos
- [ ] Compartilhamento de blocos
- [ ] PWA completo com install prompt

## 6. Decisões Técnicas Tomadas

1. **Parser próprio**: não usar bibliotecas de extração semântica de PDF; construir parser heurístico em camadas (extração → limpeza → classificação → ordenação).
2. **Monorepo**: manter backend e mobile no mesmo repositório para facilitar consistência.
3. **Accessibility-first**: toda decisão de UI parte dos requisitos de idosos (fonte grande, botões grandes, alto contraste, navegação linear).
4. **Sem PDF viewer**: o app nunca exibe o PDF diretamente; sempre converte para blocos nativos.
5. **Parser tolerante**: o PDF pode variar de estrutura; o parser deve ser resiliente e usar heurísticas de fallback.
6. **Blocos dinâmicos**: a lista de tipos litúrgicos não é fixa; o classificador infere o tipo a partir do texto e posição.
7. **pdfplumber** como biblioteca de extração de texto (preserva coordenadas para reagrupamento).
8. **Reordenação por ordem canônica**: blocos são reordenados conforme a sequência litúrgica, independente da ordem de aparecimento no PDF.
9. **Tipos litúrgicos com fallback**: blocos não identificados são marcados como "desconhecido" mas permanecem visíveis.
10. **Context API para estado global**: ThemeContext e AuthContext separados para evitar re-renderizações desnecessárias.
11. **Tokens de tema**: cores e dimensões centralizadas em tema, com suporte a 4 modos (light, dark, high contrast, high contrast dark).

## 7. Problemas Conhecidos

- **Parser litúrgico sub-ótimo**: blocos estão sendo classificados como "desconhecido" - o PDF não tem títulos em CAIXA ALTA, o que quebra a heurística de detecção. Precisa refinamento.
- Google OAuth depende de configuração do Google Cloud Console (client ID)
- PDF pode variar de estrutura; parser precisa de monitoramento
- Modo offline ainda não implementado
- Progresso de leitura ainda não persiste via API
- Python 3.9 no macOS não suporta `str | None` syntax - usar `Optional[str]`

## 8. Próximos Passos Recomendados

### Imediatos (infra):
1. Configurar banco PostgreSQL e rodar migration (Alembic)
2. Executar testes do parser: `cd backend && python -m pytest tests/ -v`

### Desenvolvimento web:
3. Iniciar servidor dev: `cd web && npx vite` (com proxy para backend)
4. Em produção: `cd web && npx vite build` e reiniciar backend

### Funcionalidades:
5. Melhorar parser litúrgico (classificação de blocos está falhando)
6. Implementar modo offline (Service Worker / PWA)
7. Implementar worker agendado no backend para download diário do PDF
8. Implementar salvamento de progresso de leitura
9. Testar acessibilidade com leitores de tela (NVDA, VoiceOver)

### URLs ativas:
- **Webapp:** http://localhost:8000 (servido pelo backend) ou http://localhost:3000 (vite dev)
- **API:** http://localhost:8000/api/v1
- **Swagger:** http://localhost:8000/docs

## 9. Instruções para Retomar o Projeto em Nova Sessão

```bash
# Ler este arquivo antes de qualquer ação
cat _dev/SESSION_SUMMARY.md

# Iniciar OpenCode com contexto
opencode --instruction "$(cat _dev/SESSION_SUMMARY.md)"
```

Ao retomar:
1. Leia este arquivo primeiro.
2. Leia `docs/ARCHITECTURE.md` para visão geral da arquitetura.
3. Verifique o estado atual das funcionalidades na seção 5.
4. Continue pelo próximo item pendente na ordem sugerida.
5. Atualize este arquivo ao final da sessão.

---

**Última atualização:** 2026-05-11  
**Sessão atual:** Migração de React Native/Expo para Webapp React + Vite. Backend servindo frontend estático.
