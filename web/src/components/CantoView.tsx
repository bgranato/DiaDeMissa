import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import { Card, LargeButton } from '../components/UI'
import { ChevronLeft, ChevronRight } from 'lucide-react'

interface Canto {
  tipo: 'canto'
  ordem: number
  titulo: string
  postura: 'de_pe' | 'sentado' | 'ajoelhado' | null
  refrao: string[]
  estrofes: string[][]
}

interface MissaData {
  blocos: any[]
}

const POSTURA_LABEL: Record<string, string> = {
  de_pe: 'De pé',
  sentado: 'Sentado',
  ajoelhado: 'Ajoelhado',
}

const POSTURA_ICON: Record<string, string> = {
  de_pe: '🙏',
  sentado: '🪑',
  ajoelhado: '🧎',
}

export default function CantoView() {
  const [canto, setCanto] = useState<Canto | null>(null)
  const [totalBlocos, setTotalBlocos] = useState(0)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/v1/missa/atual')
      .then((r) => r.json())
      .then((missa: MissaData) => {
        setTotalBlocos(missa.blocos.length)
        const primeiro = missa.blocos.find((b: any) => b.tipo === 'canto')
        setCanto(primeiro || null)
      })
      .catch(() => setErro('Erro ao carregar missa'))
  }, [])

  if (erro) return (
    <div className="min-h-screen bg-brand-bg dark:bg-slate-900 flex items-center justify-center">
      <p className="text-brand-text/60">{erro}</p>
    </div>
  )

  if (!canto) return (
    <div className="min-h-screen bg-brand-bg dark:bg-slate-900 flex items-center justify-center">
      <div className="w-10 h-10 border-4 border-brand-gold border-t-transparent rounded-full animate-spin" />
    </div>
  )

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      {/* Fixed header with navigation and posture chip */}
      <div className="sticky top-0 z-30 w-full bg-brand-bg/90 dark:bg-slate-900/90 backdrop-blur-md px-5 py-4 border-b border-black/5">
        <div className="flex items-center justify-between max-w-xl mx-auto">
          <div className="flex items-center gap-3">
            <span className="text-xs font-black text-brand-gold uppercase tracking-[0.2em]">
              CANTO {canto.ordem} DE {totalBlocos}
            </span>
          </div>
          {canto.postura && (
            <span className="inline-flex items-center gap-1.5 px-4 py-1.5 bg-brand-gold/10 text-brand-gold rounded-full text-xs font-bold">
              <span>{POSTURA_ICON[canto.postura]}</span>
              <span>{POSTURA_LABEL[canto.postura]}</span>
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-xl mx-auto px-5 mt-6 flex flex-col gap-6 pb-32">
        {/* Title */}
        <h2 className="font-serif font-black text-3xl text-brand-blue dark:text-brand-white border-l-4 border-brand-gold pl-4 leading-tight">
          {canto.titulo}
        </h2>

        {/* Refrão */}
        <div className="bg-gradient-to-r from-brand-gold/[0.07] to-transparent rounded-2xl p-6 border-l-4 border-brand-gold">
          <span className="text-[10px] font-black text-brand-gold uppercase tracking-[0.3em] block mb-3">
            REFRÃO
          </span>
          {canto.refrao.map((verso, i) => (
            <p key={i} className="text-lg font-semibold italic leading-relaxed text-brand-text dark:text-slate-100">
              {verso}
            </p>
          ))}
        </div>

        {/* Estrofes */}
        {canto.estrofes.map((estrofe, idx) => (
          <Card key={idx} className="border border-black/5 dark:border-slate-700 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <span className="w-8 h-8 rounded-full bg-brand-blue/10 dark:bg-slate-700 flex items-center justify-center text-sm font-black text-brand-blue dark:text-brand-gold">
                {idx + 1}
              </span>
              <span className="text-[10px] font-black text-brand-gray-dark/40 dark:text-brand-white/40 uppercase tracking-[0.3em]">
                ESTROFE
              </span>
            </div>
            {estrofe.map((verso, i) => (
              <p key={i} className="text-base leading-relaxed font-medium text-brand-text dark:text-slate-200 mb-1 last:mb-0">
                {verso}
              </p>
            ))}
          </Card>
        ))}
      </div>
    </motion.div>
  )
}
