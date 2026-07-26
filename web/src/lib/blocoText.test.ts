import { describe, it, expect } from 'vitest'
import { rotuloRubrica, tituloDuplicaTexto, ehVivencia, parseLeiturasSemana } from './blocoText'

describe('A1 — rubrica não re-parentesada', () => {
  it('não envolve texto que já começa com ( e termina com )', () => {
    expect(rotuloRubrica('(Momento de silêncio)')).toBe('(Momento de silêncio)')
    expect(rotuloRubrica('(Outras intenções)')).toBe('(Outras intenções)')
    expect(rotuloRubrica('  (O Presidente continua)  ')).toBe('(O Presidente continua)')
  })
  it('envolve texto sem parênteses', () => {
    expect(rotuloRubrica('Momento de silêncio')).toBe('(Momento de silêncio)')
  })
  it('nunca gera parênteses duplicados', () => {
    expect(rotuloRubrica('(Momento de silêncio)')).not.toContain('((')
  })
})

describe('A4 — título ≈ texto', () => {
  it('detecta título igual ao texto (ignora pontuação/caixa)', () => {
    expect(tituloDuplicaTexto('Momento de silêncio para oração pessoal',
                              'Momento de silêncio para oração pessoal.')).toBe(true)
  })
  it('detecta título como prefixo do texto', () => {
    expect(tituloDuplicaTexto('Vivência', 'Vivência: algo mais aqui')).toBe(true)
  })
  it('não marca quando o texto é diferente', () => {
    expect(tituloDuplicaTexto('Vivência',
                              'Vivenciar o Reino dos Céus é permitir...')).toBe(false)
  })
  it('vazio → false', () => {
    expect(tituloDuplicaTexto('', 'x')).toBe(false)
    expect(tituloDuplicaTexto('x', '')).toBe(false)
  })
})

describe('A5 — Vivência', () => {
  it('reconhece o título Vivência', () => {
    expect(ehVivencia('Vivência')).toBe(true)
    expect(ehVivencia('vivencia')).toBe(true)
  })
  it('não marca outros títulos', () => {
    expect(ehVivencia('Homilia')).toBe(false)
  })
})

describe('A6 — Leituras da Semana (parser tolerante)', () => {
  // Caso REAL de 26/07: a 5ª-FEIRA vem SEM "30/" e grudava na Qua. 29.
  const TEXTO_2607 =
    "27/2ª-FEIRA: Jr 13, 1-11; Dt 32,18-19; Mt 13,31-55; " +
    "28/3ª-FEIRA: Jr 14,17-22; Sl 78; Mt 13,36-43; " +
    "29/4ª-FEIRA: Santos Marta, Maria e Lázaro, memória: 1Jo 4,7-16; Sl 33; Jo 11,19-27 ou Lc 10,38-42; " +
    "5ª-FEIRA: São Pedro Crisólogo, bispo e doutor da Igreja: Jr 18,1-6; Sl 145; Mt 13,47-53; " +
    "31/6ª-FEIRA: Santo Inácio de Loyola, presbítero, memória: Jr 26,1-9; Sl 68; Mt 13,54-58; " +
    "01/SÁBADO: Santo Afonso, memória: Jr 26,11-16.24; Sl 68; Mt 14,1-12."

  it('abre a 5ª-FEIRA em card próprio mesmo sem "30/", inferindo o dia 30', () => {
    const dias = parseLeiturasSemana(TEXTO_2607)
    expect(dias).not.toBeNull()
    expect(dias!.length).toBe(6)               // 27,28,29,30(inferido),31,01
    const quinta = dias!.find(d => d.label.startsWith('Qui'))
    expect(quinta).toBeDefined()
    expect(quinta!.label).toBe('Qui. 30')      // número inferido de 29+1
    expect(quinta!.santo).toContain('São Pedro Crisólogo')
    // e a Qua. 29 NÃO contém mais a quinta-feira embutida
    const quarta = dias!.find(d => d.label === 'Qua. 29')!
    expect(quarta.refs).not.toContain('São Pedro Crisólogo')
  })

  it('parseia normalmente quando todos os dias têm número', () => {
    const dias = parseLeiturasSemana("20/2ª-FEIRA: A: X; 21/3ª-FEIRA: B: Y")
    expect(dias!.map(d => d.label)).toEqual(['Seg. 20', 'Ter. 21'])
  })

  it('retorna null quando não há pelo menos 2 dias', () => {
    expect(parseLeiturasSemana('texto qualquer sem dias')).toBeNull()
  })
})
