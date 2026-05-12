import { PosturaChip } from './Shared'

export default function LeituraCard({ bloco }: { bloco: any }) {
  const versiculos = bloco.versiculos || []

  return (
    <div>
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <h3 className="font-serif font-black text-2xl text-brand-blue dark:text-brand-white">{bloco.titulo}</h3>
        {bloco.referencia && (
          <span className="px-3 py-1 rounded-full text-xs font-bold bg-brand-blue text-white">{bloco.referencia}</span>
        )}
        <PosturaChip postura={bloco.postura} />
      </div>

      {bloco.introducao && (
        <p className="italic text-brand-slate dark:text-gray-400 text-base mb-4 leading-relaxed">{bloco.introducao}</p>
      )}

      {versiculos.length > 0 ? (
        <div className="text-base leading-[2] text-brand-text dark:text-slate-200">
          {versiculos.map((v: any, i: number) => (
            <span key={i}>
              <sup className="text-[11px] text-brand-gray font-semibold mr-1">{v.numero}</sup>
              <span>{v.texto} </span>
            </span>
          ))}
        </div>
      ) : bloco.texto ? (
        <div className="text-base leading-relaxed">
          {(bloco.texto as string).split('\n\n').map((p: string, i: number) => (
            <p key={i} className="mb-3">{p}</p>
          ))}
        </div>
      ) : null}

      <div className="mt-6 pt-4 border-t border-black/5 dark:border-slate-700">
        {bloco.conclusao && (
          <p className="font-semibold italic text-brand-gray-dark dark:text-slate-300 text-base">{bloco.conclusao}</p>
        )}
        {(bloco.resposta as string) && (
          <p className="font-bold text-base text-brand-gold mt-1">{bloco.resposta}</p>
        )}
      </div>
    </div>
  )
}
