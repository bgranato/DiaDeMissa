import api from './api'
import type { Missa, PalavraDoDia } from '../types/missa'

export async function getMissaHoje(): Promise<Missa> {
  const res = await api.get('/missa/atual')
  const m = res.data
  return {
    id: 1,
    data: m.data || '',
    celebracao: m.titulo_celebracao || '',
    subtitulo: m.categoria ? `${m.categoria}${m.observacoes ? ' | ' + m.observacoes : ''}` : m.observacoes || null,
    descricao: m.descricao || 'Acompanhe a liturgia diária da Igreja. Medite as leituras, salmos e evangelho do dia.',
    tempo_liturgico: null,
    status_processamento: 'concluido',
    total_blocos: (m.blocos || []).length,
    palavra_do_dia: m.palavra_do_dia as PalavraDoDia | null | undefined,
  } as Missa
}

export async function getMissaPorData(data: string): Promise<Missa> {
  const res = await api.get<Missa>(`/missas/${data}`)
  return res.data
}

export async function getMissaAtual(): Promise<{ blocos: any[] }> {
  const res = await api.get('/missa/atual')
  return res.data
}

export async function salvarProgressoMissa(
  missaId: number,
  ultimoBlocoId: number,
  percentualLido: number,
): Promise<void> {
  await api.post('/usuarios/me/historico', {
    missa_id: missaId,
    ultimo_bloco_id: ultimoBlocoId,
    percentual_lido: percentualLido,
  })
}

export async function concluirMissa(missaId: number): Promise<void> {
  await api.post(`/usuarios/me/historico/${missaId}/concluir`)
}
