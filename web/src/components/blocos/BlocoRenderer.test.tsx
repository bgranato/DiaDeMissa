import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import BlocoRenderer from './BlocoRenderer'
import { ordenarBlocos } from '../../lib/blocoText'

describe('A5 — Vivência exibe chip L', () => {
  it('renderiza o chip "L" para o bloco Vivência', () => {
    const bloco = { tipo: 'oracao', titulo: 'Vivência', texto: 'Vivenciar o Reino dos Céus é permitir a alegria...' }
    const { container } = render(<BlocoRenderer bloco={bloco} />)
    const chipL = Array.from(container.querySelectorAll('span'))
      .filter(s => s.textContent === 'L' && s.className.includes('rounded-full'))
    expect(chipL.length).toBe(1)
    expect(screen.getByText(/Vivenciar o Reino dos Céus/)).toBeInTheDocument()
  })
})

describe('A4 — título ≈ texto não duplica (estilo rubrica)', () => {
  it('renderiza o texto uma vez, em itálico/rubrica, sem parágrafo de corpo em negrito', () => {
    const bloco = {
      tipo: 'oracao',
      titulo: 'Momento de silêncio para oração pessoal',
      texto: 'Momento de silêncio para oração pessoal.',
    }
    const { container } = render(<BlocoRenderer bloco={bloco} />)
    const el = screen.getByText('Momento de silêncio para oração pessoal.')
    expect(el).toBeInTheDocument()
    expect(el.className).toContain('italic')
    // aparece uma única vez
    expect(container.querySelectorAll('p').length).toBe(1)
  })
})

describe('A3 — ordenação estrita por `ordem`', () => {
  it('ordena os blocos pelo campo ordem (silêncio antes da antífona)', () => {
    const blocos = [
      { ordem: 25, titulo: 'Antífona da Comunhão' },
      { ordem: 24, titulo: 'Momento de silêncio' },
      { ordem: 23, titulo: 'Canto de Comunhão' },
    ]
    const out = ordenarBlocos(blocos).map(b => b.titulo)
    expect(out).toEqual(['Canto de Comunhão', 'Momento de silêncio', 'Antífona da Comunhão'])
  })
})
