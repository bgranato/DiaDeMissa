import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  buscarIgrejas: vi.fn(),
  localizarEndereco: vi.fn(),
}))

vi.mock('../components/UI', () => ({
  AppHeader: () => null,
  Card: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))
vi.mock('../services/igrejas', () => ({
  buscarIgrejas: mocks.buscarIgrejas,
  localizarEndereco: mocks.localizarEndereco,
  minhasIgrejas: vi.fn().mockResolvedValue([]),
  favoritarIgreja: vi.fn(),
  desfavoritarIgreja: vi.fn(),
}))

import { IgrejasScreen } from './IgrejasScreen'

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(r => { resolve = r })
  return { promise, resolve }
}

describe('IgrejasScreen — Próximas', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    mocks.buscarIgrejas.mockResolvedValue([])
  })

  it('descarta endereço com raio antigo quando o raio é trocado durante a geocodificação', async () => {
    const primeira = deferred<{ lat: number; lng: number }>()
    const segunda = deferred<{ lat: number; lng: number }>()
    mocks.localizarEndereco.mockReturnValueOnce(primeira.promise).mockReturnValueOnce(segunda.promise)

    render(<IgrejasScreen setScreen={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Próximas' }))
    fireEvent.click(screen.getByRole('button', { name: 'Informar endereço' }))
    const campoEndereco = await screen.findByPlaceholderText('Ex.: Rua ou bairro, cidade')
    fireEvent.change(campoEndereco, { target: { value: 'Leblon, Rio de Janeiro' } })
    fireEvent.click(screen.getByRole('button', { name: 'Usar' }))
    fireEvent.click(screen.getByRole('button', { name: '10 km' }))

    await act(async () => {
      primeira.resolve({ lat: -22.9848, lng: -43.2245 })
      await Promise.resolve()
    })
    expect(mocks.buscarIgrejas).not.toHaveBeenCalled()

    await act(async () => {
      segunda.resolve({ lat: -22.9848, lng: -43.2245 })
      await Promise.resolve()
    })
    await waitFor(() => expect(mocks.buscarIgrejas).toHaveBeenCalledWith(
      { lat: -22.9848, lng: -43.2245, raio_km: 10 },
      expect.any(AbortSignal),
    ))
    expect(mocks.buscarIgrejas).toHaveBeenCalledTimes(1)
  })

  it('usa o raio selecionado ao enviar um endereço pelo botão', async () => {
    mocks.localizarEndereco.mockResolvedValue({ lat: -22.9848, lng: -43.2245 })

    render(<IgrejasScreen setScreen={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Próximas' }))
    fireEvent.click(screen.getByRole('button', { name: 'Informar endereço' }))
    const campoEndereco = await screen.findByPlaceholderText('Ex.: Rua ou bairro, cidade')
    fireEvent.change(campoEndereco, { target: { value: 'Leblon, Rio de Janeiro' } })
    fireEvent.click(screen.getByRole('button', { name: 'Usar' }))

    await waitFor(() => expect(mocks.buscarIgrejas).toHaveBeenCalledWith(
      { lat: -22.9848, lng: -43.2245, raio_km: 5 },
      expect.any(AbortSignal),
    ))
  })

  it('usa o raio numérico selecionado ao clicar em usar minha localização', async () => {
    const getCurrentPosition = vi.fn((sucesso: PositionCallback) => {
      sucesso({ coords: { latitude: -22.9848, longitude: -43.2245 } } as GeolocationPosition)
    })
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: { getCurrentPosition },
    })

    render(<IgrejasScreen setScreen={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Próximas' }))
    fireEvent.click(screen.getByRole('button', { name: 'Minha localização' }))
    fireEvent.click(screen.getByRole('button', { name: '3 km' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Usar minha localização' }))

    await waitFor(() => expect(mocks.buscarIgrejas).toHaveBeenCalledWith(
      { lat: -22.9848, lng: -43.2245, raio_km: 3 },
      expect.any(AbortSignal),
    ))
    expect(getCurrentPosition).toHaveBeenCalledOnce()
  })

  it('cancela a busca por endereço e descarta a resposta que chegar depois', async () => {
    const pendente = deferred<{ lat: number; lng: number }>()
    mocks.localizarEndereco.mockReturnValueOnce(pendente.promise)

    render(<IgrejasScreen setScreen={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Próximas' }))
    fireEvent.click(screen.getByRole('button', { name: 'Informar endereço' }))
    const campoEndereco = await screen.findByPlaceholderText('Ex.: Rua ou bairro, cidade')
    fireEvent.change(campoEndereco, { target: { value: 'Leblon, Rio de Janeiro' } })
    fireEvent.click(screen.getByRole('button', { name: 'Usar' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Cancelar busca' }))

    await act(async () => {
      pendente.resolve({ lat: -22.9848, lng: -43.2245 })
      await Promise.resolve()
    })

    expect(mocks.buscarIgrejas).not.toHaveBeenCalled()
    expect(screen.getByText('Busca cancelada.')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Cancelar busca' })).toBeNull()
  })

  it('aborta o catálogo e não renderiza o resultado tardio depois do cancelamento', async () => {
    const catalogoPendente = deferred<Array<Record<string, unknown>>>()
    let sinalCatalogo: AbortSignal | undefined
    mocks.localizarEndereco.mockResolvedValue({ lat: -22.9848, lng: -43.2245 })
    mocks.buscarIgrejas.mockImplementation((_params: unknown, signal?: AbortSignal) => {
      sinalCatalogo = signal
      return catalogoPendente.promise
    })

    render(<IgrejasScreen setScreen={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Próximas' }))
    fireEvent.click(screen.getByRole('button', { name: 'Informar endereço' }))
    fireEvent.change(await screen.findByPlaceholderText('Ex.: Rua ou bairro, cidade'), { target: { value: 'Leblon, Rio de Janeiro' } })
    fireEvent.click(screen.getByRole('button', { name: 'Usar' }))
    await waitFor(() => expect(sinalCatalogo).toBeDefined())

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar busca' }))
    expect(sinalCatalogo?.aborted).toBe(true)

    await act(async () => {
      catalogoPendente.resolve([{ id: 101, nome: 'Paróquia tardia', endereco: null, cidade: null, estado: null, cep: null, telefone: null, site: null, lat: null, lng: null, observacoes: null, horarios_missa: null, data_criacao: '', favorita: false, distancia_km: 1 }])
      await Promise.resolve()
    })

    expect(screen.queryByText('Paróquia tardia')).toBeNull()
    expect(screen.getByText('Busca cancelada.')).toBeTruthy()
  })

  it('ignora uma localização do GPS que chegue após o cancelamento', async () => {
    let sucessoGps: PositionCallback | undefined
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: { getCurrentPosition: (sucesso: PositionCallback) => { sucessoGps = sucesso } },
    })

    render(<IgrejasScreen setScreen={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Próximas' }))
    fireEvent.click(screen.getByRole('button', { name: 'Usar minha localização' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Cancelar busca' }))

    await act(async () => {
      sucessoGps?.({ coords: { latitude: -22.9848, longitude: -43.2245 } } as GeolocationPosition)
      await Promise.resolve()
    })

    expect(mocks.buscarIgrejas).not.toHaveBeenCalled()
    expect(screen.getByText('Busca cancelada.')).toBeTruthy()
  })

  it('informa o teto mensal, sem alegar que o endereço não foi encontrado', async () => {
    mocks.localizarEndereco.mockRejectedValue({ response: { status: 429 } })

    render(<IgrejasScreen setScreen={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Próximas' }))
    fireEvent.click(screen.getByRole('button', { name: 'Informar endereço' }))
    const campoEndereco = await screen.findByPlaceholderText('Ex.: Rua ou bairro, cidade')
    fireEvent.change(campoEndereco, { target: { value: 'Leblon, Rio de Janeiro' } })
    fireEvent.click(screen.getByRole('button', { name: 'Usar' }))

    expect(await screen.findByText('O limite mensal de buscas por endereço foi atingido. Use a sua localização atual ou tente no próximo mês.')).toBeTruthy()
  })
})
