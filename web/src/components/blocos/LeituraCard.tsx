import { PosturaChip } from './Shared'

export default function LeituraCard({ bloco }: { bloco: any }) {
  const versiculos = bloco.versiculos || []
  const temVersiculos = Array.isArray(versiculos) && versiculos.length > 0

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        <h3 style={{ margin: 0, fontSize: 24, fontWeight: 700, fontFamily: 'Georgia, serif' }}>{bloco.titulo}</h3>
        {bloco.referencia && (
          <span style={{ padding: '2px 10px', borderRadius: 20, fontSize: 12, fontWeight: 700, background: '#0F2A4A', color: '#fff' }}>
            {bloco.referencia}
          </span>
        )}
        <PosturaChip postura={bloco.postura} />
      </div>

      {bloco.introducao && (
        <p style={{ fontStyle: 'italic', color: '#6B7280', fontSize: 16, marginBottom: 16, lineHeight: 1.5 }}>
          {bloco.introducao}
        </p>
      )}

      {temVersiculos ? (
        <div style={{ lineHeight: 2, fontSize: 16 }}>
          {versiculos.map((v: any, i: number) => (
            <span key={i}>
              <sup style={{ fontSize: 11, color: '#9CA3AF', fontWeight: 600, marginRight: 2 }}>{v.numero}</sup>
              <span>{v.texto} </span>
            </span>
          ))}
        </div>
      ) : bloco.texto ? (
        <div style={{ lineHeight: 1.8, fontSize: 16 }}>
          {bloco.texto.split('\n\n').map((par: string, i: number) => (
            <p key={i} style={{ marginBottom: 8 }}>{par}</p>
          ))}
        </div>
      ) : null}

      {bloco.conclusao && (
        <p style={{ fontWeight: 600, fontStyle: 'italic', marginTop: 16, fontSize: 16, color: '#374151' }}>
          {bloco.conclusao}
        </p>
      )}
      {bloco.resposta && (
        <p style={{ fontWeight: 700, fontSize: 15, marginTop: 4, color: '#B48A00' }}>
          {bloco.resposta}
        </p>
      )}
    </div>
  )
}
