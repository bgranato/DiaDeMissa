import { Dialogo } from '../../types/missa.nova'
import { PosturaChip } from './Shared'

const FALANTE_CORES: Record<string, string> = {
  'P': '#0F2A4A',
  'T': '#374151',
  'L': '#B48A00',
  'V': '#0F2A4A',
  'R': '#374151',
}

export default function DialogoCard({ bloco }: { bloco: Dialogo }) {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <h3 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>{bloco.titulo}</h3>
        <PosturaChip postura={bloco.postura} />
      </div>

      {bloco.turnos.map((turno, i) => (
        <div key={i} style={{
          display: 'flex', gap: 12, marginBottom: 8,
          paddingLeft: turno.falante === 'T' || turno.falante === 'R' ? 32 : 0,
        }}>
          <span style={{
            fontWeight: 700, fontSize: 14,
            color: FALANTE_CORES[turno.falante] || '#374151',
            minWidth: 24,
            textTransform: 'uppercase',
          }}>
            {turno.falante}.
          </span>
          <p style={{ margin: 0, lineHeight: 1.6 }}>{turno.texto}</p>
        </div>
      ))}
    </div>
  )
}
