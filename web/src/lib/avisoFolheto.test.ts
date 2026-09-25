import { describe, expect, it } from 'vitest'

import { deveExibirAvisoFolheto } from './avisoFolheto'

describe('aviso do folheto litúrgico', () => {
  it('aparece na primeira entrada, quando ainda não foi fechado', () => {
    expect(deveExibirAvisoFolheto(null)).toBe(true)
  })

  it('aparece sempre que entra numa missa (saiu e voltou, o aviso abre novamente)', () => {
    expect(deveExibirAvisoFolheto(String(Date.now()))).toBe(true)
    expect(deveExibirAvisoFolheto(String(Date.now() - 1000))).toBe(true)
    expect(deveExibirAvisoFolheto(String(Date.now() - 60 * 60 * 1000))).toBe(true)
  })
})