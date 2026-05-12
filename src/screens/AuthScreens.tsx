import { motion } from 'motion/react';
import { LargeButton, Card } from '../components/UI';
import { Mail, Lock, User, Chrome, ChevronLeft } from 'lucide-react';
import { useState } from 'react';

export const AuthScreens = ({ setScreen }: { setScreen: (s: string) => void }) => {
  const [isLogin, setIsLogin] = useState(true);

  return (
    <div className="min-h-screen bg-brand-bg dark:bg-slate-900 flex flex-col items-center justify-center p-6">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        <div className="text-center mb-8">
          <div className="inline-block p-4 bg-brand-blue rounded-3xl text-white mb-4 shadow-xl">
             <div className="w-12 h-12 flex items-center justify-center font-bold text-3xl font-serif">M</div>
          </div>
          <h2 className="text-3xl font-serif font-black text-brand-blue dark:text-brand-gold">Missa Hoje</h2>
          <p className="text-brand-slate font-medium">{isLogin ? 'Bem-vindo de volta' : 'Crie sua conta gratuita'}</p>
        </div>

        <Card className="flex flex-col gap-4 p-8 border-none shadow-2xl dark:bg-slate-800">
          {!isLogin && (
            <div className="flex flex-col gap-2">
              <label className="text-xs font-bold text-gray-400 uppercase tracking-widest ml-1">Nome Completo</label>
              <div className="relative">
                <User className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
                <input 
                  type="text" 
                  placeholder="Seu nome"
                  className="w-full pl-12 pr-4 py-4 bg-gray-50 dark:bg-slate-700 rounded-2xl border-none focus:ring-2 focus:ring-brand-blue transition-all dark:text-white"
                />
              </div>
            </div>
          )}

          <div className="flex flex-col gap-2">
            <label className="text-xs font-bold text-gray-400 uppercase tracking-widest ml-1">E-mail</label>
            <div className="relative">
              <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
              <input 
                type="email" 
                placeholder="seu@email.com"
                className="w-full pl-12 pr-4 py-4 bg-gray-50 dark:bg-slate-700 rounded-2xl border-none focus:ring-2 focus:ring-brand-blue transition-all dark:text-white"
              />
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <label className="text-xs font-bold text-gray-400 uppercase tracking-widest ml-1">Senha</label>
            <div className="relative">
              <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
              <input 
                type="password" 
                placeholder="••••••••"
                className="w-full pl-12 pr-4 py-4 bg-gray-50 dark:bg-slate-700 rounded-2xl border-none focus:ring-2 focus:ring-brand-blue transition-all dark:text-white"
              />
            </div>
          </div>

          {isLogin && (
            <button className="text-right text-sm text-brand-gold font-bold p-1">Esqueci minha senha</button>
          )}

          <LargeButton 
            className="w-full mt-2" 
            onClick={() => setScreen('home')}
          >
            {isLogin ? 'Entrar' : 'Cadastrar'}
          </LargeButton>

          <div className="flex items-center gap-4 my-2">
            <div className="flex-1 h-px bg-gray-100 dark:bg-slate-700"></div>
            <span className="text-xs text-gray-400 font-bold">OU</span>
            <div className="flex-1 h-px bg-gray-100 dark:bg-slate-700"></div>
          </div>

          <button 
            onClick={() => setScreen('home')}
            className="flex items-center justify-center gap-3 py-4 border-2 border-gray-100 dark:border-slate-700 rounded-2xl font-bold hover:bg-gray-50 dark:hover:bg-slate-700 transition-all dark:text-white"
          >
            <Chrome size={20} /> Entrar com Google
          </button>
        </Card>

        <button 
          onClick={() => setIsLogin(!isLogin)}
          className="w-full text-center mt-8 text-brand-blue dark:text-brand-gold font-bold"
        >
          {isLogin ? 'Não tem uma conta? Cadastre-se' : 'Já tem uma conta? Entre agora'}
        </button>
      </motion.div>
    </div>
  );
};
