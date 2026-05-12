import { Salmo } from '../../types/missa.nova'
import { PosturaChip, RefraoBlock } from './Shared'

export default function SalmoCard({ bloco }: { bloco: Salmo }) {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
        <h3 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>{bloco.titulo}</h3>
        {bloco.referencia && (
          <span style={{
            padding: '2px 10px', borderRadius: 20, fontSize: 12, fontWeight: 700,
            background: 'var(--color-brand-blue, #0F2A4A)', color: '#fff',
          }}>
            {bloco.referencia}
          </span>
        )}
        <PosturaChip postura={bloco.postura} />
      </div>

      {bloco.refrao.length > 0 && (
        <div>
          <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--color-brand-gold, #B48A00)', textTransform: 'uppercase' }}>R.</span>
          <RefraoBlock versos={bloco.refrao} />
        </div>
      )}

      {bloco.estrofes.map((estrofe, ei) => (
        <div key={ei} style={{ marginBottom: 12 }}>
          {estrofe.map((verso, vi) => (
            <p key={vi} style={{ margin: '2px 0', lineHeight: 1.6 }}>{verso}</p>
          ))}
        </div>
      ))}
    </div>
  )
}
