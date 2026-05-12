import { motion } from 'motion/react';
import { AppHeader, Card } from '../components/UI';
import { Calendar as CalendarIcon, Bell, ChevronRight, Info } from 'lucide-react';
import { CALENDAR_MASSES } from '../data/mockMass';

export const CalendarScreen = ({ setScreen }: { setScreen: (s: string) => void }) => {
  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="pb-32"
    >
      <AppHeader title="Calendário Litúrgico" />
      
      <div className="p-5 flex flex-col gap-6 max-w-lg mx-auto">
        <div className="bg-brand-white dark:bg-slate-800 p-6 rounded-[32px] flex items-center gap-5 shadow-soft border-2 border-brand-blue/5">
          <div className="w-16 h-16 bg-brand-blue text-white rounded-2xl flex flex-col items-center justify-center font-bold">
            <span className="text-xs uppercase tracking-tighter opacity-80">Maio</span>
            <span className="text-2xl leading-none font-serif">10</span>
          </div>
          <div>
            <p className="text-brand-blue/50 dark:text-brand-white/50 text-[10px] uppercase font-black tracking-[0.2em] mb-1">Hoje é</p>
            <h3 className="text-xl font-serif font-black leading-tight text-brand-blue dark:text-brand-gold">5º Domingo da Páscoa</h3>
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <h4 className="font-bold text-brand-slate uppercase text-[10px] tracking-widest ml-1">Próximas Missas</h4>
          {CALENDAR_MASSES.map((item) => (
            <Card key={item.id} className="p-5 flex items-center gap-4 dark:bg-slate-800 border-none shadow-sm">
              <div className="flex flex-col items-center justify-center min-w-[50px] py-1 border-r border-gray-100 dark:border-slate-700 pr-4">
                <span className="text-xs font-bold text-brand-gold uppercase">{item.data.split('-')[2]}</span>
                <span className="text-xs text-gray-400">MAIO</span>
              </div>
              <div className="flex-1 overflow-hidden">
                <p className="font-bold truncate text-brand-text dark:text-white leading-tight">{item.celebracao}</p>
                <p className="text-xs text-gray-500 uppercase tracking-wider">{item.tempo}</p>
              </div>
              <div className="flex gap-3">
                <button 
                  onClick={() => setScreen('reminders')}
                  className="p-3 bg-brand-blue/[0.08] text-brand-blue rounded-2xl active:scale-90 transition-transform"
                >
                  <Bell size={24} />
                </button>
                <button 
                  onClick={() => setScreen('reading')}
                  className="p-3 bg-brand-gold/[0.08] text-brand-gold rounded-2xl active:scale-90 transition-transform"
                >
                  <ChevronRight size={24} />
                </button>
              </div>
            </Card>
          ))}
        </div>

        <div className="bg-blue-50 dark:bg-blue-900/20 p-5 rounded-3xl border border-blue-100 dark:border-blue-800/50 flex gap-4">
          <Info className="shrink-0 text-blue-500" />
          <p className="text-sm text-blue-800 dark:text-blue-300">
            As missas são atualizadas diariamente de acordo com o calendário da CNBB.
          </p>
        </div>
      </div>
    </motion.div>
  );
};
