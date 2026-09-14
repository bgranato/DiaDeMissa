import '@testing-library/jest-dom/vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { HomeScreen } from './HomeScreen'

const { apiGet, getUltimaMissaDisponivel } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  getUltimaMissaDisponivel: vi.fn(),
}))

vi.mock('../services/api', () => ({
  default: { get: apiGet, post: vi.fn() },
}))

vi.mock('../services/missa', () => ({
  getUltimaMissaDisponivel,
}))

vi.mock('../services/igrejas', () => ({
  minhasIgrejas: vi.fn().mockResolvedValue([]),
  buscarIgrejas: vi.fn().mockResolvedValue([]),
}))

describe('HomeScreen — atalhos do cabeçalho', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiGet.mockResolvedValue({ data: { ativo: false } })
    getUltimaMissaDisponivel.mockReset()
    getUltimaMissaDisponivel.mockResolvedValue(null)
  })

  it('abre dicas e sugestões pelo ícone ao lado da acessibilidade', () => {
    const setScreen = vi.fn()
    render(<HomeScreen setScreen={setScreen} missa={null} nome="Visitante" estaAutenticado={false} />)

    expect(screen.getByRole('button', { name: 'Acessibilidade' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Dicas e sugestões' }))
    expect(setScreen).toHaveBeenCalledWith('feedback')
  })

  it('mantém minha conta e sair no menu aberto pela seta abaixo do avatar', () => {
    const setScreen = vi.fn()
    const onLogout = vi.fn()
    render(<HomeScreen setScreen={setScreen} missa={null} nome="Bruno" estaAutenticado onLogout={onLogout} />)

    fireEvent.click(screen.getByRole('button', { name: 'Abrir menu da conta' }))
    expect(screen.getByRole('button', { name: 'Minha conta' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sair' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Minha conta' }))
    expect(setScreen).toHaveBeenCalledWith('profile')
  })

  it('consulta a disponibilidade de apoio para exibir o convite somente quando habilitado', () => {
    render(<HomeScreen setScreen={() => {}} missa={null} nome="Visitante" estaAutenticado={false} />)

    expect(apiGet).toHaveBeenCalledWith('/apoios/configuracao')
    expect(screen.queryByText(/apoio voluntário/i)).not.toBeInTheDocument()
  })

  it('oferece ao visitante o cadastro para acessar a última missa quando não há missa pública', () => {
    const setScreen = vi.fn()
    render(<HomeScreen setScreen={setScreen} missa={null} nome="Visitante" estaAutenticado={false} />)

    fireEvent.click(screen.getByRole('button', { name: 'Entrar ou criar conta grátis' }))

    expect(setScreen).toHaveBeenCalledWith('reading')
    expect(screen.getByText('A última missa está no acervo. Entre ou crie sua conta grátis para acessá-la.')).toBeInTheDocument()
    expect(screen.getByText(/Hoje há missa\. O Dia de Missa publica apenas as celebrações de domingos e solenidades/i)).toBeInTheDocument()
  })

  it('abre diretamente a última missa para quem já está autenticado', async () => {
    const setScreen = vi.fn()
    getUltimaMissaDisponivel.mockResolvedValue({ id: 42, data: '2026-09-13', celebracao: '24º Domingo', categoria: 'Domingo' })
    render(<HomeScreen setScreen={setScreen} missa={null} nome="Bruno" estaAutenticado />)

    fireEvent.click(await screen.findByRole('button', { name: /Ver missa do dia 13\/09\/2026/i }))

    expect(localStorage.getItem('@missa_data_alvo')).toBe('2026-09-13')
    expect(setScreen).toHaveBeenCalledWith('reading')
  })
})
