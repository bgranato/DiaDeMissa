import { useState, useEffect } from 'react'
import { motion } from 'motion/react'
import { AppHeader, Card } from '../components/UI'
import { getMissaPorData } from '../services/missa'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { Missa } from '../types/missa'

interface Props { setScreen: (s: string) => void }

export const CalendarScreen = ({ setScreen }: Props) => {
  const [missas, setMissas] = useState<Missa[]>([])
  const [ano, setAno] = useState(new Date().getFullYear())
  const [mes, setMes] = useState(new Date().getMonth())
  const meses = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']

  useEffect(() => { carregar() }, [ano, mes])

  async function carregar() {
    const dias = new Date(ano, mes + 1, 0).getDate()
    const r: Missa[] = []
    for (let d = 1; d <= Math.min(dias, 31); d++) {
      try { r.push(await getMissaPorData(`${ano}-${String(mes+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`)) } catch {}
    }
    setMissas(r)
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-h-screen bg-brand-bg dark:bg-slate-900 pb-32">
      <AppHeader title="Agenda" showAccessibility={false} onBack={() => setScreen('home')} />

      <div className="max-w-lg mx-auto px-5 mt-6">
        <div className="flex items-center justify-between mb-6">
          <button onClick={() => { if (mes===0) { setMes(11); setAno(a=>a-1) } else setMes(m=>m-1) }} className="p-3 bg-white dark:bg-slate-800 rounded-2xl shadow-soft"><ChevronLeft size={24} /></button>
          <h2 className="text-2xl font-bold">{meses[mes]} {ano}</h2>
          <button onClick={() => { if (mes===11) { setMes(0); setAno(a=>a+1) } else setMes(m=>m+1) }} className="p-3 bg-white dark:bg-slate-800 rounded-2xl shadow-soft"><ChevronRight size={24} /></button>
        </div>

        {missas.map(m => (
          <button key={m.id} onClick={() => setScreen('reading')} className="w-full mb-3 text-left">
            <Card className="flex items-center gap-4 p-5 active:scale-[0.98] transition-transform">
              <div className="text-center min-w-[50px]">
                <div className="text-xs font-bold uppercase text-brand-gold">{new Date(m.data+'T12:00:00').toLocaleDateString('pt-BR', { month: 'short' }).replace('.','')}</div>
                <div className="text-2xl font-black text-brand-blue dark:text-white">{new Date(m.data+'T12:00:00').getDate()}</div>
              </div>
              <div className="flex-1">
                <p className="font-bold">{m.celebracao || 'Missa'}</p>
                <p className="text-sm text-brand-gray-dark/60 capitalize">{new Date(m.data+'T12:00:00').toLocaleDateString('pt-BR', { weekday: 'long' })}</p>
              </div>
            </Card>
          </button>
        ))}
        {missas.length === 0 && <p className="text-center text-brand-gray-dark/40 mt-10">Nenhuma missa neste mês</p>}
      </div>
    </motion.div>
  )
}
