import { useEffect, useRef, useState } from 'react'
import { motion } from 'motion/react'
import { AppHeader, Card } from '../components/UI'
import { Church, Search, MapPin, Heart, Phone, Globe, Navigation, ExternalLink, Clock } from 'lucide-react'
import { buscarIgrejas, localizarEndereco, minhasIgrejas, favoritarIgreja, desfavoritarIgreja } from '../services/igrejas'
import type { Igreja } from '../types/igreja'

interface Props {
  setScreen: (s: string) => void
  estaAutenticado?: boolean
}

type Aba = 'salvas' | 'buscar' | 'proximas'
type OrigemProximidade = 'atual' | 'endereco'

function pontoValido(ponto: { lat: number; lng: number }) {
  return Number.isFinite(ponto.lat) && Number.isFinite(ponto.lng)
    && ponto.lat >= -90 && ponto.lat <= 90 && ponto.lng >= -180 && ponto.lng <= 180
}

// Remove igrejas duplicadas (mesma paróquia vinda de fontes diferentes — ex.: catálogo
// da Arquidiocese + Google/OSM). Agrupa por TELEFONE (sinal forte) ou, na falta,
// por endereço normalizado. Mantém o card mais completo (o que tiver horários).
function dedupIgrejas(lista: Igreja[]): Igreja[] {
  const norm = (s?: string) =>
    (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]/g, '')
  const indicePorChave = new Map<string, number>()
  const out: Igreja[] = []
  for (const ig of lista) {
    const tel = (ig.telefone || '').replace(/\D/g, '')
    const chave = tel.length >= 8 ? 'tel:' + tel.slice(-9) : 'end:' + norm(ig.endereco).slice(0, 28)
    if (chave === 'end:' && !ig.endereco) { out.push(ig); continue } // sem sinal → mantém
    if (!indicePorChave.has(chave)) {
      indicePorChave.set(chave, out.length)
      out.push(ig)
      continue
    }
    const idx = indicePorChave.get(chave)!
    const atual = out[idx]
    // Prefere o que tem horários; senão, mantém o primeiro.
    const atualTemHorario = !!(atual.horarios_missa && atual.horarios_missa.trim())
    const novoTemHorario = !!(ig.horarios_missa && ig.horarios_missa.trim())
    if (novoTemHorario && !atualTemHorario) out[idx] = ig
  }
  return out
}

