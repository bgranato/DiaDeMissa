# Mini-Gate 7 — Conectar UI ao pipeline (uma tela só)

> Cole este prompt como mensagem para o DeepSeek. Substitui temporariamente o debug-postura.

---

## Contexto

Estado atual:
- Pipeline: 44/54 verdes (Fase A concluída)
- UI: ainda não foi tocada, está rodando código antigo de antes do reset

A tela atual do app mostra texto bruto contaminado (`/`, `**Antífona:**`, `AleQue`, créditos vazando) mesmo com o pipeline produzindo JSON limpo. Isso porque a UI **não está consumindo o pipeline novo**.

Antes de avançar para Fase B (Ato Penitencial, Leituras) ou debug de postura, vamos provar visualmente que o pipeline funciona. Conecte **uma tela só** — o Canto de Entrada — ao pipeline. Quando isso estiver renderizando corretamente, retomamos a expansão do parser.

---

## Escopo (rigorosamente limitado)

Você vai fazer **apenas** o que está nesta lista:

1. Criar um endpoint HTTP que retorne o `Missa` estruturado.
2. Criar **um único componente** `<Canto>` que consuma esse endpoint.
3. Renderizar **apenas** a tela do Canto de Entrada (bloco com `ordem == 1`).

**Não vai fazer:**
- Não toque em outros componentes (Saudação, Antífona, Leitura).
- Não tente "consertar" a tela de Saudação ou Ato Penitencial.
- Não expanda o parser para novos blocos.
- Não toque no debug de postura.

Foco cirúrgico. Uma tela. Renderizada de verdade.

---

## Passo 1 — Endpoint da API

Crie `backend/app/api/main.py` (ou onde for apropriado para a stack do projeto). Use FastAPI:

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.pipeline import processar_pdf

app = FastAPI()

# CORS aberto para desenvolvimento local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PDF_PADRAO = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures" / "amissa_ascensao_2026.pdf"


@app.get("/missa/atual")
def missa_atual():
    """Retorna a Missa estruturada da fixture atual (Ascensão 2026)."""
    try:
        missa = processar_pdf(PDF_PADRAO)
        return missa.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar PDF: {e}")
```

Crie um teste em `tests/test_api.py`:

```python
from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)


def test_endpoint_missa_atual_retorna_json_valido():
    response = client.get("/missa/atual")
    assert response.status_code == 200
    data = response.json()
    assert data["titulo_celebracao"] == "Ascensão do Senhor"
    assert data["blocos"][0]["tipo"] == "canto"
    assert data["blocos"][0]["postura"] == "de_pe"


def test_endpoint_retorna_canto_entrada_limpo():
    response = client.get("/missa/atual")
    canto = response.json()["blocos"][0]
    refrao = canto["refrao"]
    # Nenhum verso pode conter artefatos
    for verso in refrao:
        assert "/" not in verso
        assert "REFRÃO" not in verso
        assert "Ale-luia" not in verso
    # 4 estrofes
    assert len(canto["estrofes"]) == 4
```

Rode os testes da API. Devem passar (já que o pipeline está 44/54).

---

## Passo 2 — Componente `<Canto>` consumindo o endpoint

Como ainda não sei o framework de UI que você está usando, identifique no projeto e crie o componente apropriado. Se for:

- **React/Next.js:** crie `frontend/components/Canto.tsx` (ou `.jsx`)
- **React Native:** crie `mobile/components/Canto.tsx`
- **Flutter:** crie `lib/widgets/canto.dart`
- **Vue:** crie `frontend/components/Canto.vue`

**Identifique a stack inspecionando `package.json`, `pubspec.yaml`, ou estrutura de pastas. Não invente.**

### Especificação do componente (independente do framework)

O componente recebe um objeto `Canto` do schema e renderiza assim:

```
┌─────────────────────────────────────────┐
│ CANTO 1 DE 20            [🧍 De pé]    │  ← header com chip de postura
│                                         │
│ Canto de Entrada                        │  ← título serifado, com barra dourada à esquerda
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ REFRÃO                              │ │  ← bloco refrão destacado
│ │ O Senhor foi preparar               │ │
│ │ um lugar para nós no céu.           │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ (1) ESTROFE                         │ │  ← cada estrofe em card próprio
│ │     Ó varões galileus, que estais   │ │     com badge numérico
│ │     no céu a olhar? Aleluia!        │ │
│ │     O Jesus que subiu ao céu deve,  │ │
│ │     depois voltar! Aleluia!         │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ (2) ESTROFE                         │ │
│ │     ...                             │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ (3) ESTROFE  ...                        │
│ (4) ESTROFE  ...                        │
└─────────────────────────────────────────┘
```

### Regras de renderização inegociáveis

1. **Cada verso é uma linha independente** no JSX/Widget. Use `<div>` separados, ou `<p>` separados, ou `Text` widgets separados. **Nunca** concatene versos com `/`, vírgula, ou espaço.

2. **Número da estrofe vem do índice do array, não da string.** `{estrofes.map((estrofe, i) => <Estrofe numero={i + 1} />)}`.

3. **Postura é um chip visual, não texto.** Receba `canto.postura` (`"de_pe"`, `"sentado"`, `"ajoelhado"`) e mapeie para um label visual ("De pé", "Sentado", "Ajoelhado") + ícone.

4. **Zero string manipulation no componente.** Se você se pegar escrevendo `.replace()`, `.split()`, `.trim()` em qualquer string vinda da API, **PARE**. O JSON da API já está limpo. Qualquer manipulação no componente significa que você está corrigindo bug do pipeline no lugar errado.

### Exemplo (React/TypeScript) — adapte para sua stack

```tsx
// frontend/components/Canto.tsx
import { useEffect, useState } from 'react';

