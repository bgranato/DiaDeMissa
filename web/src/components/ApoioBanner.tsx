import { Heart } from 'lucide-react'

export function ApoioBanner({ onApoiar }: { onApoiar: () => void }) {
  return (
    <section className="relative left-1/2 w-screen -translate-x-1/2 overflow-hidden bg-brand-blue text-white">
      <div className="pointer-events-none absolute inset-0 opacity-40" aria-hidden="true">
        <div className="absolute -right-20 -top-24 h-64 w-64 rounded-full bg-brand-gold/25 blur-3xl" />
        <div className="absolute bottom-0 left-[18%] h-24 w-px bg-brand-gold/35" />
        <div className="absolute bottom-0 left-[calc(18%+8px)] h-14 w-px bg-brand-gold/20" />
      </div>
      <div className="ds-container relative flex flex-col gap-5 py-8 sm:flex-row sm:items-center sm:justify-between sm:gap-8 sm:py-9">
        <div className="flex items-start gap-4">
          <span className="mt-0.5 flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-2xl border border-brand-gold/50 bg-brand-gold/10 text-brand-gold">
            <Heart size={21} fill="currentColor" aria-hidden="true" />
          </span>
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-brand-gold">Apoio voluntário</p>
            <h2 className="mt-1 font-serif text-xl font-black leading-tight">Para manter o Dia de Missa gratuito</h2>
            <p className="mt-2 max-w-md text-sm leading-relaxed text-white/80">Se este serviço é útil para você, uma contribuição ajuda a mantê-lo disponível.</p>
          </div>
        </div>
        <button
          type="button"
          onClick={onApoiar}
          className="inline-flex min-h-12 flex-shrink-0 items-center justify-center rounded-2xl bg-brand-gold px-5 py-3 text-sm font-black text-white shadow-lg transition hover:brightness-105 active:scale-[0.98] focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-brand-blue"
        >
          Apoiar o Dia de Missa
        </button>
      </div>
    </section>
  )
}
