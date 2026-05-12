import { PosturaChip } from './Shared'

export default function CantoCard({ bloco }: { bloco: any }) {
  const temEstruturaNova = Array.isArray(bloco.refrao) || Array.isArray(bloco.estrofes)
  const conteudo = bloco.conteudo || ''
  const linhas = conteudo ? conteudo.split('\n\n') : []

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <h3 style={{ margin: 0, fontSize: 24, fontWeight: 700, fontFamily: 'Georgia, serif' }}>{bloco.titulo}</h3>
        <PosturaChip postura={bloco.postura} />
      </div>

      {temEstruturaNova ? (
        <>
          {(bloco.refrao || []).length > 0 && (
            <div style={{ background: 'linear-gradient(to right, rgba(180,138,0,0.07), transparent)', borderRadius: 16, padding: 24, borderLeft: '4px solid #B48A00', marginBottom: 16 }}>
              <span style={{ fontSize: 10, fontWeight: 700, color: '#B48A00', textTransform: 'uppercase', letterSpacing: '0.3em', display: 'block', marginBottom: 12 }}>REFRÃO</span>
              {(bloco.refrao || []).map((v: string, i: number) => (
                <p key={i} style={{ fontSize: 18, fontWeight: 600, fontStyle: 'italic', lineHeight: 1.6, margin: '2px 0' }}>{v}</p>
              ))}
            </div>
          )}
          {(bloco.estrofes || []).map((estrofe: string[], ei: number) => (
            <div key={ei} style={{ background: 'white', border: '1px solid #eee', padding: 20, marginBottom: 12, borderRadius: 8 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                <span style={{ width: 32, height: 32, borderRadius: '50%', background: 'rgba(15,42,74,0.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, fontWeight: 700, color: '#0F2A4A' }}>{ei + 1}</span>
                <span style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: '0.3em' }}>ESTROFE</span>
              </div>
              {estrofe.map((verso, vi) => (
                <p key={vi} style={{ fontSize: 15, lineHeight: 1.6, margin: '3px 0' }}>{verso}</p>
              ))}
            </div>
          ))}
        </>
      ) : (
        <div style={{ lineHeight: 1.8, fontSize: 16 }}>
          {linhas.map((par: string, i: number) => (
            <p key={i} style={{ marginBottom: 8 }}>{par}</p>
          ))}
        </div>
      )}
    </div>
  )
}
