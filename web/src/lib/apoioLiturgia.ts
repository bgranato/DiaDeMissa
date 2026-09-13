type BlocoComConteudo = {
  titulo?: unknown
  texto?: unknown
  descricao?: unknown
  turnos?: unknown
}

function normalizar(texto: string) {
  return texto
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/gi, ' ')
    .toLocaleLowerCase('pt-BR')
}

function textoDoBloco(bloco: BlocoComConteudo) {
  const turnos = Array.isArray(bloco.turnos)
    ? bloco.turnos.map(turno => typeof turno === 'object' && turno !== null && 'texto' in turno
      ? String((turno as { texto?: unknown }).texto || '')
      : '')
    : []
  return [bloco.titulo, bloco.texto, bloco.descricao, ...turnos]
    .filter(valor => typeof valor === 'string')
    .join(' ')
}

/** O convite só nasce depois que o bloco que contém o Pai-Nosso foi concluído. */
export function conviteDeveAparecerAposPaiNosso(blocos: BlocoComConteudo[], indiceAtual: number) {
  const indicePaiNosso = blocos.findIndex(bloco => normalizar(textoDoBloco(bloco)).includes('pai nosso'))
  return indicePaiNosso >= 0 && indiceAtual > indicePaiNosso
}
