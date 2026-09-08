import api from './api'
import type { Igreja } from '../types/igreja'

export async function buscarIgrejas(params: {
  q?: string
  lat?: number
  lng?: number
  raio_km?: number
} = {}, signal?: AbortSignal): Promise<Igreja[]> {
  const res = await api.get<Igreja[]>('/igrejas', { params, signal })
  return res.data
}

export async function localizarEndereco(endereco: string, signal?: AbortSignal): Promise<{ lat: number; lng: number }> {
  const res = await api.post<{ lat: number; lng: number }>('/igrejas/localizar-endereco', { endereco }, { signal })
  return res.data
}


export async function minhasIgrejas(): Promise<Igreja[]> {
  const res = await api.get<Igreja[]>('/igrejas/minhas')
  return res.data
}

export async function favoritarIgreja(id: number): Promise<void> {
  await api.post(`/igrejas/${id}/favoritar`)
}

export async function desfavoritarIgreja(id: number): Promise<void> {
  await api.delete(`/igrejas/${id}/favoritar`)
}
