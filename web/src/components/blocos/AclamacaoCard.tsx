import { Aclamacao } from '../../types/missa.nova'
import { PosturaChip } from './Shared'

export default function AclamacaoCard({ bloco }: { bloco: Aclamacao }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginBottom: 12 }}>
        <PosturaChip postura={bloco.postura} />
      </div>

      {bloco.refrao.map((v, i) => (
        <p key={i} style={{
          fontSize: 24, fontWeight: 900, fontStyle: 'italic',
          color: 'var(--color-brand-gold, #B48A00)',
          margin: '4px 0',
        }}>
          {v}
        </p>
      ))}

      <p style={{ marginTop: 16, lineHeight: 1.6, fontStyle: 'italic' }}>
        {bloco.versiculo}
      </p>
    </div>
  )
}
