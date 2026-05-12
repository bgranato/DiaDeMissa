import { Postura } from '../types/missa.nova'

const POSTURA_LABEL: Record<string, string> = {
  'de_pe': 'De pé',
  'sentado': 'Sentado',
  'ajoelhado': 'Ajoelhado',
}

const POSTURA_ICON: Record<string, string> = {
  'de_pe': '🙏',
  'sentado': '🪑',
  'ajoelhado': '🧎',
}

export function PosturaChip({ postura }: { postura: Postura }) {
  if (!postura) return null
  const icons: Record<string, string> = { de_pe: '🙏', sentado: '🪑', ajoelhado: '🧎' }
  const labels: Record<string, string> = { de_pe: 'De pé', sentado: 'Sentado', ajoelhado: 'Ajoelhado' }
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '4px 14px', borderRadius: 999,
      fontSize: 12, fontWeight: 700,
      background: 'rgba(180,138,0,0.1)',
      color: '#B48A00',
    }}>
      <span>{icons[postura] || '•'}</span>
      <span>{labels[postura] || postura}</span>
    </span>
  )
}

export function RefraoBlock({ versos, className = '' }: { versos: string[], className?: string }) {
  return (
    <div className={className} style={{
      borderLeft: '3px solid var(--color-brand-gold, #B48A00)',
      paddingLeft: 16, margin: '12px 0',
      fontStyle: 'italic', fontWeight: 600,
    }}>
      {versos.map((v, i) => <p key={i} style={{ marginBottom: 2 }}>{v}</p>)}
    </div>
  )
}

export function CreditosBar({ creditos }: { creditos: { entrada?: string | null; ofertas?: string | null; comunhao?: string | null; final?: string | null } | undefined | null }) {
  if (!creditos) return null
  const parts: string[] = []
  if (creditos.entrada) parts.push(`Entrada: ${creditos.entrada}`)
  if (creditos.ofertas) parts.push(`Ofertas: ${creditos.ofertas}`)
  if (creditos.comunhao) parts.push(`Comunhão: ${creditos.comunhao}`)
  if (creditos.final) parts.push(`Final: ${creditos.final}`)
  if (!parts.length) return null
  return (
    <div style={{ marginTop: 16, fontSize: 13, color: 'var(--color-brand-gray-dark, #6B7280)' }}>
      {parts.map((p, i) => <p key={i}>{p}</p>)}
    </div>
  )
}
