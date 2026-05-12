import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import { AppHeader, Card } from '../components/UI'
import api from '../services/api'
import type { HistoricoEntry } from '../types/usuario'

interface Props { setScreen: (s: string) => void }

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
          <p className="text-center text-brand-gray-dark/40 mt-10">Nenhuma missa acessada ainda</p>
        ) : (
          historico.map(h => (
            <button key={h.missa_id} onClick={() => setScreen('reading')} className="w-full text-left">
              <Card className="p-5 active:scale-[0.98] transition-transform">
                <p className="font-bold text-brand-blue dark:text-brand-gold capitalize">
                  {new Date(h.data+'T12:00:00').toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })}
                </p>
                <p className="text-sm mt-1">{h.celebracao || 'Missa'}</p>
                <div className="mt-3 flex items-center gap-3">
                  <div className="flex-1 h-2 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
                    <div className="h-full bg-brand-gold rounded-full" style={{ width: `${h.percentual_lido}%` }} />
                  </div>
                  <span className="text-xs font-bold text-brand-gray-dark/50">{Math.round(h.percentual_lido)}%</span>
                </div>
              </Card>
            </button>
          ))
        )}
      </div>
    </motion.div>
  )
}
