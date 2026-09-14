import { describe, expect, it } from 'vitest'

import { deveExibirAvisoFolheto, PAUSA_AVISO_FOLHETO_MS } from './avisoFolheto'

describe('aviso do folheto litúrgico', () => {
  const agora = 1_800_000_000_000

  it('aparece na primeira entrada, quando ainda não foi fechado', () => {
    expect(deveExibirAvisoFolheto(null, agora)).toBe(true)
  })

  it('não reaparece numa nova entrada antes de completar 15 minutos', () => {
    expect(deveExibirAvisoFolheto(String(agora - PAUSA_AVISO_FOLHETO_MS + 1), agora)).toBe(false)
  })

  it('pode aparecer novamente numa nova entrada após 15 minutos', () => {
    expect(deveExibirAvisoFolheto(String(agora - PAUSA_AVISO_FOLHETO_MS), agora)).toBe(true)
  })
})
