const COOLDOWN_KEY = '@dia_de_missa_apoio_reexibir_em'
const PAUSA_APOS_PAGAMENTO_MS = 24 * 60 * 60 * 1000

export function conviteApoioEmPausa() {
  const ate = Number(localStorage.getItem(COOLDOWN_KEY) || 0)
  return Number.isFinite(ate) && ate > Date.now()
}

/** A pausa só é registrada após confirmação server-side do pagamento. */
export function pausarConviteApoioAposPagamento() {
  localStorage.setItem(COOLDOWN_KEY, String(Date.now() + PAUSA_APOS_PAGAMENTO_MS))
}
