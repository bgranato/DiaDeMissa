import { motion } from 'motion/react';
import { LargeButton, Card } from '../components/UI';
import { CheckCircle2, House, Bookmark, Share2 } from 'lucide-react';

export const ConclusionScreen = ({ setScreen }: { setScreen: (s: string) => void }) => {
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
        Que a paz do Senhor esteja sempre com você. Sua leitura foi registrada no histórico.
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

        <LargeButton 
          variant="primary" 
          onClick={() => setScreen('home')}
          icon={House}
          className="w-full"
        >
          Voltar para Início
        </LargeButton>

        <div className="grid grid-cols-2 gap-4">
          <button 
            onClick={() => setScreen('history')}
            className="flex items-center justify-center gap-2 p-5 bg-brand-white dark:bg-slate-800 rounded-[28px] font-bold text-sm text-brand-gray-dark dark:text-brand-white shadow-soft active:scale-95 transition-transform"
          >
            <Bookmark size={20} /> Histórico
          </button>
          <button 
            className="flex items-center justify-center gap-2 p-5 bg-brand-white dark:bg-slate-800 rounded-[28px] font-bold text-sm text-brand-gray-dark dark:text-brand-white shadow-soft active:scale-95 transition-transform"
          >
            <Share2 size={20} /> Compartilhar
          </button>
        </div>
      </div>
    </motion.div>
  );
};
