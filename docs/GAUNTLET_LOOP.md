# Gauntlet Loop — publicação de missas

## Contrato operacional

- **Objetivo:** publicar apenas uma missa cuja montagem foi conferida contra os PDFs oficiais da mesma edição, na política de fontes abaixo.
- **Métrica:** a publicação contém `revisao_json.conferencia.conferida=true`, no máximo três iterações, e **zero divergências de conteúdo ou hierarquia litúrgicos**. O PDF arquivado é a fonte de verdade.
- **Fontes:** **Celular** é a única fonte de extração e estruturação; **Celebrante** é a conferência secundária de falas do presidente, rubricas, postura e Oração Eucarística; **Assembleia nunca é fonte de extração nem fallback**, pois as colunas compactas elevam o risco de leitura fora de ordem.
- **Limite:** no máximo `CONFERENCIA_MAX_ITER` (padrão: 3). Falha do mapa, de qualquer conferente ou da correção encerra o ciclo; a missa fica em `pendente_revisao`. Uma missa anteriormente concluída não é substituída por uma reprovada.

## Etapas e papéis

1. **Referência principal:** o mapa litúrgico lê apenas o PDF **Celular** e produz o contrato de conteúdo e hierarquia.
2. **Construtor:** a montagem multimodal produz o JSON da missa usando exclusivamente o PDF Celular e o mapa: seção, número, tipo, falante, texto, referência e postura.
3. **Críticos:** a primeira crítica recebe PDF Celular e JSON final; a segunda recebe PDF **Celebrante** e JSON, limitada a falas do presidente, rubricas, postura e Oração Eucarística. Ambas usam instrução e contexto próprios e não recebem o raciocínio da montagem. Uma camada determinística também compara, palavra a palavra, o conteúdo estruturado ao texto do PDF Celular.
4. **Gate:** qualquer divergência de conteúdo ou hierarquia retorna ao construtor. A publicação só é permitida com lista vazia. Qualquer indisponibilidade é reprovação técnica, nunca aprovação implícita.

## Escopo explícito

O gate não compara projeto editorial: capa, marcas, créditos, imagens, cores, tipografia, colunas, alinhamento, quebras ou números de página estão fora da métrica. Ele compara apenas textos litúrgicos, rubricas, referências, seções, blocos e sua ordem/hierarquia.

## Evidência e operação

O resultado fica em `revisao_json.conferencia`: `conferida`, `iteracoes`, custo, divergências restantes, fontes (URLs e hashes) e o `contrato` (objetivo, métrica, limite, papéis e escopo). Execute a suíte do backend antes de disponibilizar uma alteração:

```bash
backend/.venv/bin/python -m pytest backend/tests -q
```

Para uma edição específica, as referências são os PDFs arquivados em `backend/data/pdfs/archive/YYYY-MM-DD.pdf` (Celular) e `backend/data/pdfs/archive/YYYY-MM-DD-celebrante.pdf`; execute também o verificador de regressão, que devolve código não zero se uma âncora do golden estiver ausente:

```bash
backend/.venv/bin/python backend/scripts/verificar_regressao.py YYYY-MM-DD
```

O crítico não deve ser ignorado via configuração. Quando o provedor estiver indisponível, corrija a disponibilidade ou faça revisão humana; não publique fallback textual.

## Frontends

O painel de revisão mostra as divergências e bloqueia a ação de publicar enquanto houver crítica, não houver conferência aprovada ou o limite tiver sido atingido. O servidor repete essa regra e devolve `409` se alguém tentar contornar a interface. Antes de um release web, execute `npm --prefix web run typecheck`, `npm --prefix web test` e `npm --prefix web run build`.
