import { motion } from 'motion/react';
import { AppHeader, Card, LargeButton } from '../components/UI';
import { Bookmark, Clock, CheckCircle2, ChevronRight, RotateCcw } from 'lucide-react';
import { MOCK_HISTORY } from '../data/mockMass';

export const HistoryScreen = ({ setScreen }: { setScreen: (s: string) => void }) => {
  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="pb-32"
    >
      <AppHeader title="Histórico de Leituras" />
      
      <div className="p-5 flex flex-col gap-6 max-w-lg mx-auto">
        <div className="flex items-center gap-3 ml-1">
          <Bookmark className="text-brand-gold" />
          <h3 className="font-bold text-xl dark:text-white">Suas atividades</h3>
        </div>

        <div className="flex flex-col gap-4">
          {MOCK_HISTORY.map((item) => (
            <Card key={item.id} className="relative overflow-hidden flex flex-col gap-4 border-none shadow-md dark:bg-slate-800">
              <div className="flex items-start justify-between">
                <div className="flex flex-col gap-1 pr-4">
                  <span className="text-[10px] font-black uppercase tracking-widest text-brand-gray-dark/40 flex items-center gap-2">
                    <Clock size={12} /> {new Date(item.data).toLocaleDateString('pt-BR')}
                  </span>
                  <h4 className="font-serif font-black text-xl leading-tight text-brand-blue dark:text-brand-white">{item.celebracao}</h4>
                </div>
                {item.progresso === 100 ? (
                  <CheckCircle2 size={28} className="text-green-500 shrink-0" />
                ) : (
                  <div className="text-[10px] font-black uppercase tracking-widest bg-brand-gold/10 text-brand-gold px-3 py-1.5 rounded-full shrink-0">
                    {item.progresso}% lido
                  </div>
                )}
              </div>

              {/* Progress visual */}
              <div className="w-full h-2 bg-brand-gray-dark/5 dark:bg-slate-700 rounded-full overflow-hidden">
                <div 
                   className={`h-full transition-all duration-1000 ${item.progresso === 100 ? 'bg-green-500' : 'bg-brand-gold'}`} 
                   style={{ width: `${item.progresso}%` }} 
                 />
              </div>

              <div className="flex gap-4">
                <LargeButton 
                   variant="secondary"
                   onClick={() => setScreen('reading')}
                   className="w-full h-[56px] text-base"
                   icon={RotateCcw}
                >
                  Abrir novamente
                </LargeButton>
              </div>
            </Card>
          ))}
        </div>

        <div className="p-8 text-center flex flex-col items-center gap-3 grayscale opacity-30 mt-4">
          <Clock size={48} />
          <p className="text-sm">Não há mais atividades registradas.</p>
        </div>
      </div>
    </motion.div>
  );
};
