import { PosturaChip } from './Shared'

export default function DialogoCard({ bloco }: { bloco: any }) {
  const turnos = bloco.turnos || []

  const coresFalante: Record<string, string> = {
    P: 'text-brand-blue dark:text-brand-gold',
    T: 'text-brand-gray-dark dark:text-slate-300',
    L: 'text-brand-gold',
    V: 'text-brand-blue',
    R: 'text-brand-gray-dark',
    rubrica: 'text-brand-slate italic',
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <h3 className="font-serif font-black text-2xl text-brand-blue dark:text-brand-white">{bloco.titulo}</h3>
        <PosturaChip postura={bloco.postura} />
      </div>

      <div className="space-y-3">
        {turnos.map((t: any, i: number) => (
          <div key={i} className={`flex gap-4 ${t.falante === 'T' || t.falante === 'R' ? 'ml-8' : ''}`}>
            <span className={`font-bold text-sm min-w-[24px] uppercase ${coresFalante[t.falante] || 'text-brand-gray-dark'}`}>
              {t.falante === 'rubrica' ? '' : `${t.falante}.`}
            </span>
            <p className={`text-base leading-relaxed flex-1 ${t.falante === 'rubrica' ? 'italic text-brand-slate' : 'text-brand-text dark:text-slate-200'}`}>
              {t.texto}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