type Canto = {
  tipo: 'canto';
  ordem: number;
  titulo: string;
  postura: 'de_pe' | 'sentado' | 'ajoelhado' | null;
  refrao: string[];
  estrofes: string[][];
};

const POSTURA_LABEL: Record<string, string> = {
  de_pe: 'De pé',
  sentado: 'Sentado',
  ajoelhado: 'Ajoelhado',
};

export function CantoView() {
  const [canto, setCanto] = useState<Canto | null>(null);

  useEffect(() => {
    fetch('http://localhost:8000/missa/atual')
      .then((r) => r.json())
      .then((missa) => {
        const primeiro = missa.blocos.find((b: any) => b.tipo === 'canto');
        setCanto(primeiro);
      });
  }, []);

  if (!canto) return <div>Carregando...</div>;

  return (
    <article className="canto">
      <header>
        <span className="ordem">CANTO {canto.ordem} DE 20</span>
        {canto.postura && (
          <span className="chip-postura">{POSTURA_LABEL[canto.postura]}</span>
        )}
      </header>

      <h1 className="titulo">{canto.titulo}</h1>

      <section className="refrao">
        <span className="label">REFRÃO</span>
        {canto.refrao.map((verso, i) => (
          <p key={i} className="verso">{verso}</p>
        ))}
      </section>

      {canto.estrofes.map((estrofe, idx) => (
        <section key={idx} className="estrofe">
          <span className="numero">{idx + 1}</span>
          <span className="label">ESTROFE</span>
          {estrofe.map((verso, i) => (
            <p key={i} className="verso">{verso}</p>
          ))}
        </section>
      ))}
    </article>
  );
}
```

CSS mínimo para validar visualmente (depois você refina):

```css
.canto { max-width: 480px; margin: 0 auto; padding: 1.5rem; font-family: serif; }
.ordem { font-size: 11px; letter-spacing: 0.1em; color: #b8860b; }
.chip-postura { float: right; background: #f5f0e0; padding: 4px 12px; border-radius: 999px; font-size: 12px; }
.titulo { font-size: 24px; border-left: 4px solid #b8860b; padding-left: 12px; margin: 16px 0 24px; }
.refrao { background: #fff8e1; padding: 16px; border-left: 4px solid #b8860b; margin-bottom: 16px; border-radius: 4px; }
.refrao .label { font-size: 11px; color: #b8860b; letter-spacing: 0.1em; display: block; margin-bottom: 8px; }
.estrofe { background: white; border: 1px solid #eee; padding: 16px; margin-bottom: 12px; border-radius: 4px; position: relative; }
.estrofe .numero { display: inline-block; width: 24px; height: 24px; border-radius: 50%; background: #f0f0f0; text-align: center; line-height: 24px; font-size: 12px; margin-right: 8px; }
.estrofe .label { font-size: 11px; color: #999; letter-spacing: 0.1em; }
.verso { margin: 4px 0; line-height: 1.5; }
```

---

## Passo 3 — Verificação visual

Rode dois processos:

```bash
# Terminal 1 — backend
cd backend
uvicorn app.api.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev
```

Abra o navegador na rota da CantoView. **Tire um print da tela renderizada** e salve em:

```
reports/assets/2026-05-12_mini-gate-7_canto-renderizado.png
```

---

## Critério de aceitação visual

A tela renderizada **deve** ter:

- ✅ Chip "De pé" no topo direito (não texto inline)
- ✅ Título "Canto de Entrada" em fonte serifada, com barra dourada à esquerda
- ✅ Bloco "REFRÃO" destacado com 2 versos em linhas separadas
- ✅ 4 cards de estrofe, cada um com badge numérico (1, 2, 3, 4)
- ✅ Cada verso de estrofe em linha separada (8 versos visíveis no total)

A tela renderizada **não pode** ter:

- ❌ Caractere `/` em nenhum lugar
- ❌ Texto `REFRÃO:` como prefixo de algum verso
- ❌ Palavra `Ale-luia` ou `AleQue`
- ❌ Texto `Entrada: José Alves;` misturado na letra
- ❌ Texto `(De pé)` em vez do chip
- ❌ "Indicação de postura como string"

---

## Protocolo de relatório

Crie `reports/<timestamp>_mini-gate-7-canto-renderizado.md` com:

1. Output dos testes (`pytest tests/test_api.py -v`)
2. Print da tela renderizada (caminho do arquivo salvo em assets)
3. Lista dos critérios visuais — marcar ✅ ou ❌ para cada um
4. Arquivos criados/modificados (endpoint, componente, CSS, testes)
5. Diagnóstico se algo não bateu

Atualize `INDEX.md` adicionando linha do mini-gate-7.

Responda no chat com path do relatório + path do print + 3 linhas de resumo.

---

## Regra de ouro

Se ao tentar renderizar você se vir tentado a fazer `texto.replace("/", "")` ou `texto.split("/")` no componente, **PARE IMEDIATAMENTE**. Isso significa que o JSON da API ainda está contaminado. Nesse caso:

1. Não conserte no componente.
2. Crie um teste no `test_api.py` que prove a contaminação (assert que o `/` está no JSON).
3. Reporte como bloqueio. Eu te ajudo a debugar o pipeline.

A premissa do mini-Gate 7 é: **o JSON da API está limpo**. Se não estiver, é regressão do pipeline, e prefiro descobrir agora que disfarçar no CSS.

---

## Após o mini-Gate 7

Quando esse relatório voltar com print mostrando o Canto de Entrada renderizado corretamente, **retomamos** a sequência original:

- Debug do `(De pé)` (descobrir onde está sendo perdido no pipeline)
- Fase B (implementar parsers de Ato Penitencial e Leituras)
- Gate 7 completo (renderizar todos os tipos de bloco)

Boa renderização.
