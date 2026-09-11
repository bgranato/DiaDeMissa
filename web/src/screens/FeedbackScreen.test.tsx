import '@testing-library/jest-dom/vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

const { post } = vi.hoisted(() => ({ post: vi.fn() }))
vi.mock('../services/api', () => ({ default: { post } }))
vi.mock('../components/UI', () => ({
  AppHeader: ({ title }: { title: string }) => <h1>{title}</h1>,
  Card: ({ children }: { children: ReactNode }) => <section>{children}</section>,
  LargeButton: ({ children, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) => <button {...props}>{children}</button>,
}))

import { FeedbackScreen } from './FeedbackScreen'

describe('FeedbackScreen', () => {
  it('envia sugestão pública e confirma o recebimento', async () => {
    post.mockResolvedValueOnce({ data: { id: 1 } })
    render(<FeedbackScreen onBack={vi.fn()} telaOrigem="home" />)

    fireEvent.change(screen.getByRole('textbox', { name: /qual é a sua ideia/i }), {
      target: { value: 'Gostaria de ver a oração do dia na tela inicial.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /enviar mensagem/i }))

    await waitFor(() => expect(post).toHaveBeenCalledWith('/feedback', expect.objectContaining({
      tipo: 'sugestao', tela: 'home',
    })))
    expect(await screen.findByText(/mensagem recebida/i)).toBeInTheDocument()
  })
})
