// Helpers PUROS de renderização de blocos litúrgicos — sem React, para serem
// testáveis isoladamente (Vitest) e reusados por vários componentes. Cada função
// corresponde a uma correção estrutural de renderização.

// A1 — Rubrica: o folheto às vezes já traz o texto entre parênteses. Não
// re-envolver (evita "((Momento de silêncio))"). Retorna o texto COM exatamente
// um par de parênteses.
export function rotuloRubrica(texto: string): string {
  const t = (texto || '').trim()
  if (t.startsWith('(') && t.endsWith(')') && t.length >= 2) return t
  return `(${t})`
}

// A3 — Ordem estrita: o renderer respeita o campo `ordem` da API e não reordena
// localmente. Ordenação estável por `ordem` (ausente = 0).
export function ordenarBlocos<T extends { ordem?: number | null }>(blocos: T[]): T[] {
  return [...blocos].sort((a, b) => (a.ordem ?? 0) - (b.ordem ?? 0))
}

// A4 — Título ≈ texto: quando o título do bloco é igual ou prefixo do texto
// (ignorando pontuação/caixa/acentos-espaços), o corpo apenas repete o título.
// Nesses casos exibimos só o texto, em estilo de rubrica (não duplicar).
export function tituloDuplicaTexto(titulo?: string | null, texto?: string | null): boolean {
  const norm = (s: string) =>
    (s || '')
      .toLowerCase()
      .replace(/[.,;:!?"'()\[\]]/g, '')
      .replace(/\s+/g, ' ')
      .trim()
  const t = norm(titulo || '')
  const x = norm(texto || '')
  if (!t || !x) return false
  return x === t || x.startsWith(t + ' ') || x === t
}

// A5 — Vivência: bloco cujo título é "Vivência" deve exibir o chip "L" (Leitor),
// decidido pelo TÍTULO no renderer (sem alterar o schema/dados).
export function ehVivencia(titulo?: string | null): boolean {
  return (titulo || '').trim().toLowerCase().startsWith('vivência') ||
         (titulo || '').trim().toLowerCase().startsWith('vivencia')
}

export interface DiaSemana {
  label: string
  santo: string
  refs: string
}

const DIA_ABREV: Record<string, string> = {
  '2ª-FEIRA': 'Seg', '3ª-FEIRA': 'Ter', '4ª-FEIRA': 'Qua',
  '5ª-FEIRA': 'Qui', '6ª-FEIRA': 'Sex', 'SÁBADO': 'Sáb', 'DOMINGO': 'Dom',
}

// A6 — Leituras da Semana: parser TOLERANTE. O folheto às vezes imprime o dia
// sem o número ("5ª-FEIRA:" em vez de "30/5ª-FEIRA:"), fazendo o dia seguinte
// grudar no anterior. Aqui o "NN/" é OPCIONAL: qualquer "Xª-FEIRA:"/"SÁBADO:"/
// "DOMINGO:" abre um novo dia; quando o número falta, é inferido do anterior +1.
export function parseLeiturasSemana(texto: string): DiaSemana[] | null {
  const re = /(?:(\d{1,2})\/)?(\d?ª-FEIRA|SÁBADO|DOMINGO):\s*/g
  const marcs: { idx: number; end: number; dia: string | null; rotulo: string }[] = []
  let m: RegExpExecArray | null
  let ultimoNum: number | null = null
  while ((m = re.exec(texto)) !== null) {
    let num: string | null = m[1] ?? null
    if (num === null && ultimoNum !== null) num = String(ultimoNum + 1)
    marcs.push({ idx: m.index, end: re.lastIndex, dia: num, rotulo: m[2] })
    if (num !== null) ultimoNum = Number(num)
  }
  if (marcs.length < 2) return null
  return marcs.map((mk, i) => {
    const fim = i + 1 < marcs.length ? marcs[i + 1].idx : texto.length
    const corpo = texto.slice(mk.end, fim).trim().replace(/;\s*$/, '')
    const ci = corpo.indexOf(':')
    const santo = ci > -1 ? corpo.slice(0, ci).trim() : corpo
    const refs = ci > -1 ? corpo.slice(ci + 1).trim() : ''
    const abrev = DIA_ABREV[mk.rotulo] || mk.rotulo
    const label = mk.dia ? `${abrev}. ${mk.dia}` : abrev
    return { label, santo, refs }
  })
}
