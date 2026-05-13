const ESTILO_FALANTE: Record<string, { bg: string; label: string; peso: string }> = {
  P: { bg: 'bg-blue-100 text-blue-700', label: 'P', peso: 'font-normal' },
  T: { bg: 'bg-amber-100 text-amber-700', label: 'T', peso: 'font-bold' },
  L: { bg: 'bg-slate-100 text-slate-600', label: 'L', peso: 'font-normal' },
  V: { bg: 'bg-slate-100 text-slate-600', label: 'V', peso: 'font-normal' },
  R: { bg: 'bg-amber-100 text-amber-700', label: 'R', peso: 'font-bold' },
  rubrica: { bg: '', label: '', peso: '' },
}

export function DialogoCard({ dialogo }: { dialogo: any }) {
  const turnos = dialogo.turnos || []
  return (
    <div className="px-4 pb-4 space-y-2 pt-4">
      {turnos.map((turno: any, i: number) => {
        // Rubricas (asides como "O Presidente continua", "Momento de silêncio") — pequenas, à direita, em parênteses.
        if (turno.falante === 'rubrica') {
          return (
            <p key={i} className="text-right text-xs italic text-slate-400 px-2">
              ({turno.texto})
            </p>
          )
        }
        const estilo = ESTILO_FALANTE[turno.falante] || ESTILO_FALANTE.P
        return (
          <div key={i} className="flex gap-3 items-start py-1">
            <span className={`flex-shrink-0 w-7 h-7 rounded-full ${estilo.bg} text-xs font-bold flex items-center justify-center mt-0.5`}>
              {estilo.label}
            </span>
            <p className={`text-[20px] leading-[1.5] text-slate-800 flex-1 ${estilo.peso}`}>{turno.texto}</p>
          </div>
        )
      })}
      <div className="flex gap-4 pt-3 mt-2 border-t border-slate-200 text-[14px] text-slate-500">
        <span className="flex items-center gap-2">
          <span className={`w-6 h-6 rounded-full ${ESTILO_FALANTE.P.bg} text-xs font-bold flex items-center justify-center`}>P</span>
          = Padre
        </span>
        <span className="flex items-center gap-2">
          <span className={`w-6 h-6 rounded-full ${ESTILO_FALANTE.T.bg} text-xs font-bold flex items-center justify-center`}>T</span>
          = Todos
        </span>
      </div>
    </div>
  )
}
