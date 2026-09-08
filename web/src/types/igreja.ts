export interface Igreja {
  id: number
  nome: string
  endereco: string | null
  cidade: string | null
  estado: string | null
  cep: string | null
  telefone: string | null
  site: string | null
  lat: number | null
  lng: number | null
  observacoes: string | null
  horarios_missa: string | null
  data_criacao: string
  favorita: boolean
  distancia_km: number | null
}
