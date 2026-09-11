import { describe, expect, it } from 'vitest'

import { rotaExigeConta } from './acesso'

describe('acesso de visitante', () => {
  it('permite somente a missa da data atual sem login', () => {
    expect(rotaExigeConta('reading', false, true)).toBe(false)
    expect(rotaExigeConta('home', false, false)).toBe(false)
  })

  it('direciona o visitante ao cadastro para recursos pessoais e conteúdo fora do dia', () => {
    for (const destino of ['calendar', 'igrejas', 'oracoes', 'history', 'reading']) {
      expect(rotaExigeConta(destino, false, false)).toBe(true)
    }
  })

  it('não impõe a barreira a uma conta autenticada', () => {
    expect(rotaExigeConta('calendar', true, false)).toBe(false)
    expect(rotaExigeConta('reading', true, false)).toBe(false)
  })
})
