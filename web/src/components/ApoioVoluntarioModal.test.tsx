import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApoioVoluntarioModal } from './ApoioVoluntarioModal'

const { apiGet } = vi.hoisted(() => ({ apiGet: vi.fn() }))

vi.mock('../services/api', () => ({
  default: { get: apiGet, post: vi.fn() },
}))

describe('ApoioVoluntarioModal', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiGet.mockResolvedValue({
      data: { ativo: true, valores_centavos: [300, 500, 1000, 1500], reexibir_em_dias: 1 },
    })
  })

  it('oferece os quatro valores e explica o impacto do apoio', async () => {
    render(<ApoioVoluntarioModal missaId={12} modo="manual" />)

    expect(await screen.findByText(/r\$\s?3,00/i)).toBeInTheDocument()
    expect(screen.getByText(/r\$\s?5,00/i)).toBeInTheDocument()
    expect(screen.getByText(/r\$\s?10,00/i)).toBeInTheDocument()
    expect(screen.getByText(/r\$\s?15,00/i)).toBeInTheDocument()
    expect(screen.getByText(/mais pessoas tenham acesso às liturgias/i)).toBeInTheDocument()
  })
})
