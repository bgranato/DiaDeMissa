import api from './api'
import type { Missa, BlocoLiturgico, MissaCompleta } from '../types/missa'
import type { MissaNova, BlocoLiturgicoNovo } from '../types/missa.nova'

export async function getMissaHoje(): Promise<Missa> {
  const res = await api.get<Missa>('/missas/hoje')
  return res.data
}

export async function getMissaHojeV2(): Promise<MissaNova> {
  const res = await api.get<MissaNova>('/api/v2/missas/hoje')
  return res.data
}

export async function getMissaPorData(data: string): Promise<Missa> {
  const res = await api.get<Missa>(`/missas/${data}`)
  return res.data
}

export async function getBlocosMissa(missaId: number): Promise<BlocoLiturgico[]> {
  const res = await api.get<BlocoLiturgico[]>(`/missas/${missaId}/blocos`)
  return res.data
}

export async function getMissaCompleta(missaId: number): Promise<MissaCompleta> {
  const res = await api.get<MissaCompleta>(`/missas/${missaId}/completa`)
  return res.data
}

export async function getBlocosMissaV2(missaId?: number): Promise<BlocoLiturgicoNovo[]> {
  const res = await api.get<MissaNova>('/api/v2/missas/hoje')
  return res.data.blocos
}
