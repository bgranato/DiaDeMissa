import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { MOCK_MASS } from '../data/mockMass';
import { AppHeader, LargeButton, Card } from '../components/UI';
import { useAccessibility } from '../hooks/useAccessibility';
import { ChevronLeft, ChevronRight, List as ListIcon, X, Check } from 'lucide-react';

export const ReadingScreen = ({ onBack, onFinish }: { onBack: () => void, onFinish: () => void }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showIndex, setShowIndex] = useState(false);
  const { prefs } = useAccessibility();

  const currentBlock = MOCK_MASS.blocos[currentIndex];
  const isLastBlock = currentIndex === MOCK_MASS.blocos.length - 1;
  const progress = Math.round(((currentIndex + 1) / MOCK_MASS.blocos.length) * 100);

  const nextBlock = () => {
    if (!isLastBlock) {
      setCurrentIndex(currentIndex + 1);
      window.scrollTo(0, 0);
    } else {
      onFinish();
    }
  };

  const prevBlock = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      window.scrollTo(0, 0);
    }
  };

  const jumpTo = (index: number) => {
    setCurrentIndex(index);
    setShowIndex(false);
    window.scrollTo(0, 0);
  };

  return (
    <div className="min-h-screen bg-brand-bg dark:bg-slate-900 pb-40">
      <AppHeader 
        title={MOCK_MASS.celebracao} 
        onBack={onBack} 
        rightElement={
          <button 
            onClick={() => setShowIndex(true)}
            className="p-2 text-brand-text dark:text-slate-100"
          >
            <ListIcon size={24} />
          </button>
        }
      />

      <div className="max-w-xl mx-auto px-5 mt-4">
        {/* Progress Bar */}
        <div className="mb-6 flex items-center gap-4">
          <div className="flex-1 h-3 bg-gray-200 dark:bg-slate-800 rounded-full overflow-hidden">
            <motion.div 
              className="h-full bg-brand-gold shadow-[0_0_10px_rgba(201,162,39,0.5)]"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
          <span className="text-sm font-bold text-gray-500 whitespace-nowrap">
            {currentIndex + 1} de {MOCK_MASS.blocos.length}
          </span>
        </div>

        {/* Content Area */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentIndex}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3 }}
            className="flex flex-col gap-6"
          >
            <div className="flex flex-col gap-2 border-l-4 border-brand-gold pl-4 py-1">
              <span className="text-xs font-bold uppercase tracking-widest text-brand-gold">
                {currentBlock.tipo.replace('_', ' ')}
              </span>
              <h2 className="font-serif font-black leading-tight text-3xl">
                {currentBlock.titulo}
              </h2>
              {currentBlock.referencia && (
                <span className="text-sm italic font-serif text-brand-slate dark:text-gray-400">
                  {currentBlock.referencia}
                </span>
              )}
            </div>

            <Card className="min-h-[300px] shadow-sm border-brand-gray dark:border-slate-800 flex flex-col p-8">
              <div className="text-lg leading-relaxed font-medium text-brand-text dark:text-slate-200 whitespace-pre-wrap">
                {currentBlock.conteudo}
              </div>
            </Card>
          </motion.div>
        </AnimatePresence>

        {/* Navigation Buttons */}
        <div className="fixed bottom-6 left-0 right-0 px-5 flex gap-3 max-w-xl mx-auto z-20">
          <LargeButton 
            variant="outline" 
            onClick={prevBlock}
            disabled={currentIndex === 0}
            className="flex-1 bg-white dark:bg-slate-800"
            icon={ChevronLeft}
          >
            Anterior
          </LargeButton>
          <LargeButton 
            variant={isLastBlock ? "secondary" : "primary"} 
            onClick={nextBlock}
            className="flex-1"
            icon={isLastBlock ? Check : ChevronRight}
          >
            {isLastBlock ? "Concluir" : "Próximo"}
          </LargeButton>
        </div>
      </div>

      {/* Index Modal */}
      <AnimatePresence>
        {showIndex && (
          <>
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowIndex(false)}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100]"
            />
            <motion.div 
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-[40px] z-[101] max-h-[85vh] overflow-hidden flex flex-col shadow-2xl"
            >
              <div className="p-6 pb-2 border-b border-gray-100 dark:border-slate-700 flex items-center justify-between">
                <h3 className="text-xl font-bold dark:text-white">Roteiro da Missa</h3>
                <button onClick={() => setShowIndex(false)} className="p-2 bg-gray-100 dark:bg-slate-700 rounded-full">
                  <X size={20} />
                </button>
              </div>
              
              <div className="overflow-y-auto p-4 flex flex-col gap-2 pb-10">
                {MOCK_MASS.blocos.map((block, idx) => (
                  <button
                    key={block.ordem}
                    onClick={() => jumpTo(idx)}
                    className={`flex items-center gap-4 p-4 rounded-2xl text-left transition-colors ${
                      currentIndex === idx 
                      ? 'bg-brand-blue text-white shadow-md' 
                      : 'bg-gray-50 dark:bg-slate-700/50 hover:bg-gray-100 dark:hover:bg-slate-700'
                    }`}
                  >
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm ${
                      currentIndex === idx ? 'bg-white text-brand-blue' : 'bg-gray-200 dark:bg-slate-600 text-gray-500'
                    }`}>
                      {block.ordem}
                    </div>
                    <div className="flex-1">
                      <p className="font-bold leading-tight">{block.titulo}</p>
                      <p className={`text-xs uppercase tracking-wider opacity-70`}>{block.tipo.replace('_', ' ')}</p>
                    </div>
                  </button>
                ))}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};
