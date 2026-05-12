export function PosturaChip({ postura }: { postura: string | null | undefined }) {
  if (!postura) return null
  const icons: Record<string, string> = { de_pe: '🙏', sentado: '🪑', ajoelhado: '🧎' }
  const labels: Record<string, string> = { de_pe: 'De pé', sentado: 'Sentado', ajoelhado: 'Ajoelhado' }
  return (
    <span className="inline-flex items-center gap-1.5 px-4 py-1.5 bg-brand-gold/10 text-brand-gold rounded-full text-xs font-bold">
      <span>{icons[postura] || '•'}</span>
      <span>{labels[postura] || postura}</span>
    </span>
  )
}

export function RefraoBlock({ versos, className = '' }: { versos: string[], className?: string }) {
  return (
    <div className={`bg-gradient-to-r from-brand-gold/[0.07] to-transparent rounded-2xl p-6 border-l-4 border-brand-gold mb-6 ${className}`}>
      {versos.map((v, i) => (
        <p key={i} className="text-lg font-semibold italic leading-relaxed text-brand-text dark:text-slate-100">{v}</p>
      ))}
    </div>
  )
}
