import { useEffect } from 'react'
import { motion } from 'motion/react'
import { HeartHandshake, X } from 'lucide-react'

import { destravarRolagem, travarRolagem } from '../lib/scrollLock'

type Props = {
  onClose: () => void
}

/** Confirmação exibida dentro do app somente após o webhook aprovar o apoio. */
export function AgradecimentoApoioModal({ onClose }: Props) {
  useEffect(() => {
    travarRolagem()
    return destravarRolagem
  }, [])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[90] flex items-start justify-center overflow-y-auto overscroll-contain bg-brand-blue/70 px-3 py-[max(0.75rem,env(safe-area-inset-top))] backdrop-blur-[2px] sm:items-center sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="agradecimento-apoio-titulo"
      onClick={onClose}
    >
      <motion.section
        initial={{ y: 24, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 24, opacity: 0 }}
        className="relative max-h-[calc(100dvh-1.5rem)] w-full max-w-md overflow-y-auto rounded-[30px] bg-brand-white p-6 text-center shadow-2xl sm:max-h-[calc(100dvh-3rem)] sm:p-8 dark:bg-slate-900"
        onClick={event => event.stopPropagation()}
      >
        <button
          type="button"
          onClick={onClose}
          aria-label="Fechar agradecimento"
          className="absolute right-4 top-4 rounded-full p-2 text-brand-gray-dark/60 hover:bg-brand-blue/5 hover:text-brand-blue dark:text-brand-white/60"
        >
          <X size={19} />
        </button>
        <span className="mx-auto flex h-16 w-16 items-center justify-center rounded-[22px] bg-brand-gold/15 text-brand-gold">
          <HeartHandshake size={32} aria-hidden="true" />
        </span>
        <p className="mt-6 text-[10px] font-black uppercase tracking-[0.22em] text-brand-gold">Apoio confirmado</p>
        <h2 id="agradecimento-apoio-titulo" className="mt-3 pr-6 font-serif text-3xl font-black leading-tight text-brand-blue dark:text-brand-white">
          Obrigado por cuidar do Dia de Missa.
        </h2>
        <p className="mx-auto mt-4 max-w-sm text-sm leading-relaxed text-brand-gray-dark/70 dark:text-brand-white/70">
          Sua contribuição ajuda a manter este projeto disponível para mais pessoas.
        </p>
        <button type="button" onClick={onClose} className="mt-7 w-full rounded-2xl bg-brand-blue px-4 py-3 font-black text-white shadow-soft active:scale-[0.98] dark:bg-brand-gold dark:text-brand-blue">
          Continuar no Dia de Missa
        </button>
      </motion.section>
    </motion.div>
  )
}