export const IgrejasScreen = ({ setScreen, estaAutenticado = true }: Props) => {
  const [aba, setAba] = useState<Aba>(() => {
    const inicial = localStorage.getItem('@igrejas_aba_inicial') as Aba | null
    localStorage.removeItem('@igrejas_aba_inicial')  // consome uma vez
    if (!estaAutenticado) return inicial && ['buscar', 'proximas'].includes(inicial) ? inicial : 'buscar'
    return inicial && ['salvas', 'buscar', 'proximas'].includes(inicial) ? inicial : 'salvas'
  })
  const [busca, setBusca] = useState('')
  const [igrejas, setIgrejas] = useState<Igreja[]>([])
  const [loading, setLoading] = useState(false)
  const [geoErro, setGeoErro] = useState('')
  const [erroBusca, setErroBusca] = useState('')
  // Localização confirmada pela pessoa; evita solicitar permissão sem uma ação explícita.
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null)
  const [raioKm, setRaioKm] = useState(5)
  const [origemProximidade, setOrigemProximidade] = useState<OrigemProximidade>('atual')
  const [enderecoProximidade, setEnderecoProximidade] = useState('')
  const consultaAtual = useRef(0)
  const abortadorBusca = useRef<AbortController | null>(null)

  function invalidarBuscaEmAndamento() {
    consultaAtual.current += 1
    abortadorBusca.current?.abort()
    abortadorBusca.current = null
  }

  function cancelarBuscaProximidade() {
    invalidarBuscaEmAndamento()
    setLoading(false)
    setCoords(null)
    setIgrejas([])
    setGeoErro('')
    setErroBusca('Busca cancelada.')
  }

  // "Próximas" solicita localização somente pelo botão, em gesto explícito do usuário.
  useEffect(() => {
    if (aba === 'buscar') {
      setIgrejas([])
      setGeoErro('')
      setErroBusca('')
      return
    }
    if (aba === 'proximas' && !coords) {
      setIgrejas([])
      setGeoErro('')
      setErroBusca('')
      return
    }
    carregar()
  }, [aba])

  async function carregar(raioSelecionado = raioKm) {
    invalidarBuscaEmAndamento()
    const idConsulta = consultaAtual.current
    const abortador = new AbortController()
    abortadorBusca.current = abortador
    setLoading(true)
    setGeoErro('')
    setErroBusca('')
    try {
      if (aba === 'salvas' && !estaAutenticado) {
        setIgrejas([])
        return
      }
      if (aba === 'salvas') {
        const resultado = await minhasIgrejas()
        if (idConsulta !== consultaAtual.current) return
        setIgrejas(resultado)
      } else if (aba === 'buscar') {
        const termo = busca.trim()
        if (!termo) {
          // Sem termo digitado: mostra top 5 mais próximas (se tem geo), senão lista vazia
          if (coords) {
            const resultado = await buscarIgrejas({ lat: coords.lat, lng: coords.lng }, abortador.signal)
            if (idConsulta !== consultaAtual.current) return
            setIgrejas(dedupIgrejas(resultado).slice(0, 5))
          } else {
            setIgrejas([])
          }
        } else {
          // Com termo: busca por relevância + distância (se geo disponível)
          const resultado = await buscarIgrejas({ q: termo, lat: coords?.lat, lng: coords?.lng }, abortador.signal)
          if (idConsulta !== consultaAtual.current) return
          setIgrejas(dedupIgrejas(resultado))
        }
      } else if (aba === 'proximas') {
        if (!coords) {
          if (origemProximidade === 'endereco') {
            setGeoErro('Informe um endereço ou bairro para encontrar paróquias próximas desse ponto.')
            setIgrejas([])
            return
          }
          let erroGeo: GeolocationPositionError | null = null
          const pos = await new Promise<GeolocationPosition>((resolve, reject) => {
            if (!navigator.geolocation) { reject(new Error('Geolocalização não disponível neste navegador')); return }
            navigator.geolocation.getCurrentPosition(resolve, reject, {
              // "Próximas" não pode aceitar uma estimativa ampla por rede/IP: ela
              // faria aparecer igrejas de bairros distantes como se fossem próximas.
              enableHighAccuracy: true,
              timeout: 30000,
              maximumAge: 60000,
            })
          }).catch((erro: GeolocationPositionError) => {
            erroGeo = erro
            return null
          })
          if (idConsulta !== consultaAtual.current) return
          if (pos) {
            const ponto = { lat: pos.coords.latitude, lng: pos.coords.longitude }
            if (!pontoValido(ponto)) {
              setGeoErro('O navegador retornou uma localização inválida. Tente novamente.')
              setIgrejas([])
              return
            }
            setCoords(ponto)
            const resultado = await buscarIgrejas({ lat: ponto.lat, lng: ponto.lng, raio_km: raioSelecionado }, abortador.signal)
            if (idConsulta !== consultaAtual.current) return
            setIgrejas(dedupIgrejas(resultado))
          } else {
            const mensagem = erroGeo?.code === 1
              ? 'Permita a localização no navegador para ver as igrejas próximas.'
              : erroGeo?.code === 3
                ? 'A localização precisa não respondeu em 30 segundos. Confirme a permissão de localização do navegador e tente novamente.'
                : 'Não foi possível obter sua localização. Habilite a localização do navegador e tente novamente.'
            setGeoErro(mensagem)
            setIgrejas([])
          }
        } else {
          const ponto = coords
          if (!pontoValido(ponto)) {
            setGeoErro('A localização usada na busca é inválida. Tente novamente.')
            setIgrejas([])
            return
          }
          const resultado = await buscarIgrejas({ lat: ponto.lat, lng: ponto.lng, raio_km: raioSelecionado }, abortador.signal)
          if (idConsulta !== consultaAtual.current) return
          setIgrejas(dedupIgrejas(resultado))
        }
      }
    } catch {
      if (idConsulta !== consultaAtual.current) return
      setIgrejas([])
      setErroBusca('Não foi possível consultar o catálogo de igrejas. Tente novamente.')
    }
    finally {
      if (idConsulta === consultaAtual.current) {
        abortadorBusca.current = null
        setLoading(false)
      }
    }
  }

  async function usarEndereco(raioSelecionado = raioKm) {
    const endereco = enderecoProximidade.trim()
    if (endereco.length < 5) {
      setErroBusca('Informe um endereço ou bairro mais completo.')
      return
    }
    invalidarBuscaEmAndamento()
    const idConsulta = consultaAtual.current
    const abortador = new AbortController()
    abortadorBusca.current = abortador
    setLoading(true)
    setGeoErro('')
    setErroBusca('')
    try {
      const ponto = await localizarEndereco(endereco, abortador.signal)
      if (idConsulta !== consultaAtual.current) return
      if (!pontoValido(ponto)) {
        setErroBusca('O serviço de localização retornou um ponto inválido. Tente novamente.')
        return
      }
      setCoords(ponto)
      const resultado = await buscarIgrejas({ lat: ponto.lat, lng: ponto.lng, raio_km: raioSelecionado }, abortador.signal)
      if (idConsulta !== consultaAtual.current) return
      setIgrejas(dedupIgrejas(resultado))
    } catch (erro: unknown) {
      if (idConsulta !== consultaAtual.current) return
      setCoords(null)
      setIgrejas([])
      const status = typeof erro === 'object' && erro !== null && 'response' in erro
        ? (erro as { response?: { status?: number } }).response?.status
        : undefined
      setErroBusca(status === 429
        ? 'O limite mensal de buscas por endereço foi atingido. Use a sua localização atual ou tente no próximo mês.'
        : status === 503
          ? 'O serviço de localização está indisponível no momento. Tente novamente mais tarde.'
          : 'Não foi possível localizar este endereço. Confira e tente novamente.')
    }
    finally {
      if (idConsulta === consultaAtual.current) {
        abortadorBusca.current = null
        setLoading(false)
      }
    }
  }

  function selecionarOrigemProximidade(origem: OrigemProximidade) {
    invalidarBuscaEmAndamento()
    setLoading(false)
    setOrigemProximidade(origem)
    setCoords(null)
    setIgrejas([])
    setGeoErro('')
    setErroBusca('')
  }

  function selecionarAba(novaAba: Aba) {
    invalidarBuscaEmAndamento()
    setLoading(false)
    setAba(novaAba)
  }

  function selecionarRaio(km: number) {
    setRaioKm(km)
    invalidarBuscaEmAndamento()
    if (coords) {
      carregar(km)
      return
    }
    if (!loading) return
    if (origemProximidade === 'endereco' && enderecoProximidade.trim().length >= 5) {
      usarEndereco(km)
    } else if (origemProximidade === 'atual') {
      carregar(km)
    } else {
      setLoading(false)
    }
  }

  async function alternarFavorito(igreja: Igreja) {
    try {
      if (igreja.favorita) await desfavoritarIgreja(igreja.id)
      else await favoritarIgreja(igreja.id)
      // Atualização otimista
      setIgrejas(prev => prev.map(i => i.id === igreja.id ? { ...i, favorita: !i.favorita } : i))
    } catch { alert('Erro ao salvar') }
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-h-screen bg-brand-bg dark:bg-slate-900 ds-bottom-nav-padding">
      <AppHeader title="Igrejas" onBack={() => setScreen('home')} />

      <div className="max-w-lg mx-auto px-5 mt-6 flex flex-col gap-4">
        {/* Abas */}
        <div className="flex gap-2 bg-brand-gray-dark/5 dark:bg-slate-800 p-1 rounded-2xl">
          {([
            ...(estaAutenticado ? [{ id: 'salvas' as const, label: 'Salvas' }] : []),
            { id: 'buscar', label: 'Buscar' },
            { id: 'proximas', label: 'Próximas' },
          ] as { id: Aba; label: string }[]).map(t => (
            <button key={t.id}
              onClick={() => selecionarAba(t.id)}
              className={`flex-1 py-2.5 rounded-xl text-sm font-bold uppercase tracking-wider transition-all ${
                aba === t.id
                  ? 'bg-brand-blue text-white dark:bg-brand-gold dark:text-brand-blue shadow-soft'
                  : 'text-brand-gray-dark/60 dark:text-brand-white/60'
              }`}>
              {t.label}
            </button>
          ))}
        </div>

        {aba === 'proximas' && (
          <>
            <div className="grid grid-cols-2 gap-2 rounded-2xl bg-brand-gray-dark/5 p-1 dark:bg-slate-800" role="group" aria-label="Origem da proximidade">
              {([
                { id: 'atual', label: 'Minha localização' },
                { id: 'endereco', label: 'Informar endereço' },
              ] as { id: OrigemProximidade; label: string }[]).map(opcao => (
                <button
                  key={opcao.id}
                  type="button"
                  aria-pressed={origemProximidade === opcao.id}
                  onClick={() => selecionarOrigemProximidade(opcao.id)}
                  className={`rounded-xl px-3 py-2.5 text-xs font-black transition-colors ${
                    origemProximidade === opcao.id
                      ? 'bg-brand-blue text-white shadow-soft dark:bg-brand-gold dark:text-brand-blue'
                      : 'text-brand-gray-dark/60 dark:text-brand-white/60'
                  }`}
                >
                  {opcao.label}
                </button>
              ))}
            </div>
            <div className="flex items-center justify-between gap-3 rounded-2xl bg-brand-white px-4 py-3 shadow-soft dark:bg-slate-800">
              <span className="text-xs font-black uppercase tracking-wider text-brand-gray-dark/60 dark:text-brand-white/60">Até</span>
              <div className="flex flex-1 justify-end gap-1.5" role="group" aria-label="Raio de busca">
                {[1, 3, 5, 10].map(km => (
                  <button
                    key={km}
                    type="button"
                    aria-pressed={raioKm === km}
                    onClick={() => selecionarRaio(km)}
                    className={`min-w-12 rounded-xl px-2 py-2 text-xs font-black transition-colors ${
                      raioKm === km
                        ? 'bg-brand-blue text-white dark:bg-brand-gold dark:text-brand-blue'
                        : 'bg-brand-gray-dark/5 text-brand-gray-dark/60 dark:bg-brand-white/10 dark:text-brand-white/70'
                    }`}
                  >
                    {km} km
                  </button>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Campo de busca (só na aba Buscar) */}
        {aba === 'buscar' && (
          <div className="flex items-center gap-2 bg-brand-white dark:bg-slate-800 rounded-2xl pl-5 pr-2 py-2 border border-black/5">
            <input
              value={busca}
              onChange={e => setBusca(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && carregar()}
              placeholder="Nome, cidade ou endereço"
              className="bg-transparent w-full text-base font-medium outline-none placeholder:text-gray-400 dark:text-white"
            />
            <button
              onClick={() => carregar()}
              disabled={loading}
              title="Buscar"
              className="flex-shrink-0 w-11 h-11 rounded-xl bg-brand-blue text-white dark:bg-brand-gold dark:text-brand-blue flex items-center justify-center active:scale-95 transition-transform disabled:opacity-60"
            >
              <Search size={20} />
            </button>
          </div>
        )}

        {aba === 'proximas' && origemProximidade === 'endereco' && !loading && (
          <Card className="p-5">
            <MapPin size={28} className="mx-auto mb-2 text-brand-gold" />
            <p className="text-center text-sm font-bold text-brand-text dark:text-brand-white">Informe um endereço ou bairro</p>
            <p className="mt-1 text-center text-xs text-brand-gray-dark/60 dark:text-brand-white/60">O endereço é enviado para localizar este ponto e não é salvo pelo Dia de Missa.</p>
            <div className="mt-4 flex gap-2">
              <input
                value={enderecoProximidade}
                onChange={e => setEnderecoProximidade(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && usarEndereco()}
                placeholder="Ex.: Rua ou bairro, cidade"
                className="min-w-0 flex-1 rounded-xl border border-black/10 bg-brand-white px-3 py-2.5 text-sm font-medium outline-none placeholder:text-gray-400 dark:border-white/10 dark:bg-slate-900 dark:text-white"
              />
              <button
                type="button"
                onClick={() => usarEndereco()}
                className="rounded-xl bg-brand-blue px-3 py-2.5 text-sm font-bold text-white dark:bg-brand-gold dark:text-brand-blue"
              >
                Usar
              </button>
            </div>
          </Card>
        )}

        {aba === 'proximas' && origemProximidade === 'atual' && !coords && !loading && (
          <Card className="p-5 text-center">
            <MapPin size={28} className="mx-auto mb-2 text-brand-gold" />
            <p className="text-sm font-bold text-brand-text dark:text-brand-white">{geoErro || 'Encontre igrejas perto de você'}</p>
            <p className="mt-1 text-xs text-brand-gray-dark/60 dark:text-brand-white/60">A lista mostra paróquias em até {raioKm} km, apenas quando o navegador fornece sua localização real.</p>
            <button
              onClick={() => carregar()}
              className="mt-4 rounded-xl bg-brand-blue px-4 py-2.5 text-sm font-bold text-white dark:bg-brand-gold dark:text-brand-blue"
            >
              Usar minha localização
            </button>
          </Card>
        )}

        {aba === 'proximas' && coords && (
          <p className="px-1 text-center text-xs font-medium text-brand-gray-dark/60 dark:text-brand-white/60">
            {origemProximidade === 'atual'
              ? 'Mostrando paróquias próximas da sua localização atual.'
              : 'Mostrando paróquias próximas do endereço informado.'}
          </p>
        )}

        {erroBusca && (
          <Card className="p-4 bg-amber-50 border-amber-200">
            <p className="text-sm text-amber-700 font-bold">{erroBusca}</p>
          </Card>
        )}

        {/* Lista */}
        {loading ? (
          <div className="text-center py-10">
            <div className="w-8 h-8 border-4 border-brand-gold border-t-transparent rounded-full animate-spin mx-auto" />
            {aba === 'proximas' && (
              <button
                type="button"
                onClick={cancelarBuscaProximidade}
                className="mt-4 rounded-xl border border-brand-blue px-4 py-2 text-sm font-bold text-brand-blue dark:border-brand-gold dark:text-brand-gold"
              >
                Cancelar busca
              </button>
            )}
          </div>
        ) : igrejas.length === 0 && !(aba === 'proximas' && !coords) ? (
          <Card className="p-8 text-center">
            <Church size={40} className="mx-auto text-brand-gold/40 mb-3" />
            <p className="text-brand-gray-dark/60 dark:text-brand-white/60 text-sm">
              {aba === 'salvas'
                ? 'Você ainda não salvou nenhuma igreja. Use Buscar ou Próximas para encontrar.'
                : aba === 'buscar'
                  ? 'Digite um nome ou endereço para buscar.'
                  : 'Nenhuma igreja próxima encontrada.'}
            </p>
          </Card>
        ) : igrejas.length > 0 ? (
          igrejas.map(ig => (
            <Card key={ig.id} className="p-5">
              <div className="flex items-start gap-3">
                <div className="w-12 h-12 bg-brand-blue/10 dark:bg-brand-gold/20 rounded-2xl flex items-center justify-center flex-shrink-0">
                  <Church size={24} className="text-brand-blue dark:text-brand-gold" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-black text-brand-text dark:text-brand-white leading-tight">{ig.nome}</h3>
                  {ig.endereco && (
                    <p className="text-sm text-brand-gray-dark/60 dark:text-brand-white/60 mt-1 flex items-start gap-1">
                      <MapPin size={14} className="flex-shrink-0 mt-0.5" />
                      <span>{ig.endereco}{ig.cidade ? ` — ${ig.cidade}/${ig.estado || ''}` : ''}</span>
                    </p>
                  )}
                  <div className="flex flex-wrap gap-3 mt-2 text-xs text-brand-gray-dark/50">
                    {ig.telefone && <span className="flex items-center gap-1"><Phone size={12} /> {ig.telefone}</span>}
                    {ig.site && <a href={ig.site} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-brand-blue dark:text-brand-gold"><Globe size={12} /> site</a>}
                    {ig.distancia_km !== null && <span className="flex items-center gap-1 text-brand-gold font-bold"><Navigation size={12} /> {ig.distancia_km} km</span>}
                  </div>
                  <div className="mt-3 p-3 bg-brand-blue/5 dark:bg-brand-gold/10 rounded-2xl">
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <Clock size={12} className="text-brand-gold" />
                      <span className="text-[10px] font-black text-brand-gold uppercase tracking-wider">Horários de Missa</span>
                    </div>
                    {ig.horarios_missa ? (
                      <p className="text-xs text-brand-gray-dark dark:text-brand-white/80 leading-relaxed">{ig.horarios_missa}</p>
                    ) : (
                      <p className="text-xs text-brand-gray-dark/50 dark:text-brand-white/40 italic">Horários não publicados</p>
                    )}
                  </div>
                  {(ig.lat && ig.lng) && (
                    <a
                      href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(ig.nome)}&query_place_id=&center=${ig.lat},${ig.lng}`}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1.5 mt-3 px-3 py-1.5 bg-brand-blue/10 dark:bg-brand-gold/10 rounded-full text-xs font-bold text-brand-blue dark:text-brand-gold hover:bg-brand-blue/20 transition-colors"
                    >
                      <MapPin size={12} /> Ver no mapa
                      <ExternalLink size={10} />
                    </a>
                  )}
                </div>
                {estaAutenticado && <button
                  onClick={() => alternarFavorito(ig)}
                  title={ig.favorita ? 'Remover dos favoritos' : 'Salvar nas minhas igrejas'}
                  aria-label={ig.favorita ? 'Remover dos favoritos' : 'Salvar nas minhas igrejas'}
                  className={`p-2 rounded-full transition-colors active:scale-90 ${
                    ig.favorita
                      ? 'bg-red-50 text-red-500 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400'
                      : 'text-brand-gray-dark/40 dark:text-brand-white/30 hover:text-red-500 hover:bg-red-50/50'
                  }`}
                >
                  <Heart size={22} fill={ig.favorita ? 'currentColor' : 'none'} strokeWidth={1.8} />
                </button>}
              </div>
            </Card>
          ))
        ) : null}
      </div>
    </motion.div>
  )
}
