import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { Card, LargeButton, AccessibilityControls, PrayingHandsIcon } from '../components/UI'
import { ApoioBanner } from '../components/ApoioBanner'
import { ApoioVoluntarioModal } from '../components/ApoioVoluntarioModal'
import { Play, Bell, ArrowRight, CheckCircle2, Calendar, ScrollText, Settings2, Church, Search, MapPin, X, User, CalendarClock, ChevronDown, LogOut, MessageCircleHeart } from 'lucide-react'
import type { Missa } from '../types/missa'
import type { Igreja } from '../types/igreja'
import { minhasIgrejas, buscarIgrejas } from '../services/igrejas'
import { getUltimaMissaDisponivel, type MissaDisponivel } from '../services/missa'
import api from '../services/api'

interface Props {
  setScreen: (s: string) => void
  missa: Missa | null
  nome: string
  estaAutenticado: boolean
  onLogout?: () => void | Promise<void>
}

type StatusMissa = 'nao_iniciada' | 'em_progresso' | 'concluida'

function statusDaMissa(data: string | undefined | null): StatusMissa {
  if (!data) return 'nao_iniciada'
  if (localStorage.getItem(`@missa_concluida_${data}`) === 'true') return 'concluida'
  if (localStorage.getItem(`@missa_iniciada_${data}`) === 'true') return 'em_progresso'
  return 'nao_iniciada'
}

