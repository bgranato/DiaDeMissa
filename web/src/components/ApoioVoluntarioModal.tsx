import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { Heart, LoaderCircle, X } from 'lucide-react'

import api from '../services/api'
import { conviteApoioEmPausa } from '../services/apoioExibicao'

type ConfiguracaoApoios = {
  ativo: boolean
  valores_centavos: number[]
  reexibir_em_dias: number
}

type Props = {
  missaId?: number
  modo?: 'automatico' | 'manual'
  onClose?: () => void
}

function formatoBRL(valorCentavos: number) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(valorCentavos / 100)
}

/** Oferta discreta. No modo automático, aparece após o bloco do Pai-Nosso. */
export function ApoioVoluntarioModal({ missaId, modo = 'automatico', onClose }: Props) {
  const [configuracao, setConfiguracao] = useState<ConfiguracaoApoios | null>(null)
  const [aberto, setAberto] = useState(modo === 'manual')
  const [enviando, setEnviando] = useState<number | null>(null)
  const [erro, setErro] = useState('')

  useEffect(() => {
    let ativo = true
    if (modo === 'automatico' && conviteApoioEmPausa()) return () => { ativo = false }

    api.get<ConfiguracaoApoios>('/apoios/configuracao')
      .then(({ data }) => {
        if (!ativo || !data.ativo || data.valores_centavos.length === 0) return
        setConfiguracao(data)
        if (modo === 'automatico') {
          window.setTimeout(() => {
            if (ativo) setAberto(true)
          }, 700)
        }
      })
      // A oferta é opcional: se a API não estiver disponível, a celebração segue normal.
      .catch(() => undefined)
    return () => { ativo = false }
  }, [modo])

  // Enquanto o convite está aberto, o conteúdo litúrgico não pode receber
  // rolagem nem cliques. O desbloqueio ocorre somente ao fechar o convite.
  useEffect(() => {
    if (!aberto) return
    const bodyOverflow = document.body.style.overflow
    const htmlOverflow = document.documentElement.style.overflow
    document.body.style.overflow = 'hidden'
    document.documentElement.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = bodyOverflow
      document.documentElement.style.overflow = htmlOverflow
    }
  }, [aberto])

  function fechar() {
    // Fechar é somente fechar: não grava pausa. Assim, quem não apoiou volta a
    // receber o convite ao retomar a missa; somente apoio aprovado descansa 24h.
    setAberto(false)
    onClose?.()
  }

  async function apoiar(valorCentavos: number) {
    setErro('')
    setEnviando(valorCentavos)
    try {
      const { data } = await api.post<{ checkout_url: string }>('/apoios/checkout', {
        valor_centavos: valorCentavos,
        missa_id: missaId,
      })
      if (!data.checkout_url.startsWith('https://')) throw new Error('Checkout inválido')
      window.location.assign(data.checkout_url)
    } catch {
      setErro('Não foi possível abrir o pagamento agora. Tente novamente mais tarde.')
      setEnviando(null)
    }
  }

  return (
    <AnimatePresence>
      {aberto && configuracao && (
        <motion.div
          className="fixed inset-0 z-[60] flex items-start justify-center overflow-y-auto overscroll-contain bg-brand-blue/65 px-3 py-[max(0.75rem,env(safe-area-inset-top))] sm:items-center sm:p-6 backdrop-blur-[1px]"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          role="dialog" aria-modal="true" aria-labelledby="apoio-titulo"
          onClick={fechar}
        >
          <motion.section
            className="relative max-h-[calc(100dvh-1.5rem)] w-full max-w-md overflow-y-auto rounded-[30px] bg-brand-white p-6 text-left shadow-2xl sm:max-h-[calc(100dvh-3rem)] sm:p-7 dark:bg-slate-900"
            initial={{ y: 32, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 32, opacity: 0 }}
            onClick={(event) => event.stopPropagation()}
          >
            <button onClick={fechar} aria-label="Fechar pedido de apoio" className="absolute right-4 top-4 rounded-full p-2 text-brand-gray-dark/60 hover:bg-brand-blue/5 hover:text-brand-blue dark:text-brand-white/60">
              <X size={19} />
            </button>
            <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-gold/15 text-brand-gold">
              <Heart size={22} fill="currentColor" />
            </div>
            <p className="mb-2 text-[10px] font-black uppercase tracking-[0.22em] text-brand-gold">Apoio voluntário</p>
            <h3 id="apoio-titulo" className="pr-8 text-2xl font-serif font-black text-brand-blue dark:text-brand-white">Se o Dia de Missa te ajudou, ajude a mantê-lo vivo.</h3>
            <p className="mt-3 text-sm leading-relaxed text-brand-gray-dark/70 dark:text-brand-white/70">
              O Dia de Missa é gratuito. Sua contribuição ajuda a manter o projeto vivo e permite que mais pessoas tenham acesso às liturgias.
            </p>
            <div className="mt-6 grid grid-cols-2 gap-3">
              {configuracao.valores_centavos.map((valor) => (
                <button key={valor} disabled={enviando !== null} onClick={() => apoiar(valor)} className="rounded-2xl border-2 border-brand-gold/35 px-2 py-4 text-center font-black text-brand-blue transition hover:border-brand-gold hover:bg-brand-gold hover:text-white disabled:cursor-wait disabled:opacity-60 dark:text-brand-white">
                  {enviando === valor ? <LoaderCircle className="mx-auto animate-spin" size={21} /> : formatoBRL(valor)}
                </button>
              ))}
            </div>
            {erro && <p role="alert" className="mt-4 text-center text-sm font-medium text-red-600">{erro}</p>}
            <p className="mt-5 text-center text-xs text-brand-gray-dark/55 dark:text-brand-white/55">Pix ou cartão, em ambiente seguro do Mercado Pago.</p>
            <button onClick={fechar} className="mt-4 w-full rounded-xl py-2 text-sm font-bold text-brand-gray-dark/70 underline decoration-brand-gold/60 underline-offset-4 dark:text-brand-white/70">Agora não, obrigado</button>
          </motion.section>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
