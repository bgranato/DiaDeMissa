const COOLDOWN_KEY = '@dia_de_missa_apoio_reexibir_em'
const PAUSA_APOS_PAGAMENTO_MS = 24 * 60 * 60 * 1000
const PAUSA_APOS_RECUSA_MS = 60 * 60 * 1000

export function conviteApoioEmPausa() {
  const ate = Number(localStorage.getItem(COOLDOWN_KEY) || 0)
  // Migração da regra antiga, que gravava 30 dias antes mesmo de haver
  // pagamento. Nenhuma pausa persistida pode ultrapassar a nova política.
  if (Number.isFinite(ate) && ate > Date.now() + PAUSA_APOS_PAGAMENTO_MS) {
    localStorage.removeItem(COOLDOWN_KEY)
    return false
  }
  return Number.isFinite(ate) && ate > Date.now()
}

/** A pausa só é registrada após confirmação server-side do pagamento. */
export function pausarConviteApoioAposPagamento() {
  localStorage.setItem(COOLDOWN_KEY, String(Date.now() + PAUSA_APOS_PAGAMENTO_MS))
}

/** Fechar a oferta é uma recusa temporária: ela volta a ficar disponível em uma hora. */
export function pausarConviteApoioAposRecusa() {
  localStorage.setItem(COOLDOWN_KEY, String(Date.now() + PAUSA_APOS_RECUSA_MS))
}
