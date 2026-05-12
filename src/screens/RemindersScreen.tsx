import { motion } from 'motion/react';
import { AppHeader, Card, LargeButton } from '../components/UI';
import { Bell, BellPlus, Clock, Trash2, CheckCircle2 } from 'lucide-react';
import { UserReminder } from '../types/mass';

export const RemindersScreen = ({ 
  reminders, 
  toggleReminder,
  markAsSeen,
  onBack
}: { 
  reminders: UserReminder[], 
  toggleReminder: (id: string) => void,
  markAsSeen: (id: string) => void,
  onBack: () => void
}) => {
  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="pb-32"
    >
      <AppHeader title="Lembretes" onBack={onBack} />
      
      <div className="p-5 flex flex-col gap-6 max-w-lg mx-auto">
        <div className="bg-brand-white dark:bg-slate-800 rounded-[32px] p-8 shadow-soft border-2 border-brand-blue/5 flex flex-col gap-5">
          <div className="flex items-center justify-between">
            <h3 className="text-2xl font-serif font-black text-brand-blue dark:text-brand-white">Configure seus avisos</h3>
            <Bell size={32} className="text-brand-blue/20" />
          </div>
          <p className="text-brand-blue/60 dark:text-brand-white/60 text-sm leading-relaxed font-medium">
            Não perca a liturgia do dia. Receba uma notificação no horário que for melhor para você.
          </p>
          <LargeButton 
            variant="primary"
            className="w-full text-lg h-[64px]"
            icon={BellPlus}
          >
            Novo Lembrete
          </LargeButton>
        </div>

        <div className="flex flex-col gap-4">
          <h4 className="font-bold text-brand-gray-dark/40 dark:text-brand-white/40 uppercase text-[10px] tracking-[0.3em] ml-2">Ativos</h4>
          {reminders.map((reminder) => (
            <Card 
              key={reminder.id} 
              className={`flex flex-col gap-5 transition-all border-none p-6 ${reminder.ativo ? 'bg-brand-white shadow-soft' : 'bg-brand-gray-dark/5 opacity-40 grayscale shadow-none'} dark:bg-slate-800 relative overflow-hidden`}
            >
              {!reminder.visto && reminder.ativo && (
                <div className="absolute top-0 right-0 w-32 h-32 bg-red-500/5 -mr-16 -mt-16 rounded-full blur-2xl" />
              )}
              
              <div className="flex items-center gap-5">
                <div className={`p-4 rounded-2xl ${reminder.ativo ? 'bg-brand-blue/[0.08] text-brand-blue' : 'bg-brand-gray-dark/10 text-brand-gray-dark'}`}>
                  <Clock size={28} />
                </div>
                <div className="flex-1">
                  <p className={`text-2xl font-black ${reminder.ativo ? 'text-brand-blue' : 'text-brand-gray-dark/60'}`}>
                    {reminder.horario}
                  </p>
                  <p className="text-sm font-black dark:text-brand-white leading-tight truncate uppercase tracking-tight">{reminder.celebracao}</p>
                </div>
                <div className="flex flex-col gap-3">
                  <button 
                    onClick={() => toggleReminder(reminder.id)}
                    className={`w-14 h-7 rounded-full relative transition-all duration-300 ${reminder.ativo ? 'bg-brand-gold' : 'bg-brand-gray-dark/20'}`}
                  >
                    <div className={`absolute top-1 w-5 h-5 rounded-full bg-brand-white shadow-sm transition-all duration-300 ${reminder.ativo ? 'left-8' : 'left-1'}`} />
                  </button>
                  <button className="p-2 text-brand-gray-dark/20 hover:text-red-500 transition-colors ml-auto">
                    <Trash2 size={20} />
                  </button>
                </div>
              </div>

              {reminder.ativo && !reminder.visto && (
                <button 
                  onClick={() => markAsSeen(reminder.id)}
                  className="w-full flex items-center justify-center gap-2 py-4 bg-red-50 text-red-600 rounded-2xl font-black text-xs uppercase tracking-widest active:scale-[0.98] transition-transform"
                >
                  <CheckCircle2 size={18} /> Marcar como lido
                </button>
              )}
            </Card>
          ))}
        </div>

        <div className="p-8 bg-brand-white dark:bg-slate-800 rounded-[32px] border border-black/[0.03] flex gap-5 shadow-soft">
          <div className="p-3 bg-green-500/10 text-green-600 rounded-2xl h-fit">
            <CheckCircle2 size={28} />
          </div>
          <div className="text-sm">
            <p className="font-black text-brand-gray-dark dark:text-brand-white uppercase tracking-wider text-xs mb-1">Notificações Inteligentes</p>
            <p className="text-brand-gray-dark/60 dark:text-brand-white/60 font-medium">Enviamos lembretes apenas 15 minutos antes da missa do dia ou no horário configurado.</p>
          </div>
        </div>
      </div>
    </motion.div>
  );
};
