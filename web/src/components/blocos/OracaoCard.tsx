import { Oracao } from '../../types/missa.nova'
import { PosturaChip } from './Shared'

export default function OracaoCard({ bloco }: { bloco: Oracao }) {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <h3 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>{bloco.titulo}</h3>
        <PosturaChip postura={bloco.postura} />
      </div>

      <p style={{ lineHeight: 1.8, marginBottom: 12, fontStyle: 'italic' }}>
        {bloco.texto}
      </p>

      {bloco.resposta && (
        <p style={{
          fontWeight: 700, fontSize: 18,
          borderTop: '1px solid var(--border, #E5E7EB)',
          paddingTop: 12, marginTop: 12,
        }}>
          {bloco.resposta}
        </p>
      )}
    </div>
  )
}
