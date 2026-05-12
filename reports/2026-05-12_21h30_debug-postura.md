# Debug — Onde a postura está sendo perdida

**Data/hora:** 2026-05-12 21:30 (BRT)
**Status:** 🔍 diagnóstico (sem alteração de código)

---

## 1. Comando executado

`python scripts/dump_pipeline.py`

Output:
```
✅ 01_extract.txt — 21450 chars
✅ 02_clean.txt — 21305 chars
📁 Dumps salvos em: reports/debug/
```

## 2. Tamanho dos dumps

- `reports/debug/01_extract.txt` — 21450 chars
- `reports/debug/02_clean.txt` — 21305 chars

## 3. Ocorrências de "De pé"

### Em 01_extract.txt

| Linha | Contexto |
|---|---|
| 33 | `(De pé)` — linha ISOLADA após "1. Canto de Entrada" |
| 174 | `(Mt 28,19a.20b) (De pé)` — junto com referência, após "9. Aclamação ao Evangelho" |
| 201 | `(De pé)` — linha ISOLADA após "12. Profissão de Fé" |
| 260 | `(De pé)` — linha ISOLADA após "15. Convite à Oração" |
| 427 | `(De pé)` — linha ISOLADA após "20. Depois da Comunhão" |

### Em 02_clean.txt

Linhas correspondentes preservadas, mesma estrutura.

## 4. Ocorrências de "Sentados"

### Em 01_extract.txt

| Linha | Contexto |
|---|---|
| 105 | `(At 1,1-11) (Sentados)` — mesma linha do título "6. Primeira Leitura" |
| 198 | `(Sentados)` — linha ISOLADA após "11. Homilia" |
| 246 | `(Sentados)` — linha ISOLADA após "14. Canto das Ofertas" |

### Em 02_clean.txt

Mesma estrutura preservada.

## 5. Linha exata do título "Canto de Entrada"

### Em 01_extract.txt (linha 32)
```
"1. Canto de Entrada"
```

### Em 02_clean.txt (linha 25)
```
"1. Canto de Entrada"
```

**Obs:** `(De pé)` está na LINHA SEGUINTE em ambos (linhas 33 e 26 respectivamente).

## 6. Linha exata do título "Primeira Leitura"

### Em 01_extract.txt (linha 104-105)
```
"e impulsiona à missão."
"6. Primeira Leitura"
```

**Obs:** `(Sentados)` aparece na linha 105 junto com a referência: `(At 1,1-11) (Sentados)`

### Em 02_clean.txt
```
"e impulsiona à missão."
"6. Primeira Leitura"
```

## 7. Hipótese diagnóstica

**Hipótese C** — A marcação chega limpa ao `02_clean.txt`, mas o `structure.py` não busca por ela na janela certa.

Evidência: `(De pé)` está presente em `01_extract.txt` (linha 33) e `02_clean.txt` (linha 26), SEMPRE na linha SEGUINTE ao título "1. Canto de Entrada". O `structure.py` atual só examina a PRIMEIRA linha do bloco (o título) para extrair postura, nunca olha a próxima linha.

Isso afeta Canto de Entrada, Profissão de Fé, Convite à Oração e Depois da Comunhão — todos com `(De pé)` ou `(Sentados)` em linha separada.

Já a Primeira Leitura tem `(Sentados)` na MESMA linha (junto com a referência), então seria capturada se o parser de Leitura existisse.

## 8. Nada foi consertado

Nenhum arquivo de produção foi modificado. Apenas:
- `scripts/dump_pipeline.py` (criado)
- `reports/debug/01_extract.txt` (gerado)
- `reports/debug/02_clean.txt` (gerado)

---

**AGUARDANDO ORIENTAÇÃO.**
