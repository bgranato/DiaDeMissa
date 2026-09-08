import { useEffect, useState, type MouseEvent } from 'react'
import { motion } from 'motion/react'
import {
  CheckCircle2, Clock, CircleDashed, MapPin, X, Target,
  TrendingUp, Flame, Award, Edit3, Calendar, BarChart3, ListChecks,
} from 'lucide-react'
import { BuscaMissas } from '../components/BuscaMissas'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
} from 'recharts'
import { AppHeader, Card } from '../components/UI'
import api from '../services/api'
import type { HistoricoEntry, HistoricoStatus } from '../types/usuario'

interface Props { setScreen: (s: string) => void }

type Aba = 'historico' | 'relatorio'

// ============================================================================
// Aba HISTÓRICO (lista de missas)
// ============================================================================

const STATUS_META: Record<HistoricoStatus, { label: string; Icon: typeof CheckCircle2; iconClass: string; cardClass: string; barClass: string }> = {
  concluida: {
    label: 'Concluída', Icon: CheckCircle2, iconClass: 'text-green-500',
    cardClass: 'border-l-4 border-green-500', barClass: 'bg-green-500',
  },
  em_progresso: {
    label: 'Em progresso', Icon: Clock, iconClass: 'text-brand-gold',
    cardClass: 'border-l-4 border-brand-gold', barClass: 'bg-brand-gold',
  },
  nao_acompanhada: {
    label: 'Não acompanhada', Icon: CircleDashed, iconClass: 'text-brand-gray-dark/40',
    cardClass: 'border-l-4 border-brand-gray opacity-70', barClass: 'bg-brand-gray',
  },
}

function AbaHistorico({ setScreen }: { setScreen: (s: string) => void }) {
  const [historico, setHistorico] = useState<HistoricoEntry[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<HistoricoEntry[]>('/usuarios/me/historico')
      .then(r => setHistorico(r.data))
      .catch(() => setHistorico([]))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="flex flex-col gap-4">
      <BuscaMissas setScreen={setScreen} titulo="Buscar missas anteriores" />

      <p className="ds-section-label mt-2">Minhas missas acompanhadas</p>

      {loading && (
        <div className="text-center py-10">
          <div className="w-8 h-8 border-4 border-brand-gold border-t-transparent rounded-full animate-spin mx-auto" />
        </div>
      )}

      {!loading && historico.length === 0 && (
        <div className="text-center mt-2 px-6 py-6 ds-card-subtle">
          <p className="text-brand-gray-dark/70 dark:text-brand-white/70 text-sm font-bold">
            Você ainda não concluiu nenhuma missa.
          </p>
          <p className="text-brand-gray-dark/50 dark:text-brand-white/50 text-xs mt-1">
            As missas que você acompanhar até o fim vão aparecer aqui.
          </p>
        </div>
      )}

      {historico.map(h => {
        const meta = STATUS_META[h.status] ?? STATUS_META.nao_acompanhada
        const { Icon } = meta
        async function desfazer(e: MouseEvent) {
          e.stopPropagation()
          if (!confirm('Desmarcar esta missa como concluída?')) return
          try {
            await api.post(`/usuarios/me/historico/${h.missa_id}/desconcluir`)
          } catch {}
          localStorage.removeItem(`@missa_concluida_${h.data}`)
          localStorage.removeItem(`@missa_iniciada_${h.data}`)
          setHistorico(prev => prev.filter(x => x.missa_id !== h.missa_id))
        }
        return (
          <Card key={h.missa_id} className={`p-5 ${meta.cardClass}`}>
            <div className="flex items-start justify-between gap-3">
              <div onClick={() => setScreen('reading')} className="flex-1 cursor-pointer active:opacity-70 transition-opacity">
                <p className="font-bold text-brand-blue dark:text-brand-gold capitalize">
                  {new Date(h.data + 'T12:00:00').toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })}
                </p>
                <p className="text-sm mt-1">{h.celebracao || 'Missa'}</p>
              </div>
              <div className={`flex items-center gap-1 px-2 py-1 rounded-full bg-green-500/10 ${meta.iconClass}`}>
                <Icon size={14} />
                <span className="text-[10px] font-black uppercase tracking-wider">{meta.label}</span>
                <button onClick={desfazer} title="Desmarcar conclusão"
                  className="ml-1 p-0.5 rounded-full hover:bg-red-500 hover:text-white text-green-700 dark:text-green-400 transition-colors">
                  <X size={12} strokeWidth={3} />
                </button>
              </div>
            </div>
            <div onClick={() => setScreen('reading')} className="cursor-pointer active:opacity-70 transition-opacity">
              <div className="mt-3 flex items-center gap-3">
                <div className="flex-1 h-2 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
                  <div className={`h-full ${meta.barClass} rounded-full`} style={{ width: `${h.percentual_lido}%` }} />
                </div>
                <span className="text-xs font-bold text-brand-gray-dark/50">{Math.round(h.percentual_lido)}%</span>
              </div>
              {h.igreja_nome && (
                <div className="mt-3 flex items-center gap-2">
                  <MapPin size={14} className="text-brand-gold flex-shrink-0" />
                  <span className="text-xs font-bold text-brand-gray-dark dark:text-brand-white/80 truncate">{h.igreja_nome}</span>
                </div>
              )}
            </div>
          </Card>
        )
      })}
    </div>
  )
}

