import { describe, expect, it } from 'vitest'

import { destravarRolagem, travarRolagem } from './scrollLock'

/**
 * Reproduz a sequência que travava a página:
 * login (AuthScreens) trava o scroll → aviso do folheto (ReadingScreen) trava
 * o scroll capturando o valor já "hidden" do login → login desmonta e restaura
 * o overflow (desbloqueando de fato) → aviso fecha e restaura o valor obsoleto
 * "hidden" que capturou → página fica travada.
 */
describe('scrollLock (trava aninhada)', () => {
  it('restaura o overflow original quando a última referência é liberada', () => {
    document.body.style.overflow = ''
    document.documentElement.style.overflow = ''

    travarRolagem() // login
    travarRolagem() // aviso do folheto
    expect(document.body.style.overflow).toBe('hidden')

    destravarRolagem() // login desmonta (consumidor mais externo)
    // O aviso ainda está aberto: a página continua travada.
    expect(document.body.style.overflow).toBe('hidden')

    destravarRolagem() // aviso fecha — última referência
    expect(document.body.style.overflow).toBe('')
    expect(document.documentElement.style.overflow).toBe('')
  })

  it('respeita um overflow pré-existente da aplicação', () => {
    document.body.style.overflow = 'scroll'
    document.documentElement.style.overflow = 'auto'

    travarRolagem()
    expect(document.body.style.overflow).toBe('hidden')
    destravarRolagem()

    expect(document.body.style.overflow).toBe('scroll')
    expect(document.documentElement.style.overflow).toBe('auto')
  })

  it('é inofensivo destravar sem nenhuma trava ativa', () => {
    document.body.style.overflow = ''
    destravarRolagem()
    expect(document.body.style.overflow).toBe('')
  })
})