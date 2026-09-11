const ROTAS_EXCLUSIVAS_DA_CONTA = new Set([
  'calendar',
  'igrejas',
  'oracoes',
  'history',
  'reminders',
  'profile',
  'meus-dados',
  'alterar-senha',
  'revisao',
])

/** Determina se uma rota deve abrir o acesso/cadastro para um visitante. */
export function rotaExigeConta(destino: string, estaAutenticado: boolean, missaDisponivelPublicamente: boolean) {
  if (estaAutenticado) return false
  return destino === 'login'
    || ROTAS_EXCLUSIVAS_DA_CONTA.has(destino)
    || (destino === 'reading' && !missaDisponivelPublicamente)
}