// ============================================================================
// Aba RELATÓRIO (dashboard agregado)
// ============================================================================

interface Relatorio {
  totais: { missas_total: number; primeira_missa: string | null }
  periodos: Record<'semana' | 'mes' | 'ano', {
    label: string
    missas: number
    dias_periodo: number
    recomendado_minimo: number
    taxa_vs_dias: number
    taxa_vs_recomendado: number | null
    meta_usuario?: number
    taxa_vs_meta?: number
  }>
  streak_domingos: number
  serie_12_meses: { ano: number; mes: number; label: string; missas: number }[]
  ranking_igrejas: { igreja_id: number; nome: string; cidade: string | null; missas: number; pct: number }[]
  meta_missas_mensal: number | null
}

function CardContador({ label, valor, sub, Icon }: { label: string; valor: number; sub?: string; Icon: typeof Target }) {
  return (
    <div className="ds-card flex-1 min-w-[100px]">
      <div className="flex items-center gap-2 mb-1">
        <Icon size={16} className="text-brand-gold" />
        <p className="ds-section-label">{label}</p>
      </div>
      <p className="text-3xl font-serif font-black text-brand-blue dark:text-brand-white leading-none">{valor}</p>
      {sub && <p className="text-xs text-brand-gray-dark/60 dark:text-brand-white/60 mt-1">{sub}</p>}
    </div>
  )
}

function BarraProgresso({ label, pct, count, total, sufixo }: { label: string; pct: number | null; count: number; total: number; sufixo?: string }) {
  if (pct == null) return null
  const pctClamp = Math.min(pct, 100)
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1">
        <span className="ds-body-sm font-bold text-brand-gray-dark dark:text-brand-white">{label}</span>
        <span className="text-sm font-black text-brand-gold">
          {count} de {total}{sufixo ?? ''} · {pct}%
        </span>
      </div>
      <div className="h-3 bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pctClamp}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className="h-full bg-gradient-to-r from-brand-gold to-amber-600 rounded-full"
        />
      </div>
    </div>
  )
}

