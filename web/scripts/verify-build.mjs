// Trava de regressão de DEPLOY: falha se o bundle não inicializa o Google
// Identity Services. O deploy b72e030 quebrou o login por ter sido buildado
// SEM VITE_GOOGLE_CLIENT_ID — este check impede que isso volte a passar batido.
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

const ASSETS = 'dist/assets'
let js = ''
try {
  for (const f of readdirSync(ASSETS)) {
    if (f.endsWith('.js')) js += readFileSync(join(ASSETS, f), 'utf8')
  }
} catch (e) {
  console.error('✗ verify-build: dist/assets ausente — rode `vite build` antes.', e.message)
  process.exit(1)
}

const erros = []
if (!js.includes('gsi/client')) {
  erros.push('script do Google Identity Services (accounts.google.com/gsi/client) não está no bundle')
}
if (!/\d{6,}-[a-z0-9]+\.apps\.googleusercontent\.com/.test(js)) {
  erros.push('VITE_GOOGLE_CLIENT_ID ausente no bundle (build sem .env.production?)')
}

if (erros.length) {
  console.error('✗ verify-build FALHOU — login Google quebraria em produção:')
  for (const e of erros) console.error('   - ' + e)
  console.error('   Corrija o ambiente de build (web/.env.production com VITE_GOOGLE_CLIENT_ID) e rebuilde.')
  process.exit(1)
}
console.log('✓ verify-build OK: GIS (gsi/client) e VITE_GOOGLE_CLIENT_ID presentes no bundle.')
