import '@testing-library/jest-dom/vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { AgradecimentoApoioModal } from './AgradecimentoApoioModal'

describe('AgradecimentoApoioModal', () => {
  it('agradece dentro do app e permite continuar', () => {
    const onClose = vi.fn()
    render(<AgradecimentoApoioModal onClose={onClose} />)

    expect(screen.getByRole('dialog', { name: /obrigado por cuidar do dia de missa/i })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /continuar no dia de missa/i }))
    expect(onClose).toHaveBeenCalledOnce()
  })
})
