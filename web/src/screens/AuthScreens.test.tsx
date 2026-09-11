import { describe, expect, it } from 'vitest'
import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'

import { AuthProvider } from '../contexts/AuthContext'
import { AuthScreens } from './AuthScreens'

describe('aviso de conteúdo restrito', () => {
  it('orienta o visitante que tentou abrir uma área exclusiva', () => {
    render(
      <AuthProvider>
        <AuthScreens conteudoRestrito setScreen={() => {}} onClose={() => {}} />
      </AuthProvider>,
    )

    expect(screen.getByText('Conteúdo restrito à usuários cadastrados.')).toBeInTheDocument()
    expect(screen.getByText('Cadastre-se gratuitamente ou faça login para acessar.')).toBeInTheDocument()
  })

  it('não mostra o aviso quando a pessoa abre o login por escolha própria', () => {
    render(
      <AuthProvider>
        <AuthScreens setScreen={() => {}} onClose={() => {}} />
      </AuthProvider>,
    )

    expect(screen.queryByText('Conteúdo restrito à usuários cadastrados.')).not.toBeInTheDocument()
  })
})
