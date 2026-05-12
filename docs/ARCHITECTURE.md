# ARCHITECTURE.md

## Visão Geral

O **Missa Hoje** é um aplicativo mobile que substitui o folheto litúrgico impresso por uma experiência digital nativa, acessível e estruturada.

O fluxo principal do sistema é:

```
PDF (fonte oficial) 
  → Download e hash check 
  → Extração de texto bruto 
  → Parsing litúrgico (limpeza, separação, classificação) 
  → JSON estruturado 
  → Banco PostgreSQL 
  → API REST 
  → App React Native
```

## Decisões Técnicas

### Por que parser próprio em vez de bibliotecas de NLP?

O PDF do folheto tem estrutura semi-fixa porém não garante consistência total. Bibliotecas de NLP seriam excesso de complexidade para um problema que pode ser resolvido com heurísticas bem definidas em camadas:

1. **Extração**: `pdfplumber` para extrair texto com coordenadas de página
2. **Limpeza**: remoção de ruídos, cabeçalhos/rodapés, numeração
3. **Segmentação**: divisão por blocos usando marcadores textuais (títulos em maiúsculo, padrões de citação bíblica)
4. **Classificação**: identificação do tipo litúrgico por correspondência de padrões e fallback posicional
5. **Ordenação**: sequência litúrgica canônica

### Por que monorepo?

Manter backend e mobile no mesmo repositório simplifica:
- Consistência de tipos e schemas
- CI/CD unificado
- Revisão de código integrada
- Versionamento sincronizado

### Por que accessibility-first?

O público principal é idoso (60+ anos). Acessibilidade não é um recurso adicional; é o requisito fundamental que guia todas as decisões de UI/UX, desde o tamanho da fonte até a navegação linear.

## Fluxo do Sistema

### Fluxo Diário

1. **Worker agendado** (cron ou scheduler) dispara o processamento diário
2. **pdf_downloader** baixa o PDF de `https://www.arqrio.com.br/app/painel/amissa/amissa.pdf`
3. **pdf_downloader** calcula hash SHA-256 e compara com o hash armazenado
4. Se o hash mudou:
   a. **pdf_parser** extrai o texto bruto com coordenadas
   b. **liturgical_parser** limpa e segmenta o texto em blocos
   c. **block_classifier** classifica cada bloco por tipo litúrgico
   d. **mass_processor** orquestra e persiste no banco
5. Se o hash não mudou: mantém a missa já processada

### Fluxo do Usuário

1. Usuário abre o app → Splash → Home
2. Home mostra a Missa do Dia com botão "Começar"
3. Ao tocar "Começar", navega para a tela de leitura sequencial
4. Usuário navega bloco a bloco com "Próximo" / "Anterior"
5. Progresso é salvo automaticamente
6. Pode acessar índice, ajustar fonte, contraste, etc.

## Camadas

### Backend (FastAPI)

```
backend/
  app/
    api/          → Rotas REST
    core/         → Config, database, security
    models/       → SQLAlchemy models
    schemas/      → Pydantic schemas
    services/     → Regras de negócio
    repositories/ → Acesso a dados
    workers/      → Tarefas agendadas
    utils/        → Utilitários
```

### Mobile (React Native / Expo)

```
apps/mobile/src/
  components/   → Componentes reutilizáveis
  screens/      → Telas do app
  navigation/   → Configuração de rotas
  services/     → API client
  hooks/        → Custom hooks
  contexts/     → Context providers (tema, auth)
  theme/        → Tokens de design system
  types/        → TypeScript types
  utils/        → Utilitários
```

## Segurança

- Senhas hashadas com bcrypt
- JWT para autenticação
- Google OAuth para login social
- Variáveis de ambiente para secrets
- CORS configurado por ambiente