function AbaRelatorio() {
  const [data, setData] = useState<Relatorio | null>(null)
  const [loading, setLoading] = useState(true)
  const [editandoMeta, setEditandoMeta] = useState(false)
  const [novaMeta, setNovaMeta] = useState<string>('')

  useEffect(() => {
    api.get<Relatorio>('/usuarios/me/jornada/relatorio')
      .then(r => {
        setData(r.data)
        setNovaMeta(String(r.data.meta_missas_mensal ?? ''))
      })
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [])

  async function salvarMeta() {
    const valor = novaMeta.trim() === '' ? null : Number(novaMeta)
    if (valor !== null && (Number.isNaN(valor) || valor < 0 || valor > 200)) {
      alert('Meta deve ser entre 0 e 200 missas/mês')
      return
    }
    try {
      await api.put('/usuarios/me/meta', { meta_missas_mensal: valor })
      const r = await api.get<Relatorio>('/usuarios/me/jornada/relatorio')
      setData(r.data)
      setEditandoMeta(false)
    } catch {
      alert('Erro ao salvar meta')
    }
  }

  if (loading) return (
    <div className="text-center py-10">
      <div className="w-8 h-8 border-4 border-brand-gold border-t-transparent rounded-full animate-spin mx-auto" />
    </div>
  )

  if (!data || data.totais.missas_total === 0) return (
    <div className="text-center mt-10 px-6">
      <p className="text-brand-gray-dark/60 dark:text-brand-white/60 text-base font-bold">
        Ainda não há dados para um relatório.
      </p>
      <p className="text-brand-gray-dark/40 dark:text-brand-white/40 text-sm mt-2">
        Acompanhe e conclua suas primeiras missas para ver estatísticas aqui.
      </p>
    </div>
  )

  const { periodos, streak_domingos, serie_12_meses, ranking_igrejas, totais, meta_missas_mensal } = data

  // Dataset pro chart Recharts
  const dadosChart = serie_12_meses.map(s => ({
    label: s.label,
    missas: s.missas,
  }))

  return (
    <div className="flex flex-col gap-5">
      {/* 3 contadores */}
      <div className="flex gap-2">
        <CardContador label="Semana" valor={periodos.semana.missas} sub={`em ${periodos.semana.dias_periodo}d`} Icon={Calendar} />
        <CardContador label="Mês" valor={periodos.mes.missas} sub={`em ${periodos.mes.dias_periodo}d`} Icon={Calendar} />
        <CardContador label="Ano" valor={periodos.ano.missas} sub={`em ${periodos.ano.dias_periodo}d`} Icon={Calendar} />
      </div>

      {/* Total + Streak + Primeira missa */}
      <div className="ds-card">
        <p className="ds-section-label mb-2">Sua Jornada</p>
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[120px]">
            <div className="flex items-center gap-2 mb-1">
              <Award size={16} className="text-brand-gold" />
              <span className="ds-caption text-brand-gray-dark/60 dark:text-brand-white/60">TOTAL DE MISSAS</span>
            </div>
            <p className="text-2xl font-serif font-black text-brand-blue dark:text-brand-white">{totais.missas_total}</p>
          </div>
          <div className="flex-1 min-w-[120px]">
            <div className="flex items-center gap-2 mb-1">
              <Flame size={16} className="text-orange-500" />
              <span className="ds-caption text-brand-gray-dark/60 dark:text-brand-white/60">SEQUÊNCIA</span>
            </div>
            <p className="text-2xl font-serif font-black text-brand-blue dark:text-brand-white">
              {streak_domingos} <span className="text-sm font-sans text-brand-gray-dark/60">domingo{streak_domingos !== 1 ? 's' : ''}</span>
            </p>
          </div>
          {totais.primeira_missa && (
            <div className="flex-1 min-w-[120px]">
              <div className="flex items-center gap-2 mb-1">
                <TrendingUp size={16} className="text-blue-500" />
                <span className="ds-caption text-brand-gray-dark/60 dark:text-brand-white/60">PRIMEIRA MISSA</span>
              </div>
              <p className="text-sm font-bold text-brand-blue dark:text-brand-white">
                {new Date(totais.primeira_missa + 'T12:00:00').toLocaleDateString('pt-BR', { day: 'numeric', month: 'long', year: 'numeric' })}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Taxas de frequência */}
      <div className="ds-card">
        <div className="flex items-center justify-between mb-3 gap-2 flex-wrap">
          <div>
            <p className="ds-section-label">Frequência este mês</p>
            {meta_missas_mensal && (
              <p className="text-xs font-bold text-brand-blue dark:text-brand-gold mt-1 flex items-center gap-1">
                <Target size={12} strokeWidth={2.5} />
                Meta: {meta_missas_mensal} missas/mês
              </p>
            )}
          </div>
          {!editandoMeta ? (
            <button
              onClick={() => setEditandoMeta(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white dark:bg-slate-800 border-2 border-brand-blue text-brand-blue dark:text-brand-gold dark:border-brand-gold text-xs font-black uppercase tracking-wider active:scale-95 transition-transform shadow-soft"
            >
              <Target size={13} strokeWidth={2.5} />
              {meta_missas_mensal ? `Editar (${meta_missas_mensal}/mês)` : 'Definir meta'}
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <input
                type="number" min={0} max={200}
                value={novaMeta}
                onChange={e => setNovaMeta(e.target.value)}
                placeholder="ex: 8"
                className="w-16 px-2 py-1 rounded-md border border-brand-gold/40 bg-white dark:bg-slate-800 text-sm font-bold text-center"
                autoFocus
              />
              <button onClick={salvarMeta} className="text-xs font-bold text-green-600 px-2 py-1">Salvar</button>
              <button onClick={() => setEditandoMeta(false)} className="text-xs font-bold text-brand-gray-dark/60 px-2 py-1">Cancelar</button>
            </div>
          )}
        </div>
        <div className="flex flex-col gap-3">
          <BarraProgresso
            label="Total de dias"
            pct={periodos.mes.taxa_vs_dias}
            count={periodos.mes.missas}
            total={periodos.mes.dias_periodo}
            sufixo=" dias"
          />
          <BarraProgresso
            label="Domingos + Solenidades (mín. recomendado)"
            pct={periodos.mes.taxa_vs_recomendado}
            count={periodos.mes.missas}
            total={periodos.mes.recomendado_minimo}
          />
          {periodos.mes.meta_usuario && (
            <BarraProgresso
              label="Sua meta"
              pct={periodos.mes.taxa_vs_meta ?? 0}
              count={periodos.mes.missas}
              total={periodos.mes.meta_usuario}
            />
          )}
        </div>
      </div>

      {/* Taxa anual */}
      <div className="ds-card">
        <p className="ds-section-label mb-3">Frequência neste ano</p>
        <div className="flex flex-col gap-3">
          <BarraProgresso
            label="Total de dias"
            pct={periodos.ano.taxa_vs_dias}
            count={periodos.ano.missas}
            total={periodos.ano.dias_periodo}
            sufixo=" dias"
          />
          <BarraProgresso
            label="Domingos + Solenidades (mín. recomendado)"
            pct={periodos.ano.taxa_vs_recomendado}
            count={periodos.ano.missas}
            total={periodos.ano.recomendado_minimo}
          />
        </div>
      </div>

      {/* Gráfico 12 meses */}
      <div className="ds-card">
        <div className="flex items-center gap-2 mb-3">
          <BarChart3 size={16} className="text-brand-gold" />
          <p className="ds-section-label">Últimos 12 meses</p>
        </div>
        <div className="h-48 -mx-1">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={dadosChart} margin={{ top: 4, right: 8, bottom: 0, left: -28 }}>
              <XAxis
                dataKey="label"
                tick={{ fontSize: 10, fill: 'currentColor' }}
                interval={0}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 10, fill: 'currentColor' }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                cursor={{ fill: 'rgba(197, 160, 89, 0.08)' }}
                contentStyle={{
                  backgroundColor: '#1A2B4C',
                  border: 'none',
                  borderRadius: 8,
                  fontSize: 12,
                  color: 'white',
                }}
                formatter={(v: number) => [`${v} missa${v !== 1 ? 's' : ''}`, '']}
                labelStyle={{ color: '#C5A059' }}
              />
              <Bar dataKey="missas" radius={[6, 6, 0, 0]}>
                {dadosChart.map((entry, idx) => (
                  <Cell key={idx} fill={entry.missas === 0 ? '#E5E7EB' : '#C5A059'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Ranking de igrejas */}
      {ranking_igrejas.length > 0 && (
        <div className="ds-card">
          <div className="flex items-center gap-2 mb-3">
            <ListChecks size={16} className="text-brand-gold" />
            <p className="ds-section-label">Igrejas mais frequentadas</p>
          </div>
          <div className="flex flex-col gap-2.5">
            {ranking_igrejas.slice(0, 10).map((ig, idx) => (
              <div key={ig.igreja_id} className="flex items-center gap-3">
                <span className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-black ${
                  idx === 0 ? 'bg-brand-gold text-white' : 'bg-brand-gold/15 text-brand-gold'
                }`}>{idx + 1}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-bold text-brand-blue dark:text-brand-white truncate">{ig.nome}</p>
                  {ig.cidade && <p className="text-xs text-brand-gray-dark/60 dark:text-brand-white/60 truncate">{ig.cidade}</p>}
                  <div className="h-1.5 mt-1 bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden">
                    <div className="h-full bg-brand-gold rounded-full" style={{ width: `${ig.pct}%` }} />
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-sm font-black text-brand-blue dark:text-brand-gold">{ig.missas}</p>
                  <p className="text-[10px] font-bold text-brand-gray-dark/60">{ig.pct}%</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Wrapper com tabs
// ============================================================================

export const JornadaScreen = ({ setScreen }: Props) => {
  const [aba, setAba] = useState<Aba>('historico')

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-h-screen bg-brand-bg dark:bg-slate-900 ds-bottom-nav-padding">
      <AppHeader title="Minha Jornada" onBack={() => setScreen('home')} />

      <div className="ds-container mt-5">
        {/* Tabs switcher */}
        <div className="flex gap-1 p-1 bg-gray-100 dark:bg-slate-800 rounded-full mb-5">
          {([
            { id: 'historico' as const, label: 'Histórico' },
            { id: 'relatorio' as const, label: 'Relatório' },
          ]).map(t => (
            <button
              key={t.id}
              onClick={() => setAba(t.id)}
              className={`flex-1 py-2.5 rounded-full text-sm font-black uppercase tracking-wider transition-colors ${
                aba === t.id
                  ? 'bg-brand-blue text-white shadow-soft'
                  : 'text-brand-gray-dark dark:text-brand-white/70'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {aba === 'historico' ? <AbaHistorico setScreen={setScreen} /> : <AbaRelatorio />}
      </div>
    </motion.div>
  )
}
