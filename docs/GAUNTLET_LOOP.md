# Gauntlet Loop — publicação de missas

## Contrato operacional

- **Objetivo:** publicar apenas uma missa cuja montagem foi conferida contra o PDF oficial da mesma edição.
- **Métrica:** a publicação contém `revisao_json.conferencia.conferida=true`, no máximo três iterações, e **zero divergências de conteúdo ou hierarquia litúrgicos**. O PDF arquivado é a fonte de verdade.
- **Limite:** no máximo `CONFERENCIA_MAX_ITER` (padrão: 3). Falha do mapa, do conferente ou da correção encerra o ciclo; a missa fica em `pendente_revisao`. Uma missa anteriormente concluída não é substituída por uma reprovada.

## Etapas e papéis

1. **Referência:** o mapa litúrgico lê apenas o PDF e produz o contrato de conteúdo e hierarquia.
2. **Construtor:** a montagem multimodal produz o JSON da missa usando o PDF e o mapa.
3. **Crítico:** outra chamada, com instrução e contexto próprios, recebe somente PDF e JSON final. Ela aponta divergências acionáveis; não recebe o raciocínio da montagem. Uma camada determinística também bloqueia palavras litúrgicas que não constam no texto-fonte.
4. **Gate:** qualquer divergência de conteúdo ou hierarquia retorna ao construtor. A publicação só é permitida com lista vazia. Qualquer indisponibilidade é reprovação técnica, nunca aprovação implícita.

## Escopo explícito

O gate não compara projeto editorial: capa, marcas, créditos, imagens, cores, tipografia, colunas, alinhamento, quebras ou números de página estão fora da métrica. Ele compara apenas textos litúrgicos, rubricas, referências, seções, blocos e sua ordem/hierarquia.

## Evidência e operação

O resultado fica em `revisao_json.conferencia`: `conferida`, `iteracoes`, custo, divergências restantes e o `contrato` (objetivo, métrica, limite, papéis e escopo). Execute a suíte do backend antes de disponibilizar uma alteração:

```bash
backend/.venv/bin/python -m pytest backend/tests -q
```

Para uma edição específica, a referência é o PDF arquivado em `backend/data/pdfs/archive/YYYY-MM-DD.pdf`; execute também o verificador de regressão, que devolve código não zero se uma âncora do golden estiver ausente:

```bash
backend/.venv/bin/python backend/scripts/verificar_regressao.py YYYY-MM-DD
```

O crítico não deve ser ignorado via configuração. Quando o provedor estiver indisponível, corrija a disponibilidade ou faça revisão humana; não publique fallback textual.

## Frontends

O painel de revisão mostra as divergências e bloqueia a ação de publicar enquanto houver crítica, não houver conferência aprovada ou o limite tiver sido atingido. O servidor repete essa regra e devolve `409` se alguém tentar contornar a interface. Antes de um release web, execute `npm --prefix web run typecheck`, `npm --prefix web test` e `npm --prefix web run build`.
