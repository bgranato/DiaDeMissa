import { describe, expect, it } from 'vitest'

import { conviteDeveAparecerAposPaiNosso } from './apoioLiturgia'

describe('convite de apoio na liturgia', () => {
  const blocos = [
    { titulo: 'Oração Eucarística', texto: '...' },
    { titulo: 'Rito da Comunhão', turnos: [{ falante: 'T', texto: 'Pai nosso... (O Presidente continua)' }] },
    { titulo: 'Canto de Comunhão', texto: '...' },
  ]

  it('não abre durante o Pai-Nosso', () => {
    expect(conviteDeveAparecerAposPaiNosso(blocos, 1)).toBe(false)
  })

  it('abre no bloco seguinte ao Pai-Nosso', () => {
    expect(conviteDeveAparecerAposPaiNosso(blocos, 2)).toBe(true)
  })

  it('não substitui a posição por uma numeração fixa quando não há Pai-Nosso', () => {
    expect(conviteDeveAparecerAposPaiNosso([{ titulo: 'Canto Final' }], 0)).toBe(false)
  })
})
