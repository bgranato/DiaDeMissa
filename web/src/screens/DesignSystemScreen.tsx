import { motion } from 'motion/react';
import { AppHeader, Card, LargeButton } from '../components/UI';
import { Palette, Type, Square, Layout, Play, ChevronRight, Bell, Settings2, House } from 'lucide-react';

export const DesignSystemScreen = ({ onBack }: { onBack: () => void }) => {
  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="pb-32 bg-brand-bg dark:bg-slate-900 min-h-screen"
    >
      <AppHeader title="Design System" onBack={onBack} />
      
      <div className="p-5 flex flex-col gap-10 max-w-lg mx-auto">
        
        {/* Colors */}
        <section>
          <h2 className="flex items-center gap-2 text-xl font-serif font-black text-brand-blue dark:text-brand-white mb-4">
            <Palette size={20} className="text-brand-gold" /> Cores
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-2">
              <div className="h-20 bg-brand-blue rounded-2xl shadow-soft" />
              <p className="text-xs font-black uppercase text-brand-blue/60 dark:text-brand-white/60">Brand Blue (#1A2B4C)</p>
            </div>
            <div className="flex flex-col gap-2">
              <div className="h-20 bg-brand-gold rounded-2xl shadow-soft" />
              <p className="text-xs font-black uppercase text-brand-blue/60 dark:text-brand-white/60">Brand Gold (#C5A059)</p>
            </div>
            <div className="flex flex-col gap-2">
              <div className="h-20 bg-brand-white rounded-2xl border border-black/5 shadow-soft" />
              <p className="text-xs font-black uppercase text-brand-blue/60 dark:text-brand-white/60">Soft White (#F9F9F9)</p>
            </div>
            <div className="flex flex-col gap-2">
              <div className="h-20 bg-brand-bg rounded-2xl border border-black/5" />
              <p className="text-xs font-black uppercase text-brand-blue/60 dark:text-brand-white/60">Background (#F5F5F5)</p>
            </div>
          </div>
        </section>

        {/* Typography */}
        <section>
          <h2 className="flex items-center gap-2 text-xl font-serif font-black text-brand-blue dark:text-brand-white mb-4">
            <Type size={20} className="text-brand-gold" /> Tipografia
          </h2>
          <Card className="p-6 bg-brand-white dark:bg-slate-800 border-none shadow-soft flex flex-col gap-4">
            <div>
              <p className="text-[10px] font-black uppercase tracking-widest text-brand-gold mb-1">Heading 1 / Playfair</p>
              <h1 className="text-4xl font-serif font-black text-brand-blue dark:text-brand-white">Celebração de Hoje</h1>
            </div>
            <div>
              <p className="text-[10px] font-black uppercase tracking-widest text-brand-gold mb-1">Heading 2 / Playfair</p>
              <h2 className="text-2xl font-serif font-bold text-brand-blue dark:text-brand-white">Ritos Iniciais</h2>
            </div>
            <div>
              <p className="text-[10px] font-black uppercase tracking-widest text-brand-gold mb-1">Body Text / Inter</p>
              <p className="text-sm text-brand-blue/70 dark:text-brand-white/70 leading-relaxed font-medium">
                Em nome do Pai e do Filho e do Espírito Santo. Amém. O Senhor esteja convosco.
              </p>
            </div>
          </Card>
        </section>

        {/* Buttons */}
        <section>
          <h2 className="flex items-center gap-2 text-xl font-serif font-black text-brand-blue dark:text-brand-white mb-4">
            <Square size={20} className="text-brand-gold" /> Botões
          </h2>
          <div className="flex flex-col gap-4">
            <LargeButton variant="primary" icon={Play} onClick={() => {}}>Primary Action</LargeButton>
            <LargeButton variant="secondary" icon={ChevronRight} onClick={() => {}}>Secondary Action</LargeButton>
            <div className="flex gap-4">
              <button className="flex-1 p-4 bg-brand-white dark:bg-slate-800 rounded-2xl shadow-soft border border-black/5 text-brand-blue dark:text-brand-gold font-black uppercase text-[10px] tracking-widest">
                Small Clear
              </button>
              <button className="flex-1 p-4 bg-brand-gold text-white rounded-2xl shadow-soft font-black uppercase text-[10px] tracking-widest">
                Small Solid
              </button>
            </div>
          </div>
        </section>

        {/* Components */}
        <section>
          <h2 className="flex items-center gap-2 text-xl font-serif font-black text-brand-blue dark:text-brand-white mb-4">
            <Layout size={20} className="text-brand-gold" /> Componentes
          </h2>
          <div className="flex flex-col gap-6">
            {/* Header Style */}
            <div>
              <p className="text-[10px] font-black uppercase tracking-widest text-brand-blue/40 dark:text-brand-white/40 mb-2">Header Item</p>
              <div className="flex justify-between items-center p-4 bg-white dark:bg-slate-800 rounded-3xl shadow-soft">
                <div className="w-12 h-12 bg-brand-bg rounded-xl flex items-center justify-center">
                  <House size={20} className="text-brand-blue" />
                </div>
                <div className="w-12 h-12 bg-brand-blue rounded-full border-4 border-white flex items-center justify-center text-white font-black text-xs">
                  JD
                </div>
              </div>
            </div>

            {/* Notification Badge */}
            <div>
              <p className="text-[10px] font-black uppercase tracking-widest text-brand-blue/40 dark:text-brand-white/40 mb-2">Icon with Badge</p>
              <div className="flex gap-4">
                <div className="relative p-4 bg-brand-white dark:bg-slate-800 rounded-2xl shadow-soft border border-black/5 text-brand-blue">
                  <Bell size={28} />
                  <span className="absolute top-2 right-2 w-6 h-6 bg-red-500 text-white text-[10px] font-black rounded-full flex items-center justify-center border-2 border-brand-white dark:border-slate-800">
                    2
                  </span>
                </div>
                <div className="p-4 bg-brand-gold text-white rounded-2xl shadow-soft">
                  <Settings2 size={28} />
                </div>
              </div>
            </div>
          </div>
        </section>

      </div>
    </motion.div>
  );
};
