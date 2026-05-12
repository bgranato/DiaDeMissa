# PARSER.md

## Funcionamento do Parser

O parser litúrgico transforma o PDF bruto em blocos litúrgicos estruturados.  
Opera em 4 camadas independentes:

```
PDF → [pdf_parser] → Texto bruto com coordenadas
    → [liturgical_parser] → Segmentos limpos com títulos
    → [block_classifier] → Blocos classificados com tipo litúrgico
    → [mass_processor] → Orquestração e persistência
```

## Camada 1: pdf_parser

**Arquivo**: `backend/app/services/pdf_parser.py`

**Responsabilidade**: Extrair texto bruto do PDF preservando informações posicionais.

**Biblioteca**: `pdfplumber`

**Estratégia**:
1. Abrir PDF com `pdfplumber.open()`
2. Iterar por cada página
3. Extrair texto com `page.extract_text()`
4. Preservar metadados: número da página, coordenadas (x_top, y_top)
5. Retornar lista de `PageText(text, page_number, x, y)`

**Riscos**:
- PDF protegido por senha (improvável; bloquear com erro claro)
- PDF escaneado/imagem (verificar se há texto extraível)
- PDF vazio ou corrompido

## Camada 2: liturgical_parser

**Arquivo**: `backend/app/services/liturgical_parser.py`

**Responsabilidade**: Limpar o texto bruto, separar blocos, identificar títulos e referências bíblicas.

### Limpeza

1. Remover cabeçalhos repetidos (nome do folheto, data, numeração)
2. Remover rodapés (endereço da paróquia, telefone, etc.)
3. Remover numeração de páginas
4. Remover linhas em branco excessivas
5. Normalizar espaçamento (simples entre palavras)
6. Remover caracteres não-imprimíveis

### Separação de Blocos

Heurísticas para identificar início de novo bloco litúrgico:

1. **Linha em maiúsculas** com comprimento entre 10 e 60 caracteres → provável título
2. **Referência bíblica** detectada por padrão regex: `^[A-Z][a-záéíóúçãõê]+ \d+[,.-]?` → leitura/salmo/evangelho
3. **Número romano** isolado → possível salmo ou canto
4. **Linha curta centralizada** → título ou subtítulo
5. **Texto após linha em branco + título** → conteúdo do bloco

### Identificação de Referências Bíblicas

Padrão regex para detectar citações:

```
^([A-Z][a-záéíóúçãõê]+)\s(\d+)[,:](\d+)([,-](\d+))?
```

Exemplos:
- `At 13,14.43-52`
- `Jo 10,1-10`
- `Sl 99(100)`

### Ordenação

Os blocos seguem a sequência canônica da missa (rito romano).  
A ordenação é feita por:
1. Posição no texto (fallback)
2. Tipo litúrgico identificado (ordem canônica)
3. Heurística de transição (ex: "Primeira Leitura" sempre vem depois de "Oração do Dia")

## Camada 3: block_classifier

**Arquivo**: `backend/app/services/block_classifier.py`

**Responsabilidade**: Classificar cada bloco extraído em um tipo litúrgico.

### Estratégia

1. **Correspondência exata do título** (tabela de equivalências)
2. **Correspondência parcial** (palavras-chave no título)
3. **Correspondência contextual** (conteúdo do bloco)
4. **Fallback por posição** na sequência canônica

### Tabela de Equivalências

