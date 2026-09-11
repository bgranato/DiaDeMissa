import { FormEvent, useState } from 'react'
import { motion } from 'motion/react'
import { Bug, CheckCircle2, Lightbulb, Send } from 'lucide-react'
import { AppHeader, Card, LargeButton } from '../components/UI'
import api from '../services/api'

type TipoFeedback = 'problema' | 'sugestao'

export const FeedbackScreen = ({ onBack, telaOrigem }: { onBack: () => void; telaOrigem?: string }) => {
  const [tipo, setTipo] = useState<TipoFeedback>('sugestao')
  const [mensagem, setMensagem] = useState('')
  const [email, setEmail] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState('')
  const [enviado, setEnviado] = useState(false)

  async function enviar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const texto = mensagem.trim()
    if (texto.length < 10) {
      setErro('Conte um pouco mais para conseguirmos entender.')
      return
    }
    setErro('')
    setEnviando(true)
    try {
      await api.post('/feedback', {
        tipo,
        mensagem: texto,
        email_contato: email.trim() || undefined,
        tela: telaOrigem || undefined,
      })
      setEnviado(true)
    } catch (error: any) {
      const detalhe = error?.response?.data?.detail
      setErro(typeof detalhe === 'string' ? detalhe : 'Não foi possível enviar agora. Tente novamente.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-h-screen bg-brand-bg dark:bg-slate-900 ds-bottom-nav-padding">
      <AppHeader title="Dicas e sugestões" onBack={onBack} />
      <main className="ds-container pt-6 flex flex-col gap-5">
        <Card className="border border-brand-gold/25 bg-brand-white dark:bg-slate-800">
          {enviado ? (
            <div className="py-6 text-center">
              <span className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-green-500/10 text-green-600">
                <CheckCircle2 size={30} aria-hidden="true" />
              </span>
              <h2 className="ds-headline text-brand-blue dark:text-brand-white">Mensagem recebida</h2>
              <p className="ds-body mt-3 text-brand-slate dark:text-brand-white/75">Obrigado por ajudar a melhorar o Dia de Missa.</p>
              <LargeButton onClick={onBack} variant="outline" size="md" className="mt-6">Voltar ao início</LargeButton>
            </div>
          ) : (
            <form onSubmit={enviar} className="flex flex-col gap-5" noValidate>
              <div>
                <p className="ds-section-label">Estamos ouvindo</p>
                <h2 className="ds-headline mt-2 text-brand-blue dark:text-brand-white">Como podemos melhorar?</h2>
                <p className="ds-body-sm mt-2 text-brand-slate dark:text-brand-white/75">Conte uma ideia ou descreva o que não funcionou.</p>
              </div>

              <div className="grid grid-cols-2 gap-3" role="group" aria-label="Tipo de mensagem">
                <button
                  type="button"
                  onClick={() => setTipo('sugestao')}
                  aria-pressed={tipo === 'sugestao'}
                  className={`rounded-2xl border-2 p-4 text-left transition-all active:scale-[0.98] ${tipo === 'sugestao' ? 'border-brand-gold bg-brand-gold/10 text-brand-blue dark:text-brand-white' : 'border-transparent bg-brand-bg dark:bg-slate-700 text-brand-gray-dark dark:text-brand-white'}`}
                >
                  <Lightbulb size={22} className="mb-2 text-brand-gold" aria-hidden="true" />
                  <span className="block text-sm font-black">Sugestão</span>
                  <span className="mt-1 block text-xs leading-relaxed opacity-70">Tenho uma ideia</span>
                </button>
                <button
                  type="button"
                  onClick={() => setTipo('problema')}
                  aria-pressed={tipo === 'problema'}
                  className={`rounded-2xl border-2 p-4 text-left transition-all active:scale-[0.98] ${tipo === 'problema' ? 'border-brand-gold bg-brand-gold/10 text-brand-blue dark:text-brand-white' : 'border-transparent bg-brand-bg dark:bg-slate-700 text-brand-gray-dark dark:text-brand-white'}`}
                >
                  <Bug size={22} className="mb-2 text-brand-gold" aria-hidden="true" />
                  <span className="block text-sm font-black">Problema</span>
                  <span className="mt-1 block text-xs leading-relaxed opacity-70">Algo não funcionou</span>
                </button>
              </div>

              <label className="flex flex-col gap-2">
                <span className="ds-caption font-black uppercase tracking-wider text-brand-gray-dark dark:text-brand-white">{tipo === 'problema' ? 'O que aconteceu?' : 'Qual é a sua ideia?'}</span>
                <textarea
                  value={mensagem}
                  onChange={event => setMensagem(event.target.value)}
                  maxLength={2000}
                  required
                  placeholder={tipo === 'problema' ? 'Descreva o que você tentou fazer e o que apareceu na tela.' : 'Conte a melhoria que faria diferença para você.'}
                  className="min-h-36 w-full resize-y rounded-2xl border border-black/10 bg-brand-bg p-4 text-sm leading-relaxed text-brand-text outline-none transition focus:border-brand-gold focus:ring-2 focus:ring-brand-gold/20 dark:border-white/10 dark:bg-slate-700 dark:text-white"
                />
                <span className="text-right text-xs text-brand-gray-dark/55 dark:text-brand-white/55">{mensagem.length}/2000</span>
              </label>

              <label className="flex flex-col gap-2">
                <span className="ds-caption font-black uppercase tracking-wider text-brand-gray-dark dark:text-brand-white">E-mail para retorno <span className="normal-case font-normal">opcional</span></span>
                <input
                  type="email"
                  value={email}
                  onChange={event => setEmail(event.target.value)}
                  maxLength={255}
                  placeholder="voce@exemplo.com"
                  className="w-full rounded-2xl border border-black/10 bg-brand-bg px-4 py-3.5 text-sm text-brand-text outline-none transition focus:border-brand-gold focus:ring-2 focus:ring-brand-gold/20 dark:border-white/10 dark:bg-slate-700 dark:text-white"
                />
              </label>

              {erro && <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm font-semibold text-red-700 dark:bg-red-950/30 dark:text-red-300">{erro}</p>}
              <LargeButton disabled={enviando} icon={Send} className="w-full">{enviando ? 'Enviando...' : 'Enviar mensagem'}</LargeButton>
            </form>
          )}
        </Card>
      </main>
    </motion.div>
  )
}
