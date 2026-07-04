import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import { AppHeader, Card } from '../components/UI'
import { Church, Search, MapPin, Heart, Phone, Globe, Navigation, ExternalLink, Clock } from 'lucide-react'
import { buscarIgrejas, minhasIgrejas, favoritarIgreja, desfavoritarIgreja } from '../services/igrejas'
import type { Igreja } from '../types/igreja'

interface Props {
  setScreen: (s: string) => void
}

type Aba = 'salvas' | 'buscar' | 'proximas'

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

export const IgrejasScreen = ({ setScreen }: Props) => {
  const [aba, setAba] = useState<Aba>(() => {
    const inicial = localStorage.getItem('@igrejas_aba_inicial') as Aba | null
    localStorage.removeItem('@igrejas_aba_inicial')  // consome uma vez
    return inicial && ['salvas', 'buscar', 'proximas'].includes(inicial) ? inicial : 'salvas'
  })
  const [busca, setBusca] = useState('')
  const [igrejas, setIgrejas] = useState<Igreja[]>([])
  const [loading, setLoading] = useState(false)
  const [geoErro, setGeoErro] = useState('')
  // Localização do usuário (auto-detecta uma vez; usada pra ordenar busca por proximidade)
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null)

  // Tenta capturar localização ao montar (silencioso — se negar, busca segue sem coords)
  useEffect(() => {
    if (!navigator.geolocation) return
    navigator.geolocation.getCurrentPosition(
      pos => setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => {},
      { enableHighAccuracy: false, timeout: 6000 },
    )
  }, [])

  // Carrega ao trocar de aba — exceto em "buscar", que só carrega ao clicar no botão
  useEffect(() => {
    if (aba === 'buscar') {
      setIgrejas([])
      return
    }
    carregar()
  }, [aba])

  async function carregar() {
    setLoading(true)
    setGeoErro('')
    try {
      if (aba === 'salvas') {
        setIgrejas(await minhasIgrejas())
      } else if (aba === 'buscar') {
        const termo = busca.trim()
        if (!termo) {
          // Sem termo digitado: mostra top 5 mais próximas (se tem geo), senão lista vazia
          if (coords) {
            setIgrejas(dedupIgrejas(await buscarIgrejas({ lat: coords.lat, lng: coords.lng })).slice(0, 5))
          } else {
            setIgrejas([])
          }
        } else {
          // Com termo: busca por relevância + distância (se geo disponível)
          setIgrejas(dedupIgrejas(await buscarIgrejas({ q: termo, lat: coords?.lat, lng: coords?.lng })))
        }
      } else if (aba === 'proximas') {
        if (!coords) {
          // Tenta de novo explicitamente — usuário precisa permitir
          const pos = await new Promise<GeolocationPosition>((resolve, reject) => {
            if (!navigator.geolocation) { reject(new Error('Geolocalização não disponível neste navegador')); return }
            navigator.geolocation.getCurrentPosition(resolve, reject, { enableHighAccuracy: false, timeout: 8000 })
          }).catch(e => { setGeoErro(e.message || 'Não foi possível obter localização'); return null })
          if (pos) {
            setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude })
            setIgrejas(dedupIgrejas(await buscarIgrejas({ lat: pos.coords.latitude, lng: pos.coords.longitude, raio_km: 50 })))
          } else {
            setIgrejas([])
          }
        } else {
          setIgrejas(dedupIgrejas(await buscarIgrejas({ lat: coords.lat, lng: coords.lng, raio_km: 50 })))
        }
      }
    } catch { setIgrejas([]) }
    finally { setLoading(false) }
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
            { id: 'salvas', label: 'Salvas' },
            { id: 'buscar', label: 'Buscar' },
            { id: 'proximas', label: 'Próximas' },
          ] as { id: Aba; label: string }[]).map(t => (
            <button key={t.id}
              onClick={() => setAba(t.id)}
              className={`flex-1 py-2.5 rounded-xl text-sm font-bold uppercase tracking-wider transition-all ${
                aba === t.id
                  ? 'bg-brand-blue text-white dark:bg-brand-gold dark:text-brand-blue shadow-soft'
                  : 'text-brand-gray-dark/60 dark:text-brand-white/60'
              }`}>
              {t.label}
            </button>
          ))}
        </div>

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
              onClick={carregar}
              disabled={loading}
              title="Buscar"
              className="flex-shrink-0 w-11 h-11 rounded-xl bg-brand-blue text-white dark:bg-brand-gold dark:text-brand-blue flex items-center justify-center active:scale-95 transition-transform disabled:opacity-60"
            >
              <Search size={20} />
            </button>
          </div>
        )}

        {/* Aviso de geo */}
        {aba === 'proximas' && geoErro && (
          <Card className="p-4 bg-amber-50 border-amber-200">
            <p className="text-sm text-amber-700 font-bold">{geoErro}</p>
            <p className="text-xs text-amber-600 mt-1">Permita acesso à localização ou use a aba Buscar.</p>
          </Card>
        )}

        {/* Lista */}
        {loading ? (
          <div className="text-center py-10">
            <div className="w-8 h-8 border-4 border-brand-gold border-t-transparent rounded-full animate-spin mx-auto" />
          </div>
        ) : igrejas.length === 0 ? (
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
        ) : (
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
                <button
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
                </button>
              </div>
            </Card>
          ))
        )}
      </div>
    </motion.div>
  )
}
