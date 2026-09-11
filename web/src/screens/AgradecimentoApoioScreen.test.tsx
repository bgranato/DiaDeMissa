import '@testing-library/jest-dom/vitest'
import type { ReactNode } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

vi.mock('../components/UI', () => ({
  LargeButton: ({ children, onClick }: { children: ReactNode; onClick: () => void }) => <button onClick={onClick}>{children}</button>,
}))

import { AgradecimentoApoioScreen } from './AgradecimentoApoioScreen'

describe('AgradecimentoApoioScreen', () => {
  it('agradece e devolve a pessoa ao início', () => {
    const onFinish = vi.fn()
    render(<AgradecimentoApoioScreen onFinish={onFinish} />)
    expect(screen.getByText(/obrigado por cuidar do dia de missa/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /voltar ao início/i }))
    expect(onFinish).toHaveBeenCalledOnce()
  })
})