```python
TITLE_TO_TYPE = {
    "CANTO DE ENTRADA": "canto_entrada",
    "ANTÍFONA DE ENTRADA": "antifona_entrada",
    "SAUDAÇÃO INICIAL": "saudacao_inicial",
    "ATO PENITENCIAL": "ato_penitencial",
    "GLÓRIA": "gloria",
    "ORAÇÃO DO DIA": "oracao_dia",
    "PRIMEIRA LEITURA": "primeira_leitura",
    "SEGUNDA LEITURA": "segunda_leitura",
    "SALMO RESPONSORIAL": "salmo_responsorial",
    "SEQUÊNCIA": "sequencia",
    "ACLAMAÇÃO AO EVANGELHO": "aclamação_evangelho",
    "EVANGELHO": "evangelho",
    "HOMILIA": "homilia",
    "PROFISSÃO DE FÉ": "profissao_fe",
    "PRECES DA COMUNIDADE": "preces_comunidade",
    "OFERTÓRIO": "ofertorio",
    "SANTO": "santo",
    "ORAÇÃO EUCARÍSTICA": "oracao_eucaristica",
    "PAI NOSSO": "pai_nosso",
    "CORDEIRO DE DEUS": "cordeiro_deus",
    "COMUNHÃO": "comunhao",
    "ORAÇÃO PÓS-COMUNHÃO": "oracao_pos_comunhao",
    "AVISOS": "avisos",
    "BÊNÇÃO FINAL": "bencao_final",
    "CANTO FINAL": "canto_final",
}
```

### Palavras-chave para Correspondência Parcial

Quando o título não corresponde exatamente, buscar palavras-chave:

```python
KEYWORD_MAP = {
    "entrada": "canto_entrada",        # "Canto de Entrada" ou "Canto de entrada"
    "penitencial": "ato_penitencial",
    "glória": "gloria",
    "leitura": None,                    # Preciso da posição para saber 1ª ou 2ª
    "salmo": "salmo_responsorial",
    "evangelho": "evangelho",
    "homilia": "homilia",
    "ofertório": "ofertorio",
    "comunhão": "comunhao",
    "comunhao": "comunhao",
    "abenção": "bencao_final",
    "bênção": "bencao_final",
}
```

### Ordem Canônica

```python
CANONICAL_ORDER = [
    "canto_entrada",
    "antifona_entrada",
    "saudacao_inicial",
    "ato_penitencial",
    "gloria",
    "oracao_dia",
    "primeira_leitura",
    "salmo_responsorial",
    "segunda_leitura",
    "sequencia",
    "aclamação_evangelho",
    "evangelho",
    "homilia",
    "profissao_fe",
    "preces_comunidade",
    "ofertorio",
    "santo",
    "oracao_eucaristica",
    "pai_nosso",
    "cordeiro_deus",
    "comunhao",
    "oracao_pos_comunhao",
    "avisos",
    "bencao_final",
    "canto_final",
]
```

## Camada 4: mass_processor

**Arquivo**: `backend/app/services/mass_processor.py`

**Responsabilidade**: Orquestrar download, parsing e salvamento no banco.

### Fluxo

```python
def process_mass():
    1. Verificar se já existe missa para hoje
    2. Baixar PDF via pdf_downloader
    3. Calcular hash SHA-256
    4. Comparar com hash existente
    5. Se diferente:
        a. Extrair texto com pdf_parser
        b. Limpar e segmentar com liturgical_parser
        c. Classificar blocos com block_classifier
        d. Ordenar blocos
        e. Persistir missa e blocos no banco
        f. Retornar JSON estruturado
    6. Se igual:
        a. Retornar missa existente do banco
```

## Riscos Conhecidos

1. **PDF muda de formato**: se a Arquidiocese alterar a estrutura do PDF, o parser pode quebrar. Solução: monitoramento e logs de falha.
2. **Bloco não classificado**: blocos que não correspondem a nenhum tipo conhecido são marcados como `tipo: "desconhecido"` e mantidos visíveis.
3. **Título ausente**: se o título não for detectado, o parser usa o conteúdo do bloco para inferir o tipo.
4. **Mesmo dia, PDF diferente**: pode acontecer do PDF ser atualizado após o processamento. O hash check detecta e reprocessa.
5. **Caracteres especiais**: acentos e caracteres latinos extras devem ser preservados.
6. **Texto em colunas**: o PDF pode usar layout de 2 colunas. O `pdfplumber` extrai sequencialmente, o que pode misturar conteúdo. Solução: extrair palavra por palavra com coordenadas e reagrupar por posição horizontal.

## Ambiente de Teste

O parser deve ser testado com:
- PDF real baixado da fonte oficial
- PDFs de dias diferentes (variação de estrutura)
- PDF com blocos incompletos
- Texto com ruídos intencionais
