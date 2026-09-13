const COOLDOWN_KEY = '@dia_de_missa_apoio_reexibir_em'
const COOLDOWN_REASON_KEY = '@dia_de_missa_apoio_pausa_motivo'
const PAUSA_APOS_PAGAMENTO_MS = 24 * 60 * 60 * 1000

function limparPausa() {
  localStorage.removeItem(COOLDOWN_KEY)
  localStorage.removeItem(COOLDOWN_REASON_KEY)
}

export function conviteApoioEmPausa() {
  const ate = Number(localStorage.getItem(COOLDOWN_KEY) || 0)
  // Antes esta chave também registrava a recusa. Como não havia a origem da
  // pausa, um valor legado não pode impedir um novo convite: só pagamentos
  // confirmados a partir desta regra têm descanso de 24 horas.
  if (localStorage.getItem(COOLDOWN_REASON_KEY) !== 'pagamento') {
    limparPausa()
    return false
  }
  if (!Number.isFinite(ate) || ate <= Date.now() || ate > Date.now() + PAUSA_APOS_PAGAMENTO_MS) {
    limparPausa()
    return false
  }
  return true
}

/** A pausa só é registrada após confirmação server-side do pagamento. */
export function pausarConviteApoioAposPagamento() {
  localStorage.setItem(COOLDOWN_KEY, String(Date.now() + PAUSA_APOS_PAGAMENTO_MS))
  localStorage.setItem(COOLDOWN_REASON_KEY, 'pagamento')
}
