/**
 * Travamento de rolagem da página com contador de referências.
 *
 * Modais e telas modais ("div de aviso", login, apoio, agradecimento) seguram
 * o scroll da página enquanto estão visíveis. Como os modais podem se
 * sobrepor (ex.: login fechando enquanto o aviso do folheto abre), o travamento
 * precisa ser aninhado e não pode capturar o valor de overflow de outro lock
 * em andamento — senão, ao desmontar, restaura um valor obsoleto e deixa a
 * página travada.
 *
 * Contrato:
 * - `travarRolagem()` trava na primeira chamada e guarda o valor ORIGINAL do
 *   overflow (o que existia antes de qualquer lock).
 * - Chamadas aninhadas apenas incrementam o contador interno.
 * - `destravarRolagem()` só restaura o overflow original quando a ÚLTIMA
 *   referência é liberada (contador volta a zero).
 */

let referencias = 0
let overflowOriginalBody = ''
let overflowOriginalHtml = ''

export function travarRolagem() {
  if (referencias === 0) {
    overflowOriginalBody = document.body.style.overflow
    overflowOriginalHtml = document.documentElement.style.overflow
    document.body.style.overflow = 'hidden'
    document.documentElement.style.overflow = 'hidden'
  }
  referencias += 1
}

export function destravarRolagem() {
  if (referencias === 0) return
  referencias -= 1
  if (referencias === 0) {
    document.body.style.overflow = overflowOriginalBody
    document.documentElement.style.overflow = overflowOriginalHtml
  }
}