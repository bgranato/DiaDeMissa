const ESTILO_FALANTE: Record<string, { bg: string; label: string; peso: string }> = {
  P: { bg: 'bg-blue-100 text-blue-700', label: 'P', peso: 'font-normal' },
  T: { bg: 'bg-amber-100 text-amber-700', label: 'T', peso: 'font-semibold' },
  L: { bg: 'bg-slate-100 text-slate-600', label: 'L', peso: 'font-normal' },
  V: { bg: 'bg-slate-100 text-slate-600', label: 'V', peso: 'font-normal' },
  R: { bg: 'bg-amber-100 text-amber-700', label: 'R', peso: 'font-semibold' },
  rubrica: { bg: 'bg-slate-50 text-slate-500', label: '·', peso: 'font-normal italic' },
}

export function DialogoCard({ dialogo }: { dialogo: any }) {
  const turnos = dialogo.turnos || []
  return (
    <div className="px-4 pb-4 space-y-2">
      {turnos.map((turno: any, i: number) => {
        const estilo = ESTILO_FALANTE[turno.falante] || ESTILO_FALANTE.P
        return (
          <div key={i} className="flex gap-3 items-start py-1">
            <span className={`flex-shrink-0 w-7 h-7 rounded-full ${estilo.bg} text-xs font-bold flex items-center justify-center mt-0.5`}>
              {estilo.label}
            </span>
            <p className={`text-[17px] leading-[1.4] text-slate-800 flex-1 ${estilo.peso}`}>{turno.texto}</p>
          </div>
        )
      })}
      <div className="flex gap-4 pt-3 mt-2 border-t border-slate-100 text-[10px] text-slate-400">
        <span>P = Padre</span>
        <span>T = Todos</span>
      </div>
    </div>
  )
}
