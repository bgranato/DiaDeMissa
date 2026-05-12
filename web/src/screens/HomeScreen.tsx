import { useState } from 'react'
import { motion } from 'motion/react'
import { Card, LargeButton } from '../components/UI'
import { Play, Calendar, Bookmark, Bell, ArrowRight } from 'lucide-react'
import type { Missa } from '../types/missa'

interface Props {
  setScreen: (s: string) => void
  missa: Missa | null
  nome: string
}

export const HomeScreen = ({ setScreen, missa, nome }: Props) => {
  const [descricaoExpandida, setDescricaoExpandida] = useState(false)
  const dataFormatada = missa?.data
    ? new Date(missa.data + 'T12:00:00').toLocaleDateString('pt-BR', { day: 'numeric', month: 'long', year: 'numeric' }).toUpperCase()
    : ''

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-6 pb-32 flex flex-col gap-6 max-w-lg mx-auto">
      <header className="flex justify-between items-start">
        <div>
          <h2 className="text-3xl font-serif font-black text-brand-gray-dark dark:text-brand-white">Olá, {nome}!</h2>
          <p className="text-brand-blue dark:text-brand-gold font-bold italic opacity-70">Paz e Bem.</p>
        </div>
        <button onClick={() => setScreen('reminders')}
          className="p-4 bg-brand-white dark:bg-slate-800 rounded-2xl shadow-soft border border-black/5 text-brand-blue dark:text-brand-gold active:scale-95 transition-transform relative">
          <Bell size={28} />
        </button>
      </header>

      {missa ? (
        <Card className="bg-brand-white dark:bg-slate-800 overflow-hidden relative border-2 border-brand-blue/5 shadow-strong">
          <div className="relative z-10">
            <div className="flex flex-wrap gap-2 mb-4">
              <span className="inline-block px-4 py-1.5 bg-brand-gold text-white text-[10px] font-black rounded-full uppercase tracking-[0.2em]">
                {dataFormatada}
              </span>
            </div>

            {/* TÍTULO PRINCIPAL */}
            <h3 className="text-3xl font-serif font-black mb-2 leading-tight text-brand-blue dark:text-brand-white break-words">
              {missa.celebracao || 'Missa do Dia'}
            </h3>

            {/* SUBTÍTULO */}
            {missa.subtitulo && (
              <p className="text-sm font-semibold text-brand-slate dark:text-brand-gold/80 leading-relaxed mb-4">
                {missa.subtitulo}
              </p>
            )}

            {/* DESCRIÇÃO */}
            {missa.descricao && (
              <div className="mb-6">
                <div>
                  <p className={`text-base leading-relaxed text-brand-text/70 dark:text-brand-white/70 font-medium ${!descricaoExpandida ? 'overflow-hidden' : ''}`}
                     style={!descricaoExpandida ? {
                       overflow: 'hidden',
                       display: '-webkit-box',
                       WebkitBoxOrient: 'vertical',
                       WebkitLineClamp: 4,
                       textOverflow: 'ellipsis',
                     } : {}}>
                    {missa.descricao}
                  </p>
                </div>
                {missa.descricao.length > 200 && (
                  <button onClick={() => setDescricaoExpandida(!descricaoExpandida)}
                    className="text-sm font-bold text-brand-gold mt-1 hover:opacity-80 transition-opacity">
                    {descricaoExpandida ? 'Ver menos' : 'Ver mais'}
                  </button>
                )}
              </div>
            )}

            <div className="flex flex-col gap-4">
              <LargeButton variant="primary" onClick={() => setScreen('reading')} icon={Play} className="w-full h-[72px] text-xl">
                Acompanhar Missa
              </LargeButton>
              <button onClick={() => setScreen('reading')}
                className="flex items-center justify-center gap-2 py-2 text-sm font-bold text-brand-blue/70 dark:text-brand-white/70 hover:opacity-100 transition-opacity">
                Continuar de onde parei <ArrowRight size={18} />
              </button>
            </div>
          </div>
          <div className="absolute -bottom-10 -right-10 w-48 h-48 bg-brand-blue opacity-5 rounded-full blur-3xl" />
        </Card>
      ) : (
        <Card className="text-center p-12">
          <p className="text-brand-text/60">Missa de hoje indisponível</p>
        </Card>
      )}

      <div className="bg-brand-white dark:bg-slate-800 p-10 rounded-[40px] shadow-soft border border-black/[0.03] dark:border-slate-700 relative text-center">
        <span className="text-[10px] font-black text-brand-gold uppercase tracking-[0.3em] mb-6 block">Evangelho do Dia</span>
        <p className="text-2xl font-serif italic font-bold text-brand-blue dark:text-brand-white leading-relaxed">
          "Ide pelo mundo inteiro e anunciai o Evangelho a toda criatura!"
        </p>
        <div className="w-16 h-1.5 bg-brand-gold/20 mx-auto mt-8 rounded-full" />
        <p className="text-sm text-brand-slate mt-4 italic">Mt 28,16-20</p>
      </div>

      <div className="flex flex-col gap-4">
        <h4 className="font-bold text-brand-gray-dark/40 dark:text-brand-white/40 uppercase text-[10px] tracking-[0.3em] ml-2">Explorar</h4>
        <div className="grid grid-cols-2 gap-4">
          <button onClick={() => setScreen('calendar')}
            className="flex flex-col items-center gap-4 bg-brand-white dark:bg-slate-800 p-8 rounded-[32px] shadow-soft border border-black/[0.03] dark:border-slate-700 active:scale-[0.98] transition-transform">
            <div className="p-4 bg-brand-blue text-brand-white rounded-2xl"><Calendar size={32} /></div>
            <p className="font-black text-brand-gray-dark dark:text-brand-white text-base">Agenda</p>
          </button>
          <button onClick={() => setScreen('history')}
            className="flex flex-col items-center gap-4 bg-brand-white dark:bg-slate-800 p-8 rounded-[32px] shadow-soft border border-black/[0.03] dark:border-slate-700 active:scale-[0.98] transition-transform">
            <div className="p-4 bg-brand-gold text-brand-white rounded-2xl"><Bookmark size={32} /></div>
            <p className="font-black text-brand-gray-dark dark:text-brand-white text-base">Histórico</p>
          </button>
        </div>
      </div>
    </motion.div>
  )
}
