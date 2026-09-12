import '@testing-library/jest-dom/vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ApoioBanner } from './ApoioBanner'

describe('ApoioBanner', () => {
  it('explica o apoio de maneira direta e abre o fluxo ao clicar', () => {
    const onApoiar = vi.fn()
    render(<ApoioBanner onApoiar={onApoiar} />)

    expect(screen.getByText(/ajude a manter o dia de missa vivo/i)).toBeInTheDocument()
    expect(screen.getByText(/5, 10 ou 15 reais/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /faça sua doação/i }))
    expect(onApoiar).toHaveBeenCalledOnce()
  })
})
