import api from './api'
import type { Missa, PalavraDoDia } from '../types/missa'

export async function getMissaHoje(): Promise<Missa> {
  const res = await api.get('/missa/atual')
  const m = res.data
  // Descrição "Cor litúrgica: X" não é resumo — vira parte do subtítulo.
  // Resumo de verdade só aparece em missas ricas (folheto Arquidiocese).
  const descRaw: string = m.descricao || ''
  const corMatch = descRaw.match(/Cor\s+lit[uú]rgica:\s*(\w+)/i)
  const ehSoCor = /^\s*Cor\s+lit[uú]rgica:\s*\w+\s*$/i.test(descRaw)
  let descReal = ehSoCor ? '' : descRaw
  // Fallback em dias sem folheto Arquidiocese (semana): trecho do Evangelho do dia
  // pra ainda ter um resumo no card. Sem fallback genérico tipo "Acompanhe a liturgia".
  if (!descReal && m.palavra_do_dia?.texto) {
    const ref = m.palavra_do_dia.referencia
    descReal = ref
      ? `${m.palavra_do_dia.texto} (${ref})`
      : m.palavra_do_dia.texto
  }
  const subPartes: string[] = []
  if (m.categoria) subPartes.push(m.categoria)
  if (m.observacoes) subPartes.push(m.observacoes)
  if (corMatch && !m.categoria) subPartes.push(`Cor litúrgica: ${corMatch[1]}`)
  return {
    id: m.id ?? 0,
    data: m.data || '',
    celebracao: m.titulo_celebracao || '',
    subtitulo: subPartes.length ? subPartes.join(' · ') : null,
    descricao: descReal || null,
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

export interface ProximaMissa {
  data: string | null
  celebracao: string | null
  categoria: string | null
}

export interface MissaDisponivel {
  id: number
  data: string
  celebracao: string | null
  categoria: string | null
}

interface AgendaMissas {
  anteriores: MissaDisponivel[]
}

// Próxima missa com folheto disponível (usada quando não há missa no dia).
export async function getProximaMissa(): Promise<ProximaMissa> {
  const res = await api.get<ProximaMissa>('/missa/proxima')
  return res.data
}

// Última missa concluída, para que dias sem folheto ainda deem acesso ao conteúdo recente.
export async function getUltimaMissaDisponivel(): Promise<MissaDisponivel | null> {
  const res = await api.get<AgendaMissas>('/missa/agenda')
  return res.data.anteriores?.[0] ?? null
}

export async function getMissaAtual(): Promise<{ blocos: any[] }> {
  const res = await api.get('/missa/atual')
  return res.data
}

export async function getMissaEstruturadaPorData(data: string): Promise<any> {
  const res = await api.get(`/missa/por-data/${data}`)
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
