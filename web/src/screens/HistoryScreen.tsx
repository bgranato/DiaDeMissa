import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import { CheckCircle2, Clock, CircleDashed } from 'lucide-react'
import { AppHeader, Card } from '../components/UI'
import api from '../services/api'
import type { HistoricoEntry, HistoricoStatus } from '../types/usuario'

interface Props { setScreen: (s: string) => void }

const STATUS_META: Record<HistoricoStatus, { label: string; Icon: typeof CheckCircle2; iconClass: string; cardClass: string; barClass: string }> = {
  concluida: {
    label: 'Concluída',
    Icon: CheckCircle2,
    iconClass: 'text-green-500',
    cardClass: 'border-l-4 border-green-500',
    barClass: 'bg-green-500',
  },
  em_progresso: {
    label: 'Em progresso',
    Icon: Clock,
    iconClass: 'text-brand-gold',
    cardClass: 'border-l-4 border-brand-gold',
    barClass: 'bg-brand-gold',
  },
  nao_acompanhada: {
    label: 'Não acompanhada',
    Icon: CircleDashed,
    iconClass: 'text-brand-gray-dark/40',
    cardClass: 'border-l-4 border-brand-gray opacity-70',
    barClass: 'bg-brand-gray',
  },
}

export const HistoryScreen = ({ setScreen }: Props) => {
  const [historico, setHistorico] = useState<HistoricoEntry[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<HistoricoEntry[]>('/usuarios/me/historico')
      .then(r => setHistorico(r.data))
      .catch(() => setHistorico([]))
      .finally(() => setLoading(false))
  }, [])

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-h-screen bg-brand-bg dark:bg-slate-900 pb-32">
      <AppHeader title="Histórico" showAccessibility={false} onBack={() => setScreen('home')} />

      <div className="max-w-lg mx-auto px-5 mt-6 flex flex-col gap-4">
        {loading ? (
          <div className="text-center py-10"><div className="w-8 h-8 border-4 border-brand-gold border-t-transparent rounded-full animate-spin mx-auto" /></div>
        ) : historico.length === 0 ? (
          <p className="text-center text-brand-gray-dark/40 mt-10">Nenhuma missa disponível ainda</p>
        ) : (
          historico.map(h => {
            const meta = STATUS_META[h.status] ?? STATUS_META.nao_acompanhada
            const { Icon } = meta
            const isInteractable = h.status !== 'nao_acompanhada'
            return (
              <button
                key={h.missa_id}
                onClick={() => isInteractable && setScreen('reading')}
                disabled={!isInteractable}
                className="w-full text-left"
              >
                <Card className={`p-5 active:scale-[0.98] transition-transform ${meta.cardClass}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <p className="font-bold text-brand-blue dark:text-brand-gold capitalize">
                        {new Date(h.data + 'T12:00:00').toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })}
                      </p>
                      <p className="text-sm mt-1">{h.celebracao || 'Missa'}</p>
                    </div>
                    <div className={`flex items-center gap-1.5 ${meta.iconClass}`}>
                      <Icon size={18} />
                      <span className="text-[10px] font-black uppercase tracking-wider">{meta.label}</span>
                    </div>
                  </div>
                  {h.status !== 'nao_acompanhada' && (
                    <div className="mt-3 flex items-center gap-3">
                      <div className="flex-1 h-2 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
                        <div className={`h-full ${meta.barClass} rounded-full`} style={{ width: `${h.percentual_lido}%` }} />
                      </div>
                      <span className="text-xs font-bold text-brand-gray-dark/50">{Math.round(h.percentual_lido)}%</span>
                    </div>
                  )}
                </Card>
              </button>
            )
          })
        )}
      </div>
    </motion.div>
  )
}
