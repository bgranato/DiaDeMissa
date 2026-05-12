export function CantoCard({ canto }: { canto: any }) {
  return (
    <div className="px-4 pb-4">
      {canto.refrao && canto.refrao.length > 0 && (
        <div className="bg-amber-50 border-l-4 border-amber-500 rounded-r-lg px-4 py-3 mb-3">
          <div className="text-[10px] font-bold tracking-widest text-amber-700 mb-1">REFRÃO</div>
          {canto.refrao.map((verso: string, i: number) => (
            <p key={i} className="text-[18px] leading-[1.4] font-medium text-slate-800 italic">{verso}</p>
          ))}
        </div>
      )}
      <div className="space-y-2">
        {(canto.estrofes || []).map((estrofe: string[], idx: number) => (
          <div key={idx} className="bg-white rounded-lg px-3 py-3 flex gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-slate-100 text-slate-600 text-xs font-semibold flex items-center justify-center mt-1">
              {idx + 1}
            </span>
            <div className="flex-1 space-y-1">
              {estrofe.map((verso: string, i: number) => (
                <p key={i} className="text-[17px] leading-[1.4] text-slate-700">{verso}</p>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
