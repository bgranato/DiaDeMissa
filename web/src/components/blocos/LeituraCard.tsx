export function LeituraCard({ leitura }: { leitura: any }) {
  // referencia e introducao agora aparecem no header da ReadingScreen
  return (
    <div className="px-4 pb-4 space-y-3 pt-4">
      <div className="text-[17px] leading-[1.6] text-slate-800">
        {(leitura.versiculos || []).map((v: any, i: number) => (
          <span key={i}>
            <sup className="text-[11px] text-slate-400 font-semibold mr-0.5">{v.numero}</sup>
            {v.texto}{' '}
          </span>
        ))}
      </div>
      {leitura.conclusao && <p className="text-[16px] font-semibold text-slate-700 mt-3">{leitura.conclusao}</p>}
      {leitura.resposta && <p className="text-[16px] font-semibold text-amber-700">{leitura.resposta}</p>}
    </div>
  )
}
