import { describe, expect, it } from 'vitest'

import { conviteDeveAparecerNoCantoDasOfertas } from './apoioLiturgia'

describe('convite de apoio na liturgia', () => {
  const blocos = [
    { titulo: 'Sobre as Oferendas', texto: '...' },
    { titulo: 'Canto das Ofertas', texto: '...' },
    { titulo: 'Rito da Comunhão', turnos: [{ falante: 'T', texto: 'Pai nosso... (O Presidente continua)' }] },
  ]

  it('não abre antes de alcançar o Canto das Ofertas', () => {
    expect(conviteDeveAparecerNoCantoDasOfertas(blocos, 0)).toBe(false)
  })

  it('abre no bloco do Canto das Ofertas', () => {
    expect(conviteDeveAparecerNoCantoDasOfertas(blocos, 1)).toBe(true)
  })

  it('permanece aberto nos blocos seguintes (ex.: Rito da Comunhão)', () => {
    expect(conviteDeveAparecerNoCantoDasOfertas(blocos, 2)).toBe(true)
  })

  it('reconhece variação de título (Canto Ofertório)', () => {
    const comOfertorio = [
      { titulo: 'Canto de Entrada' },
      { titulo: 'Canto Ofertório' },
    ]
    expect(conviteDeveAparecerNoCantoDasOfertas(comOfertorio, 0)).toBe(false)
    expect(conviteDeveAparecerNoCantoDasOfertas(comOfertorio, 1)).toBe(true)
  })

  it('não substitui a posição por uma numeração fixa quando não há Canto das Ofertas', () => {
    expect(conviteDeveAparecerNoCantoDasOfertas([{ titulo: 'Canto Final' }], 0)).toBe(false)
  })
})