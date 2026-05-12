import { PosturaChip } from './Shared'

export default function CantoCard({ bloco }: { bloco: any }) {
  const temEstruturaNova = Array.isArray(bloco.refrao) || Array.isArray(bloco.estrofes)

  if (!temEstruturaNova) {
    return (
      <div className="text-base leading-relaxed">
        {(bloco.conteudo || '').split('\n\n').map((p: string, i: number) => (
          <p key={i} className="mb-2">{p}</p>
        ))}
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <h3 className="font-serif font-black text-2xl text-brand-blue dark:text-brand-white">{bloco.titulo}</h3>
        <PosturaChip postura={bloco.postura} />
      </div>

      {(bloco.refrao || []).length > 0 && (
        <div className="bg-gradient-to-r from-brand-gold/[0.07] to-transparent rounded-2xl p-6 border-l-4 border-brand-gold mb-6">
          <span className="text-[10px] font-black text-brand-gold uppercase tracking-[0.3em] block mb-3">REFRÃO</span>
          {(bloco.refrao as string[]).map((v, i) => (
            <p key={i} className="text-lg font-semibold italic leading-relaxed text-brand-text dark:text-slate-100">{v}</p>
          ))}
        </div>
      )}

      {(bloco.estrofes || []).map((estrofe: string[], ei: number) => (
        <div key={ei} className="bg-brand-white dark:bg-slate-800 border border-black/5 dark:border-slate-700 rounded-2xl p-5 mb-4 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <span className="w-8 h-8 rounded-full bg-brand-blue/10 dark:bg-slate-700 flex items-center justify-center text-sm font-black text-brand-blue dark:text-brand-gold">{ei + 1}</span>
            <span className="text-[10px] font-black text-brand-gray-dark/40 dark:text-brand-white/40 uppercase tracking-[0.3em]">ESTROFE</span>
          </div>
          {estrofe.map((verso, vi) => (
            <p key={vi} className="text-base leading-relaxed font-medium text-brand-text dark:text-slate-200 mb-1 last:mb-0">{verso}</p>
          ))}
        </div>
      ))}
    </div>
  )
}
