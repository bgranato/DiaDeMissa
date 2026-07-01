// Renderiza canto preservando a ordem original do folheto:
//   posicao_refrao_apos = null/0 → Refrão (box amarelo) → estrofes 1, 2, 3…
//   posicao_refrao_apos = N → estrofes 1..N → Refrão (box amarelo) → estrofes N+1..
// A caixa amarela contém SÓ o refrão. As estrofes ficam fora do box.

const RefraoBox = ({ refrao }: { refrao: string[] }) => (
  <div className="ds-card-subtle">
    <p className="ds-section-label mb-1.5">Refrão</p>
    <p className="ds-body font-bold text-slate-800 dark:text-slate-200 italic">
      {refrao.join(' / ')}
    </p>
  </div>
)

const Estrofe = ({ versos, numero }: { versos: string[]; numero: number }) => (
  <div className="flex gap-2.5 items-start">
    <span className="flex-shrink-0 w-5 h-5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-[10px] font-bold flex items-center justify-center mt-0.5">
      {numero}
    </span>
    <p className="flex-1 ds-body text-slate-700 dark:text-slate-300">
      {versos.join(' / ')}
    </p>
  </div>
)

export function CantoCard({ canto }: { canto: any }) {
  const refrao: string[] = canto.refrao || []
  const estrofes: string[][] = canto.estrofes || []
  const posRefraoApos: number | null | undefined =
    canto.posicao_refrao_apos ?? canto.posicaoRefraoApos
  const antifona = canto.antifona_anexada || canto.antifonaAnexada

  // Fallback: a liturgia diária (CNBB) traz Salmo/Aclamação como TEXTO PURO
  // (sem refrão/estrofes estruturados). Renderiza o conteúdo direto pra não
  // sair vazio — antes disso o card só sabia o formato do folheto da Arqrio.
  const textoSimples = canto.conteudo || canto.texto || ''
  if (refrao.length === 0 && estrofes.length === 0 && textoSimples) {
    return (
      <div className="px-4 pb-4 pt-3">
        <p className="ds-body text-slate-800 dark:text-slate-200 whitespace-pre-line">
          {textoSimples}
        </p>
      </div>
    )
  }

  const temRefrao = refrao.length > 0
  // Quantas estrofes vêm ANTES do refrão (0 = refrão no topo)
  const estrofesAntes = posRefraoApos && posRefraoApos > 0 ? posRefraoApos : 0

  return (
    <div className="px-4 pb-4 pt-3 ds-stack-sm">
      {/* Estrofes antes do refrão (1..N) */}
      {estrofesAntes > 0 && (
        <div className="ds-stack-sm">
          {estrofes.slice(0, estrofesAntes).map((versos, idx) => (
            <Estrofe key={`pre-${idx}`} versos={versos} numero={idx + 1} />
          ))}
        </div>
      )}

      {/* Refrão (caixa amarela) */}
      {temRefrao && <RefraoBox refrao={refrao} />}

      {/* Estrofes depois do refrão (N+1..end) */}
      {estrofes.length > estrofesAntes && (
        <div className="ds-stack-sm">
          {estrofes.slice(estrofesAntes).map((versos, idx) => (
            <Estrofe
              key={`pos-${idx}`}
              versos={versos}
              numero={estrofesAntes + idx + 1}
            />
          ))}
        </div>
      )}

      {/* Antífona anexada (Entrada / Comunhão) */}
      {antifona && (
        <div className="pt-3 mt-2 border-t border-slate-200 dark:border-slate-700">
          <p className="ds-section-label mb-1.5 text-brand-gold">{antifona.titulo}</p>
          <p className="ds-body italic text-slate-700 dark:text-slate-300 whitespace-pre-line">
            {antifona.texto}
          </p>
        </div>
      )}
    </div>
  )
}
