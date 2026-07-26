import { describe, it, expect } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { DialogoCard } from './DialogoCard'

describe('A2 — turnos do mesmo falante em parágrafos separados', () => {
  it('não funde turnos consecutivos do mesmo falante (Consagração)', () => {
    const dialogo = {
      turnos: [
        { falante: 'P', texto: 'Na noite em que ia ser entregue, tomou o pão...' },
        { falante: 'P', texto: 'Do mesmo modo, ao fim da ceia, tomou o cálice...' },
        { falante: 'P', texto: 'Fazei isto em memória de mim.' },
      ],
    }
    render(<DialogoCard dialogo={dialogo} />)
    // cada turno é um <p> próprio → 3 parágrafos distintos
    expect(screen.getByText(/Na noite em que ia ser entregue/)).toBeInTheDocument()
    expect(screen.getByText(/Do mesmo modo, ao fim da ceia/)).toBeInTheDocument()
    expect(screen.getByText(/Fazei isto em memória de mim/)).toBeInTheDocument()
    // não pode haver um único parágrafo com os três textos fundidos
    const fundido = screen.queryByText(
      /Na noite.*Do mesmo modo.*Fazei isto/s
    )
    expect(fundido).toBeNull()
  })

  it('chip do falante só aparece no primeiro turno da sequência repetida', () => {
    const dialogo = {
      turnos: [
        { falante: 'P', texto: 'Primeira fala do padre.' },
        { falante: 'P', texto: 'Segunda fala do padre.' },
        { falante: 'T', texto: 'Resposta de todos.' },
      ],
    }
    const { container } = render(<DialogoCard dialogo={dialogo} />)
    // chips de TURNO são w-5 (a legenda usa w-4). O "P" deve aparecer 1x (só no
    // 1º turno da sequência), não 2x.
    const chipTurno = (label: string) => Array.from(container.querySelectorAll('span'))
      .filter(s => s.textContent === label && s.className.includes('rounded-full') && s.className.includes('w-5'))
    expect(chipTurno('P').length).toBe(1)
    expect(chipTurno('T').length).toBe(1)
  })
})

describe('A1 — rubrica com um par de parênteses no componente', () => {
  it('rubrica já parentesada não vira ((...))', () => {
    render(<DialogoCard dialogo={{ turnos: [{ falante: 'rubrica', texto: '(Momento de silêncio)' }] }} />)
    expect(screen.getByText('(Momento de silêncio)')).toBeInTheDocument()
    expect(screen.queryByText('((Momento de silêncio))')).toBeNull()
  })
})
