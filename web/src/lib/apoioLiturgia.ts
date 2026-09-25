type BlocoComConteudo = {
  titulo?: unknown
}

function normalizar(texto: string) {
  return texto
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/gi, ' ')
    .toLocaleLowerCase('pt-BR')
}

/**
 * O convite nasce quando o leitor alcança o bloco do Canto das Ofertas — o
 * momento litúrgico em que a comunidade faz sua oferta — e permanece montado
 * até uma decisão explícita. A referência é o TÍTULO do bloco (variações como
 * "Canto das Ofertas", "Canto Ofertório" ou "Canto das Oferendas" são
 * contempladas pela raiz "ofert"), não a numeração: edições diferentes do
 * folheto podem numerar a sequência de outra forma.
 */
export function conviteDeveAparecerNoCantoDasOfertas(blocos: BlocoComConteudo[], indiceAtual: number) {
  const indiceCantoDasOfertas = blocos.findIndex(bloco => {
    const titulo = normalizar(String(bloco.titulo ?? ''))
    return titulo.includes('canto') && titulo.includes('ofert')
  })
  return indiceCantoDasOfertas >= 0 && indiceAtual >= indiceCantoDasOfertas
}