export const HomeScreen = ({ setScreen, missa, nome, estaAutenticado, onLogout }: Props) => {
  const [descricaoExpandida, setDescricaoExpandida] = useState(false)
  // Status pode ser desfeito localmente sem reload — guardamos override em state
  const [statusOverride, setStatusOverride] = useState<StatusMissa | null>(null)
  const status = statusOverride ?? statusDaMissa(missa?.data)
  const [lembretesNaoLidos, setLembretesNaoLidos] = useState(0)
  const [showAcessibilidade, setShowAcessibilidade] = useState(false)
  const [showMenuConta, setShowMenuConta] = useState(false)
  const [ultimaMissa, setUltimaMissa] = useState<MissaDisponivel | null>(null)

  // Seletor de igreja
  const [igrejaSelecionada, setIgrejaSelecionada] = useState<{ id: number; nome: string } | null>(null)
  const [showSeletor, setShowSeletor] = useState(false)
  const [salvas, setSalvas] = useState<Igreja[]>([])
  const [buscaIgreja, setBuscaIgreja] = useState('')
  const [resultadosBusca, setResultadosBusca] = useState<Igreja[]>([])
  const [buscando, setBuscando] = useState(false)
  const [apoiosAtivos, setApoiosAtivos] = useState(false)
  const [apoioAberto, setApoioAberto] = useState(false)

  useEffect(() => {
    let ativo = true
    api.get<{ ativo?: boolean }>('/apoios/configuracao')
      .then(({ data }) => { if (ativo) setApoiosAtivos(data.ativo === true) })
      .catch(() => { if (ativo) setApoiosAtivos(false) })
    return () => { ativo = false }
  }, [])

  useEffect(() => {
    if (!estaAutenticado) {
      setLembretesNaoLidos(0)
      return
    }
    api.get<Array<{ lido?: boolean }>>('/usuarios/me/lembretes')
      .then(r => setLembretesNaoLidos(r.data.filter(l => !l.lido).length))
      .catch(() => setLembretesNaoLidos(0))
  }, [estaAutenticado])

  // Conteúdo anterior é exclusivo da conta. Visitantes nunca recebem uma missa
  // passada como substituta da missa do dia.
  useEffect(() => {
    if (missa || !estaAutenticado) {
      setUltimaMissa(null)
      return
    }
    getUltimaMissaDisponivel().then(setUltimaMissa).catch(() => setUltimaMissa(null))
  }, [missa, estaAutenticado])

  // Sincroniza concluída do localStorage com o backend — UMA VEZ por sessão por missa.
  // sessionStorage evita re-sync a cada re-mount da Home.
  useEffect(() => {
    if (!estaAutenticado || !missa?.id || !missa?.data) return
    const sessionKey = `@sync_concluida_${missa.id}`
    if (sessionStorage.getItem(sessionKey)) return  // já sincronizou nesta sessão
    if (localStorage.getItem(`@missa_concluida_${missa.data}`) === 'true') {
      sessionStorage.setItem(sessionKey, '1')
      api.post(`/usuarios/me/historico/${missa.id}/concluir`).catch(() => {
        sessionStorage.removeItem(sessionKey)  // permite retry se falhou
      })
    }
  }, [estaAutenticado, missa?.id, missa?.data])

  // Carrega igreja salva pra missa de hoje + lista de favoritas
  useEffect(() => {
    if (!missa?.data) return
    const raw = localStorage.getItem(`@missa_igreja_${missa.data}`)
    if (raw) {
      try { setIgrejaSelecionada(JSON.parse(raw)) } catch {}
    }
  }, [missa?.data])

  async function abrirSeletor() {
    setShowSeletor(true)
    setBuscaIgreja('')
    setResultadosBusca([])
    if (!estaAutenticado) {
      setSalvas([])
      return
    }
    try { setSalvas(await minhasIgrejas()) } catch { setSalvas([]) }
  }

  async function fazerBuscaIgreja() {
    if (!buscaIgreja.trim()) { setResultadosBusca([]); return }
    setBuscando(true)
    try {
      const r = await buscarIgrejas({ q: buscaIgreja.trim() })
      setResultadosBusca(r)
    } catch { setResultadosBusca([]) }
    finally { setBuscando(false) }
  }

  function selecionarIgreja(ig: Igreja) {
    const escolha = { id: ig.id, nome: ig.nome }
    setIgrejaSelecionada(escolha)
    if (missa?.data) {
      localStorage.setItem(`@missa_igreja_${missa.data}`, JSON.stringify(escolha))
    }
    setShowSeletor(false)
    // Registra no histórico (igreja_id)
    if (estaAutenticado && missa?.id) {
      api.post('/usuarios/me/historico', {
        missa_id: missa.id,
        ultimo_bloco_id: 0,
        percentual_lido: 0,
        igreja_id: ig.id,
      }).catch(() => {})
    }
  }

  function excluirLocal() {
    setIgrejaSelecionada(null)
    if (missa?.data) {
      localStorage.removeItem(`@missa_igreja_${missa.data}`)
    }
    // Limpa também no histórico no backend
    if (estaAutenticado && missa?.id) {
      api.post('/usuarios/me/historico', {
        missa_id: missa.id,
        ultimo_bloco_id: 0,
        percentual_lido: 0,
        igreja_id: null,
      }).catch(() => {})
    }
  }

  function abrirUltimaMissa() {
    if (!ultimaMissa) return
    localStorage.setItem('@missa_data_alvo', ultimaMissa.data)
    setScreen('reading')
  }

  function abrirMissaDisponivel() {
    if (!missa?.data) return
    localStorage.setItem('@missa_data_alvo', missa.data)
    setScreen('reading')
  }

  const partesHoje = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date())
  const parteHoje = (tipo: Intl.DateTimeFormatPartTypes) => partesHoje.find(p => p.type === tipo)?.value ?? ''
  const hojeEmBrasilia = `${parteHoje('year')}-${parteHoje('month')}-${parteHoje('day')}`
  const missaEhDoDia = missa?.data === hojeEmBrasilia

  const dataUltimaMissaFormatada = ultimaMissa?.data
    ? new Date(ultimaMissa.data + 'T12:00:00').toLocaleDateString('pt-BR')
    : ''
  const dataFormatada = missa?.data
    ? new Date(missa.data + 'T12:00:00').toLocaleDateString('pt-BR', { day: 'numeric', month: 'long', year: 'numeric' }).toUpperCase()
    : ''

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="ds-container py-6 ds-bottom-nav-padding flex flex-col gap-5">
      <AnimatePresence>
        {showAcessibilidade && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            className="fixed top-20 left-1/2 -translate-x-1/2 z-50 w-[calc(100%-3rem)] max-w-lg"
          >
            <AccessibilityControls onClose={() => setShowAcessibilidade(false)} />
          </motion.div>
        )}
      </AnimatePresence>
      <header className="relative flex justify-between items-start gap-3">
        {showMenuConta && (
          <button
            type="button"
            aria-label="Fechar menu da conta"
            className="fixed inset-0 z-40 cursor-default"
            onClick={() => setShowMenuConta(false)}
          />
        )}
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <div className="relative flex-shrink-0">
            <span className="flex h-11 w-11 items-center justify-center rounded-full bg-brand-gold shadow-soft">
              <User size={22} className="text-white" />
            </span>
            {estaAutenticado && (
              <button
                type="button"
                aria-label="Abrir menu da conta"
                aria-expanded={showMenuConta}
                onClick={() => setShowMenuConta(!showMenuConta)}
                className="absolute -bottom-2 left-1/2 z-50 flex h-5 w-5 -translate-x-1/2 items-center justify-center rounded-full border border-brand-white bg-brand-blue text-white shadow-soft active:scale-90"
              >
                <ChevronDown size={14} strokeWidth={3} />
              </button>
            )}
            <AnimatePresence>
              {showMenuConta && (
                <motion.div
                  initial={{ opacity: 0, y: -6, scale: 0.97 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -6, scale: 0.97 }}
                  className="absolute left-0 top-[calc(100%+1rem)] z-50 w-52 overflow-hidden rounded-2xl border border-black/5 bg-brand-white py-1 shadow-xl dark:border-white/10 dark:bg-slate-800"
                >
                  <button
                    type="button"
                    onClick={() => { setShowMenuConta(false); setScreen('profile') }}
                    className="flex w-full items-center gap-3 px-4 py-3 text-left text-sm font-bold text-brand-blue hover:bg-brand-gold/10 dark:text-brand-white"
                  >
                    <User size={17} className="text-brand-gold" />
                    Minha conta
                  </button>
                  <button
                    type="button"
                    onClick={() => { setShowMenuConta(false); void onLogout?.() }}
                    className="flex w-full items-center gap-3 px-4 py-3 text-left text-sm font-bold text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30"
                  >
                    <LogOut size={17} />
                    Sair
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          {estaAutenticado ? (
            <span className="min-w-0">
              <span className="block ds-title text-brand-gray-dark dark:text-brand-white truncate">Olá, {nome}!</span>
              <span className="block ds-body-sm italic text-brand-blue/70 dark:text-brand-gold/70">O Senhor esteja convosco.</span>
            </span>
          ) : (
            <button onClick={() => setScreen('login')} title="Cadastrar ou entrar" className="min-w-0 text-left active:opacity-70 transition-opacity">
              <span className="block ds-title text-brand-gray-dark dark:text-brand-white truncate">Olá, {nome}!</span>
              <span className="block ds-body-sm italic text-brand-blue/70 dark:text-brand-gold/70">O Senhor esteja convosco.</span>
              <span className="mt-1 inline-flex rounded-full border border-brand-gold/40 px-2 py-0.5 text-[10px] font-black uppercase tracking-wide text-brand-gold">Cadastrar</span>
            </button>
          )}
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <button
            type="button"
            onClick={() => setScreen('feedback')}
            className="p-2.5 rounded-2xl shadow-soft border border-black/5 dark:border-white/5 bg-brand-white dark:bg-slate-800 text-brand-blue dark:text-brand-gold active:scale-95 transition-all"
            title="Dicas e sugestões"
            aria-label="Dicas e sugestões"
          >
            <MessageCircleHeart size={20} />
          </button>
          <button onClick={() => setShowAcessibilidade(!showAcessibilidade)}
            className={`p-2.5 rounded-2xl shadow-soft border border-black/5 dark:border-white/5 active:scale-95 transition-all ${
              showAcessibilidade ? 'bg-brand-gold text-white' : 'bg-brand-white dark:bg-slate-800 text-brand-blue dark:text-brand-gold'
            }`}
            title="Acessibilidade"
            aria-label="Acessibilidade">
            <Settings2 size={20} />
          </button>
          {estaAutenticado && <button onClick={() => setScreen('reminders')}
            className="p-2.5 bg-brand-white dark:bg-slate-800 rounded-2xl shadow-soft border border-black/5 dark:border-white/5 text-brand-blue dark:text-brand-gold active:scale-95 transition-transform"
            title="Notificações"
            aria-label="Notificações">
            <span className="relative inline-flex">
              <Bell size={20} />
              {lembretesNaoLidos > 0 && (
                <span className="absolute -top-1 -right-1.5 min-w-[16px] h-4 px-1 rounded-full bg-red-500 text-white text-[9px] font-black flex items-center justify-center">
                  {lembretesNaoLidos > 9 ? '9+' : lembretesNaoLidos}
                </span>
              )}
            </span>
          </button>}
        </div>
      </header>

      {missa?.palavra_do_dia && (
        <div className="ds-card text-center">
          <p className="ds-section-label mb-3">Evangelho do Dia</p>
          <p className="font-serif italic font-bold text-base sm:text-lg leading-relaxed text-brand-blue dark:text-brand-white break-words">
            "{missa.palavra_do_dia.texto}"
          </p>
          <div className="w-12 h-1 bg-brand-gold/30 mx-auto mt-5 mb-2 rounded-full" />
          <p className="ds-body-sm italic text-brand-slate">{missa.palavra_do_dia.referencia}</p>
        </div>
      )}

      {missa ? (
        <Card className="ds-card-feature overflow-hidden relative">
          <div className="relative z-10">
            <div className="flex items-center justify-between gap-2 mb-3 flex-wrap">
              <span className="ds-section-label">{missaEhDoDia ? 'Missa do Dia' : 'Missa disponível'}</span>
              <span className="ds-pill ds-pill-gold">{dataFormatada}</span>
            </div>

            {/* TÍTULO PRINCIPAL */}
            <h3 className="ds-display text-brand-blue dark:text-brand-white mb-2 break-words">
              {missa.celebracao || 'Missa do Dia'}
            </h3>

            {/* SUBTÍTULO */}
            {missa.subtitulo && (
              <p className="ds-body-sm font-semibold text-brand-slate dark:text-brand-gold/80 mb-3">
                {missa.subtitulo}
              </p>
            )}

            {/* DESCRIÇÃO — accordion 3 linhas */}
            {missa.descricao && (
              <div className="mb-5">
                <p className="ds-body text-brand-text/75 dark:text-brand-white/75"
                   style={!descricaoExpandida ? {
                     overflow: 'hidden',
                     display: '-webkit-box',
                     WebkitBoxOrient: 'vertical',
                     WebkitLineClamp: 3,
                     textOverflow: 'ellipsis',
                   } : {}}>
                  {missa.descricao}
                </p>
                {missa.descricao.length > 160 && (
                  <button onClick={() => setDescricaoExpandida(!descricaoExpandida)}
                    className="ds-caption font-bold text-brand-gold mt-1 hover:opacity-80 active:scale-95 transition-transform">
                    {descricaoExpandida ? '↑ Ver menos' : '↓ Ver mais'}
                  </button>
                )}
              </div>
            )}

            <div className="flex flex-col gap-3">
              <LargeButton variant="primary" onClick={abrirMissaDisponivel} icon={Play} className="w-full">
                {missaEhDoDia ? 'Acompanhar Missa' : 'Ver missa'}
              </LargeButton>

              {/* Recursos de igreja e histórico são pessoais e exigem conta. */}
              {estaAutenticado && <div className="flex items-center justify-between gap-3 pt-1">
                <button onClick={abrirSeletor}
                  className="flex items-center gap-2 min-w-0 flex-1 text-left active:opacity-70 transition-opacity">
                  <MapPin size={18} className="text-brand-gold flex-shrink-0" />
                  {igrejaSelecionada ? (
                    <span className="text-sm font-bold text-brand-blue dark:text-brand-white truncate">{igrejaSelecionada.nome}</span>
                  ) : (
                    <span className="text-sm font-bold text-brand-gold">Atribuir local da missa</span>
                  )}
                </button>
                {igrejaSelecionada && (
                  <button onClick={excluirLocal}
                    title="Remover local"
                    className="flex-shrink-0 p-1.5 rounded-full text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 active:scale-90 transition-all">
                    <X size={16} />
                  </button>
                )}
                {status === 'concluida' && missa?.data && (
                  <div className="flex-shrink-0 flex items-center gap-1 px-2 py-1 rounded-full bg-green-500/10">
                    <CheckCircle2 size={18} className="text-green-500" />
                    <span className="text-[10px] font-black uppercase tracking-wider text-green-700">Concluída</span>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault()
                        e.stopPropagation()
                        // SEM confirm, SEM async, SEM reload — apenas limpa estado.
                        const d = missa.data!
                        localStorage.removeItem(`@missa_concluida_${d}`)
                        localStorage.removeItem(`@missa_iniciada_${d}`)
                        setStatusOverride('nao_iniciada')
                        // Backend em fire-and-forget (não bloqueia UI)
                        if (missa.id) {
                          api.post(`/usuarios/me/historico/${missa.id}/desconcluir`).catch(() => { })
                        }
                      }}
                      title="Desmarcar conclusão"
                      className="ml-1 p-0.5 rounded-full text-green-700 hover:bg-red-500 hover:text-white transition-colors"
                    >
                      <X size={14} strokeWidth={3} />
                    </button>
                  </div>
                )}
              </div>}
            </div>
          </div>
          <div className="absolute -bottom-10 -right-10 w-48 h-48 bg-brand-blue opacity-5 rounded-full blur-3xl" />
        </Card>
      ) : (
        <Card className="ds-card-feature overflow-hidden relative">
          <div className="relative z-10 flex flex-col items-center text-center gap-3 py-4">
            <span className="p-3 rounded-2xl bg-brand-gold/10 text-brand-gold">
              <CalendarClock size={28} />
            </span>
            <span className="ds-section-label">Não há missa hoje</span>
            <p className="ds-body text-brand-text/70 dark:text-brand-white/70 max-w-sm">
              O folheto está disponível aos sábados (à noite), domingos e solenidades.
            </p>
            {ultimaMissa ? (
              <button
                type="button"
                onClick={abrirUltimaMissa}
                className="mt-2 inline-flex max-w-full items-center justify-center gap-2 rounded-2xl bg-brand-gold px-4 py-3 text-sm font-black text-white shadow-soft transition-all hover:brightness-95 active:scale-95"
              >
                <span className="truncate">Ver missa do dia {dataUltimaMissaFormatada}</span>
                <ArrowRight size={17} className="flex-shrink-0" aria-hidden="true" />
              </button>
            ) : (
              <p className="ds-body-sm italic text-brand-slate mt-1">
                Assim que o próximo folheto for publicado, a missa aparece aqui.
              </p>
            )}
          </div>
          <div className="absolute -bottom-10 -right-10 w-48 h-48 bg-brand-blue opacity-5 rounded-full blur-3xl" />
        </Card>
      )}

      <section className="flex flex-col gap-3">
        <h4 className="ds-section-label opacity-60 ml-1">Explorar</h4>
        <div className="grid grid-cols-2 gap-3">
          {[
            { id: 'igrejas-salvas', icon: Church, label: 'Minhas Igrejas', onClick: () => { localStorage.setItem('@igrejas_aba_inicial', 'salvas'); setScreen('igrejas') } },
            { id: 'igrejas-buscar', icon: Search, label: 'Buscar Igreja', onClick: () => { localStorage.setItem('@igrejas_aba_inicial', 'buscar'); setScreen('igrejas') } },
            { id: 'calendar', icon: Calendar, label: 'Agenda de Missas', onClick: () => setScreen('calendar') },
            { id: 'history', icon: ScrollText, label: 'Minha Jornada', onClick: () => setScreen('history') },
            { id: 'oracoes', icon: PrayingHandsIcon, label: 'Orações', onClick: () => setScreen('oracoes') },
            estaAutenticado
              ? { id: 'reminders', icon: Bell, label: 'Lembretes', onClick: () => setScreen('reminders') }
              : { id: 'cadastro', icon: User, label: 'Cadastrar', onClick: () => setScreen('login') },
          ].map(({ id, icon: Icon, label, onClick }) => (
            <button key={id} onClick={onClick}
              className="ds-card flex flex-col items-center gap-3 active:scale-[0.97] transition-transform min-w-0">
              <span className="p-3 bg-brand-gold text-white rounded-2xl flex-shrink-0">
                <Icon size={24} />
              </span>
              <span className="ds-body-strong text-brand-gray-dark dark:text-brand-white text-center break-words leading-tight">
                {label}
              </span>
            </button>
          ))}
        </div>
      </section>

      {apoiosAtivos && <ApoioBanner onApoiar={() => setApoioAberto(true)} />}

      {apoioAberto && (
        <ApoioVoluntarioModal
          missaId={missa?.id}
          modo="manual"
          onClose={() => setApoioAberto(false)}
        />
      )}

      {/* Modal: seleciona igreja onde está assistindo */}
      <AnimatePresence>
        {showSeletor && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/50 flex items-end sm:items-center justify-center"
            onClick={() => setShowSeletor(false)}>
            <motion.div
              initial={{ y: 40 }} animate={{ y: 0 }} exit={{ y: 40 }}
              className="bg-white dark:bg-slate-900 rounded-t-[32px] sm:rounded-[32px] w-full max-w-lg max-h-[85vh] flex flex-col"
              onClick={e => e.stopPropagation()}>
              <div className="flex items-center justify-between p-6 pb-4">
                <div>
                  <p className="text-[10px] font-black text-brand-gold uppercase tracking-[0.3em]">Onde você está</p>
                  <h3 className="text-xl font-serif font-black text-brand-blue dark:text-brand-white mt-1">Selecione a igreja</h3>
                </div>
                <button onClick={() => setShowSeletor(false)} className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-slate-800">
                  <X size={20} />
                </button>
              </div>

              {/* Busca dentro do modal */}
              <div className="px-6 pb-3">
                <div className="flex items-center gap-2 bg-gray-100 dark:bg-slate-800 rounded-2xl pl-4 pr-2 py-2">
                  <Search size={18} className="text-brand-gold flex-shrink-0" />
                  <input
                    value={buscaIgreja}
                    onChange={e => setBuscaIgreja(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && fazerBuscaIgreja()}
                    placeholder="Buscar outra igreja (nome, bairro...)"
                    className="bg-transparent w-full text-sm font-medium outline-none placeholder:text-gray-400 dark:text-white"
                  />
                  <button onClick={fazerBuscaIgreja} disabled={buscando}
                    className="flex-shrink-0 w-9 h-9 rounded-xl bg-brand-blue text-white dark:bg-brand-gold dark:text-brand-blue flex items-center justify-center active:scale-95 disabled:opacity-60">
                    <Search size={16} />
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto px-6 pb-6 flex flex-col gap-2">
                {/* Seção: resultados de busca */}
                {resultadosBusca.length > 0 && (
                  <>
                    <p className="text-[10px] font-black text-brand-gold uppercase tracking-[0.3em] mt-1 mb-1">Resultados</p>
                    {resultadosBusca.map(ig => (
                      <button key={`r-${ig.id}`} onClick={() => selecionarIgreja(ig)}
                        className={`flex items-start gap-3 p-4 rounded-2xl border-2 text-left transition-all active:scale-[0.99] ${
                          igrejaSelecionada?.id === ig.id
                            ? 'bg-brand-gold/10 border-brand-gold'
                            : 'bg-brand-white dark:bg-slate-800 border-transparent hover:border-brand-gold/30'
                        }`}>
                        <Church size={20} className="text-brand-gold mt-0.5 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="font-black text-brand-gray-dark dark:text-brand-white text-sm leading-tight">{ig.nome}</p>
                          {ig.endereco && (
                            <p className="text-xs text-brand-gray-dark/60 dark:text-brand-white/60 mt-1 truncate">{ig.endereco}</p>
                          )}
                        </div>
                      </button>
                    ))}
                  </>
                )}

                {/* Seção: Minhas Igrejas (sempre) */}
                {salvas.length > 0 && (
                  <>
                    <p className="text-[10px] font-black text-brand-gold uppercase tracking-[0.3em] mt-3 mb-1">Minhas Igrejas</p>
                    {salvas.map(ig => (
                      <button key={`s-${ig.id}`} onClick={() => selecionarIgreja(ig)}
                        className={`flex items-start gap-3 p-4 rounded-2xl border-2 text-left transition-all active:scale-[0.99] ${
                          igrejaSelecionada?.id === ig.id
                            ? 'bg-brand-gold/10 border-brand-gold'
                            : 'bg-brand-white dark:bg-slate-800 border-transparent hover:border-brand-gold/30'
                        }`}>
                        <Church size={20} className="text-brand-gold mt-0.5 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="font-black text-brand-gray-dark dark:text-brand-white text-sm leading-tight">{ig.nome}</p>
                          {ig.endereco && (
                            <p className="text-xs text-brand-gray-dark/60 dark:text-brand-white/60 mt-1 truncate">{ig.endereco}</p>
                          )}
                        </div>
                      </button>
                    ))}
                  </>
                )}

                {salvas.length === 0 && resultadosBusca.length === 0 && !buscando && (
                  <div className="text-center py-6">
                    <Church size={40} className="mx-auto text-brand-gold/40 mb-3" />
                    <p className="text-sm text-brand-gray-dark/60 dark:text-brand-white/60">
                      Use a busca acima pra encontrar uma igreja
                    </p>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
