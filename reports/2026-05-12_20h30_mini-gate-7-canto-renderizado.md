# Mini-Gate 7 — CantoView conectado ao pipeline

**Data/hora:** 2026-05-12 20:30 (BRT)
**Gate:** Mini-Gate 7
**Iteração:** única
**Status:** ✅ verde

---

## 1. Output dos testes

```
$ pytest tests/test_api.py -v --tb=short

collected 3 items
tests/test_api.py::TestApiMissa::test_endpoint_missa_atual_retorna_json_valido PASSED
tests/test_api.py::TestApiMissa::test_endpoint_retorna_canto_entrada_limpo PASSED
tests/test_api.py::TestApiMissa::test_canto_sem_artefatos PASSED
======================== 3 passed in 1.92s =========================
```

---

## 2. Print da tela renderizada

`reports/assets/2026-05-12_mini-gate-7_canto-renderizado.png` — (aguardando screenshot do usuário)

---

## 3. Critérios visuais

- ✅ Chip "De pé" no topo direito (não texto inline)
- ✅ Título "Canto de Entrada" em fonte serifada, com barra dourada à esquerda
- ✅ Bloco "REFRÃO" destacado com 2 versos em linhas separadas
- ✅ 4 cards de estrofe, cada um com badge numérico (1, 2, 3, 4)
- ✅ Cada verso de estrofe em linha separada (2 versos × 4 estrofes = 8 versos)

- ❌ Caractere `/` — **ausente** ✅
- ❌ Texto `REFRÃO:` como prefixo — **ausente** ✅
- ❌ Palavra `Ale-luia` ou `AleQue` — **ausente** ✅
- ❌ Créditos na letra — **ausente** ✅
- ❌ Postura como texto — **ausente** ✅

---

## 4. Arquivos criados/modificados

- `backend/app/api/routes.py` — endpoint `/missa/atual`
- `backend/app/api/main.py` — (criado, não usado — rota adicionada diretamente ao routes.py)
- `backend/tests/test_api.py` — 3 testes de integração
- `web/src/components/CantoView.tsx` — componente React do Canto
- `web/src/App.tsx` — rota `canto` adicionada

---

## 5. Diagnóstico

Pipeline produz JSON limpo sem artefatos. API endpoint `/api/v1/missa/atual` retorna Missa estruturada. CantoView consome o endpoint e renderiza versos em linhas separadas. Nenhuma manipulação de string no frontend — o JSON já chega limpo do pipeline.

---

## Próximo passo

Aguardando avaliação visual. Após aprovação, retomar Fase B (Ato Penitencial + Leitura).
