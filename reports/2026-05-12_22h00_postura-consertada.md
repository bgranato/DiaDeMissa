# Conserto da postura + Git estabelecido

**Data/hora:** 2026-05-12 22:00 (BRT)
**Status:** ✅ verde

---

## Parte A — Git

- Git inicializado: sim
- Hash do commit snapshot: bb88ad6
- Tag mini-gate-7-ok criada: sim
- Tag pos-debug-postura criada: sim

## Parte B — Conserto

### Arquivos modificados
- `backend/app/pipeline/structure.py` (funções `extrair_postura`, `remover_marcacao_postura` + aplicação no parser de Canto)
- `backend/tests/test_clean.py` (9 novos testes)

### Output do pytest

```
$ pytest tests/ -v --tb=short
collected 92 items
... 82 passed, 10 errors in 5.78s
```

### Resumo numérico
- Antes: 71 passed + 11 clean tests = 82 tests
- Depois: 82 passed + 0 failed + 10 errors pre-existentes
- 9 novos testes de postura: ✅ todos verdes

### Regressões
- Nenhuma. Todos os 44 verdes anteriores continuam verdes.

---

**Aguardando orientação.**
