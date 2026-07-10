// Mapeamento dos códigos de falante usados no folheto litúrgico:
//   P = Presidente (padre)        — fala da liturgia
//   T = Todos (assembleia)        — resposta em coro, em destaque
//   L = Leitor                    — leitor leigo (Salmo, Preces, 1ª e 2ª Leituras)
//   V = Versículo                 — solista de salmo/aclamação
//   R = Refrão (Resposta)         — refrão cantado pela assembleia
const ESTILO_FALANTE: Record<string, { bg: string; label: string; peso: string; nome: string }> = {
  P: { bg: 'bg-blue-100 text-blue-700', label: 'P', peso: 'font-normal', nome: 'Padre' },
  T: { bg: 'bg-amber-100 text-amber-700', label: 'T', peso: 'font-bold', nome: 'Todos' },
  L: { bg: 'bg-slate-100 text-slate-600', label: 'L', peso: 'font-normal', nome: 'Leitor' },
  V: { bg: 'bg-slate-100 text-slate-600', label: 'V', peso: 'font-normal', nome: 'Versículo' },
  R: { bg: 'bg-amber-100 text-amber-700', label: 'R', peso: 'font-bold', nome: 'Refrão' },
  rubrica: { bg: '', label: '', peso: '', nome: 'Rubrica' },
}

export function DialogoCard({ dialogo }: { dialogo: any }) {
  const turnosOriginais = dialogo.turnos || []

  // Mescla turnos CONSECUTIVOS do mesmo falante em um único parágrafo,
  // separando os textos por quebra dupla. Reduz altura sem perder semântica.
  const turnos: any[] = []
  for (const t of turnosOriginais) {
    const ultimo = turnos[turnos.length - 1]
    if (ultimo && ultimo.falante === t.falante && t.falante !== 'rubrica') {
      ultimo.texto = `${ultimo.texto}\n\n${t.texto}`
    } else {
      turnos.push({ ...t })
    }
  }

  // Coleta SÓ os papéis usados neste bloco pra mostrar a legenda contextual
  const papeisUsados = Array.from(new Set(
    turnos.map((t: any) => t.falante).filter((f: string) => f && f !== 'rubrica' && ESTILO_FALANTE[f])
  )) as string[]

  return (
    <div className="px-3 sm:px-4 pb-3 pt-3 ds-stack-sm">
      {turnos.map((turno: any, i: number) => {
        if (turno.falante === 'rubrica') {
          return (
            <p key={i} className="ds-caption text-right italic text-slate-400 px-2">
              ({turno.texto})
            </p>
          )
        }
        const estilo = ESTILO_FALANTE[turno.falante] || ESTILO_FALANTE.P
        const ehLongo = (turno.texto || '').length > 80
        // Sem uppercase forçado: o texto já vem do folheto com a caixa correta
        // (narrativa normal + palavras da instituição em MAIÚSCULAS). Fiel à
        // diagramação e aos destaques do folheto.
        if (ehLongo) {
          return (
            <p key={i} className={`ds-body text-slate-800 dark:text-slate-200 ${estilo.peso}`}>
              <span className={`inline-flex items-center justify-center w-5 h-5 rounded-full ${estilo.bg} text-[10px] font-bold mr-2 align-middle`}>
                {estilo.label}
              </span>
              <span className="align-middle">{turno.texto}</span>
            </p>
          )
        }
        return (
          <div key={i} className="flex gap-2 items-start">
            <span className={`flex-shrink-0 w-5 h-5 rounded-full ${estilo.bg} text-[10px] font-bold flex items-center justify-center mt-0.5`}>
              {estilo.label}
            </span>
            <p className={`ds-body text-slate-800 dark:text-slate-200 flex-1 ${estilo.peso}`}>
              {turno.texto}
            </p>
          </div>
        )
      })}
      {/* Legenda dinâmica — mostra só os papéis que aparecem neste bloco */}
      {papeisUsados.length > 0 && (
        <div className="flex gap-3 flex-wrap pt-2 mt-1 border-t border-slate-200 dark:border-slate-700 ds-caption text-slate-500">
          {papeisUsados.map(p => {
            const e = ESTILO_FALANTE[p]
            return (
              <span key={p} className="flex items-center gap-1.5">
                <span className={`w-4 h-4 rounded-full ${e.bg} text-[9px] font-bold flex items-center justify-center`}>{e.label}</span>
                = {e.nome}
              </span>
            )
          })}
        </div>
      )}
    </div>
  )
}
