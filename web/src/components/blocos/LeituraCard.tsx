export function LeituraCard({ leitura }: { leitura: any }) {
  // Formato antigo (Arquidiocese): bloco tem `versiculos[]` estruturados.
  // Formato novo (Canção Nova): bloco tem `conteudo` (texto puro com quebras de linha).
  const temVersiculosEstruturados = Array.isArray(leitura.versiculos) && leitura.versiculos.length > 0

  // Padrão global das leituras: termina com "Palavra do Senhor." (P) + "Graças a Deus." (T).
  // O Evangelho é dialogo separado (não cai aqui).
  const tituloLower = (leitura.titulo || '').toLowerCase()
  const ehLeituraBiblica = leitura.tipo === 'leitura' || tituloLower.includes('primeira leitura') || tituloLower.includes('segunda leitura')
  const conclusao = leitura.conclusao || (ehLeituraBiblica ? 'Palavra do Senhor.' : null)
  const resposta = leitura.resposta || (ehLeituraBiblica ? 'Graças a Deus.' : null)

  // Texto puro (liturgia diária CNBB). Se a conclusão/resposta vão aparecer
  // estruturadas no rodapé, removemos o "Palavra do Senhor / Graças a Deus" que
  // já vem no fim do texto — senão o fecho fica duplicado.
  const textoBruto = leitura.conteudo || leitura.texto || ''
  const textoSimples = (conclusao || resposta)
    ? textoBruto.replace(/[\s\-–—]*Palavra (do Senhor|da Salvação)\.?[\s\-–—]*(Graças a Deus|Gl[óo]ria a v[óo]s,?\s*Senhor)\.?\s*$/i, '').trimEnd()
    : textoBruto

  return (
    <div className="px-4 pb-4 pt-4 ds-stack-sm">
      {temVersiculosEstruturados ? (
        <div className="ds-body text-slate-800 dark:text-slate-200">
          {leitura.versiculos.map((v: any, i: number) => (
            <span key={i}>
              <sup className="text-[10px] text-brand-gold font-bold mr-0.5">{v.numero}</sup>
              {v.texto}{' '}
            </span>
          ))}
        </div>
      ) : (
        <div className="ds-body text-slate-800 dark:text-slate-200 whitespace-pre-line">
          {textoSimples}
        </div>
      )}
      {conclusao && (
        <div className="flex gap-2 items-start pt-2 border-t border-slate-100 dark:border-slate-700">
          <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-100 text-blue-700 text-[10px] font-bold flex items-center justify-center mt-0.5">P</span>
          <p className="ds-body text-slate-800 dark:text-slate-200 flex-1">{conclusao}</p>
        </div>
      )}
      {resposta && (
        <div className="flex gap-2 items-start">
          <span className="flex-shrink-0 w-5 h-5 rounded-full bg-amber-100 text-amber-700 text-[10px] font-bold flex items-center justify-center mt-0.5">T</span>
          <p className="ds-body font-bold text-slate-800 dark:text-slate-200 flex-1">{resposta}</p>
        </div>
      )}
    </div>
  )
}
