export function AntifonaCard({ antifona }: { antifona: any }) {
  // Referência já vem no header da ReadingScreen — não duplicar.
  // Se o texto tem barras `/` separando versos (ex.: Antífona Mariana), renderiza em múltiplas linhas.
  const texto: string = antifona.texto || ''
  const versos = texto.includes('/')
    ? texto.split('/').map(v => v.trim()).filter(Boolean)
    : [texto]
  return (
    <div className="px-4 pb-4 pt-4 space-y-1">
      {versos.map((v, i) => (
        <p key={i} className="text-[18px] leading-[1.5] text-slate-800 italic">{v}</p>
      ))}
    </div>
  )
}
