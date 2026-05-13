# Diagnostico — discrepancia de blocos

**Data/hora:** 2026-05-12 20:45
**Status:** 🔍 diagnostico (sem conserto)

## Outputs

### 1. Endpoint /missa/atual (JSON)

Retorna 3 blocos:
1. canto - Canto de Entrada
2. dialogo - Saudacao
3. antifona - Antifona da Entrada

### 2. Pipeline puro (Python)

Retorna 6 blocos:
1. canto - Canto de Entrada
2. dialogo - Saudacao
3. antifona - Antifona da Entrada
4. dialogo - Ato Penitencial
5. leitura - Primeira Leitura
6. leitura - Segunda Leitura

## Diagnostico

O pipeline puro produz 6 blocos. O endpoint retorna 3.

Diferenca: 3 blocos (Ato Penitencial, Primeira Leitura, Segunda Leitura) estao sendo parseados pelo pipeline mas nao chegam ao endpoint.

**Causa provavel:** o servidor FastAPI nao foi reiniciado apos as alteracoes no `structure.py` que adicionaram os parsers de Ato Penitencial e Leitura. O modulo `app.pipeline` foi carregado em memoria com a versao antiga (antes dos parsers novos) e o servidor precisa ser restartado para recarregar.

## Acao necessaria

Reiniciar o servidor backend e testar novamente.
