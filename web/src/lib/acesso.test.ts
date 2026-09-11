import { describe, expect, it } from 'vitest'

import { rotaExigeConta } from './acesso'

describe('acesso de visitante', () => {
  it('permite a missa já disponível sem login', () => {
    expect(rotaExigeConta('reading', false, true)).toBe(false)
    expect(rotaExigeConta('home', false, false)).toBe(false)
  })

  it('direciona o visitante ao cadastro para seções e quando não há missa disponível', () => {
    for (const destino of ['calendar', 'igrejas', 'oracoes', 'history']) {
      expect(rotaExigeConta(destino, false, false)).toBe(true)
    }
    expect(rotaExigeConta('reading', false, false)).toBe(true)
  })

  it('não impõe a barreira a uma conta autenticada', () => {
    expect(rotaExigeConta('calendar', true, false)).toBe(false)
    expect(rotaExigeConta('reading', true, false)).toBe(false)
  })
})
