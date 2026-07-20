import { useState, useEffect, useCallback } from 'react'
import { motion } from 'motion/react'
import { AppHeader } from '../components/UI'
import { ShieldAlert, FileText, Check, RefreshCw } from 'lucide-react'
import api from '../services/api'

interface Divergencia {
  severidade?: string
  tipo?: string
  local?: string
  esperado_pdf?: string
  encontrado_montagem?: string
  detalhe?: string
}
interface MissaRevisao {
  data: string
  titulo_celebracao: string | null
  status: string
  pdf_url: string | null
  gate_ok: boolean | null
  criticas: Divergencia[]
  divergencias: Divergencia[]
}

const API_ORIGIN = (import.meta as any).env?.VITE_API_URL || ''

export const RevisaoScreen = ({ setScreen }: { setScreen: (s: string) => void }) => {
  const [missas, setMissas] = useState<MissaRevisao[] | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [aprovando, setAprovando] = useState<string | null>(null)

  const carregar = useCallback(() => {
    setErro(null)
    api.get<{ missas: MissaRevisao[] }>('/admin/missas/revisao')
      .then(r => setMissas(r.data.missas))
      .catch(() => setErro('Não foi possível carregar (é preciso ser admin).'))
  }, [])

  useEffect(() => { carregar() }, [carregar])

  async function aprovar(data: string) {
    setAprovando(data)
    try {
      await api.post(`/admin/missas/${data}/aprovar`)
      carregar()
    } catch {
      setErro(`Falha ao aprovar ${data}.`)
    } finally {
      setAprovando(null)
    }
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-h-screen bg-brand-bg dark:bg-slate-900 ds-bottom-nav-padding">
      <AppHeader title="Revisão de Missas" onBack={() => setScreen('profile')} />
      <div className="max-w-lg mx-auto px-5 mt-4 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <p className="ds-body-sm text-brand-slate dark:text-gray-300">
            Missas retidas pelo gate de fidelidade (PDF × montagem).
          </p>
          <button onClick={carregar} className="p-2 rounded-full bg-white dark:bg-slate-800 shadow-soft">
            <RefreshCw size={18} className="text-brand-blue" />
          </button>
        </div>

        {erro && <p className="ds-body-sm text-red-600">{erro}</p>}

        {missas && missas.length === 0 && (
          <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-soft text-center">
            <Check size={32} className="text-green-600 mx-auto mb-2" />
            <p className="font-bold">Nada pendente de revisão</p>
            <p className="ds-body-sm text-brand-slate">Todas as missas passaram no gate.</p>
          </div>
        )}

        {missas?.map(m => (
          <div key={m.data} className="bg-white dark:bg-slate-800 p-5 rounded-2xl shadow-soft border border-black/5 flex flex-col gap-3">
            <div className="flex items-start gap-3">
              <ShieldAlert size={22} className="text-brand-gold mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="font-bold">{m.titulo_celebracao || m.data}</p>
                <p className="ds-caption text-brand-slate">{m.data} · {m.status}</p>
              </div>
            </div>

            {m.criticas.length > 0 ? (
              <div className="flex flex-col gap-2">
                <p className="ds-section-label text-red-600">{m.criticas.length} divergência(s) crítica(s)</p>
                {m.criticas.map((d, i) => (
                  <div key={i} className="text-sm bg-red-50 dark:bg-red-950/30 rounded-xl p-3">
                    <p className="font-bold text-red-700 dark:text-red-300">{d.tipo} · {d.local}</p>
                    {d.esperado_pdf && <p><span className="opacity-60">PDF:</span> {d.esperado_pdf}</p>}
                    {d.encontrado_montagem && <p><span className="opacity-60">Montagem:</span> {d.encontrado_montagem}</p>}
                    {d.detalhe && <p className="italic opacity-80">{d.detalhe}</p>}
                  </div>
                ))}
              </div>
            ) : (
              <p className="ds-body-sm text-green-700 dark:text-green-400">Sem divergência crítica registrada.</p>
            )}

            <div className="flex items-center gap-2 mt-1">
              {m.pdf_url && (
                <a href={`${API_ORIGIN}${m.pdf_url}`} target="_blank" rel="noreferrer"
                   className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-blue text-white font-bold text-sm">
                  <FileText size={16} /> Abrir PDF
                </a>
              )}
              <button onClick={() => aprovar(m.data)} disabled={aprovando === m.data}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-gold text-white font-bold text-sm disabled:opacity-50">
                <Check size={16} /> {aprovando === m.data ? 'Aprovando…' : 'Aprovar e publicar'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  )
}
