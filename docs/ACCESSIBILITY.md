# ACCESSIBILITY.md

## Regras de Acessibilidade

Este documento define os padrões de acessibilidade obrigatórios para o app Missa Hoje.

O público principal são idosos (60+ anos). Todas as decisões de UI/UX partem deste público.

## Padrões de UI

### Tipografia

- **Fonte padrão**: tamanho mínimo 18px (equivalente a ~14pt em mobile)
- **Família**: sans-serif (SF Pro no iOS, Roboto no Android)
- **Espaçamento entre linhas**: 1.6 (160% da altura da fonte)
- **Contraste mínimo**: 7:1 para texto normal (WCAG AAA)
- **Títulos**: negrito, sem itálico para blocos grandes de texto

### Botões

- **Altura mínima**: 56px (toque confortável para dedos com pouca destreza)
- **Largura mínima**: 56px
- **Espaçamento entre botões**: mínimo 16px
- **Alvo de toque**: mínimo 48x48dp (recomendado 56x56dp)
- **Labels sempre visíveis**: nunca usar ícones sem texto explicativo
- **Feedback tátil**: vibração ao tocar botões principais

### Cores

- **Alto contraste**: relação 7:1 ou superior (WCAG AAA)
- **Modo escuro**: fundo preto (#000000) com texto branco (#FFFFFF)
- **Modo alto contraste**: fundo branco com texto preto e links sublinhados
- **Não depender apenas de cor** para transmitir informação (usar ícones + texto)
- **Evitar**: cores pastel, baixo contraste, combinações vermelho/verde

### Layout

- **Espaçamento generoso**: padding mínimo 24px nas laterais
- **Hierarquia visual clara**: títulos, subtítulos e corpo bem diferenciados
- **Listas curtas**: evitar scroll infinito
- **Zona de toque inferior**: botões de ação principais na metade inferior da tela

## Navegação

### Estrutura de Telas

```
Splash → Login/Cadastro → Home → Missa do Dia
                                  → Índice
                                  → Calendário
                                  → Histórico
                                  → Configurações → Preferências
                                                  → Usuário
                                                  → Lembretes
```

### Regras

- **Mínimo de toques**: Missa do Dia acessível em no máximo 2 toques a partir da Home
- **Botão "Voltar"**: sempre visível no topo ou como gesto
- **Navegação linear**: modo leitura usa apenas "Próximo" e "Anterior"
- **Indicador de progresso**: sempre visível durante a leitura
- **Posição atual**: mostrar "Bloco 3 de 18" ou similar

## Requisitos para Idosos

### Visão

- Fonte grande por padrão (18px)
- Botão "A+" para aumentar (até 28px)
- Botão "A-" para diminuir (mínimo 14px)
- Modo alto contraste com toggle rápido
- Evitar fontes decorativas ou serifadas em blocos longos
- Ícones grandes e reconhecíveis

### Audição

- Compatibilidade total com VoiceOver (iOS) e TalkBack (Android)
- Todos os elementos interativos devem ter `accessibilityLabel`
- Anunciar mudanças de tela com `accessibilityLiveRegion`

### Motricidade

- Botões grandes com áreas de toque amplas
- Gestos simples (apenas toque, evitar swipe complexo)
- Tempo ilimitado para interação
- Confirmar ações destrutivas com diálogo

### Cognição

- Interface consistente em todas as telas
- Terminologia familiar (linguagem litúrgica padrão)
- Instruções claras e curtas
- Evitar distrações visuais (animações, elementos piscando)
- Feedback visual para cada ação

## Componentes Obrigatórios

```typescript
// Tokens de tema (theme/tokens.ts)
interface AccessibilityTokens {
  fontSizeMin: 14;
  fontSizeDefault: 18;
  fontSizeMax: 28;
  lineHeightDefault: 1.6;
  buttonMinHeight: 56;
  touchTargetMin: 48;
  spacingDefault: 24;
}

// Botão acessível
interface AccessibleButtonProps {
  label: string;          // Obrigatório: texto visível
  accessibilityLabel: string;  // Obrigatório: texto para leitores de tela
  onPress: () => void;
  variant: 'primary' | 'secondary';
  size: 'large' | 'small';
}
```

## Testes de Acessibilidade

- Verificar contraste com ferramenta de avaliação de cores
- Testar com VoiceOver e TalkBack ativos
- Verificar alvos de toque (mínimo 48x48dp)
- Validar navegação apenas com teclado (Android)
- Testar com fontes no tamanho máximo
- Testar em modo alto contraste

## Referências

- WCAG 2.2 AA/AAA
- Apple Human Interface Guidelines (Accessibility)
- Google Material Design (Accessibility)
