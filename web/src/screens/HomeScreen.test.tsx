import '@testing-library/jest-dom/vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { HomeScreen } from './HomeScreen'

const { apiGet } = vi.hoisted(() => ({ apiGet: vi.fn() }))

vi.mock('../services/api', () => ({
  default: { get: apiGet, post: vi.fn() },
}))

vi.mock('../services/missa', () => ({
  getUltimaMissaDisponivel: vi.fn().mockResolvedValue(null),
}))

vi.mock('../services/igrejas', () => ({
  minhasIgrejas: vi.fn().mockResolvedValue([]),
  buscarIgrejas: vi.fn().mockResolvedValue([]),
}))

describe('HomeScreen — atalhos do cabeçalho', () => {
  beforeEach(() => {
    apiGet.mockResolvedValue({ data: { ativo: false } })
  })

  it('abre dicas e sugestões pelo ícone ao lado da acessibilidade', async () => {
    const setScreen = vi.fn()
    render(<HomeScreen setScreen={setScreen} missa={null} nome="Visitante" estaAutenticado={false} />)
    await waitFor(() => expect(apiGet).toHaveBeenCalled())

    expect(screen.getByRole('button', { name: 'Acessibilidade' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Dicas e sugestões' }))
    expect(setScreen).toHaveBeenCalledWith('feedback')
  })

  it('mantém minha conta e sair no menu aberto pela seta abaixo do avatar', async () => {
    const setScreen = vi.fn()
    const onLogout = vi.fn()
    render(<HomeScreen setScreen={setScreen} missa={null} nome="Bruno" estaAutenticado onLogout={onLogout} />)
    await waitFor(() => expect(apiGet).toHaveBeenCalled())

    fireEvent.click(screen.getByRole('button', { name: 'Abrir menu da conta' }))
    expect(screen.getByRole('button', { name: 'Minha conta' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sair' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Minha conta' }))
    expect(setScreen).toHaveBeenCalledWith('profile')
  })
})
