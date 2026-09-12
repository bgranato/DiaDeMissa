import '@testing-library/jest-dom/vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ApoioBanner } from './ApoioBanner'

describe('ApoioBanner', () => {
  it('explica o apoio de maneira direta e abre o fluxo ao clicar', () => {
    const onApoiar = vi.fn()
    render(<ApoioBanner onApoiar={onApoiar} />)

    expect(screen.getByText(/o dia de missa é gratuito/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /contribuir/i }))
    expect(onApoiar).toHaveBeenCalledOnce()
  })
})
