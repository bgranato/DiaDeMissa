import { afterEach, describe, expect, it, vi } from 'vitest'

import { conviteApoioEmPausa, pausarConviteApoioAposPagamento } from './apoioExibicao'

describe('pausa do convite de apoio', () => {
  afterEach(() => {
    localStorage.clear()
    vi.useRealTimers()
  })

  it('dura 1 hora somente quando registrada após pagamento aprovado', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-09-11T12:00:00Z'))

    expect(conviteApoioEmPausa()).toBe(false)
    pausarConviteApoioAposPagamento()
    expect(conviteApoioEmPausa()).toBe(true)

    vi.advanceTimersByTime(60 * 60 * 1000)
    expect(conviteApoioEmPausa()).toBe(false)
  })

  it('remove toda pausa legada sem a marca de pagamento confirmado', () => {
    localStorage.setItem('@dia_de_missa_apoio_reexibir_em', String(Date.now() + 30 * 24 * 60 * 60 * 1000))

    expect(conviteApoioEmPausa()).toBe(false)
    expect(localStorage.getItem('@dia_de_missa_apoio_reexibir_em')).toBeNull()
  })

  it('não considera como pagamento uma pausa sem a origem registrada', () => {
    localStorage.setItem('@dia_de_missa_apoio_reexibir_em', String(Date.now() + 60 * 60 * 1000))

    expect(conviteApoioEmPausa()).toBe(false)
    expect(localStorage.getItem('@dia_de_missa_apoio_reexibir_em')).toBeNull()
  })
})
