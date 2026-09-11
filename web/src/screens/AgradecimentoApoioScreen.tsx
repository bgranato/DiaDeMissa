import { motion } from 'motion/react'
import { HeartHandshake, House } from 'lucide-react'
import { LargeButton } from '../components/UI'

export function AgradecimentoApoioScreen({ onFinish }: { onFinish: () => void }) {
  return (
    <motion.main
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      className="min-h-screen bg-brand-blue px-6 py-12 text-center text-white flex items-center justify-center"
    >
      <div className="w-full max-w-md">
        <span className="mx-auto flex h-20 w-20 items-center justify-center rounded-[28px] border border-brand-gold/50 bg-brand-gold/15 text-brand-gold shadow-2xl">
          <HeartHandshake size={40} aria-hidden="true" />
        </span>
        <p className="mt-8 text-[10px] font-black uppercase tracking-[0.24em] text-brand-gold">Apoio confirmado</p>
        <h1 className="mt-3 font-serif text-4xl font-black leading-tight">Obrigado por cuidar do Dia de Missa.</h1>
        <p className="mx-auto mt-5 max-w-sm text-base leading-relaxed text-white/80">Seu apoio ajuda a manter a liturgia acessível, gratuita e bem cuidada.</p>
        <LargeButton variant="secondary" icon={House} onClick={onFinish} className="mt-10 w-full">Voltar ao início</LargeButton>
      </div>
    </motion.main>
  )
}
