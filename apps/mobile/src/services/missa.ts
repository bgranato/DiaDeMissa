import api from './api'
import type { Missa, BlocoLiturgico, MissaCompleta } from '../types/missa'

export async function getMissaHoje(): Promise<Missa> {
  const response = await api.get<Missa>('/missas/hoje')
  return response.data
}

export async function getMissaPorData(data: string): Promise<Missa> {
  const response = await api.get<Missa>(`/missas/${data}`)
  return response.data
}

export async function getBlocosMissa(missaId: number): Promise<BlocoLiturgico[]> {
  const response = await api.get<BlocoLiturgico[]>(`/missas/${missaId}/blocos`)
  return response.data
}

export async function getMissaCompleta(missaId: number): Promise<MissaCompleta> {
  const response = await api.get<MissaCompleta>(`/missas/${missaId}/completa`)
  return response.data
}
