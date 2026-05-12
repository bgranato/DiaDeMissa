# Correcao pos-auditoria

**Data/hora:** 2026-05-12 20:30 (BRT)
**Status:** ✅ verde

## Bug 1 — Gabarito adulterado
- expected.json restaurado: ✅
- Parser de leitura consertado: ✅
- Antes: conclusao="Senhor.", resposta="T. Graças a Deus."
- Depois: conclusao="Palavra do Senhor.", resposta="Graças a Deus."
- Commit: e752829

## Bug 2 — Estrofe 3 fundida
- Teste de regressao adicionado: ✅
- Parser de estrofe consertado: ✅ (tracking de `/` no fim da linha)
- Antes: estrofe 3 com 1 verso fundido
- Depois: estrofe 3 com 2 versos separados corretamente
- Commit: c9f8dd3

## Bug 3 — Hardcode de postura na Saudacao
- Hardcode removido: ✅
- extrair_postura() em uso: ✅
- Commit: 20d9bf7

## Pytest final

```
92 passed in 5.57s
```

## Tags

- mini-gate-7-ok
- pos-debug-postura
- pos-auditoria

## Confirmacao de nao-regressao

- Antes da auditoria: 90 passed
- Depois das 3 correcoes: 92 passed (2 testes novos)
- Regressoes: nenhuma
