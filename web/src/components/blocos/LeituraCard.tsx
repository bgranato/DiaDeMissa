import { Leitura } from '../../types/missa.nova'
import { PosturaChip } from './Shared'

export default function LeituraCard({ bloco }: { bloco: Leitura }) {
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

      {bloco.introducao && (
        <p style={{ fontStyle: 'italic', color: 'var(--color-brand-gray-dark, #6B7280)', marginBottom: 12 }}>
          {bloco.introducao}
        </p>
      )}

      <div style={{ lineHeight: 1.8, marginBottom: 12 }}>
        {bloco.texto.split('\n\n').map((par, i) => (
          <p key={i} style={{ marginBottom: 8 }}>{par}</p>
        ))}
      </div>

      {bloco.conclusao && (
        <p style={{ fontWeight: 600, fontStyle: 'italic', marginTop: 8 }}>
          {bloco.conclusao}
        </p>
      )}
    </div>
  )
}
