import { useEffect, useState, type MouseEvent } from 'react'
import { motion } from 'motion/react'
import { CheckCircle2, Clock, CircleDashed, MapPin, X } from 'lucide-react'
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
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-h-screen bg-brand-bg dark:bg-slate-900 ds-bottom-nav-padding">
      <AppHeader title="Histórico" onBack={() => setScreen('home')} />

      <div className="max-w-lg mx-auto px-5 mt-6 flex flex-col gap-4">
        {loading ? (
          <div className="text-center py-10"><div className="w-8 h-8 border-4 border-brand-gold border-t-transparent rounded-full animate-spin mx-auto" /></div>
        ) : historico.length === 0 ? (
          <div className="text-center mt-10 px-6">
            <p className="text-brand-gray-dark/60 dark:text-brand-white/60 text-base font-bold">
              Você ainda não concluiu nenhuma missa.
            </p>
            <p className="text-brand-gray-dark/40 dark:text-brand-white/40 text-sm mt-2">
              As missas que você acompanhar até o fim vão aparecer aqui.
            </p>
          </div>
        ) : (
          historico.map(h => {
            const meta = STATUS_META[h.status] ?? STATUS_META.nao_acompanhada
            const { Icon } = meta

            async function desfazer(e: MouseEvent) {
              e.stopPropagation()
              if (!confirm('Desmarcar esta missa como concluída?')) return
              // Tenta no backend (idempotente, não falha se não tinha registro)
              try {
                await api.post(`/usuarios/me/historico/${h.missa_id}/desconcluir`)
              } catch (err) {
                console.warn('Falha ao desconcluir no backend, prosseguindo localmente', err)
              }
              // Sempre limpa estado local — visual deve refletir a intenção do usuário
              localStorage.removeItem(`@missa_concluida_${h.data}`)
              localStorage.removeItem(`@missa_iniciada_${h.data}`)
              setHistorico(prev => prev.filter(x => x.missa_id !== h.missa_id))
            }

            return (
              <Card key={h.missa_id} className={`p-5 ${meta.cardClass}`}>
                <div className="flex items-start justify-between gap-3">
                  <div
                    onClick={() => setScreen('reading')}
                    className="flex-1 cursor-pointer active:opacity-70 transition-opacity"
                  >
                    <p className="font-bold text-brand-blue dark:text-brand-gold capitalize">
                      {new Date(h.data + 'T12:00:00').toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })}
                    </p>
                    <p className="text-sm mt-1">{h.celebracao || 'Missa'}</p>
                  </div>

                  {/* Badge "Concluída" com botão X integrado pra desfazer */}
                  <div className={`flex items-center gap-1 px-2 py-1 rounded-full bg-green-500/10 ${meta.iconClass}`}>
                    <Icon size={14} />
                    <span className="text-[10px] font-black uppercase tracking-wider">{meta.label}</span>
                    <button
                      onClick={desfazer}
                      title="Desmarcar conclusão"
                      className="ml-1 p-0.5 rounded-full hover:bg-red-500 hover:text-white text-green-700 dark:text-green-400 transition-colors"
                    >
                      <X size={12} strokeWidth={3} />
                    </button>
                  </div>
                </div>

                <div
                  onClick={() => setScreen('reading')}
                  className="cursor-pointer active:opacity-70 transition-opacity"
                >
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
          })
        )}
      </div>
    </motion.div>
  )
}
