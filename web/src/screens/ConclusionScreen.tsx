import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { LargeButton, Card } from '../components/UI';
import { CheckCircle2, House, Bookmark, Share2, MapPin, Church, X, ArrowRight, Search } from 'lucide-react';
import { minhasIgrejas, buscarIgrejas } from '../services/igrejas';
import type { Igreja } from '../types/igreja';
import api from '../services/api';

interface Props {
  setScreen: (s: string) => void;
  missaId?: number;
  missaData?: string;
  estaAutenticado?: boolean;
}

export const ConclusionScreen = ({ setScreen, missaId, missaData, estaAutenticado = true }: Props) => {
  const [igrejaSelecionada, setIgrejaSelecionada] = useState<{ id: number; nome: string } | null>(null);
  const [showSeletor, setShowSeletor] = useState(false);
  const [salvas, setSalvas] = useState<Igreja[]>([]);
  const [buscaIgreja, setBuscaIgreja] = useState('');
  const [resultadosBusca, setResultadosBusca] = useState<Igreja[]>([]);
  const [buscando, setBuscando] = useState(false);

  useEffect(() => {
    if (!missaData) return;
    const raw = localStorage.getItem(`@missa_igreja_${missaData}`);
    if (raw) {
      try { setIgrejaSelecionada(JSON.parse(raw)); } catch { /* ignore */ }
    }
  }, [missaData]);

  async function abrirSeletor() {
    setShowSeletor(true);
    setBuscaIgreja('');
    setResultadosBusca([]);
    if (!estaAutenticado) {
      setSalvas([]);
      return;
    }
    try { setSalvas(await minhasIgrejas()); } catch { setSalvas([]); }
  }

  async function fazerBuscaIgreja() {
    if (!buscaIgreja.trim()) { setResultadosBusca([]); return; }
    setBuscando(true);
    try {
      const r = await buscarIgrejas({ q: buscaIgreja.trim() });
      setResultadosBusca(r);
    } catch { setResultadosBusca([]); }
    finally { setBuscando(false); }
  }

  function selecionarIgreja(ig: Igreja) {
    const escolha = { id: ig.id, nome: ig.nome };
    setIgrejaSelecionada(escolha);
    if (missaData) localStorage.setItem(`@missa_igreja_${missaData}`, JSON.stringify(escolha));
    setShowSeletor(false);
    if (estaAutenticado && missaId) {
      api.post('/usuarios/me/historico', {
        missa_id: missaId,
        ultimo_bloco_id: 0,
        percentual_lido: 100,
        igreja_id: ig.id,
      }).catch(() => { /* silent */ });
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className="min-h-screen flex flex-col items-center justify-center p-6 text-center"
    >
      <div className="w-24 h-24 bg-green-500 rounded-full flex items-center justify-center text-white mb-6 shadow-strong">
        <CheckCircle2 size={56} />
      </div>

      <h2 className="text-4xl font-serif font-black text-brand-blue dark:text-brand-white mb-3">Missa Concluída!</h2>
      <p className="text-brand-gray-dark/60 dark:text-brand-white/60 text-lg mb-10 max-w-xs mx-auto">
        Que a paz do Senhor esteja sempre com você.{estaAutenticado ? ' Sua leitura foi registrada no histórico.' : ''}
      </p>

      <div className="w-full max-w-md flex flex-col gap-4">
        <Card className="bg-brand-white dark:bg-slate-800 border-none shadow-soft p-6 mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-black uppercase tracking-widest text-brand-gold">Progresso</span>
            <span className="text-sm font-black text-green-500">100% CONCLUÍDO</span>
          </div>
          <div className="w-full h-2 bg-green-500/10 rounded-full overflow-hidden">
            <div className="w-full h-full bg-green-500" />
          </div>
        </Card>

        {/* Atribuir local é um recurso de conta, pois depende da busca de igrejas. */}
        {estaAutenticado && <button onClick={abrirSeletor}
          className={`flex items-center gap-3 px-4 py-4 rounded-2xl active:scale-[0.99] transition-transform ${
            igrejaSelecionada
              ? 'bg-brand-gold/10 border-2 border-brand-gold/40'
              : 'bg-brand-blue/5 dark:bg-brand-gold/5 border-2 border-dashed border-brand-blue/40 dark:border-brand-gold/50'
          }`}>
          <div className={`p-2.5 rounded-xl flex-shrink-0 ${igrejaSelecionada ? 'bg-brand-gold' : 'bg-brand-blue dark:bg-brand-gold'}`}>
            <MapPin size={20} className="text-white" />
          </div>
          <div className="flex-1 text-left min-w-0">
            {igrejaSelecionada ? (
              <>
                <p className="text-[10px] font-black text-brand-gold uppercase tracking-[0.2em]">Local da Missa</p>
                <p className="text-sm font-black text-brand-blue dark:text-brand-white truncate">{igrejaSelecionada.nome}</p>
              </>
            ) : (
              <>
                <p className="text-[10px] font-black text-brand-blue dark:text-brand-gold uppercase tracking-[0.2em]">Atribuir local</p>
                <p className="text-sm font-bold text-brand-blue dark:text-brand-gold">Marcar igreja onde assistiu</p>
              </>
            )}
          </div>
          <ArrowRight size={18} className="text-brand-gold flex-shrink-0" />
        </button>}

        <LargeButton
          variant="primary"
          onClick={() => setScreen('home')}
          icon={House}
          className="w-full"
        >
          Voltar para Início
        </LargeButton>

        <div className={`grid ${estaAutenticado ? 'grid-cols-2' : 'grid-cols-1'} gap-4`}>
          {estaAutenticado && (
          <button
            onClick={() => setScreen('history')}
            className="flex items-center justify-center gap-2 p-5 bg-brand-white dark:bg-slate-800 rounded-[28px] font-bold text-sm text-brand-gray-dark dark:text-brand-white shadow-soft active:scale-95 transition-transform"
          >
            <Bookmark size={20} /> Histórico
          </button>
          )}
          <button
            className="flex items-center justify-center gap-2 p-5 bg-brand-white dark:bg-slate-800 rounded-[28px] font-bold text-sm text-brand-gray-dark dark:text-brand-white shadow-soft active:scale-95 transition-transform"
          >
            <Share2 size={20} /> Compartilhar
          </button>
        </div>
      </div>

      {/* Modal seletor (igual à HomeScreen) */}
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
  );
};
