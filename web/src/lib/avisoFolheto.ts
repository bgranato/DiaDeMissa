export const CHAVE_FECHAMENTO_AVISO_FOLHETO = '@missa_aviso_folheto_fechado_em'
export const PAUSA_AVISO_FOLHETO_MS = 15 * 60 * 1000

/**
 * O aviso é avaliado somente quando a tela da missa é criada. Fechá-lo não
 * agenda uma nova abertura: ele volta apenas numa nova entrada após a pausa.
 */
export function deveExibirAvisoFolheto(fechadoEm: string | null, agora = Date.now()) {
  const instanteFechamento = Number(fechadoEm)
  return !Number.isFinite(instanteFechamento)
    || instanteFechamento <= 0
    || agora - instanteFechamento >= PAUSA_AVISO_FOLHETO_MS
}
