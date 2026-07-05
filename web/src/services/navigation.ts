// Navegador global leve: permite que componentes globais (ex.: a sineta de
// notificações no AppHeader) troquem de tela sem precisar receber setScreen por
// prop em cada uso. O App registra a função de navegação uma vez.
let _navegar: ((tela: string) => void) | null = null

export function registrarNavegador(fn: (tela: string) => void) {
  _navegar = fn
}

export function navegarPara(tela: string) {
  if (_navegar) _navegar(tela)
}
