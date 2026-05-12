export function AntifonaCard({ antifona }: { antifona: any }) {
  return (
    <div className="px-4 pb-4">
      {antifona.referencia && (
        <div className="inline-block bg-slate-100 text-slate-600 text-xs font-medium px-2 py-1 rounded mb-3">
          {antifona.referencia}
        </div>
      )}
      <p className="text-[18px] leading-[1.5] text-slate-800 italic">{antifona.texto}</p>
    </div>
  )
}
