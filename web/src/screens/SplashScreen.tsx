import { motion } from 'motion/react';
import { useEffect } from 'react';

export const SplashScreen = ({ onFinish }: { onFinish: () => void }) => {
  useEffect(() => {
    const timer = setTimeout(onFinish, 2500);
    return () => clearTimeout(timer);
  }, [onFinish]);

  return (
    <div className="fixed inset-0 bg-brand-blue flex flex-col items-center justify-center text-white z-[1000]">
      <motion.div 
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ 
          type: "spring", 
          stiffness: 260, 
          damping: 20 
        }}
        className="flex flex-col items-center gap-6"
      >
        <div className="w-24 h-24 bg-white/20 backdrop-blur-md rounded-[32px] flex items-center justify-center shadow-2xl relative overflow-hidden">
          <div className="text-4xl font-black font-serif relative z-10">M</div>
          <motion.div 
            animate={{ 
              rotate: 360,
              scale: [1, 1.2, 1]
            }}
            transition={{ 
              duration: 4, 
              repeat: Infinity, 
              ease: "linear" 
            }}
            className="absolute inset-0 bg-gradient-to-tr from-brand-gold/0 via-brand-gold/20 to-brand-gold/0"
          ></motion.div>
        </div>
        
        <div className="text-center">
          <h1 className="text-3xl font-serif font-black tracking-tighter">Missa Hoje</h1>
          <p className="text-brand-gold font-bold tracking-widest uppercase text-[10px] mt-1 italic">Liturgia Diária</p>
        </div>
      </motion.div>
      
      <motion.div 
        initial={{ width: 0 }}
        animate={{ width: 120 }}
        transition={{ duration: 2, ease: "easeInOut" }}
        className="h-1 bg-white/20 rounded-full mt-12 overflow-hidden"
      >
        <motion.div 
          className="h-full bg-brand-gold"
          initial={{ x: '-100%' }}
          animate={{ x: '100%' }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
        />
      </motion.div>
    </div>
  );
};
