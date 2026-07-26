export function AntifonaCard({ antifona }: { antifona: any }) {
  // Antífonas Marianas (Regina Caeli, etc.) frequentemente vêm com `/` separando versos.
  const texto: string = antifona.texto || ''
  const versos = texto.includes('/')
    ? texto.split('/').map(v => v.trim()).filter(Boolean)
    : [texto]
  return (
    <div className="px-4 pb-4 pt-4 ds-stack-xs">
      {versos.map((v, i) => (
        <p key={i} className="ds-body italic text-slate-800 dark:text-slate-200">{v}</p>
      ))}
    </div>
  )
}
