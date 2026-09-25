/**
 * O aviso sobre o conteúdo litúrgico SEMPRE aparece ao entrar numa missa:
 * saiu e voltou, o aviso abre novamente. Não há pausa nem estado persistente
 * de fechamento — fechar é apenas fechar a janela da vez.
 */
export function deveExibirAvisoFolheto(_fechadoEm: string | null = null) {
  return true
}