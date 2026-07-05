import api from './api'
import type { Preferencias } from '../types/usuario'

export async function getPreferencias(): Promise<Preferencias> {
  const res = await api.get<Preferencias>('/usuarios/me/preferencias')
  return res.data
}

export async function atualizarPreferencias(dados: Partial<Preferencias>): Promise<Preferencias> {
  const res = await api.put<Preferencias>('/usuarios/me/preferencias', dados)
  return res.data
}
